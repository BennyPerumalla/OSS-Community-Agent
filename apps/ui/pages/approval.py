import streamlit as st
import json
from datetime import datetime
import sys
import os
from utils.reddit_client import get_subreddit_data  # 🔑 Reddit data fetch
from utils.scheduler import start_scheduler, ingest_unanswered_queries
from utils.agent_integration import generate_draft_with_groq  # Groq API integration


# Add parent directories to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from utils.database import DatabaseManager
from utils.helpers import (
    format_timestamp, create_status_badge, format_confidence_score,
    parse_citations, format_processing_time, sanitize_input
)
from utils.agent_integration import agent_integration

import praw  # Reddit API

class AgentIntegration:
    def __init__(self):
        self.db = DatabaseManager()
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent="oss-community-agent",
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD"),
        )

    def approve_request(self, request_id: int, reply: str, post_to_reddit: bool = False):
        req = self.db.get_request_by_id(request_id)
        if not req:
            return {"status": "error", "message": "Request not found"}

        if post_to_reddit:
            try:
                submission = self.reddit.submission(id=req["post_id"])
                submission.reply(reply)
                status = "success"
                msg = "Posted reply to Reddit ✅"
            except Exception as e:
                status = "error"
                msg = str(e)
        else:
            status = "dry_run"
            msg = "Reply approved locally (not posted)"

        self.db.update_request_status(request_id, "approved", reply)
        return {"status": status, "message": msg}


def render_approval_page():
    """Render the request approval workflow page"""
    db = DatabaseManager()

    # 🔑 Load latest agent settings directly from DB
    agent_settings = db.get_agent_settings() or {}
    monitored_subs = agent_settings.get("monitored_subreddits", []) or ["python"]

    # --- Start background scheduler only once ---
    if "scheduler_started" not in st.session_state:
        start_scheduler(monitored_subs)
        st.session_state.scheduler_started = True

    # Page header
    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <h1 style="color: var(--text-primary); margin-bottom: 0.5rem; font-size: 2.5rem; font-weight: 700;">
            ✅ Request Approval Workflow
        </h1>
        <p style="color: var(--text-secondary); font-size: 1.1rem;">
            Review, edit, and approve AI-generated responses before they're posted
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- Filter & Sort Options ---
    st.markdown("<h2 style='margin: 2rem 0 1rem 0; color: var(--text-primary);'>🔍 Filter & Sort</h2>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        sort_option = st.selectbox(
            "Sort by",
            options=["newest", "oldest", "confidence_high", "confidence_low"],
            format_func=lambda x: {
                "newest": "Newest First",
                "oldest": "Oldest First",
                "confidence_high": "Highest Confidence",
                "confidence_low": "Lowest Confidence"
            }[x],
            key="sort_option_selectbox"
        )

    with col2:
        subreddit_options = ["all"] + monitored_subs
        subreddit_filter = st.selectbox(
            "Filter by Subreddit",
            options=subreddit_options,
            format_func=lambda x: "All Subreddits" if x == "all" else f"r/{x}",
            key="subreddit_filter_selectbox"
        )

        # 🔥 Show live subreddit data when specific subreddit selected
        if subreddit_filter != "all":
            st.markdown(f"### 🔥 Trending in r/{subreddit_filter}")
            reddit_data = get_subreddit_data(subreddit_filter, limit=1)
            if isinstance(reddit_data, dict) and reddit_data.get("error"):
                st.error(f"Error fetching subreddit: {reddit_data['error']}")
            else:
                for post in reddit_data:
                    st.markdown(
                        f"- [{post['title']}]({post['url']}) (👍 {post['score']} | u/{post['author']})"
                    )

    with col3:
        confidence_filter = st.selectbox(
            "Confidence Level",
            options=["all", "high", "medium", "low"],
            format_func=lambda x: {
                "all": "All Confidence Levels",
                "high": "High (>80%)",
                "medium": "Medium (60-80%)",
                "low": "Low (<60%)"
            }[x],
            key="confidence_filter_selectbox"
        )

    # --- Manual fetch unanswered posts ---
    fetch_col1, _, _ = st.columns(3)
    with fetch_col1:
        fetch_button = st.button("📥 Fetch New Unanswered", use_container_width=True, key="fetch_unanswered_btn")

    if fetch_button:
        target_subreddit = subreddit_filter if subreddit_filter != "all" else None
        if target_subreddit:
            # Just ingest queries without generating answers
            new_requests = ingest_unanswered_queries(target_subreddit, limit=1)
            if new_requests:
                st.success(f"Fetched {len(new_requests)} new unanswered queries from r/{target_subreddit}!")
                # Append them to filtered_requests dynamically without waiting for rerun
                pending_requests.extend(new_requests)
                filtered_requests = apply_filters(pending_requests, subreddit_filter, confidence_filter, sort_option)
            else:
                st.warning("No new unanswered queries found.")
        else:
            st.warning("Please select a specific subreddit to fetch new queries.")
        st.rerun()

    # Get pending requests
