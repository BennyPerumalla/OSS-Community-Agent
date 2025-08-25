# utils/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from utils.reddit_client import get_unanswered_posts
from utils.database import DatabaseManager
import atexit
from datetime import datetime
from utils.reddit_client import get_subreddit_data

def ingest_unanswered_queries(subreddit: str, limit: int = 5):
    """
    Fetch unanswered posts from a subreddit and add them to the DB review queue
    WITHOUT auto-generating AI drafts.
    """
    db = DatabaseManager()
    posts = get_unanswered_posts(subreddit, limit=limit)
    for post in posts:
        # Only insert if it doesn't exist already
        if not db.get_request_by_post_id(post["id"]):
            db.insert_request({
                "post_id": post["id"],
                "post_title": post["title"],
                "post_content": post["content"],
                "post_url": post["url"],
                "post_author": post["author"],
                "created_at": post["created_at"],
                "subreddit": post["subreddit"],
                "drafted_reply": "",  # Empty initially
                "status": "pendin   g",
                "agent_confidence": 0.0,
                "citations": "[]"
            })

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
