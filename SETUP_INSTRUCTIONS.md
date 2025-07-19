# 🚀 WOPS AI - Complete Setup Instructions

## 🔧 Fixed Issues

1. **✅ SQLAlchemy Version Conflict**: Fixed compatibility between SQLAlchemy and Snowflake-SQLAlchemy
2. **✅ Virtual Environment**: Created automated venv setup
3. **✅ Dependencies**: Resolved all package conflicts
4. **✅ Python Path**: Using proper python3 with venv activation

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+
- Your OpenAI API key
- Snowflake account with private key authentication

## 🎯 Three Ways to Set Up

### Option 1: Complete Setup and Run (Recommended)
```bash
# This does everything: setup venv, install deps, configure, and start both servers
./setup_and_run.sh
```

### Option 2: Setup First, Then Run
```bash
# Step 1: Setup only
./setup_only.sh

# Step 2: Configure your .env file (edit with your credentials)
nano .env

# Step 3: Start the application
./run_app.sh
```

### Option 3: Manual Setup
```bash
# 1. Copy environment file
cp .env.example .env

# 2. Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p uploads metadata
cd ..

# 3. Frontend setup
cd frontend
npm install
cd ..

# 4. Start backend (terminal 1)
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. Start frontend (terminal 2)
cd frontend
npm run dev
```

## 🔑 Environment Configuration

Edit your `.env` file with your actual credentials:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-actual-openai-key-here
DEFAULT_AI_PROVIDER=openai

# Snowflake Configuration
SNOWFLAKE_ACCOUNT=your-snowflake-account
SNOWFLAKE_USER=your-snowflake-username
SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/your/private_key.pem
SNOWFLAKE_PRIVATE_KEY_PASSPHRASE=your_passphrase_if_any
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=PUBLIC

# App Configuration
DEBUG=true
SECRET_KEY=your-secret-key-for-dev
```

## 🌐 Access Your Application

After running the setup:

- **Frontend (Chat Interface)**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🧪 Test Your Setup

1. **Health Check**: Visit http://localhost:8000/health
2. **API Docs**: Visit http://localhost:8000/docs
3. **Chat Interface**: Visit http://localhost:3000

### Sample Queries to Try:
- "Show me all available tables"
- "What columns are in the [table_name] table?"
- "Give me a sample of data from [table_name]"
- "Analyze worker productivity trends"

## 🛠 Troubleshooting

### Common Issues:

1. **Permission Denied on Scripts:**
   ```bash
   chmod +x setup_and_run.sh setup_only.sh run_app.sh
   ```

2. **Port Already in Use:**
   ```bash
   # Kill processes on ports 3000 and 8000
   lsof -ti:3000 | xargs kill -9
   lsof -ti:8000 | xargs kill -9
   ```

3. **Python Virtual Environment Issues:**
   ```bash
   # Remove and recreate
   rm -rf backend/venv
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Node Module Issues:**
   ```bash
   # Clean install
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

5. **Snowflake Connection Issues:**
   - Verify your account identifier format
   - Check private key path and permissions
   - Ensure user has necessary Snowflake privileges

## 📂 What Gets Created

```
wops_ai/
├── backend/
│   ├── venv/              # Python virtual environment
│   ├── uploads/           # File upload directory
│   ├── metadata/          # File metadata storage
│   └── app/              # Application code
├── frontend/
│   ├── node_modules/      # Node.js dependencies
│   └── src/              # React application
└── .env                  # Your configuration
```

## 🎉 Success Indicators

When everything is working correctly, you'll see:

1. **Backend**: Server starts on port 8000
2. **Frontend**: Development server starts on port 3000
3. **Health Check**: Returns `{"status": "healthy"}`
4. **Chat Interface**: Loads and shows available AI providers
5. **Database Connection**: Can list Snowflake tables

## 🔄 Stopping the Application

Press `Ctrl+C` in the terminal where you ran the setup script. This will gracefully shutdown both servers.

## 📞 Need Help?

If you encounter any issues:
1. Check the terminal output for error messages
2. Verify your `.env` file configuration
3. Ensure all prerequisites are installed
4. Check if ports 3000 and 8000 are available

The setup scripts provide detailed output and error messages to help you troubleshoot any issues!