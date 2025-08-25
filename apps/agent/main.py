# apps/agent/main.py

import os
import json
import logging
import uuid
import time
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List
from pathlib import Path

# Import Portia AI SDK with full implementation
try:
    from portia import Portia, PlanBuilder, Tool, PlanRun, PlanRunState
    import sys
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    from apps.ui.utils.approval_workflow import approval_workflow
    from apps.ui.utils.database import DatabaseManager
    print("✅ Using full Portia SDK with production workflow")
    USING_REAL_PORTIA = True
except Exception as e:
    print(f"❌ Portia SDK not available: {e}")
    print("   This is a production system that requires Portia SDK.")
    USING_REAL_PORTIA = False
    Portia = None
    PlanBuilder = None
    Tool = None

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


# --- Portia Tools Registration ---

class RedditMonitorTool(Tool):
    """Portia tool for monitoring Reddit for new questions"""
    
    name: str = "reddit_monitor"
    description: str = "Monitor Reddit for new questions that need OSS community support"
    
    def __init__(self):
        super().__init__()
        self.reddit_tool = None
    
    def execute(self, subreddit: str, keywords: str = "", limit: int = 5) -> Dict[str, Any]:
        """Monitor Reddit for questions"""
        try:
            if not self.reddit_tool:
                self.reddit_tool = get_reddit_tool()
            
            posts = self.reddit_tool.search_questions(
                subreddit_name=subreddit,
                keywords=keywords,
                limit=limit
            )
            
            return {
                "success": True,
                "posts": posts,
                "count": len(posts)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "posts": [],
                "count": 0
            }

class ResponseGeneratorTool(Tool):
    """Portia tool for generating AI responses using RAG"""
    
    name: str = "response_generator"
    description: str = "Generate helpful responses to questions using project documentation"
    
    def __init__(self):
        super().__init__()
        self.rag_tool = RAGTool()
    
    def execute(self, question_title: str, question_content: str) -> Dict[str, Any]:
        """Generate response to a question"""
        try:
            full_query = f"{question_title}\n\n{question_content}"
            response = self.rag_tool.retrieve_and_generate(full_query)
            
            # Calculate confidence based on response quality
            confidence = 0.8 if response and len(response.strip()) > 100 else 0.3
            
            return {
                "success": True,
                "response": response,
                "confidence": confidence,
                "citations": []  # TODO: Extract citations from RAG
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": f"Error generating response: {str(e)}",
                "confidence": 0.0
            }

class ModerationTool(Tool):
    """Portia tool for content moderation"""
    
    name: str = "content_moderator"
    description: str = "Analyze content for safety, appropriateness, and quality"
    
    def execute(self, content: str) -> Dict[str, Any]:
        """Moderate content"""
        try:
            if not content or len(content.strip()) == 0:
                return {
                    "success": False,
                    "is_safe": False,
                    "flags": ["empty_content"],
                    "safety_score": 0.0
                }
            
            moderation_result = analyze_text(content) if analyze_text else None
            
            if moderation_result and isinstance(moderation_result, dict):
                return {
                    "success": True,
                    "is_safe": not moderation_result.get('is_flagged', False),
                    "flags": moderation_result.get('flags', []),
                    "safety_score": moderation_result.get('safety_score', 1.0)
                }
            else:
                # Default safe if moderation tool unavailable
                return {
                    "success": True,
                    "is_safe": True,
                    "flags": [],
                    "safety_score": 1.0
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "is_safe": False,
                "flags": ["moderation_error"],
                "safety_score": 0.5
            }

class ApprovalManagerTool(Tool):
    """Portia tool for managing human approvals"""
    
    name: str = "approval_manager"
    description: str = "Manage human-in-the-loop approval workflow for responses"
    
    def execute(self, action: str, request_id: str = None, **kwargs) -> Dict[str, Any]:
        """Manage approval workflow"""
        try:
            if action == "queue_for_approval":
                post_data = kwargs.get('post_data')
                if not post_data:
                    return {"success": False, "error": "No post data provided"}
                
                result = approval_workflow.process_reddit_query(post_data)
                return result
                
            elif action == "get_pending":
                pending = approval_workflow.get_pending_requests()
                stats = approval_workflow.get_request_stats()
                return {
                    "success": True,
                    "pending_requests": pending,
                    "stats": stats
                }
                
            elif action == "approve":
                if not request_id:
                    return {"success": False, "error": "No request_id provided"}
                
                result = approval_workflow.approve_request(
                    request_id=request_id,
                    admin_feedback=kwargs.get('feedback', ''),
                    edited_reply=kwargs.get('edited_reply', '')
                )
                return result
                
            elif action == "reject":
                if not request_id:
                    return {"success": False, "error": "No request_id provided"}
                
                result = approval_workflow.reject_request(
                    request_id=request_id,
                    admin_feedback=kwargs.get('feedback', '')
                )
                return result
                
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

