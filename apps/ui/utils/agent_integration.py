# apps/ui/utils/agent_integration.py

import sys
import os
import uuid
import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import threading
import json
import requests

import portia  # Ensure Portia package is importable

# Ensure 'apps/ui' is on sys.path so 'utils' package can be imported reliably
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from utils.database import DatabaseManager

class AgentIntegration:
    """
    Integration layer between the Streamlit UI and the existing Portia agent backend.
    This class provides a bridge to interact with the agent while maintaining UI responsiveness.
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        self.agent_status = "idle"
        self.current_runs = {}
        self.last_heartbeat = datetime.now()
        self.dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
        
        # Optionally seed demo data only if DB is empty and env allows
        try:
            seed_demo = os.getenv("SEED_DEMO_DATA", "true").lower() == "true"
            if seed_demo and len(self.db.get_requests_by_filter({"limit": 1})) == 0:
                self._initialize_demo_data()
        except Exception:
            pass
    
    def _initialize_demo_data(self):
        """Initialize some demo data for the UI to display (optional)"""
        
        # Create some sample requests for demonstration
        sample_requests = [
            {
                'id': str(uuid.uuid4()),
                'subreddit': 'learnpython',
                'post_id': 'sample_001',
                'post_title': 'How do I install Python on Windows?',
                'post_content': 'I\'m new to programming and want to install Python on my Windows 10 computer. Can someone guide me through the process?',
                'post_author': 'pythonbeginner123',
                'post_url': 'https://reddit.com/r/learnpython/sample_001',
                'status': 'pending',
                'drafted_reply': 'To install Python on Windows, you can follow these steps:\n\n1. Go to python.org\n2. Download the latest Python installer\n3. Run the installer and check "Add Python to PATH"\n4. Verify installation by opening Command Prompt and typing `python --version`\n\nThis should get you started with Python development on Windows!',
                'moderation_score': 0.1,
                'agent_confidence': 0.85,
                'citations': json.dumps([
                    {'title': 'Python Installation Guide', 'source': 'python.org'},
                    {'title': 'Windows Setup Documentation', 'source': 'docs.python.org'}
                ]),
                'processing_time': 2.3
            },
            {
                'id': str(uuid.uuid4()),
                'subreddit': 'django',
                'post_id': 'sample_002',
                'post_title': 'Django models vs SQLAlchemy - which is better?',
                'post_content': 'I\'m starting a new web project and wondering whether to use Django ORM or SQLAlchemy. What are the pros and cons?',
                'post_author': 'webdev_curious',
                'post_url': 'https://reddit.com/r/django/sample_002',
                'status': 'pending',
                'drafted_reply': 'Both Django ORM and SQLAlchemy are excellent choices, but they serve different purposes:\n\n**Django ORM:**\n- Integrated with Django framework\n- Convention over configuration\n- Great for rapid development\n- Active Record pattern\n\n**SQLAlchemy:**\n- Framework agnostic\n- More flexible and powerful\n- Data Mapper pattern\n- Better for complex queries\n\nChoose Django ORM if you\'re building a Django app, SQLAlchemy for more flexibility.',
                'moderation_score': 0.05,
                'agent_confidence': 0.92,
                'citations': json.dumps([
                    {'title': 'Django ORM Documentation', 'source': 'docs.djangoproject.com'},
                    {'title': 'SQLAlchemy Tutorial', 'source': 'sqlalchemy.org'}
                ]),
                'processing_time': 3.1
            },
            {
                'id': str(uuid.uuid4()),
                'subreddit': 'python',
                'post_id': 'sample_003',
                'post_title': 'Understanding Python decorators',
                'post_content': 'Can someone explain Python decorators in simple terms? I keep seeing @ symbols in code and don\'t understand what they do.',
                'post_author': 'decorator_confused',
                'post_url': 'https://reddit.com/r/python/sample_003',
                'status': 'approved',
                'drafted_reply': 'Python decorators are a way to modify or extend functions without changing their code directly.\n\nThink of it like wrapping a gift:\n- The function is the gift\n- The decorator is the wrapping paper\n- The @ symbol applies the wrapping\n\nHere\'s a simple example:\n\n```python\n@my_decorator\ndef say_hello():\n    print("Hello!")\n```\n\nThe decorator can add functionality before, after, or around the original function.',
                'final_reply': 'Python decorators are a way to modify or extend functions without changing their code directly.\n\nThink of it like wrapping a gift:\n- The function is the gift\n- The decorator is the wrapping paper\n- The @ symbol applies the wrapping\n\nHere\'s a simple example:\n\n```python\n@my_decorator\ndef say_hello():\n    print("Hello!")\n```\n\nThe decorator can add functionality before, after, or around the original function.',
                'moderation_score': 0.02,
                'agent_confidence': 0.78,
                'citations': json.dumps([
                    {'title': 'Python Decorators Guide', 'source': 'realpython.com'},
                    {'title': 'Decorator Documentation', 'source': 'docs.python.org'}
                ]),
                'processing_time': 1.8
            }
        ]
        
        # Add sample requests to database
        for request in sample_requests:
            try:
                self.db.add_request(request)
            except Exception as e:
                # Request might already exist, that's okay for demo
                pass
    
    def start_agent_monitoring(self, subreddit: str, keywords: str = "") -> str:
        """
        Start monitoring a subreddit for new questions.
        Returns a run ID for tracking the operation.
        """
        
        run_id = str(uuid.uuid4())
        self.current_runs[run_id] = {
            'type': 'monitoring',
            'status': 'running',
            'subreddit': subreddit,
            'keywords': keywords,
            'start_time': datetime.now(),
            'posts_found': 0,
            'replies_drafted': 0,
            'stop': False
        }
        
        thread = threading.Thread(target=self._monitoring_loop, args=(run_id,), daemon=True)
        thread.start()
        
        return run_id
    
    def _monitoring_loop(self, run_id: str):
        """Background monitoring loop that periodically calls the agent and persists results"""
        try:
            cfg_interval = int(os.getenv("SCAN_INTERVAL_SECONDS", "120"))
            while True:
                run = self.current_runs.get(run_id)
                if not run or run.get('stop'):
                    break
                subreddit = run.get('subreddit')
                keywords = run.get('keywords') or "open source help"
                self.current_runs[run_id]['status'] = 'processing'
                try:
                    from apps.agent.main import run_oss_agent
                    result = run_oss_agent(query=keywords, subreddit=subreddit)
                    posts = result.get('reddit_posts') or []
                    drafted_reply = result.get('drafted_reply') or ''
                    moderation = result.get('moderation_report') or {}

                    created = 0
                    for post in posts:
                        post_id = post.get('id')
                        if self.db.request_exists_by_post_id(post_id):
                            continue
                        self._persist_request_from_agent(post, drafted_reply, moderation)
                        created += 1
                    self.current_runs[run_id]['posts_found'] += len(posts)
                    self.current_runs[run_id]['replies_drafted'] += created
                except Exception as agent_err:
                    self.current_runs[run_id]['error'] = str(agent_err)
                    self.current_runs[run_id]['status'] = 'warning'
                
                # sleep until next polling
                for _ in range(cfg_interval):
                    time.sleep(1)
                    if self.current_runs.get(run_id, {}).get('stop'):
                        break
            self.current_runs[run_id]['status'] = 'completed'
            self.current_runs[run_id]['end_time'] = datetime.now()
        except Exception as e:
            if run_id in self.current_runs:
                self.current_runs[run_id]['status'] = 'failed'
                self.current_runs[run_id]['error'] = str(e)
    
    def get_run_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific agent run"""
        return self.current_runs.get(run_id)
    
    def get_all_active_runs(self) -> List[Dict[str, Any]]:
        """Get all currently active agent runs"""
        active_runs = []
        for run_id, run_data in self.current_runs.items():
            if run_data['status'] in ['running', 'processing']:
                run_data['id'] = run_id
                active_runs.append(run_data)
        return active_runs
    
    def stop_agent_run(self, run_id: str) -> bool:
        """Stop a specific agent run"""
        if run_id in self.current_runs:
            self.current_runs[run_id]['stop'] = True
            self.current_runs[run_id]['status'] = 'stopped'
            return True
        return False
    
    def process_single_request(self, query: str, subreddit: str, submission_id: Optional[str] = None) -> str:
        """
        Process a single request using the agent.
        Returns a run ID for tracking.
        """
        
        run_id = str(uuid.uuid4())
        self.current_runs[run_id] = {
            'type': 'single_request',
            'status': 'running',
            'query': query,
            'subreddit': subreddit,
            'submission_id': submission_id,
            'start_time': datetime.now()
        }
        
        thread = threading.Thread(target=self._run_single_request, args=(run_id,), daemon=True)
        thread.start()
        
        return run_id
    
    def _run_single_request(self, run_id: str):
        """Execute a single agent call and persist result"""
        try:
            run = self.current_runs.get(run_id)
            if not run:
                return
            query = run.get('query')
            subreddit = run.get('subreddit')

            self.current_runs[run_id]['status'] = 'searching'
            from apps.agent.main import run_oss_agent
            result = run_oss_agent(query=query, subreddit=subreddit)

            self.current_runs[run_id]['status'] = 'moderating'
            posts = result.get('reddit_posts') or []
            drafted_reply = result.get('drafted_reply') or ''
            moderation = result.get('moderation_report') or {}

            # Persist at least one pending request (first post if exists)
            if posts:
                self._persist_request_from_agent(posts[0], drafted_reply, moderation)
            else:
                # Create a generic request if no post list returned
                self._persist_request_from_agent({
                    'id': f'generated_{int(time.time())}',
                    'title': query,
                    'selftext': f'Generated based on query: {query}',
                    'url': f'https://reddit.com/r/{subreddit}/'
                }, drafted_reply, moderation)

            self.current_runs[run_id]['status'] = 'completed'
            self.current_runs[run_id]['end_time'] = datetime.now()
        except Exception as e:
            self.current_runs[run_id]['status'] = 'failed'
            self.current_runs[run_id]['error'] = str(e)
    
    def get_agent_health(self) -> Dict[str, Any]:
        """Get current agent health status"""
        
        # Simulate system health checks (lightweight without psutil here)
        return {
            'status': 'healthy',
            'uptime': str(datetime.now() - self.last_heartbeat).split('.')[0],
            'last_heartbeat': self.last_heartbeat,
            'memory_usage': 50,
            'cpu_usage': 15,
            'reddit_api_status': 'unknown',
            'rag_system_status': 'ready',
            'database_status': 'healthy',
            'active_runs': len(self.get_all_active_runs()),
            'total_requests_today': len(self.db.get_requests_by_filter({'limit': 1000})),
            'pending_approvals': len(self.db.get_pending_requests()),
            'dry_run': self.dry_run,
        }
    
    def update_heartbeat(self):
        """Update the agent heartbeat timestamp"""
        self.last_heartbeat = datetime.now()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get detailed system performance metrics (mocked)"""
        
        return {
            'response_times': {
                'avg_24h': 3.2,
                'p95_24h': 8.1,
                'p99_24h': 15.3
            },
            'success_rates': {
                'overall': 94.2,
                'last_hour': 96.8,
                'last_24h': 93.5
            },
            'api_usage': {
                'reddit_calls_today': 10,
                'llm_calls_today': 5,
                'llm_provider': os.getenv('LLM_PROVIDER', 'none').lower(),
                'rate_limit_remaining': 90
            },
            'database_stats': {
                'total_requests': len(self.db.get_requests_by_filter({'limit': 10000})),
                'total_approved': len([r for r in self.db.get_requests_by_filter({'limit': 10000}) if r['status']=='approved']),
                'total_rejected': len([r for r in self.db.get_requests_by_filter({'limit': 10000}) if r['status']=='rejected']),
                'pending': len(self.db.get_pending_requests())
            }
        }
    
    def trigger_manual_scan(self, subreddit: str, keywords: str = "") -> str:
        """Trigger a manual scan of a subreddit"""
        return self.start_agent_monitoring(subreddit, keywords)
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current agent configuration"""
        
        # In a real implementation, this would read from the actual config
        return {
            'dry_run_mode': True,
            'auto_approval': False,
            'confidence_threshold': 0.7,
            'scan_interval': 5,
            'max_requests_per_hour': 20,
            'monitored_subreddits': ['python', 'learnpython', 'django'],
            'moderation_enabled': True,
            'moderation_threshold': 0.5
        }
    
    def update_configuration(self, config: Dict[str, Any]) -> bool:
        """Update agent configuration"""
        
        # In a real implementation, this would update the actual config
        # For demo purposes, just return True
        return True

    def _persist_request_from_agent(self, post: Dict[str, Any], drafted_reply: str, moderation: Dict[str, Any]):
        """Persist a pending request derived from agent outputs"""
        request = {
            'id': str(uuid.uuid4()),
            'subreddit': post.get('subreddit') or 'unknown',
            'post_id': post.get('id'),
            'post_title': post.get('title') or 'Question',
            'post_content': post.get('selftext') or '',
            'post_author': post.get('author') or 'unknown',
            'post_url': post.get('url') or '',
            'status': 'pending',
            'drafted_reply': drafted_reply,
            'moderation_score': (1.0 - float(moderation.get('safety_score', 0.0))) if isinstance(moderation, dict) else 0.0,
            'agent_confidence': float(moderation.get('confidence', 0.75)) if isinstance(moderation, dict) else 0.75,
            'citations': []
        }
        try:
            request['citations'] = json.dumps(request['citations'])
        except Exception:
            request['citations'] = json.dumps([])
        # moderation_flags must be JSON-serializable list
        flags = []
        if isinstance(moderation, dict) and moderation.get('flags'):
            flags = moderation['flags']
        # Always pass list; DatabaseManager.add_request will JSON-encode it
        request['moderation_flags'] = flags
        self.db.add_request(request)

    def approve_request(self, request_id: str, final_reply: str, post_to_reddit: bool = True) -> Dict[str, Any]:
        """Approve a pending request and optionally post to Reddit via the agent tool.
        Respects DRY_RUN; when dry-run is enabled, it won't post to Reddit.
        Returns a result dict with posting status and messages.
        """
        req = self.db.get_request_by_id(request_id)
        if not req:
            return {"status": "error", "message": "Request not found"}
        # Update DB first with final reply and approved status
        self.db.update_request_status(request_id, 'approved', final_reply)
        self.db.log_user_action('approve', request_id, 'admin', {'posted': not self.dry_run and post_to_reddit})
        if not post_to_reddit or self.dry_run:
            return {"status": "dry_run", "message": "Approved (dry run), not posted to Reddit"}
        # Attempt to post to Reddit
        try:
            from apps.agent.main import post_reddit_reply_tool
            submission_id = req.get('post_id')
            if not submission_id:
                return {"status": "error", "message": "Missing Reddit submission ID"}
            result = post_reddit_reply_tool(submission_id=submission_id, reply_text=final_reply)
            # Optionally, we could update DB based on result
            return result or {"status": "unknown", "message": "No result returned"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def reject_request(self, request_id: str, reason: str = "") -> Dict[str, Any]:
        """Reject a pending request with optional reason"""
        req = self.db.get_request_by_id(request_id)
        if not req:
            return {"status": "error", "message": "Request not found"}
        self.db.update_request_status(request_id, 'rejected', human_feedback=reason)
        self.db.log_user_action('reject', request_id, 'admin', {'reason': reason})
        return {"status": "success", "message": "Request rejected"}

def generate_draft_with_ollama(query: str, model: str = "gemma3"):
    """Generate draft reply using Ollama running locally"""
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": f"Answer this Reddit question:\n\n{query}"}
        )
        data = resp.json()
        return data.get("response", "").strip()
    except Exception as e:
        return f"[Error generating draft: {e}]"

