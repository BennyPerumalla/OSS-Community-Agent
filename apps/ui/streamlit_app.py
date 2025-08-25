# apps/ui/streamlit_app.py

import streamlit as st
import os
import sys
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import utilities and pages with error handling
try:
    from utils.scheduler import ingest_unanswered_queries
except ImportError:
    ingest_unanswered_queries = None

try:
    from utils.helpers import load_css, init_session_state
except ImportError:
    load_css = None
    init_session_state = None

try:
    from utils.agent_integration import agent_integration
except ImportError:
    agent_integration = None

try:
    from pages.dashboard import render_dashboard
    from pages.approval import render_approval_page
    from pages.logs import render_logs_page
    from pages.monitor import render_monitor_page
    from pages.settings import render_settings_page
except ImportError as e:
    st.error(f"Failed to import page modules: {e}")
    # Define fallback functions
    def render_dashboard():
        st.error("Dashboard page not available")
    def render_approval_page():
        st.error("Approval page not available")
    def render_logs_page():
        st.error("Logs page not available")
    def render_monitor_page():
        st.error("Monitor page not available")
    def render_settings_page():
        st.error("Settings page not available")

def main():
    """Main Streamlit application"""
    
    # Load environment variables from root .env file
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
        except ImportError:
            pass  # Continue without dotenv
    
    # Page configuration
    st.set_page_config(
        page_title="OSS Community Agent",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/BennyPerumalla/oss-community-agent',
            'Report a bug': 'https://github.com/BennyPerumalla/oss-community-agent/issues',
            'About': """
            # OSS Community Auto-Responder 🤖
            
            An AI agent to help open-source maintainers manage community support on Reddit, 
            grounded in project documentation.
            
            Built with Portia AI SDK and powered by human-in-the-loop approval workflow.
            """
        }
    )
    
    # Load custom CSS
    if load_css:
        css_path = current_dir / "styles" / "main.css"
        load_css(str(css_path))
    
    # Initialize session state
    if init_session_state:
        init_session_state()
    else:
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'dashboard'
    
    # Render the application
    render_app()

def render_app():
    """Render the main application interface"""
    
    # Create sidebar navigation
    with st.sidebar:
        render_sidebar()
    
    # Render the selected page
    current_page = st.session_state.get('current_page', 'dashboard')
    
    if current_page == 'dashboard':
        render_dashboard()
    elif current_page == 'approval':
        render_approval_page()
    elif current_page == 'logs':
        render_logs_page()
    elif current_page == 'monitor':
        render_monitor_page()
    elif current_page == 'settings':
        render_settings_page()
    else:
        # Default to dashboard
        render_dashboard()