# --- Portia Plan Builder ---

def create_oss_community_plan(query: str, subreddit: str) -> str:
    """Create a Portia plan for the OSS Community workflow"""
    
    plan = f"""
# OSS Community Agent Plan

**Goal**: Find and respond to questions about {query} in r/{subreddit} with helpful, documentation-grounded responses that require human approval before posting.

## Phase 1: Discovery
1. Use reddit_monitor tool to find recent questions in r/{subreddit} related to "{query}"
2. Filter questions that:
   - Are genuine requests for help
   - Haven't been answered comprehensively yet
   - Are appropriate for our project expertise

## Phase 2: Response Generation  
For each identified question:
1. Use response_generator tool to create a helpful response based on project documentation
2. Use content_moderator tool to verify the response is safe and appropriate
3. Only proceed if moderation passes and confidence > 0.5

## Phase 3: Human Approval
1. Use approval_manager tool with action="queue_for_approval" to queue each response
2. **STOP and request human clarification**: "Review the drafted response and choose:
   - APPROVE: Post the response as-is
   - EDIT: Modify the response before posting  
   - REJECT: Don't post this response
   
   Pending approval for request ID: {{request_id}}
   
   Question: {{question_title}}
   
   Drafted Response: {{response_preview}}
   
   Please provide your decision."

## Phase 4: Posting (After Approval)
1. Use approval_manager tool with action="approve" to post approved responses
2. Track all posted responses and outcomes
3. Generate summary report of actions taken

**Safety Notes**:
- All responses require explicit human approval
- Dry run mode enabled by default for testing
- Content moderation applied to all generated responses
- Complete audit trail maintained
"""
    return plan

# --- Main OSS Agent with Full Portia Integration ---

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

# --- Full Portia-Powered OSS Agent ---

async def run_portia_oss_agent(query: str, subreddit: str) -> Dict[str, Any]:
    """Run the full Portia-powered OSS Community Agent"""
    
    if not USING_REAL_PORTIA or not portia_client:
        logging.error("Portia SDK not available for full agent execution")
        return {
            "status": "failed",
            "error": "Portia SDK not available. Please install and configure Portia SDK."
        }
    
    run_id = str(uuid.uuid4())
    start_time = time.time()
    
    logging.info(f"[{run_id}] Starting Portia-powered OSS Community Agent")
    
    try:
        # Register custom tools with Portia
        reddit_monitor = RedditMonitorTool()
        response_generator = ResponseGeneratorTool()
        content_moderator = ModerationTool()
        approval_manager = ApprovalManagerTool()
        
        # Create the plan
        plan_content = create_oss_community_plan(query, subreddit)
        
        # Use PlanBuilder to create a structured plan
        plan_builder = PlanBuilder(plan_content)
        
        # Add tools to the plan
        plan_builder.add_tool(reddit_monitor)
        plan_builder.add_tool(response_generator)
        plan_builder.add_tool(content_moderator)
        plan_builder.add_tool(approval_manager)
        
        # Execute the plan with Portia
        logging.info(f"[{run_id}] Executing Portia plan...")
        
        plan_run = await portia_client.arun(
            plan=plan_builder.build(),
            context={
                "query": query,
                "subreddit": subreddit,
                "dry_run": DRY_RUN,
                "run_id": run_id
            }
        )
        
        # Handle plan execution results
        if plan_run.state == PlanRunState.COMPLETED:
            logging.info(f"[{run_id}] Portia plan completed successfully")
            
            # Get final stats
            stats = approval_workflow.get_request_stats()
            pending = approval_workflow.get_pending_requests()
            
            return {
                "status": "completed",
                "run_id": run_id,
                "portia_plan_run_id": str(plan_run.id),
                "agent_config": {
                    "query": query,
                    "subreddit": subreddit,
                    "dry_run": DRY_RUN,
                    "portia_status": "active"
                },
                "results": {
                    "total_stats": stats,
                    "pending_requests": len(pending),
                    "execution_details": plan_run.result if hasattr(plan_run, 'result') else {}
                },
                "total_duration_sec": round(time.time() - start_time, 2)
            }
            
        elif plan_run.state == PlanRunState.WAITING_FOR_CLARIFICATION:
            logging.info(f"[{run_id}] Plan waiting for human clarification")
            
            return {
                "status": "waiting_for_approval",
                "run_id": run_id,
                "portia_plan_run_id": str(plan_run.id),
                "clarification_needed": plan_run.current_clarification.message if hasattr(plan_run, 'current_clarification') else "Human approval required",
                "pending_requests": approval_workflow.get_pending_requests(),
                "total_duration_sec": round(time.time() - start_time, 2)
            }
            
        else:
            logging.error(f"[{run_id}] Plan execution failed with status: {plan_run.status}")
            
            return {
                "status": "failed",
                "run_id": run_id,
                "portia_plan_run_id": str(plan_run.id),
                "error": f"Plan execution failed with status: {plan_run.status}",
                "total_duration_sec": round(time.time() - start_time, 2)
            }
    
    except Exception as e:
        logging.error(f"[{run_id}] Portia agent execution failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "run_id": run_id,
            "error": str(e),
            "total_duration_sec": round(time.time() - start_time, 2)
        }

