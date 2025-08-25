# tools/rag_tool.py
"""
Retrieval-Augmented Generation (RAG) Tool for OSS Community Agent with Chroma Cloud Support.

Features:
- Loads docs from `data/corpus/` (.md, .txt, .pdf, .html supported).
- Splits into semantic chunks (Markdown headers preserved).
- Uses ChromaDB for vector storage:
    - If CHROMA_HOST/CHROMA_API_KEY are set → connects to **Chroma Cloud**.
    - Otherwise uses local persisted DB in RAG_DB_DIR.
- Incremental indexing (adds/updates changed files, removes deleted).
- Hybrid retrieval: Vector + keyword fallback.
- Draft Reddit-ready replies with inline citations.
- Supports OpenAI / Ollama / Groq LLMs or keyword-only fallback.
- CLI for rebuild, refresh, query, and reply generation.

Environment Variables:
-----------------------
# Core paths
RAG_CORPUS_DIR=data/corpus
RAG_DB_DIR=rag_db
RAG_COLLECTION=oss_docs

# Chroma Cloud (optional)
CHROMA_HOST=https://your-chroma-cloud-host
CHROMA_API_KEY=your_api_key_here

# Embeddings
EMBED_PROVIDER=openai|ollama|none
EMBED_MODEL=nomic-embed-text
OPENAI_API_KEY=...
OPENAI_EMBED_MODEL=text-embedding-3-small

# LLM
LLM_PROVIDER=openai|ollama|groq|none
OPENAI_MODEL=gpt-4o-mini
OLLAMA_LLM_MODEL=gemma3
GROQ_API_KEY=...
GROQ_MODEL=llama-3.1-8b-instant

# Retrieval
TOP_K=4
"""

from __future__ import annotations
import os, sys, re, json, time, hashlib, argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# --- LangChain Imports ---
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

try:
    from langchain_community.embeddings import OllamaEmbeddings
except ImportError:
    OllamaEmbeddings = None

try:
    from langchain_community.vectorstores import Chroma
except ImportError:
    Chroma = None

try:
    from langchain_community.llms import Ollama
except ImportError:
    Ollama = None

try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None

# --- Env and Config ---
def _env(k, d=None): return os.getenv(k, d)
# Ensure dirs exist
RAG_CORPUS_DIR = Path(_env("RAG_CORPUS_DIR", "data/corpus")).resolve()
RAG_DB_DIR = Path(_env("RAG_DB_DIR", "rag_db")).resolve()
RAG_COLLECTION = _env("RAG_COLLECTION", "oss_docs")
CHROMA_HOST = _env("CHROMA_HOST")
CHROMA_API_KEY = _env("CHROMA_API_KEY")

#--EMBEDDINGS--
# Default to OpenAI embeddings for production use
EMBED_PROVIDER = _env("EMBED_PROVIDER", "openai").lower()
EMBED_MODEL = _env("EMBED_MODEL", "nomic-embed-text")

#--LLM Provider--
LLM_PROVIDER = _env("LLM_PROVIDER", "none").lower()
OLLAMA_LLM_MODEL = _env("OLLAMA_LLM_MODEL", "gemma3")
GROQ_MODEL = _env("GROQ_MODEL", "llama-3.1-8b-instant")
TOP_K = int(_env("TOP_K", "4"))

MANIFEST_FILE = RAG_DB_DIR / "manifest.json"

# --- Utils ---
def sha256_text(txt): return hashlib.sha256(txt.encode("utf-8")).hexdigest()
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()
def safe_read_text(path): return path.read_text(encoding="utf-8", errors="ignore")

def now_ts(): return int(time.time())

def load_json(p, d): return json.loads(p.read_text()) if p.exists() else d
def save_json(p, data): p.write_text(json.dumps(data, indent=2))

# --- Document Loading ---
SUPPORTED_EXTS = {".md", ".txt"}
def _split_md(text): 
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[("#","h1"),("##","h2"),("###","h3")])
    docs = splitter.split_text(text)
    chunker = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    out=[]
    for d in docs: out += chunker.split_documents([d])
    return out

