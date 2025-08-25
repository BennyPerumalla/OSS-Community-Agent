# apps/ui/utils/scheduler.py

import os
import sys
import sqlite3
import logging
import atexit
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:
    BackgroundScheduler = None

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from tools.reddit_tool import RedditTool
    from tools.rag_tool import RAGTool
    from tools.moderation_tools import analyze_text
except ImportError as e:
    logging.warning(f"Could not import tools: {e}")
    RedditTool = None
    RAGTool = None
    analyze_text = None

try:
    from apps.ui.utils.database import DatabaseManager
except ImportError:
    DatabaseManager = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ingest_unanswered_queries(subreddit: str, limit: int = 5, model: str = "groq"):
    """
    Fetch unanswered posts from a subreddit, generate AI drafts, and add them to the DB review queue.
    """
    results = {
        "subreddit": subreddit,
        "fetched_count": 0,
        "new_queries": 0,
        "errors": []
    }
    
    try:
        # Get Reddit credentials from environment
        reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        reddit_username = os.getenv("REDDIT_USERNAME")
        reddit_password = os.getenv("REDDIT_PASSWORD")
        
        if not all([reddit_client_id, reddit_client_secret, reddit_username, reddit_password]):
            results["errors"].append("Reddit API credentials not configured")
            return results
        
        if not RedditTool:
            results["errors"].append("RedditTool not available")
            return results
        
        # Initialize Reddit tool
        reddit_tool = RedditTool(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            username=reddit_username,
            password=reddit_password,
            user_agent=f"oss-community-agent/1.0 (by u/{reddit_username})"
        )
        
        # Initialize RAG tool for generating responses
        rag_tool = RAGTool() if RAGTool else None
        
        # Search for recent questions
        logger.info(f"Searching r/{subreddit} for recent questions...")
        posts = reddit_tool.search_questions(
            subreddit_name=subreddit,
            keywords="help question problem how",
            limit=limit
        )
        
        results["fetched_count"] = len(posts)
        
        # Use DatabaseManager if available, otherwise create simple storage
        if DatabaseManager:
            db = DatabaseManager()
        else:
            db = None
        
        for post in posts:
            try:
                # Draft a reply if RAG tool is available
                drafted_reply = ""
                confidence = 0.0
                
                if rag_tool:
                    query_text = f"{post['title']}\n\n{post.get('selftext', '')}"
                    try:
                        drafted_reply = rag_tool.retrieve_and_generate(query_text)
                        if drafted_reply and len(drafted_reply.strip()) > 0:
                            confidence = 0.8  # Default confidence
                        else:
                            confidence = 0.2  # Low confidence for empty responses
                    except Exception as e:
                        logger.warning(f"Failed to generate reply: {e}")
                        drafted_reply = "Error generating reply"
                        confidence = 0.0
                
                # Insert into database
                if db:
                    if not db.get_request_by_post_id(post["id"]):
                        db.insert_request({
                            "post_id": post["id"],
                            "post_title": post["title"],
                            "post_content": post.get('selftext', ''),
                            "post_url": post.get('url', ''),
                            "post_author": "unknown",  # Would need to get from Reddit API
                            "created_at": datetime.fromtimestamp(post.get('created_utc', 0)).isoformat(),
                            "subreddit": subreddit,
                            "drafted_reply": drafted_reply,
                            "status": "pending",
                            "agent_confidence": confidence,
                            "citations": "[]"
                        })
                        results["new_queries"] += 1
                else:
                    # Fallback: just log the post
                    logger.info(f"Found post: {post['title'][:50]}...")
                    results["new_queries"] += 1
                
            except Exception as e:
                error_msg = f"Error processing post {post.get('id', 'unknown')}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        logger.info(f"Ingestion complete. New queries: {results['new_queries']}")
        
    except Exception as e:
        error_msg = f"Fatal error in ingest_unanswered_queries: {str(e)}"
        results["errors"].append(error_msg)
        logger.error(error_msg)
    
    return results

# ---- Scheduler setup ----
scheduler = BackgroundScheduler()

def start_scheduler(monitored_subs):
    """
    Start a background scheduler to periodically fetch unanswered posts
    and add them to the review queue without generating answers automatically.
    """
    for sub in monitored_subs:
        scheduler.add_job(
            ingest_unanswered_queries,
            "interval",
            minutes=15,
            args=[sub],
            id=f"fetch_{sub}",
            replace_existing=True
        )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
