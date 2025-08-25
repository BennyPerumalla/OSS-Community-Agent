#!/usr/bin/env python3
"""
Full System Launcher for OSS Community Agent

Runs the frontend (Streamlit UI) and a background monitoring backend simultaneously.
The UI invokes the agent; the backend can kick off subreddit monitoring for live data.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import threading
import argparse


def load_env(project_root: Path):
    env_file = project_root / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print("Environment variables loaded from .env")
        except ImportError:
            print("python-dotenv not installed; proceeding without auto-loading .env")
    else:
        print("No .env file found; using system environment variables")


def start_streamlit_ui(project_root: Path, port: int, address: str, headless: bool = False) -> subprocess.Popen:
    """Start Streamlit UI and return the subprocess handle."""
    ui_dir = project_root / "apps" / "ui"
    python_exec = sys.executable or "python"

    args = [
        python_exec,
        "-m",
        "streamlit",
        "run",
        "streamlit_app.py",
        "--server.port",
        str(port),
        "--server.address",
        address,
        "--browser.gatherUsageStats",
        "false",
    ]
    if headless:
        args += ["--server.headless", "true"]

    print(f"Starting UI at http://{address}:{port}")
    proc = subprocess.Popen(args, cwd=str(ui_dir))
    return proc


def backend_monitor_loop(project_root: Path, subreddits: list[str], keywords: str, stop_event: threading.Event):
    """Background loop to start and maintain monitoring via AgentIntegration."""
    # Ensure project root importable
    sys.path.insert(0, str(project_root))
    try:
        from apps.ui.utils.agent_integration import agent_integration
    except Exception as e:
        print(f"Backend monitor failed to import integration: {e}")
        return

    run_ids = []
    for sr in subreddits:
        sr = sr.strip()
        if not sr:
            continue
        try:
            rid = agent_integration.start_agent_monitoring(sr, keywords)
            run_ids.append(rid)
            print(f"Monitoring started for r/{sr} (run_id={rid[:8]}...) with keywords='{keywords or ''}'")
        except Exception as e:
            print(f"Failed to start monitoring r/{sr}: {e}")

    # Keep thread alive until stop
    while not stop_event.is_set():
        time.sleep(1)
    print("Stopping backend monitoring...")


def main():
    parser = argparse.ArgumentParser(description="Run UI and backend monitoring for OSS Community Agent")
    parser.add_argument("--port", type=int, default=8501, help="UI port (default 8501)")
    parser.add_argument("--address", type=str, default="localhost", help="UI bind address (default localhost)")
    parser.add_argument("--headless", action="store_true", help="Run UI headless (no browser)")
    parser.add_argument(
        "--subreddits",
        type=str,
        default=os.getenv("MONITOR_SUBREDDITS", "oss_test"),
        help="Comma-separated subreddits to monitor (default from MONITOR_SUBREDDITS or 'learnpython')",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default=os.getenv("MONITOR_KEYWORDS", ""),
        help="Optional keywords for monitoring (default from MONITOR_KEYWORDS)",
    )
    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="Do not start backend monitoring (UI only)",
    )
    parser.add_argument(
        "--scan-interval",
        type=int,
        default=None,
        help="Override SCAN_INTERVAL_SECONDS for backend monitoring",
    )

    args = parser.parse_args()
    project_root = Path(__file__).parent.resolve()

    load_env(project_root)

    # Optionally override scan interval for monitoring loop via env
    if args.scan_interval is not None:
        os.environ["SCAN_INTERVAL_SECONDS"] = str(args.scan_interval)

    print("Starting OSS Community Agent (UI and Backend)")
    print("=" * 60)
    print(f"UI: http://{args.address}:{args.port}")
    if not args.no_monitor:
        print(f"Backend monitoring: subreddits={args.subreddits} keywords='{args.keywords}'")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    # Start UI
    ui_proc = start_streamlit_ui(project_root, port=args.port, address=args.address, headless=args.headless)

    # Start backend monitoring thread (optional)
    stop_event = threading.Event()
    monitor_thread = None
    if not args.no_monitor:
        subs = [s.strip() for s in args.subreddits.split(",") if s.strip()]
        monitor_thread = threading.Thread(
            target=backend_monitor_loop,
            args=(project_root, subs, args.keywords, stop_event),
            daemon=True,
        )
        monitor_thread.start()

    try:
        # Wait for UI to exit
        exit_code = ui_proc.wait()
        if exit_code != 0:
            print(f"UI exited with code {exit_code}")
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Signal backend to stop
        stop_event.set()
        if monitor_thread and monitor_thread.is_alive():
            monitor_thread.join(timeout=5)
        # Terminate UI if still running
        if ui_proc and ui_proc.poll() is None:
            try:
                ui_proc.terminate()
                # Give it a moment
                time.sleep(2)
                if ui_proc.poll() is None:
                    ui_proc.kill()
            except Exception:
                pass
        print("Stopped.")


if __name__ == "__main__":
    main()
