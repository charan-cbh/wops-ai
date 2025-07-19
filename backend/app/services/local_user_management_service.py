"""
Local User Management Service
Uses SQLite for local development with email verification support
"""

import logging
import jwt
import bcrypt
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import os
from dataclasses import dataclass
from enum import Enum
from app.core.config import settings
from app.services.local_email_service import local_email_service

logger = logging.getLogger(__name__)

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"

class UsagePlan(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class UserStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LOCKED = "locked"

@dataclass
class UsageLimits:
    monthly_messages: int
    daily_messages: int
    concurrent_sessions: int
    model_access: List[str]
    advanced_features: bool = False

@dataclass
class UserAccount:
    user_id: str
    email: str
    role: UserRole
    usage_plan: UsagePlan
    status: UserStatus
    is_email_verified: bool = False
    created_at: datetime = None
    updated_at: datetime = None
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    usage_limits: UsageLimits = None
    current_usage: Dict[str, int] = None
    metadata: Dict[str, Any] = None

class LocalUserManagementService:
    """
    Local user management service using SQLite for development
    """
    
    def __init__(self):
        self.jwt_secret = settings.jwt_secret_key
        self.jwt_algorithm = 'HS256'
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.refresh_token_expire_days = settings.refresh_token_expire_days
        
        # SQLite database path
        self.db_path = "./wops_ai_local.db"
        
        # Usage plan definitions
        self.usage_plans = {
            UsagePlan.FREE: UsageLimits(
                monthly_messages=100,
                daily_messages=10,
                concurrent_sessions=1,
                model_access=["gpt-3.5-turbo"],
                advanced_features=False
            ),
            UsagePlan.PREMIUM: UsageLimits(
                monthly_messages=1000,
                daily_messages=100,
                concurrent_sessions=3,
                model_access=["gpt-3.5-turbo", "gpt-4"],
                advanced_features=True
            ),
            UsagePlan.ENTERPRISE: UsageLimits(
                monthly_messages=-1,  # Unlimited
                daily_messages=1000,
                concurrent_sessions=10,
                model_access=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "claude-3", "gemini-pro"],
                advanced_features=True
            )
        }
        
        self._create_tables()
        self._create_default_admin()
    
    def _get_db_connection(self):
        """Get SQLite database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def _create_tables(self):
        """Create SQLite tables for user management"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT,
                        role TEXT DEFAULT 'user',
                        usage_plan TEXT DEFAULT 'free',
                        status TEXT DEFAULT 'pending_verification',
                        is_email_verified BOOLEAN DEFAULT FALSE,
                        failed_login_attempts INTEGER DEFAULT 0,
                        locked_until TIMESTAMP,
                        last_login TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT DEFAULT '{}'
                    )
                """)
                
                # Usage tracking table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        usage_type TEXT NOT NULL,
                        usage_date DATE DEFAULT CURRENT_DATE,
                        usage_count INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, usage_type, usage_date),
                        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                    )
                """)
                
                # Refresh tokens table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS refresh_tokens (
                        token_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        token_hash TEXT NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_revoked BOOLEAN DEFAULT FALSE,
                        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_user_date ON user_usage(user_id, usage_date)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id)")
                
                conn.commit()
                logger.info("Local SQLite tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create SQLite tables: {e}")
            raise
    
    def _create_default_admin(self):
        """Create default admin user if it doesn't exist"""
        admin_email = "admin@wops-ai.com"
        admin_password = "admin123"
        
        try:
            # Check if admin exists
            existing_admin = self._get_user_by_email(admin_email)
            if existing_admin:
                logger.info("Default admin user already exists")
                return
            
            # Create admin user
            password_hash = self._hash_password(admin_password)
            admin_user = UserAccount(
                user_id=str(uuid4()),
                email=admin_email,
                role=UserRole.ADMIN,
                usage_plan=UsagePlan.ENTERPRISE,
                status=UserStatus.ACTIVE,
                is_email_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                usage_limits=self.usage_plans[UsagePlan.ENTERPRISE],
                current_usage={},
                metadata={}
            )
            
            self._store_user(admin_user, password_hash)
            logger.info(f"Default admin user created: {admin_email}")
            
        except Exception as e:
            logger.error(f"Error creating default admin: {e}")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def _store_user(self, user: UserAccount, password_hash: Optional[str] = None):
        """Store user in SQLite database"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (
                        user_id, email, password_hash, role, usage_plan, status,
                        is_email_verified, created_at, updated_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user.user_id, user.email, password_hash, user.role.value,
                    user.usage_plan.value, user.status.value, user.is_email_verified,
                    user.created_at.isoformat() if user.created_at else None,
                    user.updated_at.isoformat() if user.updated_at else None,
                    '{}' if not user.metadata else str(user.metadata)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing user {user.email}: {e}")
            raise
    
    def _get_user_by_email(self, email: str) -> Optional[UserAccount]:
        """Get user by email from SQLite"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, email, password_hash, role, usage_plan, status,
                           is_email_verified, failed_login_attempts, locked_until,
                           last_login, created_at, updated_at, metadata
                    FROM users WHERE email = ?
                """, (email,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return self._row_to_user_account(row)
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None
    
    def _get_user_by_id(self, user_id: str) -> Optional[UserAccount]:
        """Get user by ID from SQLite"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, email, password_hash, role, usage_plan, status,
                           is_email_verified, failed_login_attempts, locked_until,
                           last_login, created_at, updated_at, metadata
                    FROM users WHERE user_id = ?
                """, (user_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return self._row_to_user_account(row)
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    def _row_to_user_account(self, row) -> UserAccount:
        """Convert database row to UserAccount"""
        created_at = datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        updated_at = datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        last_login = datetime.fromisoformat(row['last_login']) if row['last_login'] else None
        locked_until = datetime.fromisoformat(row['locked_until']) if row['locked_until'] else None
        
        return UserAccount(
            user_id=row['user_id'],
            email=row['email'],
            role=UserRole(row['role']),
            usage_plan=UsagePlan(row['usage_plan']),
            status=UserStatus(row['status']),
            is_email_verified=bool(row['is_email_verified']),
            failed_login_attempts=row['failed_login_attempts'],
            locked_until=locked_until,
            last_login=last_login,
            created_at=created_at,
            updated_at=updated_at,
            usage_limits=self.usage_plans[UsagePlan(row['usage_plan'])],
            current_usage={},  # To be loaded separately
            metadata={}
        )
    
    def _generate_tokens(self, user: UserAccount) -> Dict[str, Any]:
        """Generate access and refresh tokens"""
        now = datetime.now(timezone.utc)
        
        # Access token payload
        access_payload = {
            'user_id': user.user_id,
            'email': user.email,
            'role': user.role.value,
            'exp': now + timedelta(minutes=self.access_token_expire_minutes),
            'iat': now,
            'type': 'access'
        }
        
        # Refresh token payload
        refresh_payload = {
            'user_id': user.user_id,
            'exp': now + timedelta(days=self.refresh_token_expire_days),
            'iat': now,
            'type': 'refresh'
        }
        
        access_token = jwt.encode(access_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        refresh_token = jwt.encode(refresh_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Store refresh token
        self._store_refresh_token(user.user_id, refresh_token)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer',
            'expires_in': self.access_token_expire_minutes * 60,
            'user': {
                'user_id': user.user_id,
                'email': user.email,
                'role': user.role.value,
                'status': user.status.value,
                'is_email_verified': user.is_email_verified
            }
        }
    
    def _store_refresh_token(self, user_id: str, refresh_token: str):
        """Store refresh token in SQLite"""
        try:
            token_hash = bcrypt.hashpw(refresh_token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            expires_at = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
            token_id = str(uuid4())
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO refresh_tokens (token_id, user_id, token_hash, expires_at)
                    VALUES (?, ?, ?, ?)
                """, (token_id, user_id, token_hash, expires_at.isoformat()))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing refresh token: {e}")
    
    # Public API methods
    
    async def register_user(self, email: str, role: UserRole = UserRole.USER, usage_plan: UsagePlan = UsagePlan.FREE) -> Dict[str, Any]:
        """Register a new user with email verification"""
        try:
            # Validate email domain
            if not settings.is_allowed_email_domain(email):
                raise ValueError(f"Email domain not allowed. Allowed domains: {', '.join(settings.allowed_domains_list)}")
            
            # Check if user already exists
            existing_user = self._get_user_by_email(email)
            if existing_user:
                if existing_user.status == UserStatus.PENDING_VERIFICATION:
                    # Resend verification email
                    await local_email_service.send_verification_email(email, existing_user.user_id)
                    return {
                        "message": "Verification email sent. Please check your email.",
                        "user_id": existing_user.user_id,
                        "requires_verification": True
                    }
                else:
                    raise ValueError("User already exists")
            
            # Create new user without password
            user = UserAccount(
                user_id=str(uuid4()),
                email=email,
                role=role if role == UserRole.USER else UserRole.USER,  # Prevent admin creation
                usage_plan=usage_plan,
                status=UserStatus.PENDING_VERIFICATION,
                is_email_verified=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                usage_limits=self.usage_plans[usage_plan],
                current_usage={},
                metadata={}
            )
            
            self._store_user(user)
            
            # Send verification email
            email_sent = await local_email_service.send_verification_email(email, user.user_id)
            
            if not email_sent:
                raise RuntimeError("Failed to send verification email")
            
            logger.info(f"New user registered (pending verification): {email}")
            return {
                "message": "Registration successful. Please check your email for verification instructions.",
                "user_id": user.user_id,
                "requires_verification": True
            }
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            raise
    
    async def set_password(self, email: str, password: str, verification_token: str) -> Dict[str, Any]:
        """Set password after email verification"""
        try:
            # Verify email token
            is_verified = await local_email_service.verify_email_token(email, verification_token)
            
            if not is_verified:
                raise ValueError("Invalid or expired verification token")
            
            # Get user
            user = self._get_user_by_email(email)
            if not user:
                raise ValueError("User not found")
            
            # Hash password and update user
            password_hash = self._hash_password(password)
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET password_hash = ?, status = ?, is_email_verified = ?, updated_at = ?
                    WHERE email = ?
                """, (password_hash, UserStatus.ACTIVE.value, True, datetime.now(timezone.utc).isoformat(), email))
                conn.commit()
            
            # Update user object
            user.status = UserStatus.ACTIVE
            user.is_email_verified = True
            
            logger.info(f"Password set successfully for user: {email}")
            return self._generate_tokens(user)
            
        except Exception as e:
            logger.error(f"Set password error: {e}")
            raise
    
    async def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return tokens"""
        try:
            user = self._get_user_by_email(email)
            if not user:
                raise ValueError("Invalid credentials")
            
            # Get password hash
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT password_hash FROM users WHERE email = ?", (email,))
                result = cursor.fetchone()
                password_hash = result['password_hash'] if result else None
            
            if not password_hash:
                raise ValueError("Please complete account setup by setting your password")
            
            # Check account status
            if user.status == UserStatus.PENDING_VERIFICATION:
                raise ValueError("Please verify your email address first")
            elif user.status == UserStatus.SUSPENDED:
                raise ValueError("Account is suspended")
            elif user.status == UserStatus.LOCKED:
                if user.locked_until and datetime.now(timezone.utc) < user.locked_until:
                    raise ValueError("Account is temporarily locked")
            
            # Verify password
            if not self._verify_password(password, password_hash):
                # Increment failed attempts
                self._increment_failed_attempts(user.user_id)
                raise ValueError("Invalid credentials")
            
            # Reset failed attempts and update last login
            self._reset_failed_attempts(user.user_id)
            
            logger.info(f"User logged in: {email}")
            return self._generate_tokens(user)
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise
    
    def _increment_failed_attempts(self, user_id: str):
        """Increment failed login attempts"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get current attempts
                cursor.execute("SELECT failed_login_attempts FROM users WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()
                current_attempts = result['failed_login_attempts'] if result else 0
                new_attempts = current_attempts + 1
                
                # Update attempts and potentially lock account
                if new_attempts >= 5:
                    locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
                    cursor.execute("""
                        UPDATE users 
                        SET failed_login_attempts = ?, locked_until = ?
                        WHERE user_id = ?
                    """, (new_attempts, locked_until.isoformat(), user_id))
                else:
                    cursor.execute("""
                        UPDATE users 
                        SET failed_login_attempts = ?
                        WHERE user_id = ?
                    """, (new_attempts, user_id))
                
                conn.commit()
        except Exception as e:
            logger.error(f"Error incrementing failed attempts: {e}")
    
    def _reset_failed_attempts(self, user_id: str):
        """Reset failed login attempts"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET failed_login_attempts = 0, locked_until = NULL, last_login = ?
                    WHERE user_id = ?
                """, (datetime.now(timezone.utc).isoformat(), user_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Error resetting failed attempts: {e}")
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
    
    async def check_usage_limits(self, user_id: str, usage_type: str = 'message') -> bool:
        """Check if user can perform action based on usage limits"""
        user = self._get_user_by_id(user_id)
        if not user:
            return False
        
        # Load current usage
        current_usage = await self._get_current_usage(user_id)
        
        if usage_type == 'message':
            # Check daily limit
            if (user.usage_limits.daily_messages > 0 and 
                current_usage.get('daily_messages', 0) >= user.usage_limits.daily_messages):
                return False
            
            # Check monthly limit (if not unlimited)
            if (user.usage_limits.monthly_messages > 0 and 
                current_usage.get('monthly_messages', 0) >= user.usage_limits.monthly_messages):
                return False
        
        return True
    
    async def increment_usage(self, user_id: str, usage_type: str = 'message', count: int = 1):
        """Increment usage counter for a user"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_usage (user_id, usage_type, usage_count)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id, usage_type, usage_date)
                    DO UPDATE SET usage_count = usage_count + ?
                """, (user_id, usage_type, count, count))
                conn.commit()
        except Exception as e:
            logger.error(f"Error incrementing usage: {e}")
    
    async def _get_current_usage(self, user_id: str) -> Dict[str, int]:
        """Get current usage statistics for a user"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get monthly usage
                cursor.execute("""
                    SELECT SUM(usage_count) 
                    FROM user_usage 
                    WHERE user_id = ? 
                    AND usage_type = 'message' 
                    AND usage_date >= date('now', 'start of month')
                """, (user_id,))
                monthly_result = cursor.fetchone()
                monthly_messages = monthly_result[0] if monthly_result and monthly_result[0] else 0
                
                # Get daily usage
                cursor.execute("""
                    SELECT SUM(usage_count) 
                    FROM user_usage 
                    WHERE user_id = ? 
                    AND usage_type = 'message' 
                    AND usage_date = date('now')
                """, (user_id,))
                daily_result = cursor.fetchone()
                daily_messages = daily_result[0] if daily_result and daily_result[0] else 0
                
                return {
                    'monthly_messages': monthly_messages,
                    'daily_messages': daily_messages
                }
        except Exception as e:
            logger.error(f"Error getting current usage: {e}")
            return {'monthly_messages': 0, 'daily_messages': 0}
    
    async def can_access_model(self, user_id: str, model_name: str) -> bool:
        """Check if user can access a specific model"""
        user = self._get_user_by_id(user_id)
        if not user:
            return False
        
        return model_name in user.usage_limits.model_access
    
    async def get_all_users(self, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Get paginated list of all users (admin only)"""
        try:
            offset = (page - 1) * limit
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute("SELECT COUNT(*) FROM users")
                total_count = cursor.fetchone()[0]
                
                # Get users
                cursor.execute("""
                    SELECT user_id, email, role, usage_plan, status, is_email_verified, created_at, last_login
                    FROM users 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
                users = []
                for row in cursor.fetchall():
                    users.append({
                        'user_id': row['user_id'],
                        'email': row['email'],
                        'role': row['role'],
                        'usage_plan': row['usage_plan'],
                        'status': row['status'],
                        'is_email_verified': bool(row['is_email_verified']),
                        'created_at': row['created_at'],
                        'last_login': row['last_login']
                    })
                
                return {
                    'users': users,
                    'total_count': total_count,
                    'page': page,
                    'limit': limit,
                    'total_pages': (total_count + limit - 1) // limit
                }
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return {
                'users': [],
                'total_count': 0,
                'page': page,
                'limit': limit,
                'total_pages': 0
            }

# Global instance
local_user_management_service = LocalUserManagementService()