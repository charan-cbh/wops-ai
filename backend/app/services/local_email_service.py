"""
Local Email Service
For development - logs emails to console or uses local SMTP
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime, timedelta, timezone
import secrets
import hashlib
import sqlite3
import os
from app.core.config import settings

logger = logging.getLogger(__name__)

class LocalEmailService:
    """
    Local email service for development
    Supports console logging and local SMTP
    """
    
    def __init__(self):
        self.email_config = settings.get_email_config()
        self.backend = self.email_config['backend']
        self.sender_email = self.email_config['sender_email']
        self.frontend_url = self.email_config['frontend_url']
        
        # Initialize local SQLite database for tokens
        self.db_path = "./local_tokens.db"
        self._init_local_db()
        
        logger.info(f"Local email service initialized with backend: {self.backend}")
    
    def _init_local_db(self):
        """Initialize local SQLite database for email tokens"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create verification tokens table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_verification (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    verified BOOLEAN DEFAULT FALSE,
                    verified_at TIMESTAMP NULL
                )
            """)
            
            # Create password reset tokens table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS password_reset (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    used_at TIMESTAMP NULL
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("Local token database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize local database: {e}")
    
    def _generate_secure_token(self) -> str:
        """Generate a cryptographically secure verification token"""
        return secrets.token_urlsafe(32)
    
    def _hash_token(self, token: str) -> str:
        """Hash a token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def send_verification_email(self, email: str, user_id: str) -> bool:
        """Send email verification email"""
        try:
            # Generate verification token
            token = self._generate_secure_token()
            token_hash = self._hash_token(token)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.verification_expiry_hours)
            
            # Store verification token in local database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO email_verification (email, token_hash, user_id, expires_at)
                VALUES (?, ?, ?, ?)
            """, (email, token_hash, user_id, expires_at))
            conn.commit()
            conn.close()
            
            # Create verification URL
            verification_url = f"{self.frontend_url}/verify-email?token={token}&email={email}"
            
            # Email content
            subject = "Verify Your WOPS AI Account"
            text_body = f"""
Welcome to WOPS AI!

Thank you for registering with WOPS AI. To complete your account setup, please verify your email address by clicking the link below:

{verification_url}

This verification link will expire in {settings.verification_expiry_hours} hours.

If you didn't create an account with WOPS AI, please ignore this email.

Best regards,
The WOPS AI Team
            """
            
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 30px; border-radius: 10px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; margin: -30px -30px 30px -30px;">
            <h1 style="margin: 0;">Welcome to WOPS AI!</h1>
            <p style="margin: 10px 0 0 0;">Please verify your email address to complete registration</p>
        </div>
        
        <h2>Email Verification Required</h2>
        <p>Thank you for registering with WOPS AI. To complete your account setup and start using our AI-powered business intelligence platform, please verify your email address.</p>
        
        <p style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                Verify My Email
            </a>
        </p>
        
        <p>If the button doesn't work, copy and paste this link into your browser:</p>
        <p style="word-break: break-all; background: #e9ecef; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 12px;">{verification_url}</p>
        
        <p><strong>This verification link will expire in {settings.verification_expiry_hours} hours.</strong></p>
        
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
        
        <p style="font-size: 12px; color: #666; text-align: center;">
            If you didn't create an account with WOPS AI, please ignore this email.<br>
            &copy; 2024 WOPS AI. All rights reserved.
        </p>
    </div>
</body>
</html>
            """
            
            # Send email based on backend
            if self.backend == 'console':
                self._log_email_to_console(email, subject, text_body, verification_url)
            elif self.backend == 'smtp':
                self._send_smtp_email(email, subject, text_body, html_body)
            
            logger.info(f"Verification email sent successfully to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending verification email to {email}: {e}")
            return False
    
    async def send_password_reset_email(self, email: str, user_id: str) -> bool:
        """Send password reset email"""
        try:
            # Generate reset token
            token = self._generate_secure_token()
            token_hash = self._hash_token(token)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.password_reset_expiry_hours)
            
            # Store reset token in local database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO password_reset (email, token_hash, user_id, expires_at)
                VALUES (?, ?, ?, ?)
            """, (email, token_hash, user_id, expires_at))
            conn.commit()
            conn.close()
            
            # Create reset URL
            reset_url = f"{self.frontend_url}/reset-password?token={token}&email={email}"
            
            # Email content
            subject = "Reset Your WOPS AI Password"
            text_body = f"""
Password Reset Request - WOPS AI

We received a request to reset the password for your WOPS AI account.

If you made this request, click the link below to reset your password:
{reset_url}

This reset link will expire in {settings.password_reset_expiry_hours} hour(s) and can only be used once.

If you didn't request this password reset, please ignore this email. Your password will remain unchanged.