# Get pending requests first
    pending_requests = db.get_pending_requests()
    filtered_requests = apply_filters(pending_requests, subreddit_filter, confidence_filter, sort_option)

    # Show summary stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Pending Reviews", len(pending_requests))
    with col2:
        high_confidence = sum(1 for r in pending_requests if r.get('agent_confidence', 0) >= 0.8)
        st.metric("High Confidence", high_confidence)
    with col3:
        avg_confidence = sum(r.get('agent_confidence', 0) for r in pending_requests) / max(len(pending_requests), 1)
        st.metric("Avg Confidence", f"{avg_confidence*100:.1f}%")
    with col4:
        total_citations = sum(len(parse_citations(r.get('citations', '[]'))) for r in pending_requests)
        st.metric("Total Citations", total_citations)

    # Bulk actions
    st.markdown("<h2 style='margin: 2rem 0 1rem 0; color: var(--text-primary);'>⚡ Bulk Actions</h2>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("✅ Approve All High Confidence", use_container_width=True, key="bulk_approve_btn"):
            high_conf_requests = [r for r in filtered_requests if r.get('agent_confidence', 0) >= 0.8]
            success_count = 0
            for req in high_conf_requests:
                res = agent_integration.approve_request(req['id'], req.get('drafted_reply', ''), post_to_reddit=True)
                if res.get('status') in ["success", "dry_run"]:
                    success_count += 1
            st.success(f"Approved {success_count} high confidence requests!")
            st.rerun()

    with col2:
        if st.button("⏭️ Skip Low Confidence", use_container_width=True, key="bulk_skip_btn"):
            st.info("Low confidence requests moved to review queue")
    with col3:
        if st.button("🔄 Refresh Queue", use_container_width=True, key="refresh_queue_btn"):
            st.rerun()
    with col4:
        if st.button("📤 Export Pending", use_container_width=True, key="export_pending_btn"):
            st.success("Pending requests exported to CSV!")

    # Individual request reviews
    st.markdown("<h2 style='margin: 2rem 0 1rem 0; color: var(--text-primary);'>📝 Review Queue</h2>", unsafe_allow_html=True)

    if filtered_requests:
        st.markdown(f"<p style='color: var(--text-secondary); margin-bottom: 1rem;'>Showing {len(filtered_requests)} of {len(pending_requests)} requests</p>", unsafe_allow_html=True)
        for i, request in enumerate(filtered_requests):
            render_request_review(request, db, i)
    else:
        st.info("No requests match your current filters.")


def apply_filters(requests, subreddit_filter, confidence_filter, sort_option):
    filtered = requests.copy()

    if subreddit_filter != "all":
        filtered = [r for r in filtered if r['subreddit'] == subreddit_filter]

    if confidence_filter == "high":
        filtered = [r for r in filtered if r.get('agent_confidence', 0) >= 0.8]
    elif confidence_filter == "medium":
        filtered = [r for r in filtered if 0.6 <= r.get('agent_confidence', 0) < 0.8]
    elif confidence_filter == "low":
        filtered = [r for r in filtered if r.get('agent_confidence', 0) < 0.6]

    if sort_option == "newest":
        filtered.sort(key=lambda x: x['created_at'], reverse=True)
    elif sort_option == "oldest":
        filtered.sort(key=lambda x: x['created_at'])
    elif sort_option == "confidence_high":
        filtered.sort(key=lambda x: x.get('agent_confidence', 0), reverse=True)
    elif sort_option == "confidence_low":
        filtered.sort(key=lambda x: x.get('agent_confidence', 0))

    return filtered


def render_request_review(request, db, index):
    """Render individual request review card with on-demand answer generation"""
    with st.expander(
        f"📝 {request.get('post_title', 'No Title')[:80]}{'...' if len(request.get('post_title', '')) > 80 else ''} "
        f"• r/{request.get('subreddit', 'Unknown')} • {format_confidence_score(request.get('agent_confidence'))}",
        expanded=(index == 0)
    ):
        # Metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**📅 Created:** {format_timestamp(request.get('created_at'))}")
            st.markdown(f"**👤 Author:** u/{request.get('post_author', 'Unknown')}")
        with col2:
            st.markdown(f"**🏷️ Subreddit:** r/{request.get('subreddit', 'Unknown')}")
            st.markdown(f"**🎯 Confidence:** {format_confidence_score(request.get('agent_confidence'))}")
        with col3:
            processing_time = format_processing_time(request.get('processing_time'))
            st.markdown(f"**⏱️ Processing:** {processing_time}")
            moderation_score = request.get("moderation_score") or 0.0
            mod_color = "🟢" if moderation_score < 0.3 else "🟡" if moderation_score < 0.7 else "🔴"
            st.markdown(f"**🛡️ Safety:** {mod_color} {moderation_score*100:.0f}%")

        # Original post
        st.markdown("### 📝 Original Question")
        st.markdown(f"""
        <div style="padding: 1rem; background: var(--bg-secondary); border-radius: 8px; border-left: 3px solid var(--primary-color); margin: 1rem 0;">
            <strong>Title:</strong> {request.get('post_title', 'No Title')}<br><br>
            <strong>Content:</strong><br>
            {request.get('post_content', 'No content available') or 'No content available'}
        </div>
        """, unsafe_allow_html=True)

        if request.get('post_url'):
            st.markdown(f"[🔗 View on Reddit]({request['post_url']})")

        # AI-generated response area
        st.markdown("### 🤖 AI-Generated Response")
        citations = parse_citations(request.get('citations', '[]'))
        if citations:
            st.markdown("**📚 Sources Used:**")
            for citation in citations:
                st.markdown(f"- {citation.get('title', 'Unknown source')}")

        # Show drafted reply if exists
        drafted_reply = request.get('drafted_reply', '')
        edited_reply = st.text_area(
            "Response (edit if needed):",
            value=drafted_reply,
            height=200,
            key=f"reply_{request.get('id')}"
        )

        if moderation_score > 0.5:
            st.warning("⚠️ This response may need additional review due to moderation flags.")

        # Extra context from subreddit
        st.markdown(f"### 🔗 Context from r/{request.get('subreddit', 'Unknown')}")
        reddit_data = get_subreddit_data(request.get('subreddit', ''), limit=1)
        if isinstance(reddit_data, dict) and reddit_data.get("error"):
            st.error(f"Error fetching subreddit: {reddit_data['error']}")
        else:
            for post in reddit_data or []:
                st.markdown(f"- [{post.get('title', 'No Title')}]({post.get('url', '#')}) "
                            f"(👍 {post.get('score', 0)} | u/{post.get('author', 'Unknown')})")

        # Action buttons
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("✅ Approve", key=f"approve_{request.get('id')}", use_container_width=True):
                final_reply = sanitize_input(edited_reply)
                result = agent_integration.approve_request(
                    request.get('id'),
                    final_reply,
                    post_to_reddit=True
                )
                status = result.get('status')
                if status in ["success", "dry_run"]:
                    st.success(f"✅ Approved! {result.get('message', '')}")
                else:
                    st.warning(f"Approved locally, but posting failed: {result.get('message', 'Unknown error')}")
                st.rerun()

        with col2:
            if st.button("❌ Reject", key=f"reject_{request.get('id')}", use_container_width=True):
                feedback = st.text_input(f"Rejection reason (optional):", key=f"feedback_{request.get('id')}")
                result = agent_integration.reject_request(request.get('id'), feedback)
                if result.get('status') == 'success':
                    st.error("❌ Request rejected")
                else:
                    st.error(f"❌ Failed to reject: {result.get('message', 'Unknown error')}")
                st.rerun()

        with col3:
            if st.button("⏳ Defer", key=f"defer_{request.get('id')}", use_container_width=True):
                db.log_user_action('defer', request.get('id'), 'admin')
                st.info("⏳ Request deferred for later review")

        with col4:
            if st.button("🔍 Details", key=f"details_{request.get('id')}", use_container_width=True):
                with st.expander("🔍 Detailed Information", expanded=True):
                    st.json({
                        'request_id': request.get('id'),
                        'timestamp': request.get('created_at'),
                        'processing_time': request.get('processing_time'),
                        'confidence': request.get('agent_confidence'),
                        'moderation_flags': json.loads(request.get('moderation_flags', '[]')),
                        'citations': citations
                    })

        # --- NEW: Generate Answer Button ---
        with col5:
            if st.button("💡 Generate Answer", key=f"generate_{request.get('id')}", use_container_width=True):
                # Generate draft only for this request
                draft = generate_draft_with_groq(request.get('post_title') + "\n\n" + (request.get('post_content') or ""))
                db.update_request_draft(request.get('id'), draft)
                st.success("💡 Draft generated! Edit if needed.")
                st.rerun()

def render_request_summary(request):
    """Render summary of completed request"""
    status_color = {
        'approved': '#10b981',
        'rejected': '#ef4444'
    }.get(request['status'], '#6366f1')

    st.markdown(f"""
    <div style="padding: 1rem; margin: 1rem 0; background: var(--bg-card); border-radius: 8px; border-left: 3px solid {status_color};">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <strong style="color: var(--text-primary);">{request['post_title'][:100]}{'...' if len(request['post_title']) > 100 else ''}</strong>
            {create_status_badge(request['status'])}
        </div>
        <div style="color: var(--text-secondary); font-size: 0.9rem;">
            r/{request['subreddit']} • {format_timestamp(request['created_at'])} • {format_confidence_score(request.get('agent_confidence'))}
        </div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    render_approval_page()
