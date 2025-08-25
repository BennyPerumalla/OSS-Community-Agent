# demo_approval_workflow.py
"""
Interactive demonstration of the complete OSS Community Agent workflow
with admin approval. This script shows:

1. 🔍 Monitoring Reddit for questions
2. 🧠 Generating AI-powered draft responses 
3. ⏸️ Pausing for human approval
4. ✅ Posting approved responses to Reddit
5. 📊 Tracking all activities

Run this script to see the complete human-in-the-loop workflow in action!
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

def print_header(title, emoji="🤖"):
    """Print a formatted header"""
    print(f"\n{emoji} {title}")
    print("=" * (len(title) + 4))

def print_step(step_num, title, emoji="📌"):
    """Print a formatted step"""
    print(f"\n{emoji} Step {step_num}: {title}")
    print("-" * (len(title) + 10))

def wait_for_input(message="Press Enter to continue..."):
    """Wait for user input"""
    input(f"\n💭 {message}")

def demonstrate_workflow():
    """Demonstrate the complete workflow"""
    
    print_header("OSS Community Agent - Admin Approval Workflow Demo", "🚀")
    
    print("""
Welcome to the OSS Community Agent demonstration!

This script will show you how the agent:
1. 🔍 Finds questions on Reddit that need answers
2. 🧠 Uses AI to draft helpful responses based on your documentation
3. ⏸️ Waits for admin approval before posting anything
4. ✅ Posts approved responses to help the community
5. 📊 Tracks everything for transparency

