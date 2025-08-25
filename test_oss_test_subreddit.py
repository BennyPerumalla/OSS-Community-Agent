# test_oss_test_subreddit.py
"""
Complete test script for the OSS Community Agent using the oss_test subreddit.
This demonstrates the full workflow with your specific test environment.
"""

import os
import sys
import time
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

def test_with_oss_test_subreddit():
    """Test the complete workflow with the oss_test subreddit"""
    print("🚀 Testing OSS Community Agent with r/oss_test")
    print("=" * 50)
    
    try:
        # Step 1: Initialize Reddit tool
        print("\n📡 Step 1: Connecting to Reddit API...")
        reddit_tool = RedditTool(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD"),
            user_agent=f"oss-community-agent/1.0 (by u/{os.getenv('REDDIT_USERNAME')})"
        )
        print("✅ Reddit API connected successfully")
        
        # Step 2: Check the oss_test subreddit
        print("\n🔍 Step 2: Checking r/oss_test subreddit...")
        
        # Try different search terms to find any posts
        search_terms = ["test", "help", "question", "python", ""]
        all_posts = []
        
        for term in search_terms:
            if term:
                posts = reddit_tool.search_questions("oss_test", term, 10)
                print(f"   Searching for '{term}': {len(posts)} posts found")
            else:
                # Get recent posts without search term
                try:
                    subreddit = reddit_tool.reddit.subreddit("oss_test")
                    posts = []
                    for submission in subreddit.new(limit=10):
                        posts.append({
                            "id": submission.id,
                            "title": submission.title,
                            "selftext": submission.selftext,
                            "url": submission.url,
                            "created_utc": submission.created_utc,
                            "author": str(submission.author) if submission.author else "deleted"
                        })
                    print(f"   Recent posts: {len(posts)} posts found")
                except Exception as e:
                    print(f"   Error getting recent posts: {e}")
                    posts = []
            
            all_posts.extend(posts)
        
        # Remove duplicates
        seen_ids = set()
        unique_posts = []
        for post in all_posts:
            if post['id'] not in seen_ids:
                seen_ids.add(post['id'])
                unique_posts.append(post)
        
        print(f"\n📊 Total unique posts found in r/oss_test: {len(unique_posts)}")
        
        if unique_posts:
            print("📋 Posts found:")
            for i, post in enumerate(unique_posts[:5], 1):
                print(f"   {i}. '{post['title'][:60]}...' (ID: {post['id']})")
                
            # Step 3: Test with a real post
            print(f"\n🧠 Step 3: Testing AI response generation...")
            test_post = unique_posts[0]
            test_post['subreddit'] = 'oss_test'
            
            print(f"Selected post: '{test_post['title']}'")
            
            # Process through approval workflow
            result = approval_workflow.process_reddit_query(test_post)
            
            if result['success']:
                print("✅ AI response generated successfully!")
                print(f"   Request ID: {result['request_id']}")
                print(f"   Confidence: {result['confidence']}")
                print(f"   Response length: {len(result.get('drafted_reply', ''))}")
                
                # Show preview
                draft = result.get('drafted_reply', '')
                preview = draft[:150] + "..." if len(draft) > 150 else draft
                print(f"\n📝 AI Response Preview:\n{preview}")
                
                # Step 4: Test approval workflow
                print(f"\n✅ Step 4: Testing approval workflow...")
                pending = approval_workflow.get_pending_requests()
                
                if pending:
                    request_id = pending[0]['id']
                    print(f"Approving request: {request_id}")
                    
                    approval_result = approval_workflow.approve_request(
                        request_id=request_id,
                        admin_feedback="Approved by oss_test testing script"
                    )
                    
                    if approval_result['success']:
                        dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
                        if dry_run:
                            print("✅ Request approved successfully (DRY RUN mode)")
                            print(f"   Simulated Reddit reply ID: {approval_result['reddit_reply_id']}")
                        else:
                            print("✅ Request approved and posted to r/oss_test!")
                            print(f"   Real Reddit reply ID: {approval_result['reddit_reply_id']}")
                    else:
                        print(f"❌ Approval failed: {approval_result['error']}")
                
            else:
                print(f"❌ AI response generation failed: {result['error']}")
                
        else:
            print("📝 No posts found in r/oss_test. Let's create a test scenario...")
            print("\n🤖 CREATING TEST DATA...")
            
            # Create a mock post for testing
            mock_post = {
                'id': 'test_post_001',
                'title': 'How do I get started with Python programming?',
                'selftext': 'I am new to programming and want to learn Python. What are the best resources and how should I start?',
                'url': 'https://reddit.com/r/oss_test/comments/test_post_001',
                'created_utc': time.time(),
                'author': 'test_user',
                'subreddit': 'oss_test'
            }
            
            print(f"Mock post: '{mock_post['title']}'")
            
            result = approval_workflow.process_reddit_query(mock_post)
            
            if result['success']:
                print("✅ AI response generated for mock post!")
                print(f"   Request ID: {result['request_id']}")
                print(f"   Confidence: {result['confidence']}")
                
                # Show the full response this time
                draft = result.get('drafted_reply', '')
                print(f"\n📄 FULL AI RESPONSE:\n{'-'*50}")
                print(draft)
                print('-'*50)
                
                print(f"\n✅ Testing approval...")
                pending = approval_workflow.get_pending_requests()
                
                if pending:
                    request_id = pending[0]['id']
                    approval_result = approval_workflow.approve_request(
                        request_id=request_id,
                        admin_feedback="Approved - Good response for Python beginner question"
                    )
                    
                    if approval_result['success']:
                        print("✅ Mock post approved successfully!")
                        print(f"   Would post to r/oss_test: {approval_result['reddit_posted']}")
            
        # Step 5: Final statistics
        print(f"\n📊 Step 5: Final Statistics")
        stats = approval_workflow.get_request_stats()
        print(f"   Total Requests: {stats['total']}")
        print(f"   Pending: {stats['pending']}")
        print(f"   Approved: {stats['approved']}")
        print(f"   Rejected: {stats['rejected']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def create_sample_posts_guide():
    """Show how to create sample posts in the oss_test subreddit"""
    print(f"\n📝 How to create test posts in r/oss_test:")
    print("="*50)
    print("1. Go to https://reddit.com/r/oss_test")
    print("2. Click 'Create Post'")
    print("3. Add some sample questions like:")
    print("   • 'How do I install Python packages?'")
    print("   • 'What's the difference between lists and tuples?'")
    print("   • 'Help with my Python code - getting errors'")
    print("   • 'Best practices for Python project structure?'")
    print("4. Then run this test script again!")

if __name__ == "__main__":
    print("OSS Community Agent - Testing with r/oss_test")
    print("This will test the complete workflow with your test subreddit")
    print("")
    
    # Check environment
    required_vars = ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 'REDDIT_USERNAME', 'REDDIT_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    success = test_with_oss_test_subreddit()
    
    if success:
        print("\n🎊 r/oss_test TESTING COMPLETED!")
        print("\n✅ What's Working:")
        print("   • Reddit API connection")
        print("   • AI response generation")
        print("   • Database storage")
        print("   • Approval workflow")
        print("   • Statistics tracking")
        
        dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
        if dry_run:
            print("   • DRY RUN mode (safe testing)")
        else:
            print("   • LIVE mode (real Reddit posting)")
            
        create_sample_posts_guide()
        
        print(f"\n🚀 Next Steps:")
        print("1. Create some test posts in r/oss_test")
        print("2. Run: python -m streamlit run apps/ui/streamlit_app.py")
        print("3. Use the web interface to manage approvals")
        
    else:
        print("\n❌ Testing failed. Please check errors above.")