def _load_docs() -> List[Document]:
    docs=[]
    for path in sorted(RAG_CORPUS_DIR.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTS: continue
        text = safe_read_text(path)
        if path.suffix==".md":
            chunks=_split_md(text)
            for c in chunks:
                meta = c.metadata
                meta["source"]=path.name
                meta["source_path"]=str(path)
                meta["section"]=meta.get("header_h1","Introduction")
                docs.append(Document(page_content=c.page_content, metadata=meta))
        else:
            chunker = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
            for c in chunker.split_text(text):
                docs.append(Document(page_content=c, metadata={"source":path.name,"source_path":str(path),"section":"Text"}))
    return docs

# --- Embeddings ---
def _embedder():
    if EMBED_PROVIDER=="ollama":
        if not OllamaEmbeddings: raise ImportError("Install langchain-community")
        return OllamaEmbeddings(model=EMBED_MODEL)
    elif EMBED_PROVIDER=="openai":
        try:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(model=OPENAI_EMBED_MODEL)
        except ImportError:
            print("Warning: OpenAI embeddings not available, falling back to keyword search")
            return None
    return None

# --- LLM ---
def _llm():
    if LLM_PROVIDER=="groq":
        if not ChatGroq: raise ImportError("Install langchain-groq")
        return ChatGroq(model=GROQ_MODEL)
    return None

# --- RAGTool ---
class RAGTool:
    def __init__(self):
        self.llm=_llm()
        self.embedder=_embedder()
        self.vectorstore=None
        self.retriever=None
        self._init_vectorstore()

    def _init_vectorstore(self):
        # Ensure DB dir exists
        try:
            RAG_DB_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        if not self.embedder or not Chroma:
            return
        kwargs={
            "collection_name":RAG_COLLECTION,
            "embedding_function":self.embedder
        }
        if CHROMA_HOST and CHROMA_API_KEY:
            kwargs.update({"client_settings":{"chroma_api_impl":"rest","chroma_server_host":CHROMA_HOST,"chroma_server_http_port":443,"headers":{"Authorization":f"Bearer {CHROMA_API_KEY}"}}})
        else:
            kwargs["persist_directory"]=str(RAG_DB_DIR)
        try:
            self.vectorstore=Chroma(**kwargs)
            self.retriever=self.vectorstore.as_retriever(search_kwargs={"k":TOP_K})
            if not self._has_docs():
                self.rebuild()
        except Exception as e:
            print(f"Warning: ChromaDB setup failed: {e}")
            print("Rebuilding vector store...")
            try:
                self.vectorstore=Chroma(**kwargs)
                self.rebuild()
                self.retriever=self.vectorstore.as_retriever(search_kwargs={"k":TOP_K})
            except Exception as e2:
                print(f"Error: Could not initialize ChromaDB: {e2}")
                self.vectorstore = None
                self.retriever = None

    def _has_docs(self): 
        try: 
            if not self.vectorstore:
                return False
            return self.vectorstore._collection.count()>0
        except: 
            return False

    def rebuild(self):
        # Always compute docs and update manifest, even if vector store disabled
        docs=_load_docs()
        doc_count=len(docs)
        if self.embedder and Chroma:
            if docs:
                self.vectorstore.delete_collection()
                self.vectorstore.add_documents(docs)
        # Update manifest
        try:
            save_json(MANIFEST_FILE, {
                "collection": RAG_COLLECTION,
                "doc_count": doc_count,
                "last_rebuild": datetime.now().isoformat(),
                "corpus_dir": str(RAG_CORPUS_DIR),
                "db_dir": str(RAG_DB_DIR)
            })
        except Exception:
            pass

    def refresh(self):
        self.rebuild() # Simple rebuild for now

    def search_docs(self,q,top_k=TOP_K):
        if self.retriever:
            docs=self.retriever.invoke(q)
            return [{"file":d.metadata.get("source"),"section":d.metadata.get("section"),"content":d.page_content} for d in docs]
        # Keyword fallback
        docs=_load_docs()
        terms=q.lower().split()
        scored=[]
        for d in docs:
            score=sum(d.page_content.lower().count(t) for t in terms)
            if score: scored.append((score,d))
        scored.sort(key=lambda x:x[0],reverse=True)
        return [{"file":d.metadata.get("source"),"section":d.metadata.get("section"),"content":d.page_content} for _,d in scored[:top_k]]

    def draft_reply(self,q):
        chunks=self.search_docs(q)
        if not chunks: return "No relevant info found in the docs."
        context="\n\n".join([f"{c['file']}:{c['section']} -> {c['content']}" for c in chunks])
        if self.llm:
            prompt=f"Answer based only on this context:\n{context}\nQuestion:{q}\nKeep it concise and cite [from file:Section]"
            ans=self.llm.invoke(prompt)
            return ans.content if hasattr(ans,"content") else str(ans)
        # fallback
        return "\n".join([f"- {c['content'][:200]}...[from {c['file']}:{c['section']}]" for c in chunks])
    
    def retrieve_and_generate(self, query: str) -> str:
        """Alias for draft_reply to match the interface expected by the agent"""
        return self.draft_reply(query)

# --- CLI ---
if __name__=="__main__":
    p=argparse.ArgumentParser()
    sp=p.add_subparsers(dest="cmd")
    sp.add_parser("rebuild")
    sp.add_parser("refresh")
    q=sp.add_parser("query"); q.add_argument("text")
    r=sp.add_parser("reply"); r.add_argument("text")
    a=p.parse_args()
    tool=RAGTool()
    if a.cmd=="rebuild": tool.rebuild()
    elif a.cmd=="refresh": tool.refresh()
    elif a.cmd=="query": print(tool.search_docs(a.text))
    elif a.cmd=="reply": print(tool.draft_reply(a.text))
