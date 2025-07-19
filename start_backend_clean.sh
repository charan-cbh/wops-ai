#!/bin/bash
# Start backend with clean environment (unset system SNOWFLAKE vars)

echo "🤖 Starting Backend with Clean Environment"
echo "==========================================="

# Navigate to project directory
cd /Users/charantej/cbh_git/wops_ai

# Unset system Snowflake environment variables
unset SNOWFLAKE_ACCOUNT
unset SNOWFLAKE_USER  
unset SNOWFLAKE_PRIVATE_KEY_PATH
unset SNOWFLAKE_PRIVATE_KEY_PASSPHRASE
unset SNOWFLAKE_SCHEMA
unset SNOWFLAKE_DATABASE
unset SNOWFLAKE_WAREHOUSE

echo "✅ Unset system Snowflake environment variables"

# Export variables from .env file
echo "📁 Loading .env file..."
export $(cat .env | grep -v '^#' | xargs)

echo "✅ Loaded .env file"
echo "🔍 Snowflake User: $SNOWFLAKE_USER"
echo "🔍 Snowflake Database: $SNOWFLAKE_DATABASE"
echo "🔍 Snowflake Schema: $SNOWFLAKE_SCHEMA"

# Activate virtual environment
source backend/venv/bin/activate

# Change to backend directory
cd backend

# Start the server with explicit port
echo "🚀 Starting backend server on port 8001..."
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001