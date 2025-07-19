# WOPS AI Setup Guide

This guide covers setting up the WOPS AI system for both local development and AWS deployment with ClipboardHealth email authentication.

## 🏠 Local Development Setup

### Prerequisites

1. **Python 3.11+**
2. **Node.js 18+**
3. **Git**

### Backend Setup

1. **Clone and navigate to backend:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration:**
   ```bash
   cp .env.example .env
   ```

5. **Update `.env` file with your settings:**
   ```env
   # Keep these as defaults for local development
   ENVIRONMENT=local
   USE_LOCAL_DB=true
   USE_LOCAL_EMAIL=true
   USE_LOCAL_STORAGE=true
   
   # Add your API keys
   OPENAI_API_KEY="your-openai-key"
   ANTHROPIC_API_KEY="your-anthropic-key"
   
   # Email domain restriction (ClipboardHealth)
   ALLOWED_EMAIL_DOMAINS="clipboardhealth.com,wops-ai.com"
   ```

6. **Start the backend:**
   ```bash
   source venv/bin/activate
   python -m app.main
   ```

### Frontend Setup

1. **Navigate to frontend:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Create `.env.local` file:**
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8001
   ```

4. **Start the frontend:**
   ```bash
   npm run dev
   ```

### Local Development Features

✅ **SQLite Database** - Automatic local database creation  
✅ **Console Email Logging** - Emails logged to console (no SMTP needed)  
✅ **File Storage** - Local file system storage  
✅ **Email Verification** - Complete workflow with local token storage  
✅ **Domain Restriction** - Only ClipboardHealth emails allowed  

**Default Admin Account:**
- Email: `admin@wops-ai.com`
- Password: `admin123`

## ☁️ AWS SSO Configuration

### Step 1: Install AWS CLI v2

```bash
# macOS
brew install awscli

# Or download from AWS official documentation
# Verify installation
aws --version  # Should be 2.10+
```

### Step 2: Configure AWS SSO

Create/update `~/.aws/config`:

```ini
[profile playground]
sso_session = cbh-sso
sso_account_id = YOUR_PLAYGROUND_ACCOUNT_ID
sso_role_name = YOUR_ROLE_NAME
region = us-west-2
output = json

[profile sdlc]
sso_session = cbh-sso
sso_account_id = YOUR_SDLC_ACCOUNT_ID
sso_role_name = YOUR_ROLE_NAME
region = us-west-2
output = json

[profile prod]
sso_session = cbh-sso
sso_account_id = YOUR_PROD_ACCOUNT_ID
sso_role_name = YOUR_ROLE_NAME
region = us-west-2
output = json

[sso-session cbh-sso]
sso_start_url = YOUR_SSO_START_URL
sso_region = us-west-2
sso_registration_scopes = sso:account:access
```

### Step 3: Login to AWS SSO

```bash
# Login using your ClipboardHealth email
aws sso login --profile sdlc

# This will open browser for authentication
# Use your ClipboardHealth email credentials
```

### Step 4: Test Access

```bash
# Test basic access
aws s3 ls --profile sdlc

# Set environment variables
source <(aws configure export-credentials --profile sdlc --format env)

# Verify credentials
echo $AWS_ACCESS_KEY_ID
```

### Step 5: Update Environment for AWS

Update your `.env` file for AWS deployment:

```env
# Change to deployment environment
ENVIRONMENT=development  # or staging/production
USE_LOCAL_DB=false
USE_LOCAL_EMAIL=false
USE_LOCAL_STORAGE=false

# AWS Configuration
AWS_REGION=us-west-2
AWS_PROFILE=sdlc

# PostgreSQL (RDS) Settings
RDS_HOST=your-rds-endpoint
RDS_DATABASE=wops_ai
RDS_USER=your-db-user
RDS_PASSWORD=your-db-password

# SES Configuration
SES_SENDER_EMAIL=noreply@yourdomain.com