from groq import Groq

# Initialize the client once
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
if(groq_client is None):
    raise ValueError("GROQ_API_KEY environment variable is not set or invalid.")

def generate_draft_with_groq(query_text: str) -> str:
    """
    Generate a draft reply using Groq Python client (streaming version)
    """
    if not query_text:
        return ""

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a helpful AI agent drafting replies.you must cite your sources.answers must be accurate and safe and consise."},
                {"role": "user", "content": query_text}
            ],
            temperature=0.5,
            max_completion_tokens=1024,
            top_p=1,
            stream=True  # enable streaming chunks
        )

        # Collect streamed content
        draft_text = ""
        for chunk in completion:
            delta = chunk.choices[0].delta
            if delta and hasattr(delta, "content") and delta.content:
                draft_text += delta.content
                print(delta.content, end="")  # optional debug streaming
        print()  # newline after stream
        return draft_text.strip()

    except Exception as e:
        print(f"⚠️ Groq API error: {e}")
        return "⚠️ Unable to generate draft at the moment (Groq API error)."
    
def generate_reply(self, request_id: int):
    """Generate AI response for a single request"""
    req = self.db.get_request_by_id(request_id)
    if not req:
        return ""
    # Call Groq or your AI model here
    reply = generate_draft_with_groq(req["post_content"])  # implement your Groq function
    return reply

# Singleton instance for use throughout the UI
agent_integration = AgentIntegration()