Let's get started!
    """)
    
    wait_for_input("Ready to begin the demonstration?")
    
    try:
        # Step 1: Initialize the system
        print_step(1, "Initializing the OSS Community Agent", "⚙️")
        
        print("🔧 Setting up Reddit API connection...")
        reddit_tool = RedditTool(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD"),
            user_agent=f"oss-community-agent/1.0 (by u/{os.getenv('REDDIT_USERNAME')})"
        )
        
        print("🧠 Setting up RAG (Retrieval-Augmented Generation) system...")
        rag_tool = RAGTool()
        
        print("✅ System initialized successfully!")
        
        wait_for_input()
        
        # Step 2: Monitor Reddit
        print_step(2, "Monitoring Reddit for Questions", "🔍")
        
        print("🔍 Searching r/learnpython for questions that need help...")
        posts = reddit_tool.search_questions("learnpython", "help python problem", limit=3)
        
        print(f"📋 Found {len(posts)} potential questions to help with:")
        for i, post in enumerate(posts[:3], 1):
            print(f"   {i}. '{post['title'][:60]}...'")
        
        if not posts:
            print("❌ No posts found for demonstration. Exiting.")
            return
        
        wait_for_input()
        
        # Step 3: Generate draft response
        print_step(3, "AI Generates Draft Response", "🧠")
        
        selected_post = posts[0]
        selected_post['subreddit'] = 'learnpython'
        
        print(f"🎯 Selected post: '{selected_post['title']}'")
        print(f"📝 Post content: '{selected_post.get('selftext', 'No content')[:100]}...'")
        
        print("\n🧠 AI is analyzing the question and generating a response...")
        print("   - Searching documentation for relevant information")
        print("   - Crafting a helpful, accurate response")
        print("   - Checking for safety and appropriateness")
        
        result = approval_workflow.process_reddit_query(selected_post)
        
        if result['success']:
            print("\n✅ Draft response generated successfully!")
            print(f"📊 AI Confidence: {result['confidence']}")
            print(f"🔢 Response length: {len(result.get('drafted_reply', ''))} characters")
            print(f"🆔 Request ID: {result['request_id']}")
            
            # Show a preview of the draft
            draft = result.get('drafted_reply', '')
            preview = draft[:200] + "..." if len(draft) > 200 else draft
            print(f"\n📝 Draft preview:\n{preview}")
            
        else:
            print(f"❌ Failed to generate draft: {result['error']}")
            return
        
        wait_for_input()
        
        # Step 4: Admin review process
        print_step(4, "Admin Review & Approval Process", "👨‍💼")
        
        print("⏸️ The AI has paused and is waiting for human approval...")
        print("📋 Getting pending requests that need admin review...")
        
        pending_requests = approval_workflow.get_pending_requests()
        
        if not pending_requests:
            print("❌ No pending requests found")
            return
            
        request_to_review = pending_requests[0]
        print(f"\n📋 Request Details:")
        print(f"   🆔 ID: {request_to_review['id']}")
        print(f"   🌐 Subreddit: r/{request_to_review['subreddit']}")
        print(f"   📝 Post: {request_to_review['post_title'][:50]}...")
        print(f"   🎯 Confidence: {request_to_review['agent_confidence']}")
        print(f"   📅 Created: {request_to_review['created_at']}")
        
        # Show the full draft for admin review
        print(f"\n📄 FULL DRAFT RESPONSE FOR ADMIN REVIEW:")
        print("┌" + "─" * 60 + "┐")
        draft_lines = request_to_review['drafted_reply'].split('\n')
        for line in draft_lines[:20]:  # Show first 20 lines
            print(f"│ {line:<58} │")
        if len(draft_lines) > 20:
            print(f"│ ... (truncated, {len(draft_lines) - 20} more lines) │")
        print("└" + "─" * 60 + "┘")
        
        wait_for_input("Review complete. Ready to see approval options?")
        
        # Step 5: Approval Decision
        print_step(5, "Admin Decision & Action", "✅")
        
        print("👨‍💼 Admin has three options:")
        print("   ✅ APPROVE - Post the response as-is")
        print("   ✏️ EDIT & APPROVE - Make changes then post")
        print("   ❌ REJECT - Don't post this response")
        
        print("\n🤖 For this demo, we'll simulate admin APPROVAL...")
        
        dry_run_status = "ON" if os.getenv("DRY_RUN", "true").lower() == "true" else "OFF"
        print(f"🛡️ Safety mode: DRY RUN is {dry_run_status}")
        
        if dry_run_status == "ON":
            print("   (This means we'll simulate posting without actually posting to Reddit)")
        else:
            print("   ⚠️ WARNING: DRY RUN is OFF - this will actually post to Reddit!")
        
        wait_for_input("Proceed with approval?")
        
        # Approve the request
        print("✅ Admin approves the response!")
        print("🚀 Initiating posting process...")
        
        approval_result = approval_workflow.approve_request(
            request_id=request_to_review['id'],
            admin_feedback="Approved via demo script - response looks helpful and accurate",
            edited_reply=""  # Use original draft
        )
        
        # Step 6: Results & Summary
        print_step(6, "Results & Summary", "📊")
        
        if approval_result['success']:
            if approval_result['reddit_posted']:
                print("🎉 SUCCESS! Response posted to Reddit!")
                print(f"📋 Reddit Reply ID: {approval_result['reddit_reply_id']}")
                
                if dry_run_status == "ON":
                    print("🛡️ (Simulated in DRY RUN mode - no actual Reddit post made)")
                else:
                    print("🌐 Real post made to Reddit!")
            else:
                print("⚠️ Response approved but not posted (may have already been answered)")
        else:
            print(f"❌ Approval failed: {approval_result['error']}")
        
        # Show final statistics
        print("\n📊 FINAL STATISTICS:")
        stats = approval_workflow.get_request_stats()
        print(f"   📈 Total Requests Processed: {stats['total']}")
        print(f"   ⏳ Currently Pending: {stats['pending']}")
        print(f"   ✅ Approved & Posted: {stats['approved']}")
        print(f"   ❌ Rejected: {stats['rejected']}")
        
        print_header("Demonstration Complete!", "🎊")
        
        print("""
🎉 Congratulations! You've seen the complete OSS Community Agent workflow:

✅ What we accomplished:
  1. 🔍 Found a real question on Reddit that needed help
  2. 🧠 Used AI to generate a helpful, documentation-based response  
  3. ⏸️ Paused for human approval (maintaining control)
  4. ✅ Processed admin approval and posted the response
  5. 📊 Tracked the entire process transparently

💡 Key Benefits:
  • Saves maintainer time on repetitive questions
  • Ensures responses are grounded in your documentation
  • Maintains human oversight and control
  • Provides full transparency and audit trail
  • Scales community support without losing quality

🚀 Next Steps:
  1. Customize responses by adding your project docs to data/corpus/
  2. Run the Streamlit UI for a visual admin interface
  3. Set up monitoring for your specific subreddits
  4. When ready, set DRY_RUN=false for live posting

Thank you for trying the OSS Community Agent! 🤖
        """)
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check environment
    required_vars = ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 'REDDIT_USERNAME', 'REDDIT_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please configure your .env file with Reddit API credentials")
        sys.exit(1)
    
    demonstrate_workflow()
