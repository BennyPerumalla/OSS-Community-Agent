#!/usr/bin/env python3
"""
OSS Community Agent - Setup Verification Script
This script checks if all dependencies and configuration are properly set up.
"""

import os
import sys
import subprocess
import importlib
import json
from pathlib import Path
from dotenv import load_dotenv

class SetupVerifier:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.issues = []
        self.successes = []
        
    def log_success(self, message):
        self.successes.append(message)
        print(f"✅ {message}")
        
    def log_issue(self, message):
        self.issues.append(message)
        print(f"❌ {message}")
        
    def log_warning(self, message):
        print(f"⚠️ {message}")
        
    def check_python_version(self):
        """Check if Python version is compatible"""
        version = sys.version_info
        if version.major == 3 and version.minor >= 11:
            self.log_success(f"Python {version.major}.{version.minor}.{version.micro} is compatible")
        else:
            self.log_issue(f"Python {version.major}.{version.minor}.{version.micro} - Need Python 3.11+")
    
    def check_virtual_environment(self):
        """Check if we're in a virtual environment"""
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            self.log_success("Running in virtual environment")
        else:
            self.log_warning("Not running in virtual environment - recommended to use one")
    
    def check_dependencies(self):
        """Check if all required packages are installed"""
        required_packages = [
            'streamlit', 'praw', 'chromadb', 'langchain', 'groq',
            'pandas', 'plotly', 'requests', 'python-dotenv',
            'portia-sdk-python', 'apscheduler'
        ]
        
        for package in required_packages:
            try:
                if package == 'portia-sdk-python':
                    importlib.import_module('portia')
                else:
                    importlib.import_module(package.replace('-', '_'))
                self.log_success(f"{package} is installed")
            except ImportError:
                self.log_issue(f"{package} is not installed")
    
    def check_env_file(self):
        """Check if .env file exists and has required variables"""
        env_path = self.project_root / '.env'
        if not env_path.exists():
            self.log_issue(".env file does not exist - copy from .env.example")
            return
            
        load_dotenv(env_path)
        
        required_vars = [
            'REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 
            'REDDIT_USERNAME', 'REDDIT_PASSWORD'
        ]
        
        optional_vars = ['GROQ_API_KEY', 'OPENAI_API_KEY']
        
        for var in required_vars:
            if os.getenv(var):
                self.log_success(f"{var} is configured")
            else:
                self.log_issue(f"{var} is not configured in .env")
        
        has_ai_key = False
        for var in optional_vars:
            if os.getenv(var) and os.getenv(var) != 'your_api_key':
                self.log_success(f"{var} is configured")
                has_ai_key = True
            
        if not has_ai_key:
            self.log_warning("No AI API keys configured - some features will not work")
    
    def check_directories(self):
        """Check if required directories exist"""
        required_dirs = [
            'data', 'data/corpus', 'rag_db', 'apps', 'tools', 'tests'
        ]
        
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                self.log_success(f"Directory '{dir_name}' exists")
            else:
                self.log_issue(f"Directory '{dir_name}' does not exist")
    
    def check_database(self):
        """Check if database file exists"""
        db_path = self.project_root / 'data' / 'agent_data.db'
        if db_path.exists():
            self.log_success("Database file exists")
        else:
            self.log_warning("Database file does not exist (will be created on first run)")
    
    def test_imports(self):
        """Test if critical imports work"""
        try:
            from tools.reddit_tool import RedditTool
            self.log_success("Reddit tool import works")
        except ImportError as e:
            self.log_issue(f"Reddit tool import failed: {e}")
            
        try:
            from tools.rag_tool import RAGTool
            self.log_success("RAG tool import works")
        except ImportError as e:
            self.log_issue(f"RAG tool import failed: {e}")
            
        try:
            from apps.agent.main import run_oss_agent
            self.log_success("Main agent import works")
        except ImportError as e:
            self.log_issue(f"Main agent import failed: {e}")
    
    def generate_setup_commands(self):
        """Generate setup commands for any missing components"""
        commands = []
        
        if not (self.project_root / '.env').exists():
            commands.append("# Create .env file from example:")
            commands.append("cp .env.example .env")
            commands.append("")
        
        if self.issues:
            commands.append("# Install missing dependencies:")
            commands.append("pip install -r infra/requirements.txt")
            commands.append("")
        
        return commands
    
    def run_verification(self):
        """Run all verification checks"""
        print("🔍 OSS Community Agent - Setup Verification")
        print("=" * 50)
        
        self.check_python_version()
        self.check_virtual_environment()
        print()
        
        print("📦 Checking Dependencies...")
        self.check_dependencies()
        print()
        
        print("🔧 Checking Configuration...")
        self.check_env_file()
        print()
        
        print("📁 Checking Project Structure...")
        self.check_directories()
        self.check_database()
        print()
        
        print("🧪 Testing Imports...")
        self.test_imports()
        print()
        
        # Summary
        print("📊 VERIFICATION SUMMARY")
        print("=" * 50)
        print(f"✅ Successful checks: {len(self.successes)}")
        print(f"❌ Issues found: {len(self.issues)}")
        
        if self.issues:
            print("\n🔧 ISSUES TO FIX:")
            for issue in self.issues:
                print(f"   • {issue}")
                
            commands = self.generate_setup_commands()
            if commands:
                print("\n📝 SETUP COMMANDS:")
                for cmd in commands:
                    print(cmd)
        else:
            print("\n🎉 All checks passed! Your setup is ready.")
            
        return len(self.issues) == 0

if __name__ == "__main__":
    verifier = SetupVerifier()
    success = verifier.run_verification()
    sys.exit(0 if success else 1)
