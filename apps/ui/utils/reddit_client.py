import os
import praw
from dotenv import load_dotenv
load_dotenv()
# Initialize Reddit client
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="agent-approval-dashboard/0.1"
)

def get_unanswered_posts(subreddit_name: str, limit: int = 10):
    """Fetch unanswered queries (posts with 0 comments)."""
    subreddit = reddit.subreddit(subreddit_name)
    unanswered = []
    for post in subreddit.new(limit=limit*3):  # fetch more, filter later
        if post.num_comments == 0 and not post.stickied:
            unanswered.append({
                "id": post.id,
                "title": post.title,
                "content": post.selftext,
                "url": f"https://reddit.com{post.permalink}",
                "author": str(post.author),
                "created_at": post.created_utc,
                "subreddit": subreddit_name
            })
        if len(unanswered) >= limit:
            break
    return unanswered

def get_subreddit_data(subreddit_name: str, limit: int = 5):
    """Fetch top hot posts from a subreddit"""
    try:
        subreddit = reddit.subreddit(subreddit_name)
        posts = []
        for post in subreddit.hot(limit=limit):
            posts.append({
                "title": post.title,
                "score": post.score,
                "url": f"https://reddit.com{post.permalink}",
                "author": str(post.author) if post.author else "Unknown",
                "created_utc": post.created_utc
            })
        return posts
    except Exception as e:
        return {"error": str(e)}