Best regards,
The WOPS AI Team
            """
            
            html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 30px; border-radius: 10px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; margin: -30px -30px 30px -30px;">
            <h1 style="margin: 0;">Password Reset Request</h1>
            <p style="margin: 10px 0 0 0;">Reset your WOPS AI account password</p>
        </div>
        
        <h2>Password Reset</h2>
        <p>We received a request to reset the password for your WOPS AI account. If you made this request, click the button below to reset your password.</p>
        
        <p style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                Reset My Password
            </a>
        </p>
        
        <p>If the button doesn't work, copy and paste this link into your browser:</p>
        <p style="word-break: break-all; background: #e9ecef; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 12px;">{reset_url}</p>
        
        <div style="background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <strong>⚠️ Important Security Information:</strong>
            <ul style="margin: 10px 0;">
                <li>This reset link will expire in {settings.password_reset_expiry_hours} hour(s)</li>
                <li>The link can only be used once</li>
                <li>If you didn't request this reset, please ignore this email</li>
                <li>Your password will remain unchanged until you create a new one</li>
            </ul>
        </div>
        
        <p style="font-size: 12px; color: #666; text-align: center; margin-top: 30px;">
            If you didn't request a password reset, please ignore this email or contact support if you have concerns.<br>
            &copy; 2024 WOPS AI. All rights reserved.
        </p>
    </div>
</body>
</html>
            """
            
            # Send email based on backend
            if self.backend == 'console':
                self._log_email_to_console(email, subject, text_body, reset_url)
            elif self.backend == 'smtp':
                self._send_smtp_email(email, subject, text_body, html_body)
            
            logger.info(f"Password reset email sent successfully to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending password reset email to {email}: {e}")
            return False
    
    def _log_email_to_console(self, to_email: str, subject: str, body: str, action_url: str):
        """Log email to console for development"""
        print("\n" + "="*80)
        print("📧 EMAIL SENT (Development Mode)")
        print("="*80)
        print(f"To: {to_email}")
        print(f"From: {self.sender_email}")
        print(f"Subject: {subject}")
        print("-"*80)
        print(body)
        print("-"*80)
        print(f"🔗 Action URL: {action_url}")
        print("="*80)
        print()
    
    def _send_smtp_email(self, to_email: str, subject: str, text_body: str, html_body: str):
        """Send email via local SMTP server"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = to_email
            
            # Attach text and HTML parts
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            smtp_config = self.email_config
            with smtplib.SMTP(smtp_config['smtp_host'], smtp_config['smtp_port']) as server:
                if smtp_config['smtp_username'] and smtp_config['smtp_password']:
                    server.starttls()
                    server.login(smtp_config['smtp_username'], smtp_config['smtp_password'])
                
                server.send_message(msg)
            
            logger.info(f"SMTP email sent successfully to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send SMTP email to {to_email}: {e}")
            # Fallback to console logging
            self._log_email_to_console(to_email, subject, text_body, "")
    
    async def verify_email_token(self, email: str, token: str) -> bool:
        """Verify email verification token"""
        try:
            token_hash = self._hash_token(token)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get token from database
            cursor.execute("""
                SELECT id, user_id, expires_at, verified 
                FROM email_verification 
                WHERE email = ? AND token_hash = ?
            """, (email, token_hash))
            
            result = cursor.fetchone()
            if not result:
                logger.warning(f"Verification token not found for email: {email}")
                conn.close()
                return False
            
            token_id, user_id, expires_at_str, verified = result
            
            # Check if token has expired
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires_at:
                logger.warning(f"Verification token expired for email: {email}")
                # Clean up expired token
                cursor.execute("DELETE FROM email_verification WHERE id = ?", (token_id,))
                conn.commit()
                conn.close()
                return False
            
            # Check if already verified
            if verified:
                logger.warning(f"Email already verified: {email}")
                conn.close()
                return True
            
            # Mark as verified
            cursor.execute("""
                UPDATE email_verification 
                SET verified = TRUE, verified_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (token_id,))
            conn.commit()
            conn.close()
            
            logger.info(f"Email successfully verified: {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying email token for {email}: {e}")
            return False
    
    async def verify_password_reset_token(self, email: str, token: str) -> Optional[str]:
        """Verify password reset token and return user_id if valid"""
        try:
            token_hash = self._hash_token(token)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get token from database
            cursor.execute("""
                SELECT id, user_id, expires_at, used 
                FROM password_reset 
                WHERE email = ? AND token_hash = ?
            """, (email, token_hash))
            
            result = cursor.fetchone()
            if not result:
                logger.warning(f"Password reset token not found for email: {email}")
                conn.close()
                return None
            
            token_id, user_id, expires_at_str, used = result
            
            # Check if token has expired
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires_at:
                logger.warning(f"Password reset token expired for email: {email}")
                # Clean up expired token
                cursor.execute("DELETE FROM password_reset WHERE id = ?", (token_id,))
                conn.commit()
                conn.close()
                return None
            
            # Check if token has been used
            if used:
                logger.warning(f"Password reset token already used for email: {email}")
                conn.close()
                return None
            
            conn.close()
            logger.info(f"Password reset token verified for email: {email}")
            return user_id
            
        except Exception as e:
            logger.error(f"Error verifying password reset token for {email}: {e}")
            return None
    
    async def mark_password_reset_token_used(self, email: str, token: str) -> bool:
        """Mark password reset token as used"""
        try:
            token_hash = self._hash_token(token)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Mark token as used
            cursor.execute("""
                UPDATE password_reset 
                SET used = TRUE, used_at = CURRENT_TIMESTAMP 
                WHERE email = ? AND token_hash = ?
            """, (email, token_hash))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Password reset token marked as used for email: {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error marking password reset token as used for {email}: {e}")
            return False

# Global instance
local_email_service = LocalEmailService()