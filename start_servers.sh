#!/bin/bash

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up..."
    kill $backend_pid 2>/dev/null
    kill $frontend_pid 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo "🤖 Starting WOPS AI Servers"
echo "============================"

# Navigate to project directory
cd /Users/charantej/cbh_git/wops_ai

# Kill any existing processes on our ports
echo "🔧 Cleaning up existing processes..."
lsof -ti:8001 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

# Start backend server
echo "🚀 Starting backend server..."
source backend/venv/bin/activate && cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 &
backend_pid=$!

# Wait a bit for backend to start
sleep 3

# Start frontend server
echo "🚀 Starting frontend server..."
cd /Users/charantej/cbh_git/wops_ai/frontend && npm run dev &
frontend_pid=$!

# Display access URLs
echo ""
echo "✅ Servers started successfully!"
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8001"
echo "📚 API Docs: http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for user interrupt
wait