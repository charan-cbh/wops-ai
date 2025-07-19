#!/bin/bash

# WOPS AI Setup and Run Script
# This script sets up virtual environments and starts both backend and frontend

set -e  # Exit on any error

echo "🤖 WOPS AI - Complete Setup and Launch Script"
echo "================================================="

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

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    echo "Please copy .env.example to .env and configure your credentials:"
    echo "cp .env.example .env"
    exit 1
fi

print_success ".env file found"

# Create Python virtual environment for backend
print_step "Step 1: Setting up Python virtual environment for backend..."
cd backend

if [ -d "venv" ]; then
    print_warning "Virtual environment already exists, removing it..."
    rm -rf venv
fi

python3 -m venv venv
source venv/bin/activate

print_success "Virtual environment created and activated"

# Install backend dependencies
print_step "Step 2: Installing backend dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

print_success "Backend dependencies installed"

# Create necessary directories
mkdir -p uploads metadata
print_success "Created uploads and metadata directories"

cd ..

# Install frontend dependencies
print_step "Step 3: Installing frontend dependencies..."
cd frontend

if [ -d "node_modules" ]; then
    print_warning "Node modules already exist, removing them..."
    rm -rf node_modules
fi

npm install

print_success "Frontend dependencies installed"

cd ..

# Check environment variables
print_step "Step 4: Checking environment configuration..."
source .env

required_vars=("OPENAI_API_KEY" "SNOWFLAKE_ACCOUNT" "SNOWFLAKE_USER" "SNOWFLAKE_WAREHOUSE" "SNOWFLAKE_DATABASE")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_error "Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo "Please update your .env file"
    exit 1
fi

# Check if private key file exists (optional for now)
if [ -n "$SNOWFLAKE_PRIVATE_KEY_PATH" ]; then
    if [ ! -f "$SNOWFLAKE_PRIVATE_KEY_PATH" ]; then
        print_warning "Snowflake private key file not found at: $SNOWFLAKE_PRIVATE_KEY_PATH"
        echo "Please ensure your private key file is in the correct location"
        echo "You can continue without it, but Snowflake connection may fail"
    else
        print_success "Snowflake private key file found"
    fi
fi

print_success "Environment configuration is valid"

# Start the applications
print_step "Step 5: Starting applications..."

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
echo "================================================="
echo -e "${GREEN}🎉 WOPS AI is now running!${NC}"
echo "================================================="
echo -e "${BLUE}📡 Backend API:${NC} http://localhost:8000"
echo -e "${BLUE}📋 API Docs:${NC} http://localhost:8000/docs"
echo -e "${BLUE}🌐 Frontend:${NC} http://localhost:3000"
echo "================================================="
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