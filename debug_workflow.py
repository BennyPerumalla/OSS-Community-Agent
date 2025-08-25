#!/usr/bin/env python3
"""
Debug Script for OSS Community Agent Workflow

This script helps debug the following issues:
1. Check DRY_RUN status and other environment variables
2. Test Reddit posting workflow
3. Verify markdown to plain text conversion
4. Check if responses are being posted after approval
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

def check_environment():
    """Check key environment variables"""
    print("🔍 Environment Variable Check")
    print("=" * 40)
    
    env_vars = [
        'DRY_RUN',
        'REDDIT_CLIENT_ID',
        'REDDIT_CLIENT_SECRET', 
        'REDDIT_USERNAME',
        'REDDIT_PASSWORD',
        'LLM_PROVIDER',
        'GROQ_API_KEY',
        'OPENAI_API_KEY'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if var in ['REDDIT_CLIENT_SECRET', 'REDDIT_PASSWORD', 'GROQ_API_KEY', 'OPENAI_API_KEY']:
            # Don't show sensitive values, just whether they're set
            status = "✅ SET" if value else "❌ NOT SET"
            print(f"{var:20}: {status}")
        else:
            print(f"{var:20}: {value or '❌ NOT SET'}")
    
    print()

def test_markdown_conversion():
    """Test markdown to plain text conversion"""
    print("📝 Markdown Conversion Test")
    print("=" * 40)
    
    try:
        from apps.ui.utils.approval_workflow import markdown_to_plain_text
        
        test_markdown = """
# Installing Python Packages

Here's how to **install packages** using pip:

1. Open your terminal
2. Run `pip install package_name`
3. Check with `pip list`

For more info, see [Python docs](https://docs.python.org).

**Important**: Make sure you have *Python 3.6+* installed.

```python
# Example code
import requests
response = requests.get('https://api.github.com')
```
        """.strip()
        
        print("Original markdown:")
        print(test_markdown)
        print("\n" + "-" * 40 + "\n")
        
        plain_text = markdown_to_plain_text(test_markdown)
        print("Converted plain text:")
        print(plain_text)
        print()
        
    except Exception as e:
        print(f"❌ Error testing markdown conversion: {e}")
        print()

def test_reddit_tool():
    """Test Reddit tool initialization and connectivity"""
    print("🔗 Reddit Tool Test")
    print("=" * 40)
    
    try:
        from tools.reddit_tool import RedditTool
        
        reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        reddit_username = os.getenv("REDDIT_USERNAME") 
        reddit_password = os.getenv("REDDIT_PASSWORD")
        
        if not all([reddit_client_id, reddit_client_secret, reddit_username, reddit_password]):
            print("❌ Reddit credentials not fully configured")
            return
        
        print("✅ Reddit credentials found")
        
        # Initialize Reddit tool
        reddit_tool = RedditTool(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            username=reddit_username,
            password=reddit_password,
            user_agent=f"oss-community-agent/1.0 (by u/{reddit_username})"
        )
        
        print("✅ Reddit tool initialized successfully")
        
        # Test search functionality
        print("🔍 Testing search functionality...")
        posts = reddit_tool.search_questions(
            subreddit_name="oss_test",
            keywords="help question",
            limit=2
        )
        
        print(f"✅ Found {len(posts)} posts in r/oss_test")
        for i, post in enumerate(posts[:2], 1):
            print(f"  {i}. {post.get('title', 'No title')[:50]}...")
        
    except Exception as e:
        print(f"❌ Error testing Reddit tool: {e}")
    
    print()

def test_approval_workflow():
    """Test the approval workflow"""
    print("🔄 Approval Workflow Test")
    print("=" * 40)
    
    try:
        from apps.ui.utils.approval_workflow import ApprovalWorkflow
        from apps.ui.utils.database import DatabaseManager
        
        # Initialize workflow and database
        workflow = ApprovalWorkflow()
        db = DatabaseManager()
        
        print("✅ Approval workflow initialized")
        
        # Get pending requests
        pending = workflow.get_pending_requests()
        print(f"📊 Found {len(pending)} pending requests")
        
        if pending:
            print("Most recent pending requests:")
            for i, req in enumerate(pending[:3], 1):
                status_emoji = {"pending": "🟡", "approved": "✅", "rejected": "❌"}.get(req['status'], "⚪")
                print(f"  {i}. {status_emoji} {req['post_title'][:50]}... (ID: {req['id'][:8]})")
        
        # Check stats  
        stats = workflow.get_request_stats()
        print(f"📈 Request Stats:")
        print(f"  Total: {stats['total']}")
        print(f"  Pending: {stats['pending']}")
        print(f"  Approved: {stats['approved']}")
        print(f"  Rejected: {stats['rejected']}")
        
    except Exception as e:
        print(f"❌ Error testing approval workflow: {e}")
    
    print()

def check_dry_run_mode():
    """Check if system is in dry run mode and explain implications"""
    print("🏃 DRY RUN Mode Analysis")
    print("=" * 40)
    
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    
    if dry_run:
        print("🟡 SYSTEM IS IN DRY RUN MODE")
        print("   This means:")
        print("   • Responses are generated and queued")
        print("   • Admin can approve/reject responses")  
        print("   • BUT responses are NOT actually posted to Reddit")
        print("   • All Reddit posting is simulated")
        print()
        print("💡 To enable real Reddit posting:")
        print("   Set DRY_RUN=false in your .env file")
    else:
        print("✅ SYSTEM IS IN LIVE MODE")
        print("   • Approved responses WILL be posted to Reddit")
        print("   • Make sure you're ready for live posting!")
    
    print()

def main():
    """Run all debug checks"""
    print("🛠️  OSS Community Agent - Debug Script")
    print("=" * 50)
    print()
    
    check_environment()
    check_dry_run_mode()
    test_markdown_conversion()
    test_reddit_tool()
    test_approval_workflow()
    
    print("🏁 Debug analysis complete!")
    print()
    
    # Provide recommendations
    print("💡 Recommendations:")
    
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    if dry_run:
        print("   1. To enable real Reddit posting: Set DRY_RUN=false in .env")
    
    if not os.getenv("REDDIT_CLIENT_ID"):
        print("   2. Configure Reddit API credentials in .env file")
    
    if not os.getenv("GROQ_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("   3. Configure at least one LLM API key (GROQ_API_KEY or OPENAI_API_KEY)")

if __name__ == "__main__":
    main()
