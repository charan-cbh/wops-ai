"""
Scalable Chat History Service for AWS Deployment
Supports both PostgreSQL (RDS) and DynamoDB backends
"""

import logging
import json
import boto3
import psycopg2
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class ChatMessage(BaseModel):
    message_id: str
    session_id: str
    user_id: str
    role: str  # 'user' or 'assistant'
    content: str
    feedback_rating: Optional[int] = None
    feedback_comment: Optional[str] = None
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None  # For storing insights, charts, etc.

class ChatSession(BaseModel):
    session_id: str
    user_id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None

class ScalableChatService:
    """
    Scalable chat service that can use either PostgreSQL (for AWS RDS) 
    or DynamoDB (for serverless) as backend storage
    """
    
    def __init__(self, storage_type: str = "postgres"):
        self.storage_type = storage_type.lower()
        
        if self.storage_type == "postgres":
            self._init_postgres()
        elif self.storage_type == "dynamodb":
            self._init_dynamodb()
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")
            
        logger.info(f"Initialized ScalableChatService with {self.storage_type} backend")

    def _init_postgres(self):
        """Initialize PostgreSQL connection for AWS RDS"""
        self.db_config = {
            'host': os.getenv('RDS_HOST', 'localhost'),
            'port': os.getenv('RDS_PORT', '5432'),
            'database': os.getenv('RDS_DATABASE', 'wops_ai'),
            'user': os.getenv('RDS_USER', 'postgres'),
            'password': os.getenv('RDS_PASSWORD', 'password')
        }
        self._create_postgres_tables()

    def _init_dynamodb(self):
        """Initialize DynamoDB for serverless deployment"""
        aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.dynamodb = boto3.resource('dynamodb', region_name=aws_region)
        
        # Table names
        self.messages_table_name = os.getenv('DYNAMODB_MESSAGES_TABLE', 'wops-ai-messages')
        self.sessions_table_name = os.getenv('DYNAMODB_SESSIONS_TABLE', 'wops-ai-sessions')
        
        try:
            self.messages_table = self.dynamodb.Table(self.messages_table_name)
            self.sessions_table = self.dynamodb.Table(self.sessions_table_name)
        except Exception as e:
            logger.error(f"Error accessing DynamoDB tables: {e}")
            # Tables will be created if they don't exist

    @contextmanager
    def _get_postgres_connection(self):
        """Context manager for PostgreSQL connections"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"PostgreSQL error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _create_postgres_tables(self):
        """Create PostgreSQL tables if they don't exist"""
        with self._get_postgres_connection() as conn:
            cursor = conn.cursor()
            
            # Users table (for user management)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) DEFAULT 'user',
                    is_active BOOLEAN DEFAULT true,
                    usage_limit INTEGER DEFAULT 100,
                    usage_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Chat sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    title VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB
                );
            """)
            
            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    feedback_rating INTEGER CHECK (feedback_rating >= 1 AND feedback_rating <= 5),
                    feedback_comment TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB
                );
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_created 
                ON messages(session_id, created_at);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_user_created 
                ON messages(user_id, created_at);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_updated 
                ON chat_sessions(user_id, updated_at);
            """)
            
            conn.commit()
            logger.info("PostgreSQL tables created successfully")

    def create_dynamodb_tables(self):
        """Create DynamoDB tables (call this during AWS deployment)"""
        try:
            # Messages table
            self.dynamodb.create_table(
                TableName=self.messages_table_name,
                KeySchema=[
                    {'AttributeName': 'session_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'session_id', 'AttributeType': 'S'},
                    {'AttributeName': 'created_at', 'AttributeType': 'S'},
                    {'AttributeName': 'user_id', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'UserIndex',
                        'KeySchema': [
                            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                            {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Sessions table
            self.dynamodb.create_table(
                TableName=self.sessions_table_name,
                KeySchema=[
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'session_id', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'user_id', 'AttributeType': 'S'},
                    {'AttributeName': 'session_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            logger.info("DynamoDB tables created successfully")
            
        except Exception as e:
            logger.info(f"DynamoDB tables may already exist: {e}")

    async def save_message(self, session_id: str, user_id: str, role: str, 
                          content: str, metadata: Optional[Dict] = None) -> str:
        """Save a message to the chat history"""
        message_id = str(uuid4())
        created_at = datetime.now(timezone.utc)
        
        if self.storage_type == "postgres":
            return await self._save_message_postgres(
                message_id, session_id, user_id, role, content, created_at, metadata
            )
        else:
            return await self._save_message_dynamodb(
                message_id, session_id, user_id, role, content, created_at, metadata
            )

    async def _save_message_postgres(self, message_id: str, session_id: str, 
                                   user_id: str, role: str, content: str, 
                                   created_at: datetime, metadata: Optional[Dict]) -> str:
        """Save message to PostgreSQL"""
        with self._get_postgres_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (message_id, session_id, user_id, role, content, created_at, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (message_id, session_id, user_id, role, content, created_at, 
                 json.dumps(metadata) if metadata else None))
            conn.commit()
        return message_id

    async def _save_message_dynamodb(self, message_id: str, session_id: str, 
                                   user_id: str, role: str, content: str, 
                                   created_at: datetime, metadata: Optional[Dict]) -> str:
        """Save message to DynamoDB"""
        item = {
            'session_id': session_id,
            'created_at': created_at.isoformat(),
            'message_id': message_id,
            'user_id': user_id,
            'role': role,
            'content': content
        }
        
        if metadata:
            item['metadata'] = metadata
            
        self.messages_table.put_item(Item=item)
        return message_id

    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get chat history for a session"""
        if self.storage_type == "postgres":
            return await self._get_chat_history_postgres(session_id, limit)
        else:
            return await self._get_chat_history_dynamodb(session_id, limit)

    async def _get_chat_history_postgres(self, session_id: str, limit: int) -> List[Dict]:
        """Get chat history from PostgreSQL"""
        with self._get_postgres_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT message_id, role, content, feedback_rating, feedback_comment, 
                       created_at, metadata
                FROM messages 
                WHERE session_id = %s 
                ORDER BY created_at ASC 
                LIMIT %s
            """, (session_id, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "message_id": str(row[0]),
                    "role": row[1],
                    "content": row[2],
                    "feedback_rating": row[3],
                    "feedback_comment": row[4],
                    "created_at": row[5].isoformat(),
                    "metadata": json.loads(row[6]) if row[6] else None
                })
            return results

    async def _get_chat_history_dynamodb(self, session_id: str, limit: int) -> List[Dict]:
        """Get chat history from DynamoDB"""
        response = self.messages_table.query(
            KeyConditionExpression='session_id = :session_id',
            ExpressionAttributeValues={':session_id': session_id},
            Limit=limit,
            ScanIndexForward=True  # Sort by created_at ascending
        )
        
        results = []
        for item in response['Items']:
            results.append({
                "message_id": item['message_id'],
                "role": item['role'],
                "content": item['content'],
                "feedback_rating": item.get('feedback_rating'),
                "feedback_comment": item.get('feedback_comment'),
                "created_at": item['created_at'],
                "metadata": item.get('metadata')
            })
        return results

    async def add_feedback(self, message_id: str, rating: int, comment: Optional[str] = None):
        """Add feedback to a message"""
        if self.storage_type == "postgres":
            await self._add_feedback_postgres(message_id, rating, comment)
        else:
            await self._add_feedback_dynamodb(message_id, rating, comment)

    async def _add_feedback_postgres(self, message_id: str, rating: int, comment: Optional[str]):
        """Add feedback to PostgreSQL"""
        with self._get_postgres_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE messages 
                SET feedback_rating = %s, feedback_comment = %s 
                WHERE message_id = %s
            """, (rating, comment, message_id))
            conn.commit()

    async def _add_feedback_dynamodb(self, message_id: str, rating: int, comment: Optional[str]):
        """Add feedback to DynamoDB"""
        # This requires finding the message first, then updating it
        # Implementation would depend on having message_id as a GSI or scanning
        # For now, we'll implement a basic version
        pass  # TODO: Implement DynamoDB feedback update

    async def get_user_usage_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for a user"""
        if self.storage_type == "postgres":
            return await self._get_user_usage_postgres(user_id, days)
        else:
            return await self._get_user_usage_dynamodb(user_id, days)

    async def _get_user_usage_postgres(self, user_id: str, days: int) -> Dict[str, Any]:
        """Get user usage stats from PostgreSQL"""
        with self._get_postgres_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN role = 'user' THEN 1 END) as user_messages,
                    COUNT(CASE WHEN feedback_rating IS NOT NULL THEN 1 END) as rated_messages,
                    AVG(feedback_rating) as avg_rating
                FROM messages 
                WHERE user_id = %s 
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            """, (user_id, days))
            
            result = cursor.fetchone()
            return {
                "total_messages": result[0],
                "user_messages": result[1],
                "rated_messages": result[2],
                "average_rating": float(result[3]) if result[3] else None
            }

    async def _get_user_usage_dynamodb(self, user_id: str, days: int) -> Dict[str, Any]:
        """Get user usage stats from DynamoDB"""
        # Implementation would use GSI on user_id
        # For now, return basic stats
        return {
            "total_messages": 0,
            "user_messages": 0,
            "rated_messages": 0,
            "average_rating": None
        }

class LocalChatService:
    """
    Local chat service using SQLite for development
    Compatible with ScalableChatService interface
    """
    
    def __init__(self):
        self.db_path = "./wops_ai_chat.db"
        self._create_tables()
        logger.info("Initialized LocalChatService with SQLite backend")

    def _get_db_connection(self):
        """Get SQLite database connection"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn

    def _create_tables(self):
        """Create SQLite tables if they don't exist"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Chat sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    feedback_rating INTEGER CHECK (feedback_rating >= 1 AND feedback_rating <= 5),
                    feedback_comment TEXT,
                    created_at TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_created 
                ON messages(session_id, created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_user_created 
                ON messages(user_id, created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_updated 
                ON chat_sessions(user_id, updated_at)
            """)
            
            conn.commit()
            logger.info("SQLite chat tables created successfully")

    async def save_message(self, session_id: str, user_id: str, role: str, 
                          content: str, metadata: Optional[Dict] = None) -> str:
        """Save a message to the chat history"""
        message_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (message_id, session_id, user_id, role, content, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (message_id, session_id, user_id, role, content, created_at, 
                 json.dumps(metadata) if metadata else None))
            conn.commit()
        return message_id

    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get chat history for a session"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT message_id, role, content, feedback_rating, feedback_comment, 
                       created_at, metadata
                FROM messages 
                WHERE session_id = ? 
                ORDER BY created_at ASC 
                LIMIT ?
            """, (session_id, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "message_id": row["message_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "feedback_rating": row["feedback_rating"],
                    "feedback_comment": row["feedback_comment"],
                    "created_at": row["created_at"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None
                })
            return results

    async def add_feedback(self, message_id: str, rating: int, comment: Optional[str] = None):
        """Add feedback to a message"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE messages 
                SET feedback_rating = ?, feedback_comment = ? 
                WHERE message_id = ?
            """, (rating, comment, message_id))
            conn.commit()

    async def get_user_usage_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for a user"""
        from datetime import timedelta
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_messages,
                    SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_messages,
                    SUM(CASE WHEN feedback_rating IS NOT NULL THEN 1 ELSE 0 END) as rated_messages,
                    AVG(feedback_rating) as avg_rating
                FROM messages 
                WHERE user_id = ? 
                AND created_at >= ?
            """, (user_id, cutoff_date))
            
            result = cursor.fetchone()
            return {
                "total_messages": result["total_messages"] or 0,
                "user_messages": result["user_messages"] or 0,
                "rated_messages": result["rated_messages"] or 0,
                "average_rating": float(result["avg_rating"]) if result["avg_rating"] else None
            }

    # Additional compatibility methods
    def create_dynamodb_tables(self):
        """No-op for local development"""
        pass

# Initialize the service based on environment
def get_chat_service():
    """Factory function to get the appropriate chat service"""
    # Import settings here to avoid circular imports
    from ..core.config import settings
    
    # Use local SQLite when in local mode, otherwise use configured storage
    if settings.is_local or settings.use_local_db:
        # For local development, we'll use SQLite (same as local user management)
        # We'll create a simple local chat service instead of trying to use PostgreSQL
        return LocalChatService()
    else:
        storage_type = os.getenv('CHAT_STORAGE_TYPE', 'postgres')
        return ScalableChatService(storage_type)

# Global instance
scalable_chat_service = get_chat_service()