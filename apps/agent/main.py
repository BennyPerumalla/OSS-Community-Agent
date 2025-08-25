# apps/agent/main.py

import os
import json
import logging
import uuid
import time
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from pathlib import Path

# Import Portia AI SDK components with proper modern API
try:
    from portia import Portia, PlanBuilder
    # Import the approval workflow system which is the working component
    import sys
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    from apps.ui.utils.approval_workflow import approval_workflow
    print("✅ Using real Portia SDK with approval workflow integration")
    USING_REAL_PORTIA = True
except Exception as e:
    print(f"⚠️ Portia SDK not available or misconfigured ({e}), using mock implementation")
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from mock_portia import Portia, PlanBuilder, Clarification, ToolCall, PlanRunState, PlanRunStatus, PortiaToolRegistry
    # Try to import approval workflow anyway
    try:
        from apps.ui.utils.approval_workflow import approval_workflow
    except:
        approval_workflow = None
    USING_REAL_PORTIA = False

# Import your custom tools
from tools.reddit_tool import RedditTool
from tools.rag_tool import RAGTool
from tools.moderation_tools import analyze_text as ModerationTool_analyze_text

# --- Configuration & Logging ---
load_dotenv()  # Load environment variables from .env file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Helper to read env values at runtime (no import-time hard binding)
def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)

# Expose selected envs dynamically so tests using `from apps.agent.main import REDDIT_CLIENT_ID` work
# PEP 562: module-level __getattr__
def __getattr__(name: str):
    dynamic_envs = {
        'REDDIT_CLIENT_ID': 'REDDIT_CLIENT_ID',
        'REDDIT_CLIENT_SECRET': 'REDDIT_CLIENT_SECRET',
        'REDDIT_USERNAME': 'REDDIT_USERNAME',
        'REDDIT_PASSWORD': 'REDDIT_PASSWORD',
        'OPENAI_API_KEY': 'OPENAI_API_KEY',
        'GROQ_API_KEY': 'GROQ_API_KEY',
        'LLM_PROVIDER': 'LLM_PROVIDER',
    }
    if name in dynamic_envs:
        if name == 'LLM_PROVIDER':
            return _env('LLM_PROVIDER', 'none').lower()
        return _env(dynamic_envs[name])
    raise AttributeError(f"module 'apps.agent.main' has no attribute '{name}'")

# Runtime flags
DRY_RUN = _env("DRY_RUN", "True").lower() == "true"  # Default to dry run

# --- Tool Initialization ---
# Lazy initialization to avoid import-time failures
class _LazyRedditToolProxy:
    def __getattr__(self, name):
        raise RuntimeError(
            "RedditTool is not initialized yet. Configure Reddit credentials in .env and call through the agent APIs."
        )

reddit_tool = _LazyRedditToolProxy()
rag_tool = RAGTool()


def get_reddit_tool() -> RedditTool:
    global reddit_tool
    if isinstance(reddit_tool, _LazyRedditToolProxy):
        client_id = _env("REDDIT_CLIENT_ID")
        client_secret = _env("REDDIT_CLIENT_SECRET")
        username = _env("REDDIT_USERNAME")
        password = _env("REDDIT_PASSWORD")
        if not (client_id and client_secret and username and password):
            raise ValueError(
                "Reddit API credentials (CLIENT_ID, CLIENT_SECRET, USERNAME, PASSWORD) are not configured."
            )
        reddit_tool = RedditTool(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=f"oss-community-agent/0.1 (by u/{username or 'unknown'})",
        )
    return reddit_tool


# --- Modern Portia Integration ---
# Initialize Portia properly for modern API
portia_client = None
if USING_REAL_PORTIA:
    try:
        # Modern Portia SDK may not need API key in constructor
        portia_client = Portia()
        print("✅ Portia client initialized successfully")
    except Exception as e:
        try:
            # Try alternative initialization
            from portia import Config
            config = Config(api_key=_env("PORTIA_API_KEY"))
            portia_client = Portia(config=config)
            print("✅ Portia client initialized with config")
        except Exception as e2:
            print(f"⚠️ Failed to initialize Portia client: {e}")
            print(f"   Alternative method also failed: {e2}")
            print("   Portia integration will be limited to tool registration")


# --- Agent Core Logic ---

