#!/bin/bash
# Start backend with completely isolated environment

echo "🤖 Starting Backend with Isolated Environment"
echo "=============================================="

# Navigate to project directory
cd /Users/charantej/cbh_git/wops_ai

# Start with a clean environment and only load .env
echo "📁 Starting with clean environment..."

# Use env -i to start with clean environment, then source .env
env -i bash -c '
    cd /Users/charantej/cbh_git/wops_ai
    
    # Load .env file
    set -a  # automatically export all variables
    source .env
    set +a  # disable automatic export
    
    echo "✅ Loaded .env file in clean environment"
    echo "🔍 Snowflake User: $SNOWFLAKE_USER"
    echo "🔍 Snowflake Database: $SNOWFLAKE_DATABASE"
    echo "🔍 Snowflake Schema: $SNOWFLAKE_SCHEMA"
    echo "🔍 Snowflake Account: $SNOWFLAKE_ACCOUNT"
    
    # Activate virtual environment
    source backend/venv/bin/activate
    
    # Change to backend directory
    cd backend
    
    # Start the server
    echo "🚀 Starting backend server on port 8001..."
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
'