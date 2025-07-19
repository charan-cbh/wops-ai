#!/bin/bash

# WOPS AI Run Script
# This script starts both backend and frontend servers

set -e  # Exit on any error

echo "🤖 WOPS AI - Starting Application"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if setup has been run
if [ ! -d "backend/venv" ]; then
    print_error "Backend virtual environment not found!"
    echo "Please run setup first: ./setup_only.sh"
    exit 1
fi

if [ ! -d "frontend/node_modules" ]; then
    print_error "Frontend dependencies not found!"
    echo "Please run setup first: ./setup_only.sh"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    echo "Please copy .env.example to .env and configure your credentials"
    exit 1
fi

print_success "Prerequisites check passed"

# Function to cleanup on exit
cleanup() {
    print_warning "Shutting down servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up trap for cleanup
trap cleanup SIGINT SIGTERM

# Start backend
print_step "Starting backend server..."
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait a bit for backend to start
sleep 5

# Start frontend
print_step "Starting frontend server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait a bit for frontend to start
sleep 5

echo ""
echo "=================================="
echo -e "${GREEN}🎉 WOPS AI is now running!${NC}"
echo "=================================="
echo -e "${BLUE}📡 Backend API:${NC} http://localhost:8000"
echo -e "${BLUE}📋 API Docs:${NC} http://localhost:8000/docs"
echo -e "${BLUE}🌐 Frontend:${NC} http://localhost:3000"
echo "=================================="
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo ""

# Test backend health
print_step "Testing backend health..."
sleep 2
if curl -s http://localhost:8000/health > /dev/null; then
    print_success "Backend is healthy"
else
    print_warning "Backend health check failed, but it might still be starting..."
fi

# Keep the script running
wait $BACKEND_PID $FRONTEND_PID