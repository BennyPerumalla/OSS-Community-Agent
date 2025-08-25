# apps/ui/utils/approval_workflow.py

import os
import sys
import logging
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

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

# Load environment variables
load_dotenv()

def markdown_to_plain_text(text: str) -> str:
    """
    Convert markdown text to plain text suitable for Reddit posting.
    
    This removes markdown formatting while preserving readability:
    - Headers become plain text with newlines
    - Bold/italic formatting is removed but text preserved
    - Links are converted to plain text with URL shown
    - Lists are converted to simple bullet points
    - Code blocks become plain text
    """
    if not text:
        return text
    
    # Remove code blocks (triple backticks)
    text = re.sub(r'```[\s\S]*?```', lambda m: m.group(0).replace('```', '').strip(), text)
    
    # Remove inline code (single backticks)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Convert headers to plain text with emphasis
    text = re.sub(r'^#{1,6}\s*(.+)$', r'\1\n\n', text, flags=re.MULTILINE)
    
    # Remove bold and italic formatting but keep the text
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
    text = re.sub(r'__([^_]+)__', r'\1', text)      # __bold__
    text = re.sub(r'_([^_]+)_', r'\1', text)        # _italic_
    
    # Convert links [text](url) to "text (url)"
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', text)
    
    # Convert bullet points
    text = re.sub(r'^[\s]*[-*+]\s+', '• ', text, flags=re.MULTILINE)
    
    # Convert numbered lists
    text = re.sub(r'^[\s]*\d+\.\s+', '• ', text, flags=re.MULTILINE)
    
    # Remove remaining markdown artifacts
    text = re.sub(r'[\*_~`]', '', text)
    
    # Clean up excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)
    
    return text.strip()