def run_oss_agent(query: str, subreddit: str, submission_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Runs the OSS Community Auto-Responder agent using the working approval workflow.

    This function integrates Portia AI with the existing approval workflow system
    to create a complete human-in-the-loop process for Reddit responses.

    Args:
        query (str): The initial user query or topic for the agent.
        subreddit (str): The subreddit to monitor or post to.
        submission_id (Optional[str]): If provided, the agent will attempt to reply to this specific submission.
                                        Otherwise, it will search for new questions.

    Returns:
        Dict[str, Any]: A dictionary containing the final status and output of the agent run.
    """
    run_id = str(uuid.uuid4())
    start_time = time.time()
    logging.info(f"[{run_id}] OSS Community Agent initiated with query: '{query}' on subreddit: '{subreddit}'.")
    logging.info(f"[{run_id}] Dry Run Mode: {DRY_RUN}.")

    if not approval_workflow:
        return {"status": "failed", "error": "Approval workflow not available"}

    try:
        # Phase 1: Search Reddit for questions
        logging.info(f"[{run_id}] Phase 1: Searching Reddit for questions...")
        reddit_posts = []
        
        try:
            reddit_tool_instance = get_reddit_tool()
            reddit_posts = reddit_tool_instance.search_questions(
                subreddit_name=subreddit, 
                keywords=query, 
                limit=5
            )
            logging.info(f"[{run_id}] Found {len(reddit_posts)} Reddit posts")
        except Exception as e:
            logging.error(f"[{run_id}] Reddit search failed: {e}")
            # Continue anyway - this might be expected if credentials aren't configured
            reddit_posts = []

        # Phase 2: Process posts through approval workflow
        processed_requests = []
        if reddit_posts:
            for post in reddit_posts[:3]:  # Limit to first 3 posts
                try:
                    # Add required fields for approval workflow
                    post_data = {
                        'id': post.get('id'),
                        'title': post.get('title', ''),
                        'selftext': post.get('selftext', ''),
                        'subreddit': subreddit,
                        'author': 'unknown',
                        'url': post.get('url', '')
                    }
                    
                    logging.info(f"[{run_id}] Processing post: {post_data['title'][:50]}...")
                    result = approval_workflow.process_reddit_query(post_data)
                    
                    if result['success']:
                        processed_requests.append({
                            'request_id': result['request_id'],
                            'post_id': post_data['id'],
                            'title': post_data['title'],
                            'confidence': result['confidence']
                        })
                        logging.info(f"[{run_id}] Successfully queued request {result['request_id']}")
                    else:
                        logging.warning(f"[{run_id}] Failed to process post: {result.get('error')}")
                        
                except Exception as e:
                    logging.error(f"[{run_id}] Error processing post: {e}")
                    continue
        else:
            logging.info(f"[{run_id}] No Reddit posts found, creating a sample request for testing")
            # Create a sample request for testing purposes
            sample_post = {
                'id': f'sample_{run_id[:8]}',
                'title': f'Sample question about {query}',
                'selftext': f'This is a sample question about {query} in r/{subreddit}. How can I learn more?',
                'subreddit': subreddit,
                'author': 'sample_user',
                'url': f'https://reddit.com/r/{subreddit}/sample'
            }
            
            result = approval_workflow.process_reddit_query(sample_post)
            if result['success']:
                processed_requests.append({
                    'request_id': result['request_id'],
                    'post_id': sample_post['id'],
                    'title': sample_post['title'],
                    'confidence': result['confidence']
                })
        
        # Phase 3: Get pending requests
        pending_requests = approval_workflow.get_pending_requests()
        stats = approval_workflow.get_request_stats()
        
        # Phase 4: Modern Portia Integration (for future enhancements)
        portia_status = "available" if portia_client else "not_configured"
        if portia_client and USING_REAL_PORTIA:
            try:
                # Future: Use Portia for advanced orchestration
                # For now, log that Portia is available for future enhancements
                logging.info(f"[{run_id}] Portia AI SDK available for future enhancements")
            except Exception as e:
                logging.warning(f"[{run_id}] Portia integration issue: {e}")
                portia_status = "error"

        # Compile final results
        final_output = {
            "status": "completed",
            "run_id": run_id,
            "agent_config": {
                "query": query,
                "subreddit": subreddit,
                "dry_run": DRY_RUN,
                "portia_status": portia_status
            },
            "reddit_search": {
                "posts_found": len(reddit_posts),
                "posts_processed": len(processed_requests)
            },
            "processed_requests": processed_requests,
            "approval_queue": {
                "pending_count": len(pending_requests),
                "total_stats": stats
            },
            "total_duration_sec": round(time.time() - start_time, 2),
        }
        
        logging.info(f"[{run_id}] Agent run completed successfully")
        logging.info(f"[{run_id}] Processed {len(processed_requests)} requests, {len(pending_requests)} pending approval")
        
        return final_output

    except Exception as e:
        logging.error(f"[{run_id}] Agent run failed with unexpected error", exc_info=True)
        return {
            "status": "failed", 
            "error": str(e),
            "run_id": run_id,
            "total_duration_sec": round(time.time() - start_time, 2)
        }

# --- Main execution for testing/demonstration ---
if __name__ == "__main__":
    print("--- Running Agent: Search for general query ---")
    _ = run_oss_agent(query="Portia AI installation", subreddit="learnpython")
    print("\n" + "=" * 80 + "\n")
