"""
Comprehensive User Management Service
Handles authentication, authorization, roles, and usage limits
"""

import logging
import jwt
import bcrypt
import redis
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pydantic import BaseModel, EmailStr
import os
from contextlib import contextmanager
import psycopg2
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"

class UsagePlan(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

@dataclass
class UsageLimits:
    monthly_messages: int
    daily_messages: int
    concurrent_sessions: int
    model_access: List[str]
    advanced_features: bool = False

class UserAccount(BaseModel):
    user_id: str
    email: EmailStr
    role: UserRole
    usage_plan: UsagePlan
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None
    usage_limits: UsageLimits
    current_usage: Dict[str, int] = {}

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.USER
    usage_plan: UsagePlan = UsagePlan.FREE

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class UserManagementService:
    """
    Comprehensive user management with authentication, authorization, and usage tracking
    """
    
    def __init__(self):
        self.jwt_secret = os.getenv('JWT_SECRET_KEY', 'your-super-secret-key-change-in-production')
        self.jwt_algorithm = 'HS256'
        self.access_token_expire_minutes = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
        self.refresh_token_expire_days = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '7'))
        
        # Database configuration
        self.db_config = {
            'host': os.getenv('RDS_HOST', 'localhost'),
            'port': os.getenv('RDS_PORT', '5432'),
            'database': os.getenv('RDS_DATABASE', 'wops_ai'),
            'user': os.getenv('RDS_USER', 'postgres'),
            'password': os.getenv('RDS_PASSWORD', 'password')
        }
        
        # Redis for rate limiting and session management
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            password=os.getenv('REDIS_PASSWORD'),
            decode_responses=True
        )
        
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
                model_access=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
                advanced_features=True
            )
        }
        
        self._create_tables()
        self._create_default_admin()

    @contextmanager
    def _get_db_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _create_tables(self):
        """Create user management tables"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Users table with comprehensive fields
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) DEFAULT 'user',
                    usage_plan VARCHAR(50) DEFAULT 'free',
                    is_active BOOLEAN DEFAULT true,
                    is_verified BOOLEAN DEFAULT false,
                    last_login TIMESTAMP WITH TIME ZONE,
                    failed_login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB DEFAULT '{}'::jsonb
                );
            """)
            
            # Usage tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_usage (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    usage_type VARCHAR(50) NOT NULL, -- 'message', 'session', etc.
                    usage_date DATE DEFAULT CURRENT_DATE,
                    usage_count INTEGER DEFAULT 1,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, usage_type, usage_date)
                );
            """)
            
            # Refresh tokens table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    token_hash VARCHAR(255) NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    is_revoked BOOLEAN DEFAULT false
                );
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_user_date ON user_usage(user_id, usage_date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);")
            
            conn.commit()
            logger.info("User management tables created successfully")

    def _create_default_admin(self):
        """Create default admin user if it doesn't exist"""
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@wops-ai.com')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users WHERE email = %s", (admin_email,))
                
                if not cursor.fetchone():
                    password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
                    cursor.execute("""
                        INSERT INTO users (email, password_hash, role, usage_plan, is_active, is_verified)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (admin_email, password_hash.decode('utf-8'), UserRole.ADMIN, 
                         UsagePlan.ENTERPRISE, True, True))
                    conn.commit()
                    logger.info(f"Default admin user created: {admin_email}")
        except Exception as e:
            logger.error(f"Error creating default admin: {e}")

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

    def _generate_tokens(self, user_id: str, email: str, role: str) -> TokenResponse:
        """Generate access and refresh tokens"""
        now = datetime.now(timezone.utc)
        
        # Access token payload
        access_payload = {
            'user_id': user_id,
            'email': email,
            'role': role,
            'exp': now + timedelta(minutes=self.access_token_expire_minutes),
            'iat': now,
            'type': 'access'
        }
        
        # Refresh token payload
        refresh_payload = {
            'user_id': user_id,
            'exp': now + timedelta(days=self.refresh_token_expire_days),
            'iat': now,
            'type': 'refresh'
        }
        
        access_token = jwt.encode(access_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        refresh_token = jwt.encode(refresh_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Store refresh token in database
        self._store_refresh_token(user_id, refresh_token)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60,
            user={
                'user_id': user_id,
                'email': email,
                'role': role
            }
        )

    def _store_refresh_token(self, user_id: str, refresh_token: str):
        """Store refresh token in database"""
        token_hash = bcrypt.hashpw(refresh_token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
                VALUES (%s, %s, %s)
            """, (user_id, token_hash, expires_at))
            conn.commit()

    async def register_user(self, request: RegisterRequest) -> TokenResponse:
        """Register a new user"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (request.email,))
            if cursor.fetchone():
                raise ValueError("User already exists")
            
            # Create new user
            password_hash = self._hash_password(request.password)
            cursor.execute("""
                INSERT INTO users (email, password_hash, role, usage_plan)
                VALUES (%s, %s, %s, %s)
                RETURNING user_id
            """, (request.email, password_hash, request.role, request.usage_plan))
            
            user_id = str(cursor.fetchone()[0])
            conn.commit()
            
            logger.info(f"New user registered: {request.email}")
            return self._generate_tokens(user_id, request.email, request.role)

    async def login_user(self, request: LoginRequest) -> TokenResponse:
        """Authenticate user and return tokens"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get user data
            cursor.execute("""
                SELECT user_id, password_hash, role, is_active, failed_login_attempts, locked_until
                FROM users WHERE email = %s
            """, (request.email,))
            
            user_data = cursor.fetchone()
            if not user_data:
                raise ValueError("Invalid credentials")
            
            user_id, password_hash, role, is_active, failed_attempts, locked_until = user_data
            
            # Check if account is locked
            if locked_until and datetime.now(timezone.utc) < locked_until.replace(tzinfo=timezone.utc):
                raise ValueError("Account is temporarily locked")
            
            # Check if account is active
            if not is_active:
                raise ValueError("Account is deactivated")
            
            # Verify password
            if not self._verify_password(request.password, password_hash):
                # Increment failed attempts
                failed_attempts += 1
                lock_until = None
                
                if failed_attempts >= 5:
                    lock_until = datetime.now(timezone.utc) + timedelta(minutes=30)
                
                cursor.execute("""
                    UPDATE users 
                    SET failed_login_attempts = %s, locked_until = %s 
                    WHERE email = %s
                """, (failed_attempts, lock_until, request.email))
                conn.commit()
                
                raise ValueError("Invalid credentials")
            
            # Reset failed attempts and update last login
            cursor.execute("""
                UPDATE users 
                SET failed_login_attempts = 0, locked_until = NULL, last_login = CURRENT_TIMESTAMP 
                WHERE email = %s
            """, (request.email,))
            conn.commit()
            
            logger.info(f"User logged in: {request.email}")
            return self._generate_tokens(str(user_id), request.email, role)

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")

    async def get_user_by_id(self, user_id: str) -> Optional[UserAccount]:
        """Get user by ID"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, email, role, usage_plan, is_active, created_at, last_login
                FROM users WHERE user_id = %s
            """, (user_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                return None
            
            # Get usage limits for the user's plan
            usage_limits = self.usage_plans[UsagePlan(user_data[3])]
            
            # Get current usage
            current_usage = await self._get_current_usage(user_id)
            
            return UserAccount(
                user_id=str(user_data[0]),
                email=user_data[1],
                role=UserRole(user_data[2]),
                usage_plan=UsagePlan(user_data[3]),
                is_active=user_data[4],
                created_at=user_data[5],
                last_login=user_data[6],
                usage_limits=usage_limits,
                current_usage=current_usage
            )

    async def _get_current_usage(self, user_id: str) -> Dict[str, int]:
        """Get current usage statistics for a user"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get monthly usage
            cursor.execute("""
                SELECT SUM(usage_count) 
                FROM user_usage 
                WHERE user_id = %s 
                AND usage_type = 'message' 
                AND usage_date >= date_trunc('month', CURRENT_DATE)
            """, (user_id,))
            monthly_messages = cursor.fetchone()[0] or 0
            
            # Get daily usage
            cursor.execute("""
                SELECT SUM(usage_count) 
                FROM user_usage 
                WHERE user_id = %s 
                AND usage_type = 'message' 
                AND usage_date = CURRENT_DATE
            """, (user_id,))
            daily_messages = cursor.fetchone()[0] or 0
            
            return {
                'monthly_messages': monthly_messages,
                'daily_messages': daily_messages
            }

    async def check_usage_limits(self, user_id: str, usage_type: str = 'message') -> bool:
        """Check if user can perform action based on usage limits"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        if usage_type == 'message':
            # Check daily limit
            if (user.usage_limits.daily_messages > 0 and 
                user.current_usage.get('daily_messages', 0) >= user.usage_limits.daily_messages):
                return False
            
            # Check monthly limit (if not unlimited)
            if (user.usage_limits.monthly_messages > 0 and 
                user.current_usage.get('monthly_messages', 0) >= user.usage_limits.monthly_messages):
                return False
        
        return True

    async def increment_usage(self, user_id: str, usage_type: str = 'message', count: int = 1):
        """Increment usage counter for a user"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_usage (user_id, usage_type, usage_count)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, usage_type, usage_date)
                DO UPDATE SET usage_count = user_usage.usage_count + %s
            """, (user_id, usage_type, count, count))
            conn.commit()

    async def can_access_model(self, user_id: str, model_name: str) -> bool:
        """Check if user can access a specific model"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        return model_name in user.usage_limits.model_access

    def require_role(self, required_roles: List[UserRole]):
        """Decorator to require specific roles"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # This would be used as a dependency in FastAPI
                # Implementation depends on how you handle request context
                pass
            return wrapper
        return decorator

    async def get_all_users(self, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Get paginated list of all users (admin only)"""
        offset = (page - 1) * limit
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM users")
            total_count = cursor.fetchone()[0]
            
            # Get users
            cursor.execute("""
                SELECT user_id, email, role, usage_plan, is_active, created_at, last_login
                FROM users 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """, (limit, offset))
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    'user_id': str(row[0]),
                    'email': row[1],
                    'role': row[2],
                    'usage_plan': row[3],
                    'is_active': row[4],
                    'created_at': row[5].isoformat() if row[5] else None,
                    'last_login': row[6].isoformat() if row[6] else None
                })
            
            return {
                'users': users,
                'total_count': total_count,
                'page': page,
                'limit': limit,
                'total_pages': (total_count + limit - 1) // limit
            }

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user information (admin only)"""
        allowed_fields = ['role', 'usage_plan', 'is_active']
        update_fields = []
        update_values = []
        
        for field, value in updates.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = %s")
                update_values.append(value)
        
        if not update_fields:
            return False
        
        update_values.append(user_id)
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE users 
                SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, update_values)
            conn.commit()
            
            return cursor.rowcount > 0

# Global instance
user_management_service = UserManagementService()