class ApprovalWorkflow:
    """
    Manages the complete approval workflow:
    1. Generate draft responses
    2. Queue for human approval
    3. Post approved responses to Reddit
    4. Track all actions and outcomes
    """
    
    def __init__(self):
        self.db = DatabaseManager() if DatabaseManager else None
        self._reddit_tool = None
        self._rag_tool = None
        
    def _get_reddit_tool(self) -> Optional[RedditTool]:
        """Lazy initialization of Reddit tool"""
        if self._reddit_tool is None and RedditTool:
            try:
                reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
                reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET") 
                reddit_username = os.getenv("REDDIT_USERNAME")
                reddit_password = os.getenv("REDDIT_PASSWORD")
                
                if all([reddit_client_id, reddit_client_secret, reddit_username, reddit_password]):
                    self._reddit_tool = RedditTool(
                        client_id=reddit_client_id,
                        client_secret=reddit_client_secret,
                        username=reddit_username,
                        password=reddit_password,
                        user_agent=f"oss-community-agent/1.0 (by u/{reddit_username})"
                    )
                    logger.info("Reddit tool initialized successfully")
                else:
                    logger.warning("Reddit credentials not configured")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit tool: {e}")
        
        return self._reddit_tool
    
    def _get_rag_tool(self) -> Optional[RAGTool]:
        """Lazy initialization of RAG tool"""
        if self._rag_tool is None and RAGTool:
            try:
                self._rag_tool = RAGTool()
                logger.info("RAG tool initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize RAG tool: {e}")
                
        return self._rag_tool
    
    def process_reddit_query(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a Reddit query through the complete workflow:
        1. Generate draft response using RAG
        2. Moderate the response  
        3. Queue for human approval
        
        Args:
            post_data: Dictionary containing Reddit post information
            
        Returns:
            Dictionary with processing results and request ID
        """
        result = {
            "success": False,
            "request_id": None,
            "error": None,
            "drafted_reply": None,
            "moderation_flags": [],
            "confidence": 0.0
        }
        
        try:
            # Generate unique request ID
            request_id = str(uuid.uuid4())
            
            # Extract query text from post
            query_text = f"{post_data.get('title', '')}\n\n{post_data.get('selftext', '')}"
            
            # Generate draft response using RAG
            rag_tool = self._get_rag_tool()
            drafted_reply = ""
            confidence = 0.0
            
            if rag_tool:
                try:
                    drafted_reply = rag_tool.retrieve_and_generate(query_text)
                    if drafted_reply and len(drafted_reply.strip()) > 0:
                        confidence = 0.8  # High confidence for successful generation
                    else:
                        confidence = 0.2  # Low confidence for empty/poor responses
                        drafted_reply = "Unable to generate a comprehensive response based on available documentation."
                except Exception as e:
                    logger.warning(f"RAG generation failed: {e}")
                    drafted_reply = f"Error generating response: {str(e)}"
                    confidence = 0.0
            else:
                drafted_reply = "RAG tool not available. Please configure the system properly."
                confidence = 0.0
            
            # Moderate the drafted response
            moderation_flags = []
            moderation_score = 1.0  # Default to safe
            
            if analyze_text and drafted_reply:
                try:
                    moderation_result = analyze_text(drafted_reply)
                    if isinstance(moderation_result, dict):
                        if moderation_result.get('is_flagged', False):
                            moderation_flags = moderation_result.get('flags', [])
                            moderation_score = moderation_result.get('safety_score', 0.5)
                        else:
                            moderation_score = moderation_result.get('safety_score', 1.0)
                except Exception as e:
                    logger.warning(f"Moderation failed: {e}")
                    moderation_flags.append("moderation_error")
                    moderation_score = 0.5
            
            # Create request record
            request_data = {
                "id": request_id,
                "subreddit": post_data.get('subreddit', 'unknown'),
                "post_id": post_data.get('id'),
                "post_title": post_data.get('title', ''),
                "post_content": post_data.get('selftext', ''),
                "post_author": post_data.get('author', 'unknown'),
                "post_url": post_data.get('url', ''),
                "status": "pending",
                "drafted_reply": drafted_reply,
                "moderation_score": moderation_score,
                "moderation_flags": moderation_flags,
                "agent_confidence": confidence,
                "citations": [],
                "created_at": datetime.now().isoformat()
            }
            
            # Store in database
            if self.db:
                try:
                    self.db.insert_request(request_data)
                    self.db.log_user_action(
                        action_type="draft_generated",
                        request_id=request_id,
                        action_data={
                            "confidence": confidence,
                            "moderation_score": moderation_score,
                            "flags": moderation_flags
                        }
                    )
                    logger.info(f"Request {request_id} queued for approval")
                except Exception as e:
                    logger.error(f"Database error: {e}")
                    result["error"] = f"Database error: {str(e)}"
                    return result
            else:
                logger.warning("Database not available - request not stored")
                result["error"] = "Database not available"
                return result
            
            # Update result
            result.update({
                "success": True,
                "request_id": request_id,
                "drafted_reply": drafted_reply,
                "moderation_flags": moderation_flags,
                "confidence": confidence
            })
            
        except Exception as e:
            logger.error(f"Error processing Reddit query: {e}")
            result["error"] = str(e)
        
        return result
    
    def approve_request(self, request_id: str, admin_feedback: str = "", edited_reply: str = "") -> Dict[str, Any]:
        """
        Approve a pending request and post it to Reddit
        
        Args:
            request_id: ID of the request to approve
            admin_feedback: Optional feedback from admin
            edited_reply: Optional edited version of the reply
            
        Returns:
            Dictionary with approval results
        """
        result = {
            "success": False,
            "reddit_posted": False,
            "error": None,
            "reddit_reply_id": None
        }
        
        try:
            if not self.db:
                result["error"] = "Database not available"
                return result
            
            # Get the request
            request = self.db.get_request_by_id(request_id)
            if not request:
                result["error"] = "Request not found"
                return result
            
            if request['status'] != 'pending':
                result["error"] = f"Request status is '{request['status']}', not pending"
                return result
            
            # Use edited reply if provided, otherwise use original draft
            final_reply = edited_reply.strip() if edited_reply else request['drafted_reply']
            
            if not final_reply:
                result["error"] = "No reply content to post"
                return result
            
            # Convert markdown to plain text for Reddit posting
            final_reply = markdown_to_plain_text(final_reply)
            
            # Check if dry run mode
            dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
            
            if dry_run:
                # Simulate Reddit posting in dry run mode
                logger.info(f"DRY RUN: Would post reply to {request['post_id']}")
                reddit_result = {
                    "status": "success",
                    "message": "DRY RUN: Reply simulated successfully",
                    "reply_id": f"dry_run_{request_id[:8]}",
                    "submission_id": request['post_id']
                }
            else:
                # Actually post to Reddit
                reddit_tool = self._get_reddit_tool()
                if not reddit_tool:
                    result["error"] = "Reddit tool not available"
                    return result
                
                logger.info(f"Posting reply to Reddit post {request['post_id']}")
                reddit_result = reddit_tool.post_reply(request['post_id'], final_reply)
            
            # Check Reddit posting result
            if reddit_result.get("status") == "success":
                # Update request status to approved and posted
                self.db.update_request_status(
                    request_id=request_id,
                    status="approved",
                    final_reply=final_reply,
                    human_feedback=admin_feedback
                )
                
                # Log the action
                self.db.log_user_action(
                    action_type="request_approved",
                    request_id=request_id,
                    action_data={
                        "reddit_reply_id": reddit_result.get("reply_id"),
                        "admin_feedback": admin_feedback,
                        "edited": bool(edited_reply),
                        "dry_run": dry_run
                    }
                )
                
                result.update({
                    "success": True,
                    "reddit_posted": True,
                    "reddit_reply_id": reddit_result.get("reply_id")
                })
                
                logger.info(f"Request {request_id} approved and posted successfully")
                
            elif reddit_result.get("status") == "skipped":
                # Already replied - still mark as approved but don't post again
                self.db.update_request_status(
                    request_id=request_id,
                    status="approved",
                    final_reply=final_reply,
                    human_feedback=f"{admin_feedback}\nNote: Already replied to this post"
                )
                
                result.update({
                    "success": True,
                    "reddit_posted": False,
                    "error": "Already replied to this post"
                })
                
            else:
                # Reddit posting failed
                error_msg = reddit_result.get("message", "Unknown Reddit error")
                logger.error(f"Reddit posting failed: {error_msg}")
                
                # Update status to error
                self.db.update_request_status(
                    request_id=request_id,
                    status="error",
                    human_feedback=f"Reddit posting failed: {error_msg}"
                )
                
                result["error"] = f"Reddit posting failed: {error_msg}"
            
        except Exception as e:
            logger.error(f"Error approving request: {e}")
            result["error"] = str(e)
            
            # Try to update status to error
            if self.db:
                try:
                    self.db.update_request_status(
                        request_id=request_id,
                        status="error",
                        human_feedback=f"Approval error: {str(e)}"
                    )
                except:
                    pass
        
        return result
    
    def reject_request(self, request_id: str, admin_feedback: str = "") -> Dict[str, Any]:
        """
        Reject a pending request
        
        Args:
            request_id: ID of the request to reject
            admin_feedback: Reason for rejection
            
        Returns:
            Dictionary with rejection results
        """
        result = {
            "success": False,
            "error": None
        }
        
        try:
            if not self.db:
                result["error"] = "Database not available"
                return result
            
            # Get the request
            request = self.db.get_request_by_id(request_id)
            if not request:
                result["error"] = "Request not found"
                return result
            
            if request['status'] != 'pending':
                result["error"] = f"Request status is '{request['status']}', not pending"
                return result
            
            # Update request status to rejected
            self.db.update_request_status(
                request_id=request_id,
                status="rejected",
                human_feedback=admin_feedback or "Rejected by admin"
            )
            
            # Log the action
            self.db.log_user_action(
                action_type="request_rejected",
                request_id=request_id,
                action_data={
                    "admin_feedback": admin_feedback
                }
            )
            
            result["success"] = True
            logger.info(f"Request {request_id} rejected")
            
        except Exception as e:
            logger.error(f"Error rejecting request: {e}")
            result["error"] = str(e)
        
        return result
    
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all requests pending approval"""
        if not self.db:
            return []
        
        try:
            return self.db.get_pending_requests()
        except Exception as e:
            logger.error(f"Error getting pending requests: {e}")
            return []
    
    def get_request_stats(self) -> Dict[str, Any]:
        """Get statistics about requests"""
        if not self.db:
            return {
                "total": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "error": 0
            }
        
        try:
            # Get counts by status
            all_requests = self.db.get_requests_by_filter({"limit": 1000})
            stats = {
                "total": len(all_requests),
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "error": 0
            }
            
            for request in all_requests:
                status = request.get('status', 'unknown')
                if status in stats:
                    stats[status] += 1
                    
            return stats
            
        except Exception as e:
            logger.error(f"Error getting request stats: {e}")
            return {
                "total": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "error": 0
            }

# Create global instance
approval_workflow = ApprovalWorkflow()
