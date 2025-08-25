# apps/ui/pages/logs.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import sys
import os
import plotly.graph_objects as go
import plotly.express as px

# Add parent directories to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from utils.database import DatabaseManager
from utils.helpers import (
    format_timestamp, create_status_badge, format_confidence_score,
    export_data_to_json, get_chart_colors, truncate_text
)

def render_logs_page():
    """Render the comprehensive logs and filtering page"""
    
    # Initialize database
    db = DatabaseManager()
    
    # Page header
    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <h1 style="color: var(--text-primary); margin-bottom: 0.5rem; font-size: 2.5rem; font-weight: 700;">
            📊 Request Logs & Analytics
        </h1>
        <p style="color: var(--text-secondary); font-size: 1.1rem;">
            Search, filter, and analyze all agent requests with detailed insights
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Advanced filters section
    render_filters_section(db)
    
    # Apply filters and get data
    filtered_data = get_filtered_data(db)
    
    # Summary statistics for filtered data
    render_summary_stats(filtered_data)
    
    # Charts and visualizations
    render_analytics_charts(filtered_data)
    
    # Detailed data table
    render_data_table(filtered_data, db)

def render_filters_section(db):
    """Render the advanced filters section"""
    
    st.markdown("<h2 style='margin: 2rem 0 1rem 0; color: var(--text-primary);'>🔍 Advanced Filters</h2>", unsafe_allow_html=True)
    
    with st.expander("🎛️ Filter Options", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Date range filter
            st.markdown("**📅 Date Range**")
            date_range = st.date_input(
                "Select date range:",
                value=(datetime.now().date() - timedelta(days=30), datetime.now().date()),
                key="date_range"
            )
        
        with col2:
            # Status filter
            st.markdown("**📋 Status**")
            status_options = ['All', 'pending', 'approved', 'rejected', 'processing']
            selected_status = st.multiselect(
                "Filter by status:",
                options=status_options[1:],  # Exclude 'All' from options
                default=[],
                key="status_filter"
            )
            if not selected_status:
                selected_status = status_options[1:]  # Default to all if none selected
        
        with col3:
            # Subreddit filter
            st.markdown("**🏷️ Subreddit**")
            all_requests = db.get_requests_by_filter({'limit': 1000})
            unique_subreddits = list(set(r['subreddit'] for r in all_requests if r['subreddit']))
            
            selected_subreddits = st.multiselect(
                "Filter by subreddit:",
                options=unique_subreddits,
                default=[],
                key="subreddit_filter"
            )
        
        with col4:
            # Confidence range filter
            st.markdown("**🎯 Confidence Range**")
            confidence_range = st.slider(
                "Confidence level:",
                min_value=0.0,
                max_value=1.0,
                value=(0.0, 1.0),
                step=0.1,
                key="confidence_range"
            )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Search text filter
            search_term = st.text_input(
                "🔍 Search in titles and content:",
                placeholder="Enter keywords...",
                key="search_term"
            )
        
        with col2:
            # Author filter
            authors = list(set(r.get('post_author', '') for r in all_requests if r.get('post_author')))
            selected_authors = st.multiselect(
                "👤 Filter by author:",
                options=authors,
                default=[],
                key="author_filter"
            )
        
        with col3:
            # Moderation score filter
            moderation_threshold = st.slider(
                "🛡️ Max moderation score:",
                min_value=0.0,
                max_value=1.0,
                value=1.0,
                step=0.1,
                key="moderation_threshold"
            )

def get_filtered_data(db):
    """Apply all filters and return filtered data"""
    
    # Build filter dictionary
    filters = {}
    
    # Date range
    if len(st.session_state.get('date_range', [])) == 2:
        date_from, date_to = st.session_state.date_range
        filters['date_from'] = date_from.strftime('%Y-%m-%d')
        filters['date_to'] = (date_to + timedelta(days=1)).strftime('%Y-%m-%d')  # Include full day
    
    # Get all requests with date filter
    filters['limit'] = 5000  # Large limit for comprehensive analysis
    all_requests = db.get_requests_by_filter(filters)
    
    # Apply additional filters
    filtered_requests = []
    
    for request in all_requests:
        # Status filter
        if st.session_state.get('status_filter') and request['status'] not in st.session_state.status_filter:
            continue
        
        # Subreddit filter
        if st.session_state.get('subreddit_filter') and request['subreddit'] not in st.session_state.subreddit_filter:
            continue
        
        # Confidence filter
        confidence = request.get('agent_confidence', 0)
        conf_min, conf_max = st.session_state.get('confidence_range', (0.0, 1.0))
        if not (conf_min <= confidence <= conf_max):
            continue
        
        # Search term filter
        search_term = st.session_state.get('search_term', '').lower()
        if search_term:
            searchable_text = f"{request.get('post_title', '')} {request.get('post_content', '')}".lower()
            if search_term not in searchable_text:
                continue
        
        # Author filter
        if st.session_state.get('author_filter') and request.get('post_author') not in st.session_state.author_filter:
            continue
        
        # Moderation score filter
        moderation_score = request.get('moderation_score', 0)
        if moderation_score is not None and moderation_score > st.session_state.get('moderation_threshold', 1.0):
            continue
        
        filtered_requests.append(request)
    
    return filtered_requests

def render_summary_stats(filtered_data):
    """Render summary statistics for filtered data"""
    
    if not filtered_data:
        st.warning("No data matches your current filters.")
        return
    
    st.markdown("<h2 style='margin: 2rem 0 1rem 0; color: var(--text-primary);'>📈 Filtered Results Summary</h2>", unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Requests", len(filtered_data))
    
    with col2:
        approved = sum(1 for r in filtered_data if r['status'] == 'approved')
        st.metric("Approved", approved)
    
    with col3:
        rejected = sum(1 for r in filtered_data if r['status'] == 'rejected')
        st.metric("Rejected", rejected)
    
    with col4:
        pending = sum(1 for r in filtered_data if r['status'] == 'pending')
        st.metric("Pending", pending)
    
    with col5:
        if filtered_data:
            avg_confidence = sum(r.get('agent_confidence', 0) for r in filtered_data) / len(filtered_data)
            st.metric("Avg Confidence", f"{avg_confidence*100:.1f}%")
        else:
            st.metric("Avg Confidence", "N/A")

def render_analytics_charts(filtered_data):
    """Render analytics charts for filtered data"""
    
    if not filtered_data:
        return
    
    st.markdown("<h2 style='margin: 2rem 0 1rem 0; color: var(--text-primary);'>📊 Visual Analytics</h2>", unsafe_allow_html=True)
    
    # Convert to DataFrame for easier plotting
    df = pd.DataFrame(filtered_data)
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['date'] = df['created_at'].dt.date
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Status distribution pie chart
        status_counts = df['status'].value_counts()
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=status_counts.index,
            values=status_counts.values,
            hole=0.4,
            textfont_size=12,
            marker=dict(colors=[
                get_chart_colors()['success'] if status == 'approved' 
                else get_chart_colors()['error'] if status == 'rejected'
                else get_chart_colors()['warning'] if status == 'pending'
                else get_chart_colors()['info']
                for status in status_counts.index
            ])
        )])
        
        fig_pie.update_layout(
            title="Status Distribution",
            title_font=dict(size=16, color='#1e293b'),
            height=350,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Confidence score histogram
        confidence_scores = [r.get('agent_confidence', 0) * 100 for r in filtered_data]
        
        fig_hist = go.Figure(data=[go.Histogram(
            x=confidence_scores,
            nbinsx=20,
            marker_color=get_chart_colors()['primary'],
            opacity=0.7
        )])
        
        fig_hist.update_layout(
            title="Confidence Score Distribution",
            title_font=dict(size=16, color='#1e293b'),
            xaxis_title="Confidence Score (%)",
            yaxis_title="Count",
            height=350,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        st.plotly_chart(fig_hist, use_container_width=True)
    
    # Timeline chart
    if len(df) > 1:
        daily_counts = df.groupby('date').agg({
            'id': 'count',
            'status': lambda x: (x == 'approved').sum()
        }).rename(columns={'id': 'total_requests', 'status': 'approved_requests'})
        daily_counts['approval_rate'] = (daily_counts['approved_requests'] / daily_counts['total_requests'] * 100).fillna(0)
        
        fig_timeline = go.Figure()
        
        # Add total requests
        fig_timeline.add_trace(go.Scatter(
            x=daily_counts.index,
            y=daily_counts['total_requests'],
            mode='lines+markers',
            name='Total Requests',
            line=dict(color=get_chart_colors()['primary'], width=3),
            yaxis='y'
        ))
        
        # Add approval rate on secondary y-axis
        fig_timeline.add_trace(go.Scatter(
            x=daily_counts.index,
            y=daily_counts['approval_rate'],
            mode='lines+markers',
            name='Approval Rate (%)',
            line=dict(color=get_chart_colors()['success'], width=3),
            yaxis='y2'
        ))
        
        fig_timeline.update_layout(
            title="Request Volume and Approval Rate Over Time",
            title_font=dict(size=16, color='#1e293b'),
            xaxis_title="Date",
            yaxis=dict(title="Total Requests", side='left'),
            yaxis2=dict(title="Approval Rate (%)", side='right', overlaying='y'),
            height=400,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Subreddit activity
    if 'subreddit' in df.columns:
        subreddit_counts = df['subreddit'].value_counts().head(10)
        
        fig_bar = go.Figure(data=[go.Bar(
            x=subreddit_counts.values,
            y=[f"r/{sub}" for sub in subreddit_counts.index],
            orientation='h',
            marker_color=get_chart_colors()['secondary']
        )])
        
        fig_bar.update_layout(
            title="Top 10 Most Active Subreddits",
            title_font=dict(size=16, color='#1e293b'),
            xaxis_title="Number of Requests",
            height=400,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)

def render_data_table(filtered_data, db):
    """Render detailed data table with export functionality"""
    
    if not filtered_data:
        return
    
    st.markdown("<h2 style='margin: 2rem 0 1rem 0; color: var(--text-primary);'>📋 Detailed Request Log</h2>", unsafe_allow_html=True)
    
    # Export functionality
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("📤 Export to CSV", use_container_width=True):
            df = pd.DataFrame(filtered_data)
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name=f"agent_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📤 Export to JSON", use_container_width=True):
            import json
            json_data = json.dumps(filtered_data, indent=2, default=str)
            st.download_button(
                label="⬇️ Download JSON",
                data=json_data,
                file_name=f"agent_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    # Pagination
    items_per_page = 25
    total_items = len(filtered_data)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    if total_pages > 1:
        page = st.selectbox(
            f"Page (showing {min(items_per_page, total_items)} of {total_items} items):",
            range(1, total_pages + 1)
        )
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_data = filtered_data[start_idx:end_idx]
    else:
        page_data = filtered_data[:items_per_page]
    
    # Sortable table
    sort_by = st.selectbox(
        "Sort by:",
        options=['created_at', 'status', 'subreddit', 'agent_confidence', 'moderation_score'],
        format_func=lambda x: {
            'created_at': 'Date Created',
            'status': 'Status',
            'subreddit': 'Subreddit',
            'agent_confidence': 'Confidence Score',
            'moderation_score': 'Moderation Score'
        }[x]
    )
    
    sort_desc = st.checkbox("Sort descending", value=True)
    
    # Sort the page data
    page_data = sorted(
        page_data,
        key=lambda x: x.get(sort_by, 0),
        reverse=sort_desc
    )
    
    # Render table
    for request in page_data:
        with st.expander(
            f"📝 {truncate_text(request['post_title'], 80)} • r/{request['subreddit']} • {format_timestamp(request['created_at'])}",
            expanded=False
        ):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"**ID:** `{request['id']}`")
                st.markdown(f"**Status:** {create_status_badge(request['status'])}", unsafe_allow_html=True)
                st.markdown(f"**Created:** {format_timestamp(request['created_at'])}")
                st.markdown(f"**Author:** u/{request.get('post_author', 'Unknown')}")
            
            with col2:
                st.markdown(f"**Subreddit:** r/{request['subreddit']}")
                st.markdown(f"**Confidence:** {format_confidence_score(request.get('agent_confidence'))}")
                
                moderation_score = request.get('moderation_score', 0)
                mod_color = "🟢" if moderation_score < 0.3 else "🟡" if moderation_score < 0.7 else "🔴"
                st.markdown(f"**Moderation:** {mod_color} {moderation_score*100:.0f}%")
                
                if request.get('processing_time'):
                    st.markdown(f"**Processing:** {request['processing_time']:.2f}s")
            
            with col3:
                if request.get('post_url'):
                    st.markdown(f"[🔗 View on Reddit]({request['post_url']})")
                
                if request.get('human_feedback'):
                    st.markdown(f"**Feedback:** {truncate_text(request['human_feedback'], 50)}")
                
                # Quick actions
                if request['status'] == 'pending':
                    action_col1, action_col2 = st.columns(2)
                    with action_col1:
                        if st.button("✅ Approve", key=f"approve_log_{request['id']}"):
                            db.update_request_status(request['id'], 'approved', request.get('drafted_reply'))
                            st.success("Approved!")
                            st.rerun()
                    
                    with action_col2:
                        if st.button("❌ Reject", key=f"reject_log_{request['id']}"):
                            db.update_request_status(request['id'], 'rejected')
                            st.error("Rejected!")
                            st.rerun()
            
            # Show content in expandable sections
            if request.get('post_content'):
                with st.expander("📖 Original Content"):
                    st.text(request['post_content'])
            
            if request.get('drafted_reply'):
                with st.expander("🤖 AI Response"):
                    st.text(request['drafted_reply'])
            
            if request.get('final_reply') and request['final_reply'] != request.get('drafted_reply'):
                with st.expander("✏️ Final Reply"):
                    st.text(request['final_reply'])

if __name__ == "__main__":
    render_logs_page()
