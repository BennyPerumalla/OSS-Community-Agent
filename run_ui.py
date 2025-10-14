#!/usr/bin/env python3
"""
Launch script for the OSS Community Agent UI

This script sets up the environment and launches the Streamlit application
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Main launch function"""
    
    # Get the project root directory
    project_root = Path(__file__).parent
    ui_dir = project_root / "apps" / "ui"
    
    # Change to the UI directory
    try:
        os.chdir(ui_dir)
    except OSError as e:
        print(f"❌ Error changing to UI directory: {e}")
        print(f"📁 UI directory path: {ui_dir}")
        return
    
    # Check for root .env file
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    
    if env_file.exists():
        print("✅ Using .env configuration file")
    elif env_example.exists():
        print("⚠️  No .env file found. Creating one from .env.example...")
        with open(env_example, 'r') as src, open(env_file, 'w') as dst:
            dst.write(src.read())
        print("✅ Created .env file. Please edit it with your actual API keys before running.")
        print(f"📝 Edit: {env_file}")
        return
    else:
        print("⚠️  No .env or .env.example file found. Please create one.")
        env_file = None
    
    # Check for required dependencies
    try:
        import streamlit
        import plotly
        import pandas
        print("✅ Core dependencies found")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("📦 Install dependencies with: pip install -r infra/requirements.txt")
        return
    
    # Set up environment variables
    if env_file and env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print("✅ Environment variables loaded from .env")
        except ImportError:
            print("⚠️  python-dotenv not available, make sure environment variables are set")
    
    # Launch Streamlit
    print("🚀 Starting OSS Community Agent UI...")
    print(f"📁 Working directory: {ui_dir}")
    print("🌐 The application will open in your web browser")
    print("⏹️  Press Ctrl+C to stop the application")
    print("-" * 60)
    
    try:
        # Use the current Python executable for cross-platform support
        python_exec = sys.executable or "python"
        subprocess.run([
            python_exec, "-m", "streamlit", "run",
            "streamlit_app.py",
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false",
            "--theme.primaryColor", "#6366f1",
            "--theme.backgroundColor", "#ffffff",
            "--theme.secondaryBackgroundColor", "#f8fafc"
        ])
    except KeyboardInterrupt:
        print("\n👋 Shutting down OSS Community Agent UI...")
    except Exception as e:
        print(f"❌ Error starting Streamlit: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
