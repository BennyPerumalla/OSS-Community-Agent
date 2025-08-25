# tools/reddit_tool.py

import os
import time
import random
import re
from typing import List, Dict, Any, Optional

# Import PRAW and capture exception classes into local aliases so tests that patch
# tools.reddit_tool.praw to MagicMock won't break "except" clauses.
try:
    import praw as _praw
    import prawcore as _prawcore
    RedditAPIException = _praw.exceptions.RedditAPIException
    PRAWException = _praw.exceptions.PRAWException
    TooManyRequests = _prawcore.exceptions.TooManyRequests
    RequestException = _prawcore.exceptions.RequestException
    ResponseException = _prawcore.exceptions.ResponseException
    # Some versions expose a common base exception; fall back to Exception if absent
    PrawcoreException = getattr(_prawcore.exceptions, 'PrawcoreException', Exception)
    praw = _praw
    prawcore = _prawcore
except Exception:
    praw = None
    prawcore = None
    class RedditAPIException(Exception):
        pass
    class PRAWException(Exception):
        pass
    class TooManyRequests(Exception):
        pass
    class RequestException(Exception):
        pass
    class ResponseException(Exception):
        pass
    class PrawcoreException(Exception):
        pass

class RedditTool:
    """
    A robust and modular tool for interacting with the Reddit API.

    This class encapsulates all Reddit-related functionality, including
    authentication, searching for posts, and posting replies. It is
    designed to be resilient to network issues and API rate limits.

    Implements automatic exponential backoff with jitter for known rate-limit
    scenarios (RedditAPIException with RATELIMIT and prawcore TooManyRequests).
    """

    def __init__(self, client_id: str, client_secret: str, username: str, password: str, user_agent: str):
        """
        Initializes the Reddit tool with API credentials and a user agent.

        Args:
            client_id (str): The Reddit application client ID.
            client_secret (str): The Reddit application client secret.
            username (str): The Reddit account username for authentication.
            password (str): The Reddit account password.
            user_agent (str): A unique, descriptive user agent string as required by Reddit.
        """
        if not all([client_id, client_secret, username, password, user_agent]):
            raise ValueError("All Reddit credentials and user_agent must be provided.")
        
        # Use PRAW's built-in authentication for security
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent
        )
        # Backoff settings
        self._max_retries = int(os.getenv("REDDIT_MAX_RETRIES", "5"))
        self._base_sleep = float(os.getenv("REDDIT_BASE_SLEEP", "1.0"))  # seconds
        print("Reddit instance created and authenticated.")

    def _parse_ratelimit_wait(self, message: str) -> float:
        """Parse Reddit 'RATELIMIT' message to seconds to wait."""
        if not message:
            return 0
        # Typical formats: 'you are doing that too much. try again in 6 minutes.'
        # or '... in 12 seconds.'
        match = re.search(r"(\d+)\s*(minute|second)s?", message, re.IGNORECASE)
        if not match:
            return 0
        value = int(match.group(1))
        unit = match.group(2).lower()
        return value * 60.0 if unit.startswith("minute") else float(value)

    def _with_backoff(self, func, *args, **kwargs):
        """Execute a Reddit API call with exponential backoff and jitter."""
        attempt = 0
        while True:
            try:
                return func(*args, **kwargs)
            except TooManyRequests as e:
                retry_after = 0
                try:
                    retry_after = float(getattr(getattr(e, 'response', None), 'headers', {}).get('Retry-After', 0))
                except Exception:
                    retry_after = 0
                wait = max(retry_after, (self._base_sleep * (2 ** attempt)))
                wait += random.uniform(0, 0.5)
                if attempt >= self._max_retries:
                    raise
                time.sleep(wait)
                attempt += 1
            except RedditAPIException as e:
                # Check for RATELIMIT errors; pick the maximum wait we can extract
                waits = []
                for item in getattr(e, 'items', []) or []:
                    if getattr(item, 'error_type', '').upper() == 'RATELIMIT':
                        waits.append(self._parse_ratelimit_wait(getattr(item, 'message', '')))
                wait = max(waits) if waits else 0
                if wait == 0 and attempt < self._max_retries:
                    wait = self._base_sleep * (2 ** attempt)
                if attempt >= self._max_retries:
                    raise
                time.sleep(wait + random.uniform(0, 0.5))
                attempt += 1
            except (RequestException, ResponseException) as e:
                # Transient network/API errors
                if attempt >= self._max_retries:
                    raise
                wait = self._base_sleep * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(wait)
                attempt += 1
            except Exception:
                # Fallback catch-all to prevent tests with patched mocks from breaking
                if attempt >= self._max_retries:
                    raise
                wait = self._base_sleep * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(wait)
                attempt += 1

    def search_questions(self, subreddit_name: str, keywords: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Searches a subreddit for posts that match the given keywords.

        Args:
            subreddit_name (str): The name of the subreddit (e.g., 'python').
            keywords (str): The keywords to search for.
            limit (int): The maximum number of posts to retrieve.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                                   represents a post with key details.
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            def _do_search():
                return subreddit.search(query=keywords, limit=limit)

            search_results = self._with_backoff(_do_search)

            posts = []
            for submission in search_results:
                posts.append({
                    "id": submission.id,
                    "title": submission.title,
                    "url": getattr(submission, 'url', ''),
                    "created_utc": getattr(submission, 'created_utc', 0),
                    "selftext": getattr(submission, 'selftext', '')
                })

            print(f"Found {len(posts)} relevant posts in r/{subreddit_name}.")
            return posts

        except (RedditAPIException, PRAWException, PrawcoreException) as e:
            print(f"Reddit API error during search: {e}", file=os.sys.stderr)
            return []
        except Exception as e:
            print(f"An unexpected error occurred during search: {e}", file=os.sys.stderr)
            return []

    def post_reply(self, submission_id: str, reply_text: str) -> Dict[str, Any]:
        """
        Posts a reply to a specific Reddit submission.

        Args:
            submission_id (str): The ID of the Reddit submission to reply to.
            reply_text (str): The content of the reply message.

        Returns:
            Dict[str, Any]: A dictionary containing the status of the reply.
        """
        try:
            # Get the submission object by its ID
            submission = self.reddit.submission(id=submission_id)
            submission._fetch()  # Ensure the submission data is loaded
            print(f"Preparing to reply to post ID: {submission_id} - Title: {submission.title}")
            # Check if the bot has already replied to avoid spamming
            def _list_comments():
                # Force a comments fetch when available; handle simple list in tests
                comments_obj = submission.comments
                if hasattr(comments_obj, 'replace_more'):
                    comments_obj.replace_more(limit=0)
                    return list(comments_obj)
                # If it's already a list-like (as in unit tests), just return it
                return list(comments_obj) if isinstance(comments_obj, (list, tuple)) else []
            print("Fetching existing comments to check for prior replies...")

            comments = self._with_backoff(_list_comments)
            print(f"Fetched {len(comments)} comments.")
            me = self._with_backoff(lambda: self.reddit.user.me())
            print(f"Authenticated as Reddit user: {getattr(me, 'name', 'unknown')}")
            has_replied = any(getattr(c, 'author', None) and getattr(c.author, 'name', None) == getattr(me, 'name', None) for c in comments)
            print(f"Has already replied: {has_replied}")
            if has_replied:
                return {"status": "skipped", "message": "Already replied to this post."}

            # Post the reply with backoff
            reply_object = self._with_backoff(lambda: submission.reply(reply_text))

            print(f"Successfully replied to post ID: {submission_id}")
            return {
                "status": "success",
                "message": "Reply posted.",
                "reply_id": getattr(reply_object, 'id', None),
                "submission_id": submission_id
            }

        except (RedditAPIException, PRAWException, PrawcoreException) as e:
            print(f"Reddit API error while posting: {e}", file=os.sys.stderr)
            return {"status": "error", "message": str(e)}
        except Exception as e:
            print(f"An unexpected error occurred while posting: {e}", file=os.sys.stderr)
            return {"status": "error", "message": str(e)}

# --- For local testing/demonstration ---
# This block is for testing the tool in isolation
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Use dummy credentials if not available for a quick test
    try:
        reddit_tool = RedditTool(
            client_id=os.getenv("REDDIT_CLIENT_ID", "dummy_id"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET", "dummy_secret"),
            username=os.getenv("REDDIT_USERNAME", "dummy_user"),
            password=os.getenv("REDDIT_PASSWORD", "dummy_pass"),
            user_agent="oss-community-agent/0.1 (by u/TestUser)"
        )

        # Example 1: Search for a post
        print("--- Searching for posts ---")
        posts = reddit_tool.search_questions(subreddit_name="learnpython", keywords="Python 3.11", limit=2)
        print("Search Results:")
        for post in posts:
            print(f"- Title: {post['title']} (ID: {post['id']})")
        
        # Example 2: Post a dummy reply (requires a real submission ID and proper credentials)
        # Note: This will not work with dummy credentials
        # print("\n--- Posting a reply (Dry Run) ---")
        # dummy_id = "1b8p6m5"
        # reply_text = "Hello from the test bot! This is an example reply."
        # result = reddit_tool.post_reply(submission_id=dummy_id, reply_text=reply_text)
        # print("Post Result:", result)

    except ValueError as e:
        print(f"Could not initialize RedditTool: {e}")