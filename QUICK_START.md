# 🚀 Quick Start Guide - WOPS AI

Get your Worker Operations BI Chatbot running in minutes with just OpenAI and Snowflake!

## Prerequisites

- Python 3.11+
- Node.js 18+
- Your OpenAI API key
- Snowflake account with key-based authentication

## Step 1: Environment Setup

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Configure your .env file:**
   ```bash
   # AI Provider Configuration
   OPENAI_API_KEY=sk-your-openai-key-here
   DEFAULT_AI_PROVIDER=openai

   # Snowflake Configuration (Key-based authentication)
   SNOWFLAKE_ACCOUNT=your-snowflake-account
   SNOWFLAKE_USER=your-snowflake-username
   SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/your/private_key.pem
   SNOWFLAKE_PRIVATE_KEY_PASSPHRASE=your_key_passphrase  # Optional
   SNOWFLAKE_WAREHOUSE=your_warehouse_name
   SNOWFLAKE_DATABASE=your_database_name
   SNOWFLAKE_SCHEMA=PUBLIC

   # Application Configuration
   DEBUG=true
   SECRET_KEY=your-secret-key-for-local-dev
   ```

## Step 2: Install Dependencies

```bash
# Backend dependencies
cd backend
pip install -r requirements.txt
cd ..

# Frontend dependencies
cd frontend
npm install
cd ..
```

## Step 3: Start the Application

### Option A: Using the startup script (Recommended)
```bash
python start_dev.py
```

### Option B: Manual startup
```bash
# Terminal 1 - Backend
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Option C: Using Make (simplified)
```bash
make -f Makefile.simple dev-simple
```

## Step 4: Access the Application

- **Frontend (Chat Interface):** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs

## Step 5: Test Your Setup

1. **Open the chat interface** at http://localhost:3000
2. **Try these example queries:**
   - "Show me the available tables in our database"
   - "What are the column names in the [your_table_name] table?"
   - "Give me a sample of data from [your_table_name]"

## 🔧 Configuration Notes

### Snowflake Private Key Setup
1. Your private key should be in PEM format
2. Make sure the key path in your .env file is correct
3. If your key has a passphrase, include it in the configuration

### Authentication
- The system includes optional authentication (currently using mock users)
- For local development, you can use:
  - Username: `admin`, Password: `admin123`
  - Username: `analyst`, Password: `analyst123`

## 🚨 Troubleshooting

### Common Issues

1. **Snowflake Connection Error:**
   - Verify your account identifier is correct
   - Check that your private key path and format are correct
   - Ensure your user has the necessary permissions

2. **OpenAI API Error:**
   - Verify your API key is valid and active
   - Check that you have sufficient credits

3. **Port Already in Use:**
   - Backend (8000): `lsof -ti:8000 | xargs kill -9`
   - Frontend (3000): `lsof -ti:3000 | xargs kill -9`

### Health Checks
- Backend health: http://localhost:8000/health
- Available tables: http://localhost:8000/api/v1/tables
- AI providers: http://localhost:8000/api/v1/providers

## 🎯 What's Included

- ✅ **Chat Interface**: Natural language querying
- ✅ **Snowflake Integration**: Direct database access
- ✅ **OpenAI Integration**: Intelligent query processing
- ✅ **Query Results**: Formatted data tables
- ✅ **Business Insights**: AI-generated analysis
- ✅ **File Upload**: Context documents (ready for future use)
- ✅ **Authentication**: Basic security layer

## 🔮 Next Steps

Once you have the basic setup working:

1. **Add more AI providers** (Claude, Gemini) by adding API keys
2. **Configure Confluence** for business context
3. **Deploy to AWS** using the provided Terraform configuration
4. **Add more sophisticated authentication** and user management

## 💡 Tips

- Use the API documentation at `/docs` to explore available endpoints
- Check the browser console for any frontend errors
- Backend logs will show detailed error information
- The system works offline (no external dependencies beyond OpenAI and Snowflake)