# DynamoDB Table Names
USERS_TABLE=wops-users-development
VERIFICATION_TABLE=wops-email-verification-development
PASSWORD_RESET_TABLE=wops-password-reset-development
USAGE_TABLE=wops-user-usage-development
```

## 🔐 Google OAuth Setup (Future)

### Prerequisites Information Needed:

1. **Google Cloud Project**
2. **OAuth 2.0 Client ID**
3. **Client Secret**
4. **Authorized domains**

### Configuration:

```env
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
ALLOWED_EMAIL_DOMAINS=clipboardhealth.com
```

## 📧 Email Verification Flow

### Local Development:
1. User registers with ClipboardHealth email
2. Verification email logged to console
3. Copy verification URL from console
4. Complete password setup

### Production:
1. User registers with ClipboardHealth email
2. Verification email sent via AWS SES
3. User clicks email link
4. Complete password setup

## 🔧 Environment Variables Reference

### Core Settings:
```env
ENVIRONMENT=local|development|staging|production
USE_LOCAL_DB=true|false
USE_LOCAL_EMAIL=true|false
USE_LOCAL_STORAGE=true|false
```

### Security:
```env
JWT_SECRET_KEY="secure-random-key"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Email Restrictions:
```env
ALLOWED_EMAIL_DOMAINS="clipboardhealth.com,wops-ai.com"
```

### AWS Services:
```env
AWS_REGION=us-west-2
AWS_PROFILE=sdlc
SES_SENDER_EMAIL=noreply@yourdomain.com
```

## 🚀 Deployment Workflow

### Local → AWS Transition:

1. **Update Environment:**
   ```bash
   export ENVIRONMENT=development
   export USE_LOCAL_DB=false
   export USE_LOCAL_EMAIL=false
   export USE_LOCAL_STORAGE=false
   ```

2. **Configure AWS Resources:**
   - RDS PostgreSQL database
   - DynamoDB tables
   - SES domain verification
   - S3 bucket for file storage

3. **Update Environment Variables:**
   - Database connection strings
   - AWS service configurations
   - Production secrets

## 🛡️ Security Features

✅ **Email Domain Restriction** - Only ClipboardHealth emails  
✅ **JWT Authentication** - Secure token-based auth  
✅ **Email Verification** - Required before account activation  
✅ **Password Reset** - Secure token-based reset  
✅ **Usage Limits** - Rate limiting and quotas  
✅ **Role-Based Access** - Admin/User permissions  
✅ **Account Locking** - Failed attempt protection  

## 📱 User Registration Flow

### ClipboardHealth Employees:

1. **Register:** Enter ClipboardHealth email
2. **Verify:** Check email for verification link
3. **Set Password:** Create secure password
4. **Access:** Full system access with usage limits

### Admins:

- Full access to all features
- User management capabilities
- AI model configuration
- System administration

## 🔍 Troubleshooting

### Common Issues:

1. **SQLite Database Errors:**
   ```bash
   rm wops_ai_local.db local_tokens.db
   # Restart backend to recreate
   ```

2. **AWS SSO Session Expired:**
   ```bash
   aws sso login --profile sdlc
   ```

3. **Email Not Received:**
   - Check console logs in local development
   - Verify SES domain in production
   - Check spam folder

4. **Domain Restriction:**
   - Only ClipboardHealth emails allowed
   - Update `ALLOWED_EMAIL_DOMAINS` if needed

### Logs and Debugging:

```bash
# Backend logs
tail -f logs/app.log

# Check database
sqlite3 wops_ai_local.db ".tables"

# AWS credentials
aws sts get-caller-identity --profile sdlc
```

## 📞 Support

For setup issues or questions:
1. Check logs for error details
2. Verify environment configuration
3. Test AWS SSO connectivity
4. Confirm email domain restrictions

---

**Next Steps:** Once local development is working, we can proceed with AWS deployment configuration and Google OAuth integration.