"""
AWS-Ready Email Verification Service
Handles email verification, password resets, and email notifications using AWS SES and DynamoDB
"""

import logging
import boto3
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import uuid4
import os
from botocore.exceptions import ClientError, NoCredentialsError
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

class EmailVerificationService:
    """
    Production-ready email verification service using AWS SES and DynamoDB
    """
    
    def __init__(self):
        # AWS Configuration
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.ses_sender_email = os.getenv('SES_SENDER_EMAIL', 'noreply@wops-ai.com')
        self.frontend_url = os.getenv('FRONTEND_URL', 'https://wops-ai.com')
        
        # DynamoDB table names
        self.verification_table = os.getenv('VERIFICATION_TABLE', 'wops-email-verification')
        self.password_reset_table = os.getenv('PASSWORD_RESET_TABLE', 'wops-password-reset')
        
        # Token expiration settings
        self.verification_expiry_hours = int(os.getenv('VERIFICATION_EXPIRY_HOURS', '24'))
        self.password_reset_expiry_hours = int(os.getenv('PASSWORD_RESET_EXPIRY_HOURS', '1'))
        
        # Initialize AWS clients
        self._init_aws_clients()
        self._create_dynamodb_tables()
    
    def _init_aws_clients(self):
        """Initialize AWS SES and DynamoDB clients"""
        try:
            # Use IAM roles in production, access keys in development
            session = boto3.Session(region_name=self.aws_region)
            
            self.ses_client = session.client('ses')
            self.dynamodb = session.resource('dynamodb')
            
            logger.info("AWS clients initialized successfully")
            
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure AWS credentials.")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            raise
    
    def _create_dynamodb_tables(self):
        """Create DynamoDB tables if they don't exist"""
        try:
            # Email verification table
            try:
                self.verification_table_resource = self.dynamodb.Table(self.verification_table)
                self.verification_table_resource.load()
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.info(f"Creating {self.verification_table} table...")
                    self.verification_table_resource = self.dynamodb.create_table(
                        TableName=self.verification_table,
                        KeySchema=[
                            {'AttributeName': 'email', 'KeyType': 'HASH'},
                            {'AttributeName': 'token', 'KeyType': 'RANGE'}
                        ],
                        AttributeDefinitions=[
                            {'AttributeName': 'email', 'AttributeType': 'S'},
                            {'AttributeName': 'token', 'AttributeType': 'S'},
                            {'AttributeName': 'expires_at', 'AttributeType': 'N'}
                        ],
                        BillingMode='PAY_PER_REQUEST',
                        GlobalSecondaryIndexes=[
                            {
                                'IndexName': 'token-index',
                                'KeySchema': [
                                    {'AttributeName': 'token', 'KeyType': 'HASH'}
                                ],
                                'Projection': {'ProjectionType': 'ALL'}
                            }
                        ],
                        TimeToLiveSpecification={
                            'AttributeName': 'expires_at',
                            'Enabled': True
                        }
                    )
                    # Wait for table to be created
                    self.verification_table_resource.wait_until_exists()
                    logger.info(f"{self.verification_table} table created successfully")
            
            # Password reset table
            try:
                self.password_reset_table_resource = self.dynamodb.Table(self.password_reset_table)
                self.password_reset_table_resource.load()
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.info(f"Creating {self.password_reset_table} table...")
                    self.password_reset_table_resource = self.dynamodb.create_table(
                        TableName=self.password_reset_table,
                        KeySchema=[
                            {'AttributeName': 'email', 'KeyType': 'HASH'},
                            {'AttributeName': 'token', 'KeyType': 'RANGE'}
                        ],
                        AttributeDefinitions=[
                            {'AttributeName': 'email', 'AttributeType': 'S'},
                            {'AttributeName': 'token', 'AttributeType': 'S'},
                            {'AttributeName': 'expires_at', 'AttributeType': 'N'}
                        ],
                        BillingMode='PAY_PER_REQUEST',
                        GlobalSecondaryIndexes=[
                            {
                                'IndexName': 'token-index',
                                'KeySchema': [
                                    {'AttributeName': 'token', 'KeyType': 'HASH'}
                                ],
                                'Projection': {'ProjectionType': 'ALL'}
                            }
                        ],
                        TimeToLiveSpecification={
                            'AttributeName': 'expires_at',
                            'Enabled': True
                        }
                    )
                    # Wait for table to be created
                    self.password_reset_table_resource.wait_until_exists()
                    logger.info(f"{self.password_reset_table} table created successfully")
                    
        except Exception as e:
            logger.error(f"Failed to create DynamoDB tables: {e}")
            raise
    
    def _generate_secure_token(self) -> str:
        """Generate a cryptographically secure verification token"""
        return secrets.token_urlsafe(32)
    
    def _hash_token(self, token: str) -> str:
        """Hash a token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def validate_email_address(self, email: str) -> bool:
        """Validate email address format"""
        try:
            validate_email(email)
            return True
        except EmailNotValidError:
            return False
    
    async def send_verification_email(self, email: str, user_id: str) -> bool:
        """Send email verification email using AWS SES"""
        try:
            # Validate email format
            if not self.validate_email_address(email):
                raise ValueError("Invalid email format")
            
            # Generate verification token
            token = self._generate_secure_token()
            token_hash = self._hash_token(token)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=self.verification_expiry_hours)
            
            # Store verification token in DynamoDB
            self.verification_table_resource.put_item(
                Item={
                    'email': email,
                    'token': token_hash,
                    'user_id': user_id,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'expires_at': int(expires_at.timestamp()),
                    'verified': False
                }
            )
            
            # Create verification URL
            verification_url = f"{self.frontend_url}/verify-email?token={token}&email={email}"
            
            # Email template
            subject = "Verify Your WOPS AI Account"
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Verify Your Email</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Welcome to WOPS AI!</h1>
                        <p>Please verify your email address to complete registration</p>
                    </div>
                    <div class="content">
                        <h2>Email Verification Required</h2>
                        <p>Thank you for registering with WOPS AI. To complete your account setup and start using our AI-powered business intelligence platform, please verify your email address.</p>
                        
                        <p><a href="{verification_url}" class="button">Verify My Email</a></p>
                        
                        <p>If the button doesn't work, copy and paste this link into your browser:</p>
                        <p style="word-break: break-all; background: #e9ecef; padding: 10px; border-radius: 5px; font-family: monospace;">{verification_url}</p>
                        
                        <p><strong>This verification link will expire in {self.verification_expiry_hours} hours.</strong></p>
                        
                        <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                        
                        <h3>What's Next?</h3>
                        <ul>
                            <li>Access powerful AI-driven business analytics</li>
                            <li>Generate insights from your operational data</li>
                            <li>Create custom reports and visualizations</li>
                            <li>Collaborate with your team on data analysis</li>
                        </ul>
                    </div>
                    <div class="footer">
                        <p>If you didn't create an account with WOPS AI, please ignore this email.</p>
                        <p>&copy; 2024 WOPS AI. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            Welcome to WOPS AI!
            
            Thank you for registering with WOPS AI. To complete your account setup, please verify your email address by clicking the link below:
            
            {verification_url}
            
            This verification link will expire in {self.verification_expiry_hours} hours.
            
            If you didn't create an account with WOPS AI, please ignore this email.
            
            Best regards,
            The WOPS AI Team
            """
            
            # Send email via SES
            response = self.ses_client.send_email(
                Source=self.ses_sender_email,
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                        'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                    }
                }
            )
            
            logger.info(f"Verification email sent successfully to {email}. Message ID: {response['MessageId']}")
            return True
            
        except ClientError as e:
            logger.error(f"SES error sending verification email to {email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending verification email to {email}: {e}")
            return False
    
    async def verify_email_token(self, email: str, token: str) -> bool:
        """Verify email verification token"""
        try:
            token_hash = self._hash_token(token)
            
            # Get token from DynamoDB
            response = self.verification_table_resource.get_item(
                Key={'email': email, 'token': token_hash}
            )
            
            if 'Item' not in response:
                logger.warning(f"Verification token not found for email: {email}")
                return False
            
            item = response['Item']
            
            # Check if token has expired
            expires_at = datetime.fromtimestamp(item['expires_at'], tz=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                logger.warning(f"Verification token expired for email: {email}")
                # Clean up expired token
                self.verification_table_resource.delete_item(
                    Key={'email': email, 'token': token_hash}
                )
                return False
            
            # Check if already verified
            if item.get('verified', False):
                logger.warning(f"Email already verified: {email}")
                return True
            
            # Mark as verified
            self.verification_table_resource.update_item(
                Key={'email': email, 'token': token_hash},
                UpdateExpression='SET verified = :verified, verified_at = :verified_at',
                ExpressionAttributeValues={
                    ':verified': True,
                    ':verified_at': datetime.now(timezone.utc).isoformat()
                }
            )
            
            logger.info(f"Email successfully verified: {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying email token for {email}: {e}")
            return False
    
    async def send_password_reset_email(self, email: str, user_id: str) -> bool:
        """Send password reset email"""
        try:
            # Validate email format
            if not self.validate_email_address(email):
                raise ValueError("Invalid email format")
            
            # Generate reset token
            token = self._generate_secure_token()
            token_hash = self._hash_token(token)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=self.password_reset_expiry_hours)
            
            # Store reset token in DynamoDB
            self.password_reset_table_resource.put_item(
                Item={
                    'email': email,
                    'token': token_hash,
                    'user_id': user_id,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'expires_at': int(expires_at.timestamp()),
                    'used': False
                }
            )
            
            # Create reset URL
            reset_url = f"{self.frontend_url}/reset-password?token={token}&email={email}"
            
            # Email template
            subject = "Reset Your WOPS AI Password"
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Reset Your Password</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                    .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Password Reset Request</h1>
                        <p>Reset your WOPS AI account password</p>
                    </div>
                    <div class="content">
                        <h2>Password Reset</h2>
                        <p>We received a request to reset the password for your WOPS AI account. If you made this request, click the button below to reset your password.</p>
                        
                        <p><a href="{reset_url}" class="button">Reset My Password</a></p>
                        
                        <p>If the button doesn't work, copy and paste this link into your browser:</p>
                        <p style="word-break: break-all; background: #e9ecef; padding: 10px; border-radius: 5px; font-family: monospace;">{reset_url}</p>
                        
                        <div class="warning">
                            <strong>⚠️ Important Security Information:</strong>
                            <ul>
                                <li>This reset link will expire in {self.password_reset_expiry_hours} hour(s)</li>
                                <li>The link can only be used once</li>
                                <li>If you didn't request this reset, please ignore this email</li>
                                <li>Your password will remain unchanged until you create a new one</li>
                            </ul>
                        </div>
                        
                        <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                        
                        <h3>Need Help?</h3>
                        <p>If you're having trouble with password reset, please contact our support team.</p>
                    </div>
                    <div class="footer">
                        <p>If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
                        <p>&copy; 2024 WOPS AI. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            Password Reset Request - WOPS AI
            
            We received a request to reset the password for your WOPS AI account.
            
            If you made this request, click the link below to reset your password:
            {reset_url}
            
            This reset link will expire in {self.password_reset_expiry_hours} hour(s) and can only be used once.
            
            If you didn't request this password reset, please ignore this email. Your password will remain unchanged.
            
            Best regards,
            The WOPS AI Team
            """
            
            # Send email via SES
            response = self.ses_client.send_email(
                Source=self.ses_sender_email,
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                        'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                    }
                }
            )
            
            logger.info(f"Password reset email sent successfully to {email}. Message ID: {response['MessageId']}")
            return True
            
        except ClientError as e:
            logger.error(f"SES error sending password reset email to {email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending password reset email to {email}: {e}")
            return False
    
    async def verify_password_reset_token(self, email: str, token: str) -> Optional[str]:
        """Verify password reset token and return user_id if valid"""
        try:
            token_hash = self._hash_token(token)
            
            # Get token from DynamoDB
            response = self.password_reset_table_resource.get_item(
                Key={'email': email, 'token': token_hash}
            )
            
            if 'Item' not in response:
                logger.warning(f"Password reset token not found for email: {email}")
                return None
            
            item = response['Item']
            
            # Check if token has expired
            expires_at = datetime.fromtimestamp(item['expires_at'], tz=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                logger.warning(f"Password reset token expired for email: {email}")
                # Clean up expired token
                self.password_reset_table_resource.delete_item(
                    Key={'email': email, 'token': token_hash}
                )
                return None
            
            # Check if token has been used
            if item.get('used', False):
                logger.warning(f"Password reset token already used for email: {email}")
                return None
            
            logger.info(f"Password reset token verified for email: {email}")
            return item['user_id']
            
        except Exception as e:
            logger.error(f"Error verifying password reset token for {email}: {e}")
            return None
    
    async def mark_password_reset_token_used(self, email: str, token: str) -> bool:
        """Mark password reset token as used"""
        try:
            token_hash = self._hash_token(token)
            
            # Mark token as used
            self.password_reset_table_resource.update_item(
                Key={'email': email, 'token': token_hash},
                UpdateExpression='SET used = :used, used_at = :used_at',
                ExpressionAttributeValues={
                    ':used': True,
                    ':used_at': datetime.now(timezone.utc).isoformat()
                }
            )
            
            logger.info(f"Password reset token marked as used for email: {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error marking password reset token as used for {email}: {e}")
            return False
    
    async def cleanup_expired_tokens(self):
        """Clean up expired tokens (this would typically be run as a scheduled job)"""
        try:
            current_time = int(datetime.now(timezone.utc).timestamp())
            
            # DynamoDB TTL should handle this automatically, but we can add manual cleanup if needed
            logger.info("Token cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during token cleanup: {e}")

# Global instance
email_verification_service = EmailVerificationService()