#!/usr/bin/env python3
"""
Simple test to verify RAG tool works with Ollama
"""
import os
import sys
sys.path.append('.')

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from tools.rag_tool import RAGTool

def test_rag_basic():
    print("🔧 Testing RAG Tool with Ollama...")
    
    # Set environment variables for testing - use OpenAI since it's configured
    os.environ['EMBED_PROVIDER'] = 'openai'
    os.environ['LLM_PROVIDER'] = 'groq'  # Use Groq for LLM since it's configured
    
    try:
        # Initialize RAG tool
        print("⚙️ Initializing RAG tool...")
        rag_tool = RAGTool()
        
        # Test search
        print("🔍 Testing document search...")
        results = rag_tool.search_docs("API documentation")
        print(f"✅ Search returned {len(results)} results")
        
        # Test retrieve and generate
        print("🤖 Testing retrieve and generate...")
        response = rag_tool.retrieve_and_generate("How do I use the API?")
        print(f"✅ Generated response: {response[:100]}...")
        
        print("🎉 RAG tool test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ RAG tool test failed: {e}")
        return False

if __name__ == "__main__":
    test_rag_basic()
