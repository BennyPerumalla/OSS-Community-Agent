import json
import sqlite3
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

class DatabaseManager:
    """
    Manages SQLite database for storing agent requests, responses, analytics, and settings
    """
    
    def __init__(self, db_path: str = "data/agent_data.db"):
        # Special-case in-memory DB; do not alter the path
        if db_path == ":memory:":
            self.db_path = db_path
            self.init_database()
            return
        # If relative path, make it relative to project root
        if not os.path.isabs(db_path):
            project_root = Path(__file__).parent.parent.parent.parent
            db_path = str(project_root / db_path)
        
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    subreddit TEXT NOT NULL,
                    post_id TEXT,
                    post_title TEXT,
                    post_content TEXT,
                    post_author TEXT,
                    post_url TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    drafted_reply TEXT,
                    final_reply TEXT,
                    moderation_score REAL,
                    moderation_flags TEXT,
                    processing_time REAL,
                    agent_confidence REAL,
                    citations TEXT,
                    human_feedback TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id TEXT PRIMARY KEY,
                    run_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time DATETIME,
                    end_time DATETIME,
                    duration REAL,
                    subreddit TEXT,
                    query TEXT,
                    posts_found INTEGER DEFAULT 0,
                    replies_drafted INTEGER DEFAULT 0,
                    replies_approved INTEGER DEFAULT 0,
                    replies_rejected INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS analytics_daily (
                    date DATE PRIMARY KEY,
                    total_requests INTEGER DEFAULT 0,
                    approved_requests INTEGER DEFAULT 0,
                    rejected_requests INTEGER DEFAULT 0,
                    avg_processing_time REAL DEFAULT 0,
                    avg_confidence_score REAL DEFAULT 0,
                    unique_subreddits INTEGER DEFAULT 0,
                    top_subreddit TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS user_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    request_id TEXT,
                    user_id TEXT DEFAULT 'admin',
                    action_data TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS agent_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    settings_json TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status);
                CREATE INDEX IF NOT EXISTS idx_requests_subreddit ON requests(subreddit);
                CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON requests(timestamp);
                CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);
            ''')
    
    # -----------------------------
    # Request Management
    # -----------------------------
    def add_request(self, request_data: Dict[str, Any]) -> str:
        """Add a new request to the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO requests (
                    id, subreddit, post_id, post_title, post_content, 
                    post_author, post_url, status, drafted_reply, 
                    moderation_score, moderation_flags, agent_confidence, citations
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                request_data.get('id'),
                request_data.get('subreddit'),
                request_data.get('post_id'),
                request_data.get('post_title'),
                request_data.get('post_content'),
                request_data.get('post_author'),
                request_data.get('post_url'),
                request_data.get('status', 'pending'),
                request_data.get('drafted_reply'),
                request_data.get('moderation_score'),
                json.dumps(request_data.get('moderation_flags', [])),
                request_data.get('agent_confidence'),
                json.dumps(request_data.get('citations', []))
            ))
            return request_data.get('id')
    
    def insert_request(self, request_data: Dict[str, Any]) -> str:
        """
        Compatibility wrapper for add_request.
        Ensures unique ID and avoids duplicate post_ids.
        """
        # Avoid duplicate Reddit post ingestion
        if self.request_exists_by_post_id(request_data.get("post_id")):
            return request_data.get("id") or request_data.get("post_id")
        
        # Ensure a unique ID
        if not request_data.get("id"):
            request_data["id"] = str(uuid.uuid4())
        
        return self.add_request(request_data)
    
    def update_request_status(self, request_id: str, status: str, 
                            final_reply: str = None, human_feedback: str = None):
        """Update request status and final reply"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE requests 
                SET status = ?, final_reply = ?, human_feedback = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, final_reply, human_feedback, request_id))
    
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending requests for approval"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM requests 
                WHERE status = 'pending' 
                ORDER BY created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    def get_request_by_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single request by its ID"""
        if not request_id:
            return None
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM requests WHERE id = ? LIMIT 1
            ''', (request_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_requests_by_filter(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get requests with filters"""
        query = "SELECT * FROM requests WHERE 1=1"
        params = []
        
        if filters.get('status'):
            query += " AND status = ?"
            params.append(filters['status'])
        
        if filters.get('subreddit'):
            query += " AND subreddit LIKE ?"
            params.append(f"%{filters['subreddit']}%")
        
        if filters.get('date_from'):
            query += " AND created_at >= ?"
            params.append(filters['date_from'])
        
        if filters.get('date_to'):
            query += " AND created_at <= ?"
            params.append(filters['date_to'])
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(filters.get('limit', 100))
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # -----------------------------
    # Analytics
    # -----------------------------
    def get_analytics_overview(self) -> Dict[str, Any]:
        """Get overview analytics for dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Total requests today
            today = datetime.now().strftime('%Y-%m-%d')
            cursor = conn.execute('''
                SELECT COUNT(*) as total_today FROM requests 
                WHERE DATE(created_at) = ?
            ''', (today,))
            total_today = cursor.fetchone()['total_today']
            
            # Pending requests
            cursor = conn.execute('''
                SELECT COUNT(*) as pending FROM requests WHERE status = 'pending'
            ''')
            pending = cursor.fetchone()['pending']
            
            # Approval rate (last 7 days)
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            cursor = conn.execute('''
                SELECT 
                    COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved,
                    COUNT(*) as total
                FROM requests 
                WHERE DATE(created_at) >= ?
            ''', (week_ago,))
            approval_data = cursor.fetchone()
            approval_rate = (approval_data['approved'] / approval_data['total'] * 100) if approval_data['total'] > 0 else 0
            
            # Average response time
            cursor = conn.execute('''
                SELECT AVG(processing_time) as avg_time 
                FROM requests 
                WHERE processing_time IS NOT NULL AND DATE(created_at) >= ?
            ''', (week_ago,))
            avg_time = cursor.fetchone()['avg_time'] or 0
            
            # Top subreddits
            cursor = conn.execute('''
                SELECT subreddit, COUNT(*) as count 
                FROM requests 
                WHERE DATE(created_at) >= ? 
                GROUP BY subreddit 
                ORDER BY count DESC 
                LIMIT 5
            ''', (week_ago,))
            top_subreddits = [dict(row) for row in cursor.fetchall()]
            
            return {
                'total_today': total_today,
                'pending_requests': pending,
                'approval_rate': round(approval_rate, 1),
                'avg_response_time': round(avg_time, 2),
                'top_subreddits': top_subreddits
            }
    
    def get_daily_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily statistics for charts"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as total_requests,
                    COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved,
                    COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected,
                    AVG(processing_time) as avg_time,
                    AVG(agent_confidence) as avg_confidence
                FROM requests 
                WHERE DATE(created_at) >= ?
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            ''', (start_date,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # -----------------------------
    # User Actions
    # -----------------------------
    def log_user_action(self, action_type: str, request_id: str = None, 
                       user_id: str = 'admin', action_data: Dict = None):
        """Log user actions for audit trail"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO user_actions (action_type, request_id, user_id, action_data)
                VALUES (?, ?, ?, ?)
            ''', (action_type, request_id, user_id, json.dumps(action_data or {})))
    
    def request_exists_by_post_id(self, post_id: str) -> bool:
        """Check if a request already exists for a given Reddit post_id"""
        if not post_id:
            return False
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT 1 FROM requests WHERE post_id = ? LIMIT 1
            ''', (post_id,))
            return cursor.fetchone() is not None
    
    def get_request_by_post_id(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Get a request by Reddit post_id"""
        if not post_id:
            return None
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM requests WHERE post_id = ? LIMIT 1
            ''', (post_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    def update_request_draft(self, request_id: int, draft: str):
        """
        Update the drafted reply for a specific request.
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = """
                UPDATE requests
                SET drafted_reply = %s
                WHERE id = %s
            """
            cursor.execute(query, (draft, request_id))
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Error updating draft for request {request_id}: {e}")

    # -----------------------------
    # Agent Settings
    # -----------------------------
    def get_agent_settings(self) -> Dict[str, Any]:
        """Fetch agent settings from DB"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT settings_json FROM agent_settings WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return json.loads(row["settings_json"])
            return {}

    def save_agent_settings(self, settings: Dict[str, Any]):
        """Save agent settings into DB (overwrite row id=1)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO agent_settings (id, settings_json, updated_at)
                VALUES (1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET 
                    settings_json = excluded.settings_json,
                    updated_at = CURRENT_TIMESTAMP
            ''', (json.dumps(settings),))
