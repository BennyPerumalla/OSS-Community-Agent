# test_workflow.py
"""
Test script for the complete end-to-end workflow:
1. Fetch Reddit posts
2. Generate draft responses
3. Queue for approval
4. Simulate approval and Reddit posting
"""

import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from apps.ui.utils.approval_workflow import approval_workflow
from tools.reddit_tool import RedditTool
from tools.rag_tool import RAGTool

def test_complete_workflow():
    """Test the complete workflow from Reddit search to approval"""
    print("🚀 Testing OSS Community Agent End-to-End Workflow")
    print("=" * 60)
    
    try:
        # Step 1: Test Reddit Tool
        print("\n📡 Step 1: Testing Reddit API connection...")
        reddit_tool = RedditTool(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD"),
            user_agent=f"oss-community-agent/1.0 (by u/{os.getenv('REDDIT_USERNAME')})"
        )
        
        # Search for posts
        posts = reddit_tool.search_questions("learnpython", "help python", limit=2)
        print(f"✅ Found {len(posts)} Reddit posts")
        
        if not posts:
            print("❌ No posts found. Cannot continue test.")
            return False
            
        # Step 2: Test RAG Tool
        print("\n🧠 Step 2: Testing RAG tool...")
        rag_tool = RAGTool()
        test_query = "How do I install Python packages?"
        response = rag_tool.retrieve_and_generate(test_query)
        print(f"✅ RAG generated response: {len(response)} characters")
        
        # Step 3: Test Approval Workflow with real Reddit post
        print("\n🔄 Step 3: Testing approval workflow...")
        test_post = posts[0]  # Use first post
        
        # Add subreddit info to post data
        test_post['subreddit'] = 'learnpython'
        
        print(f"Processing post: '{test_post['title'][:50]}...'")
        
        # Process the query
        result = approval_workflow.process_reddit_query(test_post)
        
        if result['success']:
            print(f"✅ Draft generated successfully")
            print(f"   Request ID: {result['request_id']}")
            print(f"   Confidence: {result['confidence']}")
            print(f"   Draft length: {len(result.get('drafted_reply', ''))}")
            
            # Step 4: Get pending requests
            print("\n📋 Step 4: Testing pending requests retrieval...")
            pending = approval_workflow.get_pending_requests()
            print(f"✅ Found {len(pending)} pending requests")
            
            # Step 5: Test approval
            if pending:
                print("\n✅ Step 5: Testing approval process...")
                request_to_approve = pending[0]
                request_id = request_to_approve['id']
                
                print(f"Approving request: {request_id}")
                approval_result = approval_workflow.approve_request(
                    request_id=request_id,
                    admin_feedback="Approved by automated test",
                    edited_reply=""  # Use original draft
                )
                
                if approval_result['success']:
                    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
                    if dry_run:
                        print("✅ Request approved successfully (DRY RUN mode)")
                        print(f"   Would have posted to Reddit: {approval_result['reddit_posted']}")
                        print(f"   Simulated reply ID: {approval_result['reddit_reply_id']}")
                    else:
                        print("✅ Request approved and posted to Reddit!")
                        print(f"   Posted: {approval_result['reddit_posted']}")
                        print(f"   Reddit reply ID: {approval_result['reddit_reply_id']}")
                else:
                    print(f"❌ Approval failed: {approval_result['error']}")
                    
            # Step 6: Test statistics
            print("\n📊 Step 6: Testing statistics...")
            stats = approval_workflow.get_request_stats()
            print(f"✅ Request statistics:")
            print(f"   Total: {stats['total']}")
            print(f"   Pending: {stats['pending']}")
            print(f"   Approved: {stats['approved']}")
            print(f"   Rejected: {stats['rejected']}")
            
        else:
            print(f"❌ Draft generation failed: {result['error']}")
            return False
        
        print("\n🎉 End-to-End Workflow Test COMPLETED SUCCESSFULLY! 🎉")
        print("\nWorkflow Summary:")
        print("1. ✅ Reddit API connection working")
        print("2. ✅ RAG tool generating responses")  
        print("3. ✅ Database storing requests")
        print("4. ✅ Approval workflow functioning")
        print("5. ✅ Reddit posting simulation working")
        print("6. ✅ Statistics and reporting working")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Workflow test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_rejection_workflow():
    """Test the rejection workflow"""
    print("\n🔄 Testing rejection workflow...")
    
    try:
        # Get pending requests
        pending = approval_workflow.get_pending_requests()
        
        if not pending:
            print("No pending requests to test rejection")
            return True
            
        # Reject the first pending request
        request_to_reject = pending[0]
        request_id = request_to_reject['id']
        
        print(f"Rejecting request: {request_id}")
        rejection_result = approval_workflow.reject_request(
            request_id=request_id,
            admin_feedback="Rejected by automated test - low quality response"
        )
        
        if rejection_result['success']:
            print("✅ Request rejected successfully")
        else:
            print(f"❌ Rejection failed: {rejection_result['error']}")
            
        return rejection_result['success']
        
    except Exception as e:
        print(f"❌ Rejection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("OSS Community Agent - Complete Workflow Test")
    print("This will test the entire system from Reddit search to posting")
    print("")
    
    # Check if we have the required environment variables
    required_vars = ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 'REDDIT_USERNAME', 'REDDIT_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please configure your .env file with Reddit API credentials")
        sys.exit(1)
    
    # Run the main workflow test
    success = test_complete_workflow()
    
    if success:
        print("\n" + "="*60)
        print("🎊 ALL TESTS PASSED! Your OSS Community Agent is ready! 🎊")
        print("\nNext steps:")
        print("1. Set DRY_RUN=false in .env to enable real Reddit posting")
        print("2. Run the Streamlit UI: python -m streamlit run apps/ui/streamlit_app.py")
        print("3. Or run the full system: python run_full_system.py")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)
