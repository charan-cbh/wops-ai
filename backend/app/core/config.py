from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import os
import logging
from enum import Enum

# Force load .env to override system variables
load_dotenv(override=True)

logger = logging.getLogger(__name__)

class Environment(str, Enum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class Settings(BaseSettings):
    # Environment settings
    environment: Environment = Environment.LOCAL
    debug: bool = False
    
    # App settings
    app_name: str = "Worker Operations BI Chatbot"
    version: str = "1.0.0"
    
    # Environment flags (automatically set based on environment)
    use_local_db: bool = True
    use_local_email: bool = True
    use_local_storage: bool = True
    
    # AI Provider settings
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    default_ai_provider: str = "openai"
    
    # Snowflake settings
    snowflake_account: Optional[str] = None
    snowflake_user: Optional[str] = None
    snowflake_private_key_path: Optional[str] = None
    snowflake_private_key_passphrase: Optional[str] = None
    snowflake_warehouse: Optional[str] = None
    snowflake_database: Optional[str] = None
    snowflake_schema: str = "PUBLIC"
    
    # Database settings
    database_url: str = "sqlite:///./wops_ai_local.db"
    
    # PostgreSQL settings (for AWS deployment)
    rds_host: Optional[str] = None
    rds_port: int = 5432
    rds_database: Optional[str] = None
    rds_user: Optional[str] = None
    rds_password: Optional[str] = None
    
    # Confluence settings
    confluence_base_url: Optional[str] = None
    confluence_api_token: Optional[str] = None
    confluence_username: Optional[str] = None
    
    # AWS settings
    aws_region: str = "us-west-2"
    aws_profile: str = "sdlc"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    s3_bucket_name: Optional[str] = None
    
    # DynamoDB Table Names
    users_table: str = "wops-users-local"
    verification_table: str = "wops-email-verification-local"
    password_reset_table: str = "wops-password-reset-local"
    usage_table: str = "wops-user-usage-local"
    
    # Redis settings
    redis_url: str = "redis://localhost:6379"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    
    # Security settings
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Email settings
    email_backend: str = "console"  # console, smtp, ses
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    sender_email: str = "noreply@localhost"
    
    # SES settings (for AWS)
    ses_sender_email: Optional[str] = None
    
    # Google OAuth settings
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    allowed_email_domains: str = "clipboardhealth.com,wops-ai.com"
    
    # Frontend settings
    frontend_url: str = "http://localhost:3000"
    
    # File upload settings
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: str = ".pdf,.txt,.csv,.json,.xlsx"
    local_storage_path: str = "./storage"
    
    # Email verification settings
    verification_expiry_hours: int = 24
    password_reset_expiry_hours: int = 1
    
    @property
    def is_local(self) -> bool:
        """Check if running in local environment"""
        return self.environment == Environment.LOCAL
    
    @property
    def allowed_file_types_list(self) -> list:
        """Convert comma-separated string to list"""
        return [ext.strip() for ext in self.allowed_file_types.split(",") if ext.strip()]
    
    @property
    def allowed_domains_list(self) -> List[str]:
        """Get list of allowed email domains"""
        return [domain.strip().lower() for domain in self.allowed_email_domains.split(",")]
    
    def is_allowed_email_domain(self, email: str) -> bool:
        """Check if email domain is allowed for registration"""
        domain = email.split('@')[1].lower() if '@' in email else ''
        return domain in self.allowed_domains_list
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration based on environment"""
        if self.use_local_db or self.is_local:
            return {
                'type': 'sqlite',
                'url': self.database_url
            }
        else:
            return {
                'type': 'dynamodb',
                'aws_region': self.aws_region,
                'users_table': self.users_table,
                'verification_table': self.verification_table,
                'password_reset_table': self.password_reset_table,
                'usage_table': self.usage_table
            }
    
    def get_email_config(self) -> Dict[str, Any]:
        """Get email configuration based on environment"""
        if self.use_local_email or self.is_local:
            return {
                'backend': self.email_backend,
                'smtp_host': self.smtp_host,
                'smtp_port': self.smtp_port,
                'smtp_username': self.smtp_username,
                'smtp_password': self.smtp_password,
                'sender_email': self.sender_email,
                'frontend_url': self.frontend_url
            }
        else:
            return {
                'backend': 'ses',
                'aws_region': self.aws_region,
                'sender_email': self.ses_sender_email or self.sender_email,
                'frontend_url': self.frontend_url
            }
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration based on environment"""
        if self.use_local_storage or self.is_local:
            return {
                'type': 'local',
                'path': self.local_storage_path
            }
        else:
            return {
                'type': 'aws',
                'region': self.aws_region,
                's3_bucket': self.s3_bucket_name,
                'users_table': f'wops-users-{self.environment}',
                'verification_table': f'wops-email-verification-{self.environment}',
                'password_reset_table': f'wops-password-reset-{self.environment}',
                'usage_table': f'wops-user-usage-{self.environment}'
            }
    
    def get_secret_or_env(self, secret_name: str, default: str = None) -> str:
        """
        Get value from AWS Secrets Manager or environment variable
        In local development, falls back to environment variables
        """
        # First try environment variable
        value = os.getenv(secret_name)
        if value:
            return value
        
        # If not local and no env var, try AWS Secrets Manager
        if not self.is_local:
            try:
                import boto3
                from botocore.exceptions import ClientError
                
                secrets_client = boto3.client('secretsmanager', region_name=self.aws_region)
                secret_arn = os.getenv(f'{secret_name}_ARN')
                
                if secret_arn:
                    response = secrets_client.get_secret_value(SecretId=secret_arn)
                    return response['SecretString']
            except (ClientError, ImportError) as e:
                logger.warning(f"Failed to get secret {secret_name}: {e}")
        
        return default
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields instead of raising errors


settings = Settings()