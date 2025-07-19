import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ChatHistoryService:
    """Service for managing chat history and user sessions"""
    
    def __init__(self, db_path: str = "chat_history.db"):
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for chat history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        session_id TEXT UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT  -- JSON for additional user info
                    )
                """)
                
                # Chat sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        title TEXT DEFAULT 'New Chat',
                        is_active BOOLEAN DEFAULT TRUE,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Messages table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        message_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        role TEXT NOT NULL,  -- 'user' or 'assistant'
                        content TEXT NOT NULL,
                        query_results TEXT,  -- JSON for SQL results
                        insights TEXT,       -- JSON for insights
                        sql_query TEXT,      -- Generated SQL
                        feedback_rating INTEGER,  -- 1-5 rating
                        feedback_comment TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES chat_sessions (session_id),
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_user ON messages (user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages (created_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON chat_sessions (user_id)")
                
                conn.commit()
                logger.info("Chat history database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize chat history database: {str(e)}")
            raise
    
    def create_user_session(self, user_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Create a new user and session"""
        try:
            user_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create user
                cursor.execute(
                    "INSERT INTO users (user_id, session_id, metadata) VALUES (?, ?, ?)",
                    (user_id, session_id, json.dumps(user_metadata or {}))
                )
                
                # Create initial session
                cursor.execute(
                    "INSERT INTO chat_sessions (session_id, user_id) VALUES (?, ?)",
                    (session_id, user_id)
                )
                
                conn.commit()
                
            logger.info(f"Created new user session: {user_id}")
            return {"user_id": user_id, "session_id": session_id}
            
        except Exception as e:
            logger.error(f"Failed to create user session: {str(e)}")
            raise
    
    def get_or_create_user(self, session_id: Optional[str] = None) -> Dict[str, str]:
        """Get existing user by session ID or create new one"""
        if session_id:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT user_id, session_id FROM users WHERE session_id = ?",
                        (session_id,)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        # Update last active
                        cursor.execute(
                            "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
                            (result[0],)
                        )
                        conn.commit()
                        
                        return {"user_id": result[0], "session_id": result[1]}
            except Exception as e:
                logger.warning(f"Failed to get existing user: {str(e)}")
        
        # Create new user if not found
        return self.create_user_session()
    
    def save_message(
        self, 
        user_id: str, 
        session_id: str, 
        role: str, 
        content: str,
        query_results: Optional[Dict[str, Any]] = None,
        insights: Optional[List[str]] = None,
        sql_query: Optional[str] = None
    ) -> str:
        """Save a message to chat history"""
        try:
            message_id = str(uuid.uuid4())
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO messages (
                        message_id, session_id, user_id, role, content, 
                        query_results, insights, sql_query
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    message_id, session_id, user_id, role, content,
                    json.dumps(query_results) if query_results else None,
                    json.dumps(insights) if insights else None,
                    sql_query
                ))
                
                # Update session last message time and generate title if first message
                if role == 'user':
                    cursor.execute(
                        "SELECT COUNT(*) FROM messages WHERE session_id = ? AND role = 'user'",
                        (session_id,)
                    )
                    user_message_count = cursor.fetchone()[0]
                    
                    if user_message_count == 1:  # First user message
                        # Generate a title from the first few words
                        title = content[:50] + "..." if len(content) > 50 else content
                        cursor.execute(
                            "UPDATE chat_sessions SET title = ?, last_message_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                            (title, session_id)
                        )
                    else:
                        cursor.execute(
                            "UPDATE chat_sessions SET last_message_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                            (session_id,)
                        )
                
                conn.commit()
                
            logger.info(f"Saved message {message_id} for user {user_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to save message: {str(e)}")
            raise
    
    def get_chat_history(self, user_id: str, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for a session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT message_id, role, content, query_results, insights, sql_query, 
                           feedback_rating, feedback_comment, created_at
                    FROM messages 
                    WHERE session_id = ? AND user_id = ?
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (session_id, user_id, limit))
                
                messages = []
                for row in cursor.fetchall():
                    message = {
                        "id": row[0],
                        "role": row[1],
                        "content": row[2],
                        "query_results": json.loads(row[3]) if row[3] else None,
                        "insights": json.loads(row[4]) if row[4] else None,
                        "sql_query": row[5],
                        "feedback_rating": row[6],
                        "feedback_comment": row[7],
                        "timestamp": row[8]
                    }
                    messages.append(message)
                
                return messages
                
        except Exception as e:
            logger.error(f"Failed to get chat history: {str(e)}")
            return []
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT session_id, title, created_at, last_message_at, is_active,
                           (SELECT COUNT(*) FROM messages WHERE session_id = cs.session_id) as message_count
                    FROM chat_sessions cs
                    WHERE user_id = ?
                    ORDER BY last_message_at DESC
                """, (user_id,))
                
                sessions = []
                for row in cursor.fetchall():
                    session = {
                        "session_id": row[0],
                        "title": row[1],
                        "created_at": row[2],
                        "last_message_at": row[3],
                        "is_active": bool(row[4]),
                        "message_count": row[5]
                    }
                    sessions.append(session)
                
                return sessions
                
        except Exception as e:
            logger.error(f"Failed to get user sessions: {str(e)}")
            return []
    
    def add_feedback(self, message_id: str, rating: int, comment: Optional[str] = None):
        """Add feedback for a message"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "UPDATE messages SET feedback_rating = ?, feedback_comment = ? WHERE message_id = ?",
                    (rating, comment, message_id)
                )
                
                conn.commit()
                
            logger.info(f"Added feedback for message {message_id}: {rating}/5")
            
        except Exception as e:
            logger.error(f"Failed to add feedback: {str(e)}")
            raise
    
    def get_feedback_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get feedback statistics for the last N days"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_ratings,
                        AVG(feedback_rating) as avg_rating,
                        COUNT(CASE WHEN feedback_rating >= 4 THEN 1 END) as positive_ratings,
                        COUNT(CASE WHEN feedback_rating <= 2 THEN 1 END) as negative_ratings
                    FROM messages 
                    WHERE feedback_rating IS NOT NULL 
                    AND created_at >= datetime('now', '-{} days')
                """.format(days))
                
                result = cursor.fetchone()
                
                return {
                    "total_ratings": result[0],
                    "average_rating": round(result[1], 2) if result[1] else 0,
                    "positive_ratings": result[2],
                    "negative_ratings": result[3],
                    "satisfaction_rate": round((result[2] / result[0]) * 100, 1) if result[0] > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get feedback stats: {str(e)}")
            return {}
    
    def cleanup_old_sessions(self, days: int = 90):
        """Clean up sessions older than N days"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Mark old sessions as inactive
                cursor.execute(
                    "UPDATE chat_sessions SET is_active = FALSE WHERE last_message_at < datetime('now', '-{} days')".format(days)
                )
                
                deleted_count = cursor.rowcount
                conn.commit()
                
            logger.info(f"Marked {deleted_count} old sessions as inactive")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {str(e)}")


# Global instance
chat_history_service = ChatHistoryService()