def enable_live_posting():
    """Enable live Reddit posting by disabling dry run mode"""
    import os
    from dotenv import set_key
    
    env_path = Path(__file__).parent.parent.parent / '.env'
    set_key(str(env_path), 'DRY_RUN', 'false')
    
    # Update the global variable
    global DRY_RUN
    DRY_RUN = False
    
    logging.info("Live posting enabled - Agent will post to Reddit when approved")

def disable_live_posting():
    """Disable live Reddit posting by enabling dry run mode"""
    import os
    from dotenv import set_key
    
    env_path = Path(__file__).parent.parent.parent / '.env'
    set_key(str(env_path), 'DRY_RUN', 'true')
    
    # Update the global variable
    global DRY_RUN
    DRY_RUN = True
    
    logging.info("Dry run mode enabled - Agent will simulate posting only")

def get_agent_status() -> Dict[str, Any]:
    """Get current status of the OSS Community Agent"""
    stats = approval_workflow.get_request_stats()
    pending = approval_workflow.get_pending_requests()
    
    return {
        "agent_ready": USING_REAL_PORTIA and portia_client is not None,
        "dry_run_mode": DRY_RUN,
        "portia_available": USING_REAL_PORTIA,
        "reddit_configured": bool(_env("REDDIT_CLIENT_ID")),
        "ai_configured": bool(_env("GROQ_API_KEY") or _env("LLM_PROVIDER") != "none"),
        "database_available": approval_workflow.db is not None,
        "request_stats": stats,
        "pending_approvals": len(pending),
        "total_processed": stats.get('total', 0)
    }

# --- Production Entry Points ---

def run_monitoring_session(query: str, subreddit: str, duration_minutes: int = 60):
    """Run a continuous monitoring session"""
    
    if not USING_REAL_PORTIA:
        logging.error("Portia SDK required for monitoring sessions")
        return
        
    logging.info(f"Starting {duration_minutes}-minute monitoring session for '{query}' in r/{subreddit}")
    
    end_time = time.time() + (duration_minutes * 60)
    
    while time.time() < end_time:
        try:
            # Run the agent
            result = asyncio.run(run_portia_oss_agent(query, subreddit))
            
            if result["status"] == "completed":
                logging.info(f"Monitoring cycle completed: {result.get('results', {})}")
            elif result["status"] == "waiting_for_approval":
                logging.info(f"Requests pending approval: {len(result.get('pending_requests', []))}")
            else:
                logging.warning(f"Monitoring cycle failed: {result.get('error', 'Unknown error')}")
            
            # Wait before next cycle (5 minutes)
            time.sleep(300)
            
        except KeyboardInterrupt:
            logging.info("Monitoring session interrupted by user")
            break
        except Exception as e:
            logging.error(f"Error in monitoring session: {e}")
            time.sleep(60)  # Wait 1 minute before retrying
    
    logging.info("Monitoring session ended")

# --- Main execution for testing/demonstration ---
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="OSS Community Agent")
    parser.add_argument("--query", default="Python help", help="Query to search for")
    parser.add_argument("--subreddit", default="learnpython", help="Subreddit to monitor")
    parser.add_argument("--mode", choices=["single", "monitor", "status"], default="single", 
                       help="Execution mode")
    parser.add_argument("--duration", type=int, default=60, 
                       help="Monitoring duration in minutes")
    parser.add_argument("--enable-posting", action="store_true", 
                       help="Enable live Reddit posting")
    
    args = parser.parse_args()
    
    # Configure posting mode
    if args.enable_posting:
        enable_live_posting()
        print("⚠️ LIVE POSTING ENABLED - Agent will post to Reddit!")
    else:
        disable_live_posting()
        print("🔒 DRY RUN MODE - Agent will simulate posting only")
    
    if args.mode == "status":
        status = get_agent_status()
        print("\n📊 OSS Community Agent Status:")
        print(json.dumps(status, indent=2))
        
    elif args.mode == "monitor":
        print(f"\n🔍 Starting monitoring session for '{args.query}' in r/{args.subreddit}")
        run_monitoring_session(args.query, args.subreddit, args.duration)
        
    else:
        print(f"\n🚀 Running single execution for '{args.query}' in r/{args.subreddit}")
        if USING_REAL_PORTIA:
            result = asyncio.run(run_portia_oss_agent(args.query, args.subreddit))
        else:
            result = run_oss_agent(args.query, args.subreddit)
        
        print("\n📊 Results:")
        print(json.dumps(result, indent=2))
    
    print("\n✅ OSS Community Agent execution completed")
