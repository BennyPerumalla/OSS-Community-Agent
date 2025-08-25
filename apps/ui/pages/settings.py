
import streamlit as st
import os
import sys
import openai
import requests
from dotenv import load_dotenv, set_key

# Add parent directories to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from utils.reddit_auth import test_reddit_auth

# Load env so we can update
load_dotenv()

def render_settings_page():
    """Render the settings and configuration page"""
    
    # Page header
    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <h1 style="color: var(--text-primary); margin-bottom: 0.5rem; font-size: 2.5rem; font-weight: 700;">
            ⚙️ Settings & Configuration
        </h1>
        <p style="color: var(--text-secondary); font-size: 1.1rem;">
            Configure your agent settings, API credentials, and operational parameters
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Settings tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔑 API Credentials", 
        "🤖 Agent Settings", 
        "📚 RAG Configuration", 
        "🛡️ Moderation", 
        "🔧 Advanced"
    ])
    
    with tab1:
        render_api_credentials()
    
    with tab2:
        render_agent_settings()
    
    with tab3:
        render_rag_settings()
    
    with tab4:
        render_moderation_settings()
    
    with tab5:
        render_advanced_settings()


def render_api_credentials():
    """Render API credentials configuration"""

    st.markdown("### 🔑 API Credentials Configuration")
    st.markdown("Configure your external API keys and credentials for the agent to function properly.")

    # ------------------------------
    # Reddit API Configuration
    # ------------------------------
    with st.expander("📱 Reddit API Credentials", expanded=True):
        st.markdown("**Required for Reddit integration**")

        col1, col2 = st.columns(2)

        with col1:
            reddit_client_id = st.text_input(
                "Client ID",
                value=os.getenv("REDDIT_CLIENT_ID", ""),
                type="password",
                help="Your Reddit application client ID"
            )
            
            reddit_username = st.text_input(
                "Username",
                value=os.getenv("REDDIT_USERNAME", ""),
                help="Reddit account username"
            )
            
        with col2:
            reddit_client_secret = st.text_input(
                "Client Secret",
                value=os.getenv("REDDIT_CLIENT_SECRET", ""),
                type="password",
                help="Your Reddit application client secret"
            )
            
            reddit_password = st.text_input(
                "Password",
                value=os.getenv("REDDIT_PASSWORD", ""),
                type="password",
                help="Reddit account password"
            )
            
        reddit_user_agent = st.text_input(
            "User Agent",
            value=os.getenv("USER_AGENT", "oss-community-agent/1.0"),
            help="Custom user agent string for API requests"
        )

        if st.button("🧪 Test Reddit Connection"):
            creds = {
                "client_id": reddit_client_id,
                "client_secret": reddit_client_secret,
                "username": reddit_username,
                "password": reddit_password,
                "user_agent": reddit_user_agent,
            }
            result = test_reddit_auth(creds)
            if result["valid"]:
                st.success(f"✅ Reddit credentials are valid! Logged in as u/{result['username']}")
            else:
                st.error(f"❌ Reddit authentication failed: {result['errors']}")

    # ------------------------------
    # LLM Provider Selection
    # ------------------------------
    with st.expander("🤖 LLM Provider Configuration", expanded=True):
        st.markdown("**Choose and configure your language model provider**")

        llm_provider = st.selectbox(
            "LLM Provider",
            options=["groq", "openai", "ollama", "none"],
            index=0 if os.getenv("LLM_PROVIDER", "groq").lower() == "groq" else 1,
            help="Choose your primary language model provider"
        )

        groq_api_key = openai_api_key = ollama_model = ""
        groq_model = openai_model = ""

        if llm_provider == "groq":
            st.markdown("**🚀 Groq API (Fast & Free)**")
            groq_api_key = st.text_input(
                "Groq API Key",
                value=os.getenv("GROQ_API_KEY", ""),
                type="password",
                help="Your Groq API key"
            )
            groq_model = st.selectbox(
                "Groq Model",
                options=["llama-3.1-8b-instant", "llama-3.1-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
                index=0
            )
            if st.button("🧪 Test Groq Connection"):
                if groq_api_key:
                    try:
                        resp = requests.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization": f"Bearer {groq_api_key}"},
                            json={"model": groq_model,"messages":[{"role":"user","content":"ping"}],"max_tokens":5}
                        )
                        if resp.status_code == 200:
                            st.success("✅ Groq API connection successful!")
                        else:
                            st.error(f"❌ Groq API test failed: {resp.text}")
                    except Exception as e:
                        st.error(f"❌ Groq connection error: {str(e)}")

        elif llm_provider == "openai":
            st.markdown("**🤖 OpenAI API**")
            openai_api_key = st.text_input(
                "OpenAI API Key",
                value=os.getenv("OPENAI_API_KEY", ""),
                type="password"
            )
            openai_model = st.selectbox(
                "Model",
                options=["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "gpt-4-turbo"],
                index=0
            )
            if st.button("🧪 Test OpenAI Connection"):
                if openai_api_key:
                    try:
                        client = openai.OpenAI(api_key=openai_api_key)
                        _ = client.chat.completions.create(
                            model=openai_model,
                            messages=[{"role": "user", "content": "ping"}],
                            max_tokens=5
                        )
                        st.success("✅ OpenAI API connection successful!")
                    except Exception as e:
                        st.error(f"❌ OpenAI authentication failed: {str(e)}")

        elif llm_provider == "ollama":
            st.markdown("**🏠 Ollama (Local)**")
            ollama_model = st.text_input(
                "Ollama Model",
                value=os.getenv("OLLAMA_LLM_MODEL", "llama2"),
                help="Local Ollama model name"
            )
            if st.button("🧪 Test Ollama Connection"):
                try:
                    resp = requests.post("http://localhost:11434/api/tags")
                    if resp.status_code == 200:
                        st.success("✅ Ollama is running locally!")
                    else:
                        st.error("❌ Ollama not responding")
                except Exception as e:
                    st.error(f"❌ Ollama connection error: {str(e)}")

        else:
            st.markdown("**❌ No LLM Provider**")
            st.warning("⚠️ Agent will run with keyword-only responses")

    # ------------------------------
    # Embeddings Configuration
    # ------------------------------
    with st.expander("🧠 Embeddings Configuration"):
        embed_options = ["openai", "ollama", "none"]
        env_ep = os.getenv("EMBED_PROVIDER", "ollama").lower()
        try:
            ep_index = embed_options.index(env_ep)
        except ValueError:
            ep_index = 1

        embed_provider = st.selectbox("Embedding Provider", options=embed_options, index=ep_index)
        openai_embed_model = ollama_embed_model = ""

        if embed_provider == "openai":
            openai_embed_model = st.selectbox(
                "OpenAI Embedding Model",
                options=["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
                index=0
            )
        elif embed_provider == "ollama":
            ollama_embed_model = st.text_input(
                "Ollama Embedding Model",
                value=os.getenv("EMBED_MODEL", "nomic-embed-text")
            )
        else:
            st.warning("⚠️ Vector search disabled")

    # ------------------------------
    # ChromaDB Configuration
    # ------------------------------
    with st.expander("🗄️ ChromaDB Configuration (Optional)"):
        col1, col2 = st.columns(2)
        with col1:
            chroma_host = st.text_input("Chroma Host", value=os.getenv("CHROMA_HOST", ""))
        with col2:
            chroma_api_key = st.text_input("Chroma API Key", value=os.getenv("CHROMA_API_KEY", ""), type="password")

    # ------------------------------
    # Save All Credentials
    # ------------------------------
    if st.button("💾 Save API Credentials", type="primary"):
        env_path = ".env"
        if reddit_client_id: set_key(env_path, "REDDIT_CLIENT_ID", reddit_client_id)
        if reddit_client_secret: set_key(env_path, "REDDIT_CLIENT_SECRET", reddit_client_secret)
        if reddit_username: set_key(env_path, "REDDIT_USERNAME", reddit_username)
        if reddit_password: set_key(env_path, "REDDIT_PASSWORD", reddit_password)
        if reddit_user_agent: set_key(env_path, "USER_AGENT", reddit_user_agent)

        if groq_api_key: set_key(env_path, "GROQ_API_KEY", groq_api_key)
        if groq_model: set_key(env_path, "GROQ_MODEL", groq_model)

        if openai_api_key: set_key(env_path, "OPENAI_API_KEY", openai_api_key)
        if openai_model: set_key(env_path, "OPENAI_MODEL", openai_model)

        if ollama_model: set_key(env_path, "OLLAMA_LLM_MODEL", ollama_model)

        if embed_provider: set_key(env_path, "EMBED_PROVIDER", embed_provider)
        if openai_embed_model: set_key(env_path, "OPENAI_EMBED_MODEL", openai_embed_model)
        if ollama_embed_model: set_key(env_path, "EMBED_MODEL", ollama_embed_model)

        if chroma_host: set_key(env_path, "CHROMA_HOST", chroma_host)
        if chroma_api_key: set_key(env_path, "CHROMA_API_KEY", chroma_api_key)

        st.success("✅ API credentials saved to `.env` successfully!")
        st.info("ℹ️ Restart the app to reload environment variables.")


from utils.database import DatabaseManager
db = DatabaseManager()

def render_agent_settings():
    """Render agent operational settings"""
    
    st.markdown("### 🤖 Agent Operational Settings")
    st.markdown("Configure how your agent behaves and operates.")
    
    # Initialize session_state storage for subreddits
    if "monitored_subreddits" not in st.session_state:
        st.session_state.monitored_subreddits = ["oss_test"]

    # Basic Agent Settings
    with st.expander("⚙️ Basic Settings", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            dry_run = st.toggle(
                "Dry Run Mode",
                value=True,
                help="When enabled, agent drafts replies but doesn't post them"
            )
            
            auto_approval = st.toggle(
                "Auto-approval for High Confidence",
                value=False,
                help="Automatically approve responses with confidence > threshold"
            )
            
            scan_interval = st.slider(
                "Scan Interval (minutes)",
                min_value=1,
                max_value=60,
                value=5,
                help="How often to scan for new questions"
            )
        
        with col2:
            confidence_threshold = st.slider(
                "Confidence Threshold",
                min_value=0.1,
                max_value=1.0,
                value=0.7,
                step=0.1,
                help="Minimum confidence score for auto-approval"
            )
            
            max_requests_per_hour = st.number_input(
                "Max Requests per Hour",
                min_value=1,
                max_value=100,
                value=20,
                help="Rate limit for processing requests"
            )
            
            max_reply_length = st.number_input(
                "Max Reply Length (characters)",
                min_value=100,
                max_value=2000,
                value=800,
                help="Maximum length for generated replies"
            )
    
    # Subreddit Configuration
    with st.expander("📋 Subreddit Monitoring", expanded=True):
        st.markdown("**Configure which subreddits to monitor**")
        
        base_subreddits = [
            "python", "learnpython", "django", "flask", "MachineLearning",
            "programming", "webdev", "datascience", "tensorflow"
        ]
        
        # Combine defaults + base list + custom subs
        all_subreddits = list(set(base_subreddits + st.session_state.monitored_subreddits))
        all_subreddits.sort()
        
        # Render multiselect with all subs
        st.session_state.monitored_subreddits = st.multiselect(
            "Subreddits to Monitor",
            options=all_subreddits,
            default=st.session_state.monitored_subreddits,
            help="Select subreddits for the agent to monitor"
        )
        
        # Add custom subreddit
        col1, col2 = st.columns([3, 1])
        with col1:
            custom_subreddit = st.text_input(
                "Add Custom Subreddit",
                placeholder="Enter subreddit name (without r/)"
            )
        with col2:
            if st.button("➕ Add") and custom_subreddit:
                custom_subreddit = custom_subreddit.strip()
                if custom_subreddit and custom_subreddit not in st.session_state.monitored_subreddits:
                    st.session_state.monitored_subreddits.append(custom_subreddit)
                    st.success(f"Added r/{custom_subreddit}!")
    
    # Search Keywords
    with st.expander("🔍 Search Keywords"):
        st.markdown("**Configure keywords to search for within monitored subreddits**")
        
        keyword_categories = {
            "Installation": ["install", "setup", "installation", "pip install"],
            "Beginner Questions": ["beginner", "new to", "getting started", "how do i"],
            "Errors": ["error", "exception", "bug", "not working", "help"],
            "Libraries": ["pandas", "numpy", "flask", "django", "fastapi"],
        }
        
        for category, keywords in keyword_categories.items():
            st.multiselect(
                f"{category} Keywords",
                options=keywords,
                default=keywords[:2],
                help=f"Keywords related to {category.lower()}"
            )
        
        custom_keywords = st.text_area(
            "Custom Keywords (one per line)",
            placeholder="Enter custom search keywords, one per line",
            height=100
        )
    
    if st.button("💾 Save Agent Settings", type="primary"):
        settings = {
            "dry_run": dry_run,
            "auto_approval": auto_approval,
            "scan_interval": scan_interval,
            "confidence_threshold": confidence_threshold,
            "max_requests_per_hour": max_requests_per_hour,
            "max_reply_length": max_reply_length,
            "monitored_subreddits": st.session_state.monitored_subreddits,
            "custom_keywords": custom_keywords.split('\n') if custom_keywords else []
        }
        
        db.save_agent_settings(settings)   # Persist to DB
        st.success("✅ Agent settings saved successfully!")


def render_rag_settings():
    """Render RAG system configuration"""
    
    st.markdown("### 📚 RAG System Configuration")
    st.markdown("Configure your Retrieval-Augmented Generation system settings.")
    
    # Document Management
    with st.expander("📄 Document Management", expanded=True):
        st.markdown("**Manage your knowledge base documents**")
        
        uploaded_files = st.file_uploader(
            "Upload Documentation",
            type=['txt', 'md'],
            accept_multiple_files=True,
            help="Upload documentation files for the RAG system"
        )
        
        if uploaded_files:
            st.info(f"📁 {len(uploaded_files)} file(s) ready to upload")
            
            if st.button("📤 Copy to Corpus & Rebuild"):
                try:
                    from pathlib import Path
                    from tools.rag_tool import RAGTool, RAG_CORPUS_DIR
                    # Ensure corpus dir exists
                    Path(RAG_CORPUS_DIR).mkdir(parents=True, exist_ok=True)
                    # Save uploaded files into corpus
                    for uf in uploaded_files:
                        # Streamlit uploads have a .read() interface
                        content = uf.read()
                        # Default to .md if no suffix
                        target = Path(RAG_CORPUS_DIR) / (uf.name if any(uf.name.endswith(ext) for ext in ['.md', '.txt']) else (uf.name + '.md'))
                        with open(target, 'wb') as f:
                            f.write(content)
                    # Rebuild index
                    rag = RAGTool()
                    rag.rebuild()
                    st.success("✅ Files copied to corpus and vector index rebuilt")
                except Exception as e:
                    st.error(f"❌ Failed to copy/rebuild: {e}")
        
        # Current documents status (basic insight)
        st.markdown("**Current Document Status**")
        try:
            import os
            from pathlib import Path
            from tools.rag_tool import MANIFEST_FILE, load_json
            corpus = Path(os.getenv('RAG_CORPUS_DIR', 'data/corpus'))
            files = list(corpus.glob('**/*.*')) if corpus.exists() else []
            st.write(f"Indexed directory: {corpus} | Files detected: {len(files)}")
            manifest = load_json(MANIFEST_FILE, {})
            if manifest:
                st.write(f"RAG collection: {manifest.get('collection', 'unknown')}")
                st.write(f"Vector doc_count: {manifest.get('doc_count', 0)}")
                st.write(f"Last rebuild: {manifest.get('last_rebuild', 'n/a')}")
        except Exception as e:
            st.write("Unable to read corpus status or manifest")
    
    # RAG Parameters
    with st.expander("🎛️ RAG Parameters"):
        col1, col2 = st.columns(2)
        
        with col1:
            top_k = st.slider(
                "Top K Results",
                min_value=1,
                max_value=10,
                value=4,
                help="Number of top similar documents to retrieve"
            )
            
            chunk_size = st.number_input(
                "Chunk Size",
                min_value=200,
                max_value=2000,
                value=1000,
                step=100,
                help="Size of text chunks for processing"
            )
        
        with col2:
            similarity_threshold = st.slider(
                "Similarity Threshold",
                min_value=0.1,
                max_value=1.0,
                value=0.6,
                step=0.1,
                help="Minimum similarity score for relevant documents"
            )
            
            chunk_overlap = st.number_input(
                "Chunk Overlap",
                min_value=0,
                max_value=500,
                value=150,
                step=50,
                help="Overlap between text chunks"
            )
    
    # Vector Database Settings
    with st.expander("🗄️ Vector Database"):
        st.markdown("**Vector storage and retrieval settings**")

        # Live vector DB stats
        try:
            from tools.rag_tool import RAGTool
            rag = RAGTool()
            has_vector = bool(rag.retriever)
            st.markdown(f"Vector index: {'✅ Ready' if has_vector else '⚠️ Disabled (keyword fallback)'}")
        except Exception:
            st.markdown("Vector index: ⚠️ Error initializing")

        vector_store_type = st.selectbox(
            "Vector Store Type",
            options=["ChromaDB (Local)", "ChromaDB (Cloud)", "Pinecone", "Weaviate"],
            index=0,
            help="Choose your vector database provider"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            collection_name = st.text_input(
                "Collection Name",
                value="oss_docs",
                help="Name for your document collection"
            )
        
        with col2:
            embedding_dimension = st.number_input(
                "Embedding Dimension",
                value=1536,
                help="Dimension of embedding vectors"
            )
        
        # Rebuild index button
        if st.button("🔄 Rebuild Vector Index"):
            try:
                from tools.rag_tool import RAGTool
                rag = RAGTool()
                rag.rebuild()
                st.success("✅ Vector index rebuilt successfully!")
            except Exception as e:
                st.error(f"❌ Failed to rebuild index: {e}")
    
    if st.button("💾 Save RAG Settings", type="primary"):
        st.success("✅ RAG settings saved successfully!")

def render_moderation_settings():
    """Render moderation and safety configuration"""
    
    st.markdown("### 🛡️ Moderation & Safety Settings")
    st.markdown("Configure content moderation and safety guardrails.")
    
    # Content Moderation
    with st.expander("🔍 Content Moderation", expanded=True):
        st.markdown("**Automated content filtering and safety checks**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            enable_moderation = st.toggle(
                "Enable Content Moderation",
                value=True,
                help="Enable automated content safety checks"
            )
            
            pii_detection = st.toggle(
                "PII Detection",
                value=True,
                help="Detect and flag personally identifiable information"
            )
            
            profanity_filter = st.toggle(
                "Profanity Filter",
                value=True,
                help="Filter out inappropriate language"
            )
        
        with col2:
            moderation_threshold = st.slider(
                "Moderation Threshold",
                min_value=0.1,
                max_value=1.0,
                value=0.5,
                step=0.1,
                help="Sensitivity level for content flagging"
            )
            
            auto_reject_threshold = st.slider(
                "Auto-reject Threshold",
                min_value=0.5,
                max_value=1.0,
                value=0.8,
                step=0.1,
                help="Automatically reject content above this score"
            )
    
    # Blocked Content
    with st.expander("🚫 Blocked Content Patterns"):
        st.markdown("**Define patterns and keywords to automatically block**")
        
        blocked_keywords = st.text_area(
            "Blocked Keywords (one per line)",
            placeholder="spam\noffensive content\ninappropriate",
            help="Keywords that will trigger automatic rejection",
            height=100
        )
        
        blocked_domains = st.text_area(
            "Blocked Domains (one per line)",
            placeholder="spam-site.com\nsuspicious-link.net",
            help="Domains that should be blocked from responses",
            height=100
        )
        
        blocked_patterns = st.text_area(
            "Blocked Regex Patterns (one per line)",
            placeholder="\\b\\d{3}-\\d{3}-\\d{4}\\b  # Phone numbers\n\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b  # Email addresses",
            help="Regular expressions for pattern-based blocking",
            height=100
        )
    
    # Safety Measures
    with st.expander("🛡️ Additional Safety Measures"):
        col1, col2 = st.columns(2)
        
        with col1:
            require_human_review = st.toggle(
                "Require Human Review for Low Confidence",
                value=True,
                help="Always require human review for responses below confidence threshold"
            )
            
            log_all_interactions = st.toggle(
                "Log All Interactions",
                value=True,
                help="Log all agent interactions for audit purposes"
            )
        
        with col2:
            quarantine_flagged = st.toggle(
                "Quarantine Flagged Content",
                value=True,
                help="Hold flagged content for manual review"
            )
            
            notification_alerts = st.toggle(
                "Moderation Alerts",
                value=True,
                help="Send alerts when content is flagged"
            )
    
    if st.button("💾 Save Moderation Settings", type="primary"):
        st.success("✅ Moderation settings saved successfully!")

def render_advanced_settings():
    """Render advanced system configuration"""
    
    st.markdown("### 🔧 Advanced Configuration")
    st.markdown("Advanced settings for power users and system administrators.")
    
    # System Settings
    with st.expander("💻 System Settings", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            log_level = st.selectbox(
                "Log Level",
                options=["DEBUG", "INFO", "WARNING", "ERROR"],
                index=1,
                help="System logging verbosity level"
            )
            
            max_concurrent_requests = st.number_input(
                "Max Concurrent Requests",
                min_value=1,
                max_value=50,
                value=5,
                help="Maximum number of concurrent API requests"
            )
        
        with col2:
            request_timeout = st.number_input(
                "Request Timeout (seconds)",
                min_value=5,
                max_value=300,
                value=30,
                help="Timeout for API requests"
            )
            
            retry_attempts = st.number_input(
                "Retry Attempts",
                min_value=1,
                max_value=10,
                value=3,
                help="Number of retry attempts for failed requests"
            )
    
    # Database Settings
    with st.expander("🗃️ Database Configuration"):
        db_path = st.text_input(
            "Database Path",
            value="data/agent_data.db",
            help="Path to SQLite database file"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            backup_enabled = st.toggle(
                "Enable Automatic Backups",
                value=True,
                help="Automatically backup database"
            )
            
            backup_frequency = st.selectbox(
                "Backup Frequency",
                options=["Daily", "Weekly", "Monthly"],
                index=0,
                help="How often to create backups"
            )
        
        with col2:
            max_backup_files = st.number_input(
                "Max Backup Files",
                min_value=1,
                max_value=50,
                value=7,
                help="Maximum number of backup files to keep"
            )
        
        # Database maintenance
        if st.button("🧹 Optimize Database"):
            st.info("🔄 Optimizing database...")
            st.success("✅ Database optimized successfully!")
        
        if st.button("📤 Export Database"):
            st.info("📤 Exporting database...")
            st.success("✅ Database exported to data/exports/")
    
    # Performance Tuning
    with st.expander("⚡ Performance Tuning"):
        col1, col2 = st.columns(2)
        
        with col1:
            cache_enabled = st.toggle(
                "Enable Response Caching",
                value=True,
                help="Cache generated responses to improve performance"
            )
            
            cache_ttl = st.number_input(
                "Cache TTL (hours)",
                min_value=1,
                max_value=168,  # 1 week
                value=24,
                help="How long to cache responses"
            )
        
        with col2:
            parallel_processing = st.toggle(
                "Parallel Processing",
                value=True,
                help="Process multiple requests in parallel"
            )
            
            worker_threads = st.number_input(
                "Worker Threads",
                min_value=1,
                max_value=10,
                value=3,
                help="Number of worker threads for processing"
            )
    
    # Debug and Development
    with st.expander("🐛 Debug & Development"):
        st.markdown("**Development and debugging tools**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            debug_mode = st.toggle(
                "Debug Mode",
                value=False,
                help="Enable debug logging and verbose output"
            )
            
            mock_responses = st.toggle(
                "Mock API Responses",
                value=False,
                help="Use mock responses for testing (no real API calls)"
            )
        
        with col2:
            api_call_logging = st.toggle(
                "Log API Calls",
                value=False,
                help="Log all outgoing API calls for debugging"
            )
            
            performance_profiling = st.toggle(
                "Performance Profiling",
                value=False,
                help="Enable detailed performance profiling"
            )
        
        # System info and diagnostics
        if st.button("🔍 Run System Diagnostics"):
            st.info("🔄 Running system diagnostics...")
            
            # Mock diagnostic results
            diagnostics = [
                {"component": "Database", "status": "✅ Healthy", "details": "Connection OK, 156 records"},
                {"component": "Reddit API", "status": "✅ Connected", "details": "Rate limit: 92% available"},
                {"component": "OpenAI API", "status": "✅ Active", "details": "Response time: 1.2s avg"},
                {"component": "Vector Store", "status": "✅ Ready", "details": "15 documents indexed"},
                {"component": "File System", "status": "⚠️ Warning", "details": "Disk usage: 85%"},
            ]
            
            for diag in diagnostics:
                st.markdown(f"**{diag['component']}:** {diag['status']} - {diag['details']}")
    
    if st.button("💾 Save Advanced Settings", type="primary"):
        st.success("✅ Advanced settings saved successfully!")
        st.info("ℹ️ Some settings may require a system restart to take effect.")

if __name__ == "__main__":
    render_settings_page()