def render_sidebar():
    """Render the sidebar navigation"""
    
    # Logo and title
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0; margin-bottom: 2rem;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🤖</div>
        <h2 style="margin: 0; color: var(--text-primary); font-size: 1.2rem; font-weight: 700;">
            OSS Community Agent
        </h2>
        <p style="margin: 0.25rem 0 0 0; color: var(--text-secondary); font-size: 0.8rem;">
            AI-Powered Reddit Support
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation menu
    st.markdown("### 📍 Navigation")
    
    current_page = st.session_state.get('current_page', 'dashboard')
    
    # Navigation items
    nav_items = [
        ('dashboard', '📊', 'Dashboard', 'Overview and key metrics'),
        ('approval', '✅', 'Approval Queue', 'Review pending requests'),
        ('logs', '📋', 'Request Logs', 'Search and filter all requests'),
        ('monitor', '🔍', 'Agent Monitor', 'Real-time agent status'),
        ('settings', '⚙️', 'Settings', 'Configure agent and APIs')
    ]
    
    for page_key, icon, label, description in nav_items:
        is_active = current_page == page_key
        
        # Create clickable navigation item
        if st.button(
            f"{icon} {label}",
            key=f"nav_{page_key}",
            help=description,
            use_container_width=True,
            type="primary" if is_active else "secondary"
        ):
            st.session_state.current_page = page_key
            st.rerun()
    
    # Quick stats section
    st.markdown("---")
    st.markdown("### 📈 Quick Stats")
    
    # Get agent health for quick stats
    try:
        if agent_integration:
            health = agent_integration.get_agent_health()
            
            # Pending requests
            pending = health.get('pending_approvals', 0)
            st.metric("Pending Reviews", pending, delta=None)
            
            # Today's requests
            today_requests = health.get('total_requests_today', 0)
            st.metric("Requests Today", today_requests, delta="+3 vs yesterday")
            
            # System status
            status = health.get('status', 'unknown')
            status_color = "🟢" if status == 'healthy' else "🟡" if status == 'warning' else "🔴"
            st.markdown(f"**Status:** {status_color} {status.title()}")
        else:
            # Show default stats when agent_integration is not available
            st.metric("Pending Reviews", "N/A", delta=None)
            st.metric("Requests Today", "N/A", delta=None)
            st.markdown("**Status:** 🔴 Agent Offline")
        
    except Exception as e:
        st.warning(f"Agent integration unavailable: {str(e)}")
    
    # Quick actions section
    st.markdown("### ⚡ Quick Actions")
    
    # Manual scan button
    if st.button("🔍 Start Manual Scan", use_container_width=True):
        if agent_integration:
            with st.expander("Manual Scan Options", expanded=True):
                subreddit = st.text_input("Subreddit", value="learnpython", placeholder="Enter subreddit name")
                keywords = st.text_input("Keywords", value="", placeholder="Optional keywords")
                
                if st.button("🚀 Start Scan"):
                    run_id = agent_integration.start_agent_monitoring(subreddit, keywords)
                    st.success(f"✅ Manual scan started! Run ID: `{run_id[:8]}...`")
                    st.info("Check the Monitor page for real-time progress.")
        else:
            st.warning("⚠️ Agent integration not available. Please check configuration.")
    
    # Emergency stop
    if st.button("⏹️ Emergency Stop", use_container_width=True, type="secondary"):
        if agent_integration:
            st.warning("⚠️ This would stop all active agent processes.")
            if st.button("⚠️ Confirm Stop", type="secondary"):
                # Stop all active runs
                active_runs = agent_integration.get_all_active_runs()
                for run in active_runs:
                    agent_integration.stop_agent_run(run['id'])
                st.success("✅ All agent processes stopped.")
        else:
            st.info("ℹ️ No active agent processes to stop.")
    
    # System info section
    st.markdown("---")
    st.markdown("### ℹ️ System Info")
    
    try:
        health = agent_integration.get_agent_health()
        uptime = health.get('uptime', 'Unknown')
        st.markdown(f"**Uptime:** {uptime}")
        
        memory = health.get('memory_usage', 0)
        cpu = health.get('cpu_usage', 0)
        st.markdown(f"**Memory:** {memory}%")
        st.markdown(f"**CPU:** {cpu}%")
        
    except Exception:
        st.markdown("**Status:** System info unavailable")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: var(--text-muted); font-size: 0.7rem; margin-top: 1rem;">
        <p>OSS Community Agent v1.0</p>
        <p>Powered by Portia AI</p>
        <p>Built for AgentHack 2025</p>
    </div>
    """, unsafe_allow_html=True)

def render_page_header(title: str, subtitle: str, icon: str = ""):
    """Render a consistent page header"""
    st.markdown(f"""
    <div style="margin-bottom: 2rem;">
        <h1 style="color: var(--text-primary); margin-bottom: 0.5rem; font-size: 2.5rem; font-weight: 700;">
            {icon} {title}
        </h1>
        <p style="color: var(--text-secondary); font-size: 1.1rem;">
            {subtitle}
        </p>
    </div>
    """, unsafe_allow_html=True)

# Add some custom JavaScript for enhanced interactivity
def add_custom_js():
    """Add custom JavaScript for enhanced UI interactions"""
    st.markdown("""
    <script>
    // Auto-refresh functionality
    function autoRefresh() {
        if (window.autoRefreshEnabled) {
            setTimeout(function() {
                window.location.reload();
            }, window.autoRefreshInterval || 30000);
        }
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(event) {
        // Ctrl/Cmd + R for refresh
        if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
            event.preventDefault();
            window.location.reload();
        }
        
        // Ctrl/Cmd + D for dashboard
        if ((event.ctrlKey || event.metaKey) && event.key === 'd') {
            event.preventDefault();
            // Navigate to dashboard - this would need to be implemented
        }
    });
    
    // Initialize auto-refresh
    autoRefresh();
    </script>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"""
        ## 🚨 Application Error
        
        An error occurred while running the application:
        
        ```
        {str(e)}
        ```
        
        Please check:
        1. All required dependencies are installed
        2. Python version is 3.11+
        3. Database is accessible
        4. All configuration files are present
        
        For help, please visit: https://github.com/BennyPerumalla/oss-community-agent
        """)
        
        # Show system info for debugging
        with st.expander("🔍 Debug Information"):
            st.code(f"""
            Python Version: {sys.version}
            Current Directory: {os.getcwd()}
            Script Path: {__file__}
            
            Environment Variables:
            REDDIT_CLIENT_ID: {'Set' if os.getenv('REDDIT_CLIENT_ID') else 'Not Set'}
            
            Error Details:
            {str(e)}
            """, language='text')
