#!/usr/bin/env python3
"""
OSS Community Agent - Master Project Runner
This script provides different ways to run the project components.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from dotenv import load_dotenv

class ProjectRunner:
    def __init__(self):
        self.project_root = Path(__file__).parent
        load_dotenv()
        
    def run_setup_verification(self):
        """Run setup verification"""
        print("🔍 Running setup verification...")
        try:
            result = subprocess.run([sys.executable, "setup_verification.py"], 
                                  cwd=self.project_root, capture_output=False)
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Setup verification failed: {e}")
            return False
    
    def run_streamlit_ui(self, port=8501):
        """Run the Streamlit UI"""
        print(f"🚀 Starting Streamlit UI on port {port}...")
        try:
            cmd = [sys.executable, "-m", "streamlit", "run", "apps/ui/streamlit_app.py", 
                   "--server.port", str(port)]
            subprocess.run(cmd, cwd=self.project_root)
        except KeyboardInterrupt:
            print("\n⏹️ Streamlit UI stopped by user")
        except Exception as e:
            print(f"❌ Failed to start Streamlit UI: {e}")
    
    def run_reddit_test(self):
        """Run Reddit API test"""
        print("🧪 Running Reddit API test...")
        try:
            result = subprocess.run([sys.executable, "test_oss_test_subreddit.py"], 
                                  cwd=self.project_root, capture_output=False)
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Reddit test failed: {e}")
            return False
    
    def run_demo_workflow(self):
        """Run the demo approval workflow"""
        print("🎭 Running demo approval workflow...")
        try:
            result = subprocess.run([sys.executable, "demo_approval_workflow.py"], 
                                  cwd=self.project_root, capture_output=False)
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Demo workflow failed: {e}")
            return False
    
    def run_agent_test(self, query="Python help", subreddit="learnpython"):
        """Run a test of the main agent"""
        print(f"🤖 Running agent test with query: '{query}' in r/{subreddit}")
        try:
            from apps.agent.main import run_oss_agent
            result = run_oss_agent(query=query, subreddit=subreddit)
            
            print("\n📊 Agent Test Results:")
            print(f"Status: {result.get('status')}")
            print(f"Duration: {result.get('total_duration_sec', 0):.2f} seconds")
            if result.get('reddit_search'):
                print(f"Posts found: {result['reddit_search']['posts_found']}")
            if result.get('processed_requests'):
                print(f"Requests processed: {len(result['processed_requests'])}")
            
            return result.get('status') == 'completed'
            
        except Exception as e:
            print(f"❌ Agent test failed: {e}")
            return False
    
    def run_full_tests(self):
        """Run all tests"""
        print("🧪 Running full test suite...")
        try:
            result = subprocess.run([sys.executable, "run_tests.py"], 
                                  cwd=self.project_root, capture_output=False)
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Full tests failed: {e}")
            return False
    
    def show_project_status(self):
        """Show current project status"""
        print("📊 OSS Community Agent - Project Status")
        print("=" * 50)
        
        # Check environment
        print("\n🔧 Environment Status:")
        if os.path.exists(".env"):
            print("✅ .env file exists")
        else:
            print("❌ .env file missing")
            
        # Check database
        if os.path.exists("data/agent_data.db"):
            print("✅ Database exists")
        else:
            print("⚠️ Database will be created on first run")
        
        # Check Reddit credentials
        reddit_configured = all([
            os.getenv("REDDIT_CLIENT_ID"),
            os.getenv("REDDIT_CLIENT_SECRET"), 
            os.getenv("REDDIT_USERNAME"),
            os.getenv("REDDIT_PASSWORD")
        ])
        
        if reddit_configured:
            print("✅ Reddit credentials configured")
        else:
            print("❌ Reddit credentials not configured")
        
        # Check AI API keys
        ai_keys = []
        if os.getenv("GROQ_API_KEY") and os.getenv("GROQ_API_KEY") != "your_api_key":
            ai_keys.append("Groq")
        if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your_api_key":
            ai_keys.append("OpenAI")
            
        if ai_keys:
            print(f"✅ AI API keys configured: {', '.join(ai_keys)}")
        else:
            print("⚠️ No AI API keys configured")
        
        print(f"\n🏠 Project directory: {self.project_root}")
        print(f"🐍 Python version: {sys.version}")

def main():
    parser = argparse.ArgumentParser(description="OSS Community Agent Project Runner")
    parser.add_argument("command", choices=[
        "verify", "ui", "test-reddit", "demo", "test-agent", 
        "full-tests", "status", "all"
    ], help="Command to run")
    
    parser.add_argument("--port", type=int, default=8501, 
                       help="Port for Streamlit UI (default: 8501)")
    parser.add_argument("--query", default="Python help", 
                       help="Query for agent test (default: 'Python help')")
    parser.add_argument("--subreddit", default="learnpython", 
                       help="Subreddit for agent test (default: 'learnpython')")
    
    args = parser.parse_args()
    runner = ProjectRunner()
    
    if args.command == "verify":
        success = runner.run_setup_verification()
        sys.exit(0 if success else 1)
        
    elif args.command == "ui":
        runner.run_streamlit_ui(args.port)
        
    elif args.command == "test-reddit":
        success = runner.run_reddit_test()
        sys.exit(0 if success else 1)
        
    elif args.command == "demo":
        success = runner.run_demo_workflow()
        sys.exit(0 if success else 1)
        
    elif args.command == "test-agent":
        success = runner.run_agent_test(args.query, args.subreddit)
        sys.exit(0 if success else 1)
        
    elif args.command == "full-tests":
        success = runner.run_full_tests()
        sys.exit(0 if success else 1)
        
    elif args.command == "status":
        runner.show_project_status()
        
    elif args.command == "all":
        print("🚀 Running complete project demonstration...")
        
        # 1. Verify setup
        print("\n" + "="*50)
        if not runner.run_setup_verification():
            print("❌ Setup verification failed. Please fix issues first.")
            sys.exit(1)
        
        # 2. Run agent test
        print("\n" + "="*50)
        runner.run_agent_test(args.query, args.subreddit)
        
        # 3. Run demo workflow
        print("\n" + "="*50)
        runner.run_demo_workflow()
        
        # 4. Show how to start UI
        print("\n" + "="*50)
        print("🎉 Demonstration complete!")
        print(f"\nTo start the web interface, run:")
        print(f"python run_project.py ui")
        print(f"\nOr directly:")
        print(f"python -m streamlit run apps/ui/streamlit_app.py")

if __name__ == "__main__":
    main()
