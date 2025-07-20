"""
AWS-Ready User Management Service
Production-ready user management with email verification, authentication, and multi-storage support
"""

import logging
import jwt
import bcrypt
import boto3
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pydantic import BaseModel, EmailStr
import os
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from enum import Enum
from botocore.exceptions import ClientError
import psycopg2
import psycopg2.extras
from .email_verification_service import email_verification_service

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

class RegisterRequest(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.USER
    usage_plan: UsagePlan = UsagePlan.FREE

class SetPasswordRequest(BaseModel):
    email: EmailStr
    password: str
    verification_token: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr

class ConfirmPasswordResetRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class AWSUserManagementService:
    """
    Production-ready user management service for AWS deployment
    Supports both PostgreSQL (RDS) and DynamoDB storage backends
    """
    
    def __init__(self, storage_type: str = "auto"):
        # JWT Configuration
        self.jwt_secret = os.getenv('JWT_SECRET_KEY', 'your-super-secret-key-change-in-production')
        self.jwt_algorithm = 'HS256'
        self.access_token_expire_minutes = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
        self.refresh_token_expire_days = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '7'))
        
        # Storage configuration
        self.storage_type = self._determine_storage_type(storage_type)
        
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
        
        # Initialize storage backend
        if self.storage_type == "postgresql":
            self._init_postgresql()
        elif self.storage_type == "dynamodb":
            self._init_dynamodb()
        
        self._create_default_admin()
    
    def _determine_storage_type(self, storage_type: str) -> str:
        """Determine which storage backend to use"""
        if storage_type == "auto":
            # For AWS environments, always use DynamoDB
            # For local development, the local service will be used instead
            return "dynamodb"
        return storage_type.lower()
    
    def _init_postgresql(self):
        """Initialize PostgreSQL connection"""
        self.db_config = {
            'host': os.getenv('RDS_HOST', 'localhost'),
            'port': int(os.getenv('RDS_PORT', '5432')),
            'database': os.getenv('RDS_DATABASE', 'wops_ai'),
            'user': os.getenv('RDS_USER', 'postgres'),
            'password': os.getenv('RDS_PASSWORD', 'password')
        }
        
        try:
            # Test connection and create tables
            with self._get_db_connection() as conn:
                self._create_postgresql_tables(conn)
            logger.info("PostgreSQL backend initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            # Fallback to DynamoDB if PostgreSQL fails
            logger.info("Falling back to DynamoDB storage")
            self.storage_type = "dynamodb"
            self._init_dynamodb()
    
    def _init_dynamodb(self):
        """Initialize DynamoDB connection"""
        try:
            self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
            session = boto3.Session(region_name=self.aws_region)
            self.dynamodb = session.resource('dynamodb')
            
            # Table names
            self.users_table_name = os.getenv('USERS_TABLE', 'wops-users')
            self.usage_table_name = os.getenv('USAGE_TABLE', 'wops-user-usage')
            self.tokens_table_name = os.getenv('TOKENS_TABLE', 'wops-refresh-tokens')
            
            self._create_dynamodb_tables()
            logger.info("DynamoDB backend initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB: {e}")
            raise
    
    @contextmanager
    def _get_db_connection(self):
        """Context manager for PostgreSQL connections"""
        if self.storage_type != "postgresql":
            raise RuntimeError("Not using PostgreSQL backend")
        
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.set_session(autocommit=False)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _create_postgresql_tables(self, conn):
        """Create PostgreSQL tables"""
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255),
                role VARCHAR(50) DEFAULT 'user',
                usage_plan VARCHAR(50) DEFAULT 'free',
                status VARCHAR(50) DEFAULT 'pending_verification',
                is_email_verified BOOLEAN DEFAULT false,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP WITH TIME ZONE,
                last_login TIMESTAMP WITH TIME ZONE,
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
                usage_type VARCHAR(50) NOT NULL,
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_user_date ON user_usage(user_id, usage_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);")
        
        # Update trigger for updated_at
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        
        cursor.execute("""
            DROP TRIGGER IF EXISTS update_users_updated_at ON users;
            CREATE TRIGGER update_users_updated_at
                BEFORE UPDATE ON users
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at();
        """)
        
        conn.commit()
        logger.info("PostgreSQL tables created successfully")
    
    def _create_dynamodb_tables(self):
        """Create DynamoDB tables"""
        try:
            # Users table
            try:
                self.users_table = self.dynamodb.Table(self.users_table_name)
                self.users_table.load()
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    self.users_table = self.dynamodb.create_table(
                        TableName=self.users_table_name,
                        KeySchema=[
                            {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                        ],
                        AttributeDefinitions=[
                            {'AttributeName': 'user_id', 'AttributeType': 'S'},
                            {'AttributeName': 'email', 'AttributeType': 'S'}
                        ],
                        BillingMode='PAY_PER_REQUEST',
                        GlobalSecondaryIndexes=[
                            {
                                'IndexName': 'email-index',
                                'KeySchema': [
                                    {'AttributeName': 'email', 'KeyType': 'HASH'}
                                ],
                                'Projection': {'ProjectionType': 'ALL'}
                            }
                        ]
                    )
                    self.users_table.wait_until_exists()
            
            # Usage table
            try:
                self.usage_table = self.dynamodb.Table(self.usage_table_name)
                self.usage_table.load()
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    self.usage_table = self.dynamodb.create_table(
                        TableName=self.usage_table_name,
                        KeySchema=[
                            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                            {'AttributeName': 'usage_date_type', 'KeyType': 'RANGE'}
                        ],
                        AttributeDefinitions=[
                            {'AttributeName': 'user_id', 'AttributeType': 'S'},
                            {'AttributeName': 'usage_date_type', 'AttributeType': 'S'}
                        ],
                        BillingMode='PAY_PER_REQUEST'
                    )
                    self.usage_table.wait_until_exists()
            
            # Tokens table
            try:
                self.tokens_table = self.dynamodb.Table(self.tokens_table_name)
                self.tokens_table.load()
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    self.tokens_table = self.dynamodb.create_table(
                        TableName=self.tokens_table_name,
                        KeySchema=[
                            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                            {'AttributeName': 'token_id', 'KeyType': 'RANGE'}
                        ],
                        AttributeDefinitions=[
                            {'AttributeName': 'user_id', 'AttributeType': 'S'},
                            {'AttributeName': 'token_id', 'AttributeType': 'S'},
                            {'AttributeName': 'expires_at', 'AttributeType': 'N'}
                        ],
                        BillingMode='PAY_PER_REQUEST',
                        TimeToLiveSpecification={
                            'AttributeName': 'expires_at',
                            'Enabled': True
                        }
                    )
                    self.tokens_table.wait_until_exists()
            
            logger.info("DynamoDB tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create DynamoDB tables: {e}")
            raise
    
    def _create_default_admin(self):
        """Create default admin user if it doesn't exist"""
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@wops-ai.com')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        
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
    
    def _generate_tokens(self, user: UserAccount) -> TokenResponse:
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
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60,
            user={
                'user_id': user.user_id,
                'email': user.email,
                'role': user.role.value,
                'status': user.status.value,
                'is_email_verified': user.is_email_verified
            }
        )
    
    def _store_user(self, user: UserAccount, password_hash: Optional[str] = None):
        """Store user in the backend"""
        if self.storage_type == "postgresql":
            self._store_user_postgresql(user, password_hash)
        elif self.storage_type == "dynamodb":
            self._store_user_dynamodb(user, password_hash)
    
    def _store_user_postgresql(self, user: UserAccount, password_hash: Optional[str] = None):
        """Store user in PostgreSQL"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (
                    user_id, email, password_hash, role, usage_plan, status,
                    is_email_verified, created_at, updated_at, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user.user_id, user.email, password_hash, user.role.value,
                user.usage_plan.value, user.status.value, user.is_email_verified,
                user.created_at, user.updated_at, psycopg2.extras.Json(user.metadata or {})
            ))
            conn.commit()
    
    def _store_user_dynamodb(self, user: UserAccount, password_hash: Optional[str] = None):
        """Store user in DynamoDB"""
        item = {
            'user_id': user.user_id,
            'email': user.email,
            'role': user.role.value,
            'usage_plan': user.usage_plan.value,
            'status': user.status.value,
            'is_email_verified': user.is_email_verified,
            'failed_login_attempts': user.failed_login_attempts,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'locked_until': user.locked_until.isoformat() if user.locked_until else None,
            'metadata': user.metadata or {}
        }
        
        if password_hash:
            item['password_hash'] = password_hash
        
        self.users_table.put_item(Item=item)
    
    def _get_user_by_email(self, email: str) -> Optional[UserAccount]:
        """Get user by email"""
        if self.storage_type == "postgresql":
            return self._get_user_by_email_postgresql(email)
        elif self.storage_type == "dynamodb":
            return self._get_user_by_email_dynamodb(email)
    
    def _get_user_by_email_postgresql(self, email: str) -> Optional[UserAccount]:
        """Get user by email from PostgreSQL"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                cursor.execute("""
                    SELECT user_id, email, password_hash, role, usage_plan, status,
                           is_email_verified, failed_login_attempts, locked_until,
                           last_login, created_at, updated_at, metadata
                    FROM users WHERE email = %s
                """, (email,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return self._row_to_user_account(row)
        except Exception as e:
            logger.error(f"Error getting user by email from PostgreSQL: {e}")
            return None
    
    def _get_user_by_email_dynamodb(self, email: str) -> Optional[UserAccount]:
        """Get user by email from DynamoDB"""
        try:
            response = self.users_table.query(
                IndexName='email-index',
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={':email': email}
            )
            
            if not response['Items']:
                return None
            
            return self._item_to_user_account(response['Items'][0])
        except Exception as e:
            logger.error(f"Error getting user by email from DynamoDB: {e}")
            return None
    
    def _row_to_user_account(self, row) -> UserAccount:
        """Convert database row to UserAccount"""
        return UserAccount(
            user_id=str(row['user_id']),
            email=row['email'],
            role=UserRole(row['role']),
            usage_plan=UsagePlan(row['usage_plan']),
            status=UserStatus(row['status']),
            is_email_verified=row['is_email_verified'],
            failed_login_attempts=row['failed_login_attempts'],
            locked_until=row['locked_until'],
            last_login=row['last_login'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            usage_limits=self.usage_plans[UsagePlan(row['usage_plan'])],
            current_usage={},  # To be loaded separately
            metadata=row['metadata'] or {}
        )
    
    def _item_to_user_account(self, item) -> UserAccount:
        """Convert DynamoDB item to UserAccount"""
        return UserAccount(
            user_id=item['user_id'],
            email=item['email'],
            role=UserRole(item['role']),
            usage_plan=UsagePlan(item['usage_plan']),
            status=UserStatus(item['status']),
            is_email_verified=item.get('is_email_verified', False),
            failed_login_attempts=item.get('failed_login_attempts', 0),
            locked_until=datetime.fromisoformat(item['locked_until']) if item.get('locked_until') else None,
            last_login=datetime.fromisoformat(item['last_login']) if item.get('last_login') else None,
            created_at=datetime.fromisoformat(item['created_at']) if item.get('created_at') else None,
            updated_at=datetime.fromisoformat(item['updated_at']) if item.get('updated_at') else None,
            usage_limits=self.usage_plans[UsagePlan(item['usage_plan'])],
            current_usage={},  # To be loaded separately
            metadata=item.get('metadata', {})
        )
    
    def _store_refresh_token(self, user_id: str, refresh_token: str):
        """Store refresh token"""
        token_hash = bcrypt.hashpw(refresh_token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        token_id = str(uuid4())
        
        if self.storage_type == "postgresql":
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
                    VALUES (%s, %s, %s)
                """, (user_id, token_hash, expires_at))
                conn.commit()
        elif self.storage_type == "dynamodb":
            self.tokens_table.put_item(
                Item={
                    'user_id': user_id,
                    'token_id': token_id,
                    'token_hash': token_hash,
                    'expires_at': int(expires_at.timestamp()),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'is_revoked': False
                }
            )
    
    # Public API methods
    
    async def register_user(self, request: RegisterRequest) -> Dict[str, Any]:
        """Register a new user with email verification"""
        try:
            # Check if user already exists
            existing_user = self._get_user_by_email(request.email)
            if existing_user:
                if existing_user.status == UserStatus.PENDING_VERIFICATION:
                    # Resend verification email
                    await email_verification_service.send_verification_email(
                        request.email, existing_user.user_id
                    )
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
                email=request.email,
                role=request.role if request.role == UserRole.USER else UserRole.USER,  # Prevent admin creation
                usage_plan=request.usage_plan,
                status=UserStatus.PENDING_VERIFICATION,
                is_email_verified=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                usage_limits=self.usage_plans[request.usage_plan],
                current_usage={},
                metadata={}
            )
            
            self._store_user(user)
            
            # Send verification email
            email_sent = await email_verification_service.send_verification_email(
                request.email, user.user_id
            )
            
            if not email_sent:
                raise RuntimeError("Failed to send verification email")
            
            logger.info(f"New user registered (pending verification): {request.email}")
            return {
                "message": "Registration successful. Please check your email for verification instructions.",
                "user_id": user.user_id,
                "requires_verification": True
            }
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            raise
    
    async def set_password(self, request: SetPasswordRequest) -> TokenResponse:
        """Set password after email verification"""
        try:
            # Verify email token
            is_verified = await email_verification_service.verify_email_token(
                request.email, request.verification_token
            )
            
            if not is_verified:
                raise ValueError("Invalid or expired verification token")
            
            # Get user
            user = self._get_user_by_email(request.email)
            if not user:
                raise ValueError("User not found")
            
            # Hash password and update user
            password_hash = self._hash_password(request.password)
            
            # Update user status and verification
            if self.storage_type == "postgresql":
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE users 
                        SET password_hash = %s, status = %s, is_email_verified = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE email = %s
                    """, (password_hash, UserStatus.ACTIVE.value, True, request.email))
                    conn.commit()
            elif self.storage_type == "dynamodb":
                self.users_table.update_item(
                    Key={'user_id': user.user_id},
                    UpdateExpression='SET password_hash = :ph, #status = :status, is_email_verified = :verified, updated_at = :updated',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':ph': password_hash,
                        ':status': UserStatus.ACTIVE.value,
                        ':verified': True,
                        ':updated': datetime.now(timezone.utc).isoformat()
                    }
                )
            
            # Update user object
            user.status = UserStatus.ACTIVE
            user.is_email_verified = True
            
            logger.info(f"Password set successfully for user: {request.email}")
            return self._generate_tokens(user)
            
        except Exception as e:
            logger.error(f"Set password error: {e}")
            raise
    
    async def login_user(self, request: LoginRequest) -> TokenResponse:
        """Authenticate user and return tokens"""
        try:
            user = self._get_user_by_email(request.email)
            if not user:
                raise ValueError("Invalid credentials")
            
            # Check if user has a password set
            password_hash = self._get_user_password_hash(user.user_id)
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
            if not self._verify_password(request.password, password_hash):
                # Increment failed attempts
                self._increment_failed_attempts(user.user_id)
                raise ValueError("Invalid credentials")
            
            # Reset failed attempts and update last login
            self._reset_failed_attempts(user.user_id)
            
            logger.info(f"User logged in: {request.email}")
            return self._generate_tokens(user)
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise
    
    def _get_user_password_hash(self, user_id: str) -> Optional[str]:
        """Get user password hash"""
        if self.storage_type == "postgresql":
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT password_hash FROM users WHERE user_id = %s", (user_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        elif self.storage_type == "dynamodb":
            response = self.users_table.get_item(Key={'user_id': user_id})
            return response.get('Item', {}).get('password_hash')
    
    def _increment_failed_attempts(self, user_id: str):
        """Increment failed login attempts"""
        if self.storage_type == "postgresql":
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET failed_login_attempts = failed_login_attempts + 1,
                        locked_until = CASE 
                            WHEN failed_login_attempts + 1 >= 5 
                            THEN CURRENT_TIMESTAMP + INTERVAL '30 minutes'
                            ELSE locked_until 
                        END
                    WHERE user_id = %s
                """, (user_id,))
                conn.commit()
        elif self.storage_type == "dynamodb":
            # Get current attempts
            response = self.users_table.get_item(Key={'user_id': user_id})
            current_attempts = response.get('Item', {}).get('failed_login_attempts', 0)
            new_attempts = current_attempts + 1
            
            update_expr = 'SET failed_login_attempts = :attempts'
            expr_values = {':attempts': new_attempts}
            
            if new_attempts >= 5:
                locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
                update_expr += ', locked_until = :locked'
                expr_values[':locked'] = locked_until.isoformat()
            
            self.users_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values
            )
    
    def _reset_failed_attempts(self, user_id: str):
        """Reset failed login attempts"""
        if self.storage_type == "postgresql":
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET failed_login_attempts = 0, locked_until = NULL, last_login = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (user_id,))
                conn.commit()
        elif self.storage_type == "dynamodb":
            self.users_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET failed_login_attempts = :zero, last_login = :login REMOVE locked_until',
                ExpressionAttributeValues={
                    ':zero': 0,
                    ':login': datetime.now(timezone.utc).isoformat()
                }
            )
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
    
    def _get_user_by_id(self, user_id: str) -> Optional[UserAccount]:
        """Get user by ID"""
        if self.storage_type == "postgresql":
            return self._get_user_by_id_postgresql(user_id)
        elif self.storage_type == "dynamodb":
            return self._get_user_by_id_dynamodb(user_id)
    
    def _get_user_by_id_postgresql(self, user_id: str) -> Optional[UserAccount]:
        """Get user by ID from PostgreSQL"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                cursor.execute("""
                    SELECT user_id, email, password_hash, role, usage_plan, status,
                           is_email_verified, failed_login_attempts, locked_until,
                           last_login, created_at, updated_at, metadata
                    FROM users WHERE user_id = %s
                """, (user_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return self._row_to_user_account(row)
        except Exception as e:
            logger.error(f"Error getting user by ID from PostgreSQL: {e}")
            return None
    
    def _get_user_by_id_dynamodb(self, user_id: str) -> Optional[UserAccount]:
        """Get user by ID from DynamoDB"""
        try:
            response = self.users_table.get_item(Key={'user_id': user_id})
            
            if 'Item' not in response:
                return None
            
            return self._item_to_user_account(response['Item'])
        except Exception as e:
            logger.error(f"Error getting user by ID from DynamoDB: {e}")
            return None
    
    async def check_usage_limits(self, user_id: str, usage_type: str = 'message') -> bool:
        """Check if user can perform action based on usage limits"""
        user = self._get_user_by_id(user_id)
        if not user:
            return False
        
        # Load current usage
        current_usage = await self._get_current_usage(user_id)
        user.current_usage = current_usage
        
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
        if self.storage_type == "postgresql":
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_usage (user_id, usage_type, usage_count)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, usage_type, usage_date)
                    DO UPDATE SET usage_count = user_usage.usage_count + %s
                """, (user_id, usage_type, count, count))
                conn.commit()
        elif self.storage_type == "dynamodb":
            today = datetime.now(timezone.utc).date().isoformat()
            usage_date_type = f"{today}#{usage_type}"
            
            try:
                self.usage_table.update_item(
                    Key={
                        'user_id': user_id,
                        'usage_date_type': usage_date_type
                    },
                    UpdateExpression='ADD usage_count :count',
                    ExpressionAttributeValues={':count': count}
                )
            except ClientError as e:
                if e.response['Error']['Code'] == 'ValidationException':
                    # Item doesn't exist, create it
                    self.usage_table.put_item(
                        Item={
                            'user_id': user_id,
                            'usage_date_type': usage_date_type,
                            'usage_type': usage_type,
                            'usage_date': today,
                            'usage_count': count,
                            'created_at': datetime.now(timezone.utc).isoformat()
                        }
                    )
                else:
                    raise
    
    async def _get_current_usage(self, user_id: str) -> Dict[str, int]:
        """Get current usage statistics for a user"""
        if self.storage_type == "postgresql":
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
        elif self.storage_type == "dynamodb":
            try:
                current_date = datetime.now(timezone.utc).date()
                month_start = current_date.replace(day=1).isoformat()
                today = current_date.isoformat()
                
                # Get usage for this month
                monthly_response = self.usage_table.query(
                    KeyConditionExpression='user_id = :user_id AND begins_with(usage_date_type, :month)',
                    ExpressionAttributeValues={
                        ':user_id': user_id,
                        ':month': month_start
                    }
                )
                
                monthly_messages = sum(item.get('usage_count', 0) 
                                     for item in monthly_response['Items'] 
                                     if item.get('usage_type') == 'message')
                
                # Get usage for today
                daily_response = self.usage_table.query(
                    KeyConditionExpression='user_id = :user_id AND begins_with(usage_date_type, :today)',
                    ExpressionAttributeValues={
                        ':user_id': user_id,
                        ':today': today
                    }
                )
                
                daily_messages = sum(item.get('usage_count', 0) 
                                   for item in daily_response['Items'] 
                                   if item.get('usage_type') == 'message')
                
                return {
                    'monthly_messages': monthly_messages,
                    'daily_messages': daily_messages
                }
            except Exception as e:
                logger.error(f"Error getting current usage from DynamoDB: {e}")
                return {'monthly_messages': 0, 'daily_messages': 0}
    
    async def can_access_model(self, user_id: str, model_name: str) -> bool:
        """Check if user can access a specific model"""
        user = self._get_user_by_id(user_id)
        if not user:
            return False
        
        return model_name in user.usage_limits.model_access
    
    async def get_all_users(self, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Get paginated list of all users (admin only)"""
        if self.storage_type == "postgresql":
            return await self._get_all_users_postgresql(page, limit)
        elif self.storage_type == "dynamodb":
            return await self._get_all_users_dynamodb(page, limit)
    
    async def _get_all_users_postgresql(self, page: int, limit: int) -> Dict[str, Any]:
        """Get all users from PostgreSQL"""
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
                LIMIT %s OFFSET %s
            """, (limit, offset))
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    'user_id': str(row[0]),
                    'email': row[1],
                    'role': row[2],
                    'usage_plan': row[3],
                    'status': row[4],
                    'is_email_verified': row[5],
                    'created_at': row[6].isoformat() if row[6] else None,
                    'last_login': row[7].isoformat() if row[7] else None
                })
            
            return {
                'users': users,
                'total_count': total_count,
                'page': page,
                'limit': limit,
                'total_pages': (total_count + limit - 1) // limit
            }
    
    async def _get_all_users_dynamodb(self, page: int, limit: int) -> Dict[str, Any]:
        """Get all users from DynamoDB"""
        try:
            # DynamoDB scan (not ideal for large datasets, but works for moderate user counts)
            response = self.users_table.scan()
            
            all_users = []
            for item in response['Items']:
                all_users.append({
                    'user_id': item['user_id'],
                    'email': item['email'],
                    'role': item['role'],
                    'usage_plan': item['usage_plan'],
                    'status': item['status'],
                    'is_email_verified': item.get('is_email_verified', False),
                    'created_at': item.get('created_at'),
                    'last_login': item.get('last_login')
                })
            
            # Sort by created_at (newest first)
            all_users.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Paginate
            total_count = len(all_users)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_users = all_users[start_idx:end_idx]
            
            return {
                'users': paginated_users,
                'total_count': total_count,
                'page': page,
                'limit': limit,
                'total_pages': (total_count + limit - 1) // limit
            }
        except Exception as e:
            logger.error(f"Error getting all users from DynamoDB: {e}")
            return {
                'users': [],
                'total_count': 0,
                'page': page,
                'limit': limit,
                'total_pages': 0
            }

# Global instance with auto-detection of storage backend
aws_user_management_service = AWSUserManagementService()