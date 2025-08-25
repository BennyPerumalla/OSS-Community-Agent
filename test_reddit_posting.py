#!/usr/bin/env python3
"""
Test script to validate the complete Reddit workflow including posting.
This script tests the end-to-end functionality with proper error handling.
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_reddit_credentials():
    """Test if Reddit credentials are properly configured"""
    print("🔑 Testing Reddit API Credentials...")
    
    required_vars = ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 'REDDIT_USERNAME', 'REDDIT_PASSWORD']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value == 'your_client_id' or value == 'your_client_secret' or value == 'your_username' or value == 'your_password':
            missing_vars.append(var)
        else:
            print(f"  ✅ {var}: Configured")
    
    if missing_vars:
        print(f"  ❌ Missing or placeholder values: {', '.join(missing_vars)}")
        return False
    
    return True

def test_reddit_connection():
    """Test Reddit API connection"""
    print("\n📡 Testing Reddit API Connection...")
    
    try:
        from tools.reddit_tool import RedditTool
        
        reddit_tool = RedditTool(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD"),
            user_agent=f"oss-community-agent/1.0 (by u/{os.getenv('REDDIT_USERNAME')})"
        )
        
        # Try a simple search
        posts = reddit_tool.search_questions("learnpython", "python help", limit=2)
        print(f"  ✅ Successfully connected! Found {len(posts)} posts")
        
        if posts:
            print(f"  📝 Sample post: '{posts[0]['title'][:50]}...'")
        
        return True, reddit_tool, posts
        
    except Exception as e:
        print(f"  ❌ Reddit connection failed: {e}")
        return False, None, []

def test_approval_workflow():
    """Test the approval workflow system"""
    print("\n🔄 Testing Approval Workflow System...")
    
    try:
        from apps.ui.utils.approval_workflow import approval_workflow
        
        # Test with a sample post
        sample_post = {
            'id': 'test_post_123',
            'title': 'How do I install Python packages?',
            'selftext': 'I am new to Python and need help installing packages with pip. Can someone help?',
            'subreddit': 'learnpython',
            'author': 'test_user',
            'url': 'https://reddit.com/r/learnpython/test_post_123'
        }
        
        print("  📝 Processing sample Reddit query...")
        result = approval_workflow.process_reddit_query(sample_post)
        
        if result['success']:
            print(f"  ✅ Request processed successfully!")
            print(f"     Request ID: {result['request_id']}")
            print(f"     Confidence: {result['confidence']}")
            print(f"     Draft length: {len(result.get('drafted_reply', ''))}")
            
            # Get pending requests
            pending = approval_workflow.get_pending_requests()
            print(f"  📋 Pending requests: {len(pending)}")
            
            return True, result['request_id']
        else:
            print(f"  ❌ Failed to process request: {result['error']}")
            return False, None
            
    except Exception as e:
        print(f"  ❌ Approval workflow test failed: {e}")
        return False, None

def test_approval_and_posting(request_id):
    """Test the approval and Reddit posting functionality"""
    print(f"\n✅ Testing Approval and Posting for Request {request_id[:8]}...")
    
    try:
        from apps.ui.utils.approval_workflow import approval_workflow
        
        # Check dry run status
        dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
        print(f"  🛡️ Dry Run Mode: {'ON' if dry_run else 'OFF'}")
        
        if not dry_run:
            print("  ⚠️  WARNING: Dry run is OFF - this will make real Reddit posts!")
            response = input("  Continue with live posting? (y/N): ")
            if response.lower() != 'y':
                print("  ℹ️  Switching to dry run mode for safety")
                os.environ["DRY_RUN"] = "true"
        
        print("  👤 Simulating admin approval...")
        approval_result = approval_workflow.approve_request(
            request_id=request_id,
            admin_feedback="Approved via automated testing - response looks helpful",
            edited_reply=""  # Use original draft
        )
        
        if approval_result['success']:
            print("  🎉 Approval processed successfully!")
            
            if approval_result['reddit_posted']:
                print(f"  📱 Posted to Reddit! Reply ID: {approval_result['reddit_reply_id']}")
                if dry_run:
                    print("  🛡️  (Simulated in dry run mode)")
                else:
                    print("  🌐 Real post made to Reddit!")
            else:
                print("  ⚠️  Approved but not posted (may already exist or other issue)")
                
            return True
        else:
            print(f"  ❌ Approval failed: {approval_result['error']}")
            return False
            
    except Exception as e:
        print(f"  ❌ Approval/posting test failed: {e}")
        return False

def test_complete_workflow():
    """Test the complete integrated workflow"""
    print("\n🚀 Testing Complete Agent Workflow...")
    
    try:
        from apps.agent.main import run_oss_agent
        
        print("  🤖 Running OSS Community Agent...")
        result = run_oss_agent(
            query="python help installation",
            subreddit="learnpython"
        )
        
        if result['status'] == 'completed':
            print("  ✅ Agent workflow completed successfully!")
            print(f"     Posts processed: {result.get('reddit_search', {}).get('posts_processed', 0)}")
            print(f"     Pending approvals: {result.get('approval_queue', {}).get('pending_count', 0)}")
            print(f"     Duration: {result.get('total_duration_sec', 0)}s")
            return True
        else:
            print(f"  ❌ Agent workflow failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"  ❌ Complete workflow test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 OSS Community Agent - Complete System Test")
    print("=" * 60)
    
    # Test 1: Credentials
    if not test_reddit_credentials():
        print("\n❌ Reddit credentials not configured. Please update your .env file.")
        print("   You need to:")
        print("   1. Create a Reddit app at https://www.reddit.com/prefs/apps")
        print("   2. Get your client_id and client_secret") 
        print("   3. Update REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD in .env")
        print("\nFor now, continuing with tests that don't require Reddit API...")
    
    # Test 2: Reddit Connection (may fail if credentials not set)
    reddit_success, reddit_tool, posts = test_reddit_connection()
    
    # Test 3: Approval Workflow (should work regardless of Reddit)
    workflow_success, request_id = test_approval_workflow()
    
    # Test 4: Approval and Posting
    if workflow_success and request_id:
        posting_success = test_approval_and_posting(request_id)
    else:
        posting_success = False
        print("\n⏭️  Skipping posting test (no request to approve)")
    
    # Test 5: Complete Workflow
    complete_success = test_complete_workflow()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    tests = [
        ("Reddit Credentials", test_reddit_credentials()),
        ("Reddit Connection", reddit_success),
        ("Approval Workflow", workflow_success),
        ("Posting System", posting_success),
        ("Complete Integration", complete_success)
    ]
    
    for test_name, success in tests:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    passed = sum(1 for _, success in tests if success)
    total = len(tests)
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All systems working! Your OSS Community Agent is ready!")
    elif workflow_success:
        print("🔧 Core functionality works! Just need to configure Reddit API for live posting.")
    else:
        print("🚨 Some issues detected. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    main()
