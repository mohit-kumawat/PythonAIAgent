"""
Memory Manager - Persistent Knowledge Base for PM Agent
Stores decisions, thread context, and learned patterns using SQLite.
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional


class MemoryManager:
    """
    Manages persistent memory for the PM Agent.
    
    Tables:
    - decisions: Tracks approved/rejected actions for learning
    - thread_context: Stores Slack thread summaries for continuity
    - knowledge: Extracted facts, user preferences, patterns
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Check for persistent storage path
            data_dir = os.environ.get('PERSISTENT_DATA_PATH')
            if data_dir:
                os.makedirs(data_dir, exist_ok=True)
                db_path = os.path.join(data_dir, "pm_agent.db")
            else:
                db_path = "memory/pm_agent.db"
        
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Decisions table - track what was approved/rejected
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                approved INTEGER NOT NULL,
                reasoning TEXT,
                action_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Thread context table - store Slack thread continuity
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS thread_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_ts TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                summary TEXT,
                entities TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(thread_ts, channel_id)
            )
        ''')
        
        # Processed Messages table - De-duplication across restarts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_messages (
                message_ts TEXT PRIMARY KEY,
                channel_id TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Knowledge table - extracted facts and patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Action history table - full log of executed actions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                status TEXT NOT NULL,
                reasoning TEXT,
                action_data TEXT,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Sent reports table - track daily/weekly reports to prevent duplicates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_reports (
                report_key TEXT PRIMARY KEY,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_processed_message(self, message_ts: str, channel_id: str = ""):
        """Mark a message as processed in the persistent DB."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT OR IGNORE INTO processed_messages (message_ts, channel_id) VALUES (?, ?)',
                (message_ts, channel_id)
            )
            conn.commit()
        except Exception as e:
            print(f"Error marking message processed: {e}")
        finally:
            conn.close()

    def is_message_processed(self, message_ts: str) -> bool:
        """Check if a message has already been processed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM processed_messages WHERE message_ts = ?', (message_ts,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def log_decision(self, action_type: str, approved: bool, reasoning: str, action_data: dict = None) -> int:
        """
        Log a decision (approval or rejection) for learning.
        
        Args:
            action_type: Type of action (e.g., 'schedule_reminder', 'send_email_summary')
            approved: Whether the action was approved
            reasoning: The agent's reasoning for the action
            action_data: Optional action parameters
            
        Returns:
            The ID of the logged decision
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO decisions (action_type, approved, reasoning, action_data)
            VALUES (?, ?, ?, ?)
        ''', (action_type, 1 if approved else 0, reasoning, json.dumps(action_data) if action_data else None))
        
        decision_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return decision_id
    
    def get_decision_history(self, action_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent decisions, optionally filtered by action type.
        
        Args:
            action_type: Filter by action type (optional)
            limit: Maximum number of decisions to return
            
        Returns:
            List of decision records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if action_type:
            cursor.execute('''
                SELECT * FROM decisions WHERE action_type = ?
                ORDER BY created_at DESC LIMIT ?
            ''', (action_type, limit))
        else:
            cursor.execute('''
                SELECT * FROM decisions ORDER BY created_at DESC LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_approval_rate(self, action_type: str = None) -> Dict[str, Any]:
        """
        Calculate approval rate for decisions.
        
        Returns:
            Dict with total, approved, rejected counts and rate
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if action_type:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(approved) as approved
                FROM decisions WHERE action_type = ?
            ''', (action_type,))
        else:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(approved) as approved
                FROM decisions
            ''')
        
        row = cursor.fetchone()
        conn.close()
        
        total = row[0] or 0
        approved = row[1] or 0
        
        return {
            "total": total,
            "approved": approved,
            "rejected": total - approved,
            "rate": round(approved / total * 100, 1) if total > 0 else 0
        }
    
    def store_thread_context(self, thread_ts: str, channel_id: str, summary: str, entities: List[str] = None):
        """
        Store or update context for a Slack thread.
        
        Args:
            thread_ts: Slack thread timestamp
            channel_id: Slack channel ID
            summary: Summary of the thread's content/context
            entities: List of extracted entities (user mentions, topics, etc.)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO thread_context (thread_ts, channel_id, summary, entities, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(thread_ts, channel_id) DO UPDATE SET
                summary = excluded.summary,
                entities = excluded.entities,
                updated_at = CURRENT_TIMESTAMP
        ''', (thread_ts, channel_id, summary, json.dumps(entities) if entities else None))
        
        conn.commit()
        conn.close()
    
    def get_thread_context(self, thread_ts: str, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve context for a Slack thread.
        
        Returns:
            Thread context dict or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM thread_context 
            WHERE thread_ts = ? AND channel_id = ?
        ''', (thread_ts, channel_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = dict(row)
            if result.get('entities'):
                result['entities'] = json.loads(result['entities'])
            return result
        return None
    
    def store_insight(self, category: str, content: str, source: str = None, metadata: dict = None):
        """
        Store a learned insight or fact.
        
        Categories:
        - 'user_preference': User preferences and patterns
        - 'project_fact': Facts about the project
        - 'team_pattern': Team working patterns
        - 'blocker_pattern': Common blocker types
        
        Args:
            category: Category of the insight
            content: The insight content
            source: Where this was learned from (e.g., 'slack:C123:ts456')
            metadata: Additional metadata
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO knowledge (category, content, source, metadata)
            VALUES (?, ?, ?, ?)
        ''', (category, content, source, json.dumps(metadata) if metadata else None))
        
        conn.commit()
        conn.close()
    
    def search_memory(self, query: str, category: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search through stored knowledge.
        
        Args:
            query: Search query (simple LIKE matching)
            category: Optional category filter
            limit: Maximum results
            
        Returns:
            List of matching knowledge entries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if category:
            cursor.execute('''
                SELECT * FROM knowledge 
                WHERE category = ? AND content LIKE ?
                ORDER BY created_at DESC LIMIT ?
            ''', (category, f'%{query}%', limit))
        else:
            cursor.execute('''
                SELECT * FROM knowledge 
                WHERE content LIKE ?
                ORDER BY created_at DESC LIMIT ?
            ''', (f'%{query}%', limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            result = dict(row)
            if result.get('metadata'):
                result['metadata'] = json.loads(result['metadata'])
            results.append(result)
        
        return results
    
    def get_knowledge_by_category(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all knowledge in a category."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM knowledge 
            WHERE category = ?
            ORDER BY created_at DESC LIMIT ?
        ''', (category, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def log_action_execution(self, action_id: str, action_type: str, status: str, 
                             reasoning: str, action_data: dict = None, result: str = None):
        """
        Log an executed action for history.
        
        Args:
            action_id: Unique action identifier
            action_type: Type of action
            status: Execution status (SUCCESS, FAILED, REJECTED)
            reasoning: Original reasoning
            action_data: Action parameters
            result: Execution result or error message
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO action_history (action_id, action_type, status, reasoning, action_data, result)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (action_id, action_type, status, reasoning, 
              json.dumps(action_data) if action_data else None, result))
        
        conn.commit()
        conn.close()
    
    def get_action_history(self, limit: int = 50, status: str = None) -> List[Dict[str, Any]]:
        """
        Get action execution history.
        
        Args:
            limit: Maximum actions to return
            status: Optional status filter
            
        Returns:
            List of action history records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT * FROM action_history 
                WHERE status = ?
                ORDER BY created_at DESC LIMIT ?
            ''', (status, limit))
        else:
            cursor.execute('''
                SELECT * FROM action_history 
                ORDER BY created_at DESC LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            result = dict(row)
            if result.get('action_data'):
                result['action_data'] = json.loads(result['action_data'])
            results.append(result)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get overall memory statistics.
        
        Returns:
            Dict with counts and stats
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM decisions')
        decisions_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM thread_context')
        threads_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM knowledge')
        knowledge_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM action_history')
        actions_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM action_history WHERE status = 'SUCCESS'")
        successful_actions = cursor.fetchone()[0]
        
        conn.close()
        
        approval = self.get_approval_rate()
        
        return {
            "decisions": decisions_count,
            "threads": threads_count,
            "knowledge_entries": knowledge_count,
            "total_actions": actions_count,
            "successful_actions": successful_actions,
            "approval_rate": approval["rate"]
        }
    
    def has_sent_report(self, report_key: str) -> bool:
        """
        Check if a report has already been sent today.
        
        Args:
            report_key: Unique key for the report (e.g., 'daily_morning_2025-12-10')
            
        Returns:
            True if report was already sent, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM sent_reports WHERE report_key = ?', (report_key,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def mark_report_sent(self, report_key: str):
        """
        Mark a report as sent.
        
        Args:
            report_key: Unique key for the report (e.g., 'daily_morning_2025-12-10')
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT OR REPLACE INTO sent_reports (report_key) VALUES (?)',
                (report_key,)
            )
            conn.commit()
        except Exception as e:
            print(f"Error marking report sent: {e}")
        finally:
            conn.close()

    def save_context(self, content: str):
        """Save project context (File based fallback)."""
        # Determine path
        try:
            path = "context.md"
            if os.environ.get('PERSISTENT_DATA_PATH'):
                path = os.path.join(os.environ.get('PERSISTENT_DATA_PATH'), "context.md")
            
            with open(path, "w") as f:
                f.write(content)
        except Exception as e:
            print(f"Error saving context file: {e}")

    def load_context(self) -> str:
        """Load project context (File based fallback)."""
        try:
            path = "context.md"
            if os.environ.get('PERSISTENT_DATA_PATH'):
                path = os.path.join(os.environ.get('PERSISTENT_DATA_PATH'), "context.md")
            
            if os.path.exists(path):
                with open(path, "r") as f:
                    return f.read()
            return ""
        except Exception as e:
            print(f"Error loading context file: {e}")
            return ""


# Start Postgres Support
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

class PostgresMemoryManager:
    """PostgreSQL implementation of MemoryManager."""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self._init_db()

    def get_connection(self):
        return psycopg2.connect(self.db_url)

    def _init_db(self):
        """Initialize Postgres tables."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # Decisions
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS decisions (
                        id SERIAL PRIMARY KEY,
                        action_type TEXT NOT NULL,
                        approved INTEGER NOT NULL,
                        reasoning TEXT,
                        action_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Thread context
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS thread_context (
                        id SERIAL PRIMARY KEY,
                        thread_ts TEXT NOT NULL,
                        channel_id TEXT NOT NULL,
                        summary TEXT,
                        entities TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(thread_ts, channel_id)
                    )
                ''')
                
                # Processed Messages
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS processed_messages (
                        message_ts TEXT PRIMARY KEY,
                        channel_id TEXT,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Knowledge
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS knowledge (
                        id SERIAL PRIMARY KEY,
                        category TEXT NOT NULL,
                        content TEXT NOT NULL,
                        source TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Action history
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS action_history (
                        id SERIAL PRIMARY KEY,
                        action_id TEXT NOT NULL,
                        action_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        reasoning TEXT,
                        action_data TEXT,
                        result TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Sent reports
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sent_reports (
                        report_key TEXT PRIMARY KEY,
                        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Project Context (New for full robustness)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS project_context (
                        key TEXT PRIMARY KEY,
                        content TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            conn.commit()
        finally:
            conn.close()

    def add_processed_message(self, message_ts: str, channel_id: str = ""):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO processed_messages (message_ts, channel_id) VALUES (%s, %s) ON CONFLICT DO NOTHING',
                    (message_ts, channel_id)
                )
            conn.commit()
        except Exception as e:
            print(f"PG: Error marking processed: {e}")
        finally:
            conn.close()

    def is_message_processed(self, message_ts: str) -> bool:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1 FROM processed_messages WHERE message_ts = %s', (message_ts,))
                result = cursor.fetchone()
            return result is not None
        finally:
            conn.close()

    def log_decision(self, action_type: str, approved: bool, reasoning: str, action_data: dict = None) -> int:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO decisions (action_type, approved, reasoning, action_data)
                    VALUES (%s, %s, %s, %s) RETURNING id
                ''', (action_type, 1 if approved else 0, reasoning, json.dumps(action_data) if action_data else None))
                decision_id = cursor.fetchone()[0]
            conn.commit()
            return decision_id
        finally:
            conn.close()

    def get_decision_history(self, action_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if action_type:
                    cursor.execute('SELECT * FROM decisions WHERE action_type = %s ORDER BY created_at DESC LIMIT %s', (action_type, limit))
                else:
                    cursor.execute('SELECT * FROM decisions ORDER BY created_at DESC LIMIT %s', (limit,))
                rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
            
    def get_approval_rate(self, action_type: str = None) -> Dict[str, Any]:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                if action_type:
                    cursor.execute('SELECT COUNT(*), SUM(approved) FROM decisions WHERE action_type = %s', (action_type,))
                else:
                    cursor.execute('SELECT COUNT(*), SUM(approved) FROM decisions')
                row = cursor.fetchone()
            
            total = row[0] or 0
            approved = row[1] or 0
            return {
                "total": total, 
                "approved": approved, 
                "rejected": total - approved, 
                "rate": round(approved / total * 100, 1) if total > 0 else 0
            }
        finally:
            conn.close()

    def store_thread_context(self, thread_ts: str, channel_id: str, summary: str, entities: List[str] = None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO thread_context (thread_ts, channel_id, summary, entities, updated_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT(thread_ts, channel_id) DO UPDATE SET
                        summary = EXCLUDED.summary,
                        entities = EXCLUDED.entities,
                        updated_at = CURRENT_TIMESTAMP
                ''', (thread_ts, channel_id, summary, json.dumps(entities) if entities else None))
            conn.commit()
        finally:
            conn.close()

    def get_thread_context(self, thread_ts: str, channel_id: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute('SELECT * FROM thread_context WHERE thread_ts = %s AND channel_id = %s', (thread_ts, channel_id))
                row = cursor.fetchone()
            if row:
                res = dict(row)
                if res.get('entities'): res['entities'] = json.loads(res['entities'])
                return res
            return None
        finally:
            conn.close()

    def store_insight(self, category: str, content: str, source: str = None, metadata: dict = None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO knowledge (category, content, source, metadata)
                    VALUES (%s, %s, %s, %s)
                ''', (category, content, source, json.dumps(metadata) if metadata else None))
            conn.commit()
        finally:
            conn.close()

    def search_memory(self, query: str, category: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if category:
                    cursor.execute('SELECT * FROM knowledge WHERE category = %s AND content ILIKE %s ORDER BY created_at DESC LIMIT %s', (category, f'%{query}%', limit))
                else:
                    cursor.execute('SELECT * FROM knowledge WHERE content ILIKE %s ORDER BY created_at DESC LIMIT %s', (f'%{query}%', limit))
                rows = cursor.fetchall()
            results = []
            for row in rows:
                r = dict(row)
                if r.get('metadata'): r['metadata'] = json.loads(r['metadata'])
                results.append(r)
            return results
        finally:
            conn.close()

    def get_knowledge_by_category(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute('SELECT * FROM knowledge WHERE category = %s ORDER BY created_at DESC LIMIT %s', (category, limit))
                rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def log_action_execution(self, action_id: str, action_type: str, status: str, reasoning: str, action_data: dict = None, result: str = None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO action_history (action_id, action_type, status, reasoning, action_data, result)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (action_id, action_type, status, reasoning, json.dumps(action_data) if action_data else None, result))
            conn.commit()
        finally:
            conn.close()
            
    def get_action_history(self, limit: int = 50, status: str = None) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if status:
                    cursor.execute('SELECT * FROM action_history WHERE status = %s ORDER BY created_at DESC LIMIT %s', (status, limit))
                else:
                    cursor.execute('SELECT * FROM action_history ORDER BY created_at DESC LIMIT %s', (limit,))
                rows = cursor.fetchall()
            results = []
            for row in rows:
                r = dict(row)
                if r.get('action_data'): r['action_data'] = json.loads(r['action_data'])
                results.append(r)
            return results
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM decisions')
                decisions = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM thread_context')
                threads = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM knowledge')
                knowledge = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM action_history')
                actions = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM action_history WHERE status = 'SUCCESS'")
                success = cursor.fetchone()[0]
            
            approval = self.get_approval_rate()
            return {
                "decisions": decisions,
                "threads": threads,
                "knowledge_entries": knowledge,
                "total_actions": actions,
                "successful_actions": success,
                "approval_rate": approval["rate"]
            }
        finally:
            conn.close()

    def has_sent_report(self, report_key: str) -> bool:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1 FROM sent_reports WHERE report_key = %s', (report_key,))
                return cursor.fetchone() is not None
        finally:
            conn.close()

    def mark_report_sent(self, report_key: str):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('INSERT INTO sent_reports (report_key) VALUES (%s) ON CONFLICT DO NOTHING', (report_key,))
            conn.commit()
        finally:
            conn.close()
            
    # New methods for Context Management (Professional Mode)
    def save_context(self, content: str):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO project_context (key, content, updated_at) 
                    VALUES ('main', %s, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET content = EXCLUDED.content, updated_at = CURRENT_TIMESTAMP
                ''', (content,))
            conn.commit()
        finally:
            conn.close()

    def load_context(self) -> str:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT content FROM project_context WHERE key = 'main'")
                row = cursor.fetchone()
            return row[0] if row else ""
        finally:
            conn.close()

# Singleton instance for easy import
_memory_instance = None

def get_memory_manager(db_path: str = None):
    """Get or create the singleton MemoryManager instance."""
    global _memory_instance
    if _memory_instance is None:
        # Check for DATABASE_URL (Render Postgres)
        db_url = os.environ.get('DATABASE_URL')
        if db_url and POSTGRES_AVAILABLE:
            print("🔌 Connecting to PostgreSQL Database...")
            _memory_instance = PostgresMemoryManager(db_url)
        else:
            # Fallback to SQLite
            _memory_instance = MemoryManager(db_path)
    return _memory_instance
