#!/bin/bash

# WOPS AI Setup Only Script
# This script only sets up the environment without running the servers

set -e  # Exit on any error

echo "🤖 WOPS AI - Setup Only Script"
echo "================================"

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
    print_warning ".env file not found, creating from example..."
    cp .env.example .env
    echo "Please edit .env file with your credentials:"
    echo "- OPENAI_API_KEY"
    echo "- SNOWFLAKE_ACCOUNT"
    echo "- SNOWFLAKE_USER"
    echo "- SNOWFLAKE_PRIVATE_KEY_PATH"
    echo "- SNOWFLAKE_WAREHOUSE"
    echo "- SNOWFLAKE_DATABASE"
fi

print_success ".env file ready"

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

echo ""
echo "================================"
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo "================================"
echo ""
echo "To start the application:"
echo -e "${YELLOW}./run_app.sh${NC}"
echo ""
echo "Or manually:"
echo -e "${BLUE}# Backend:${NC}"
echo "cd backend && source venv/bin/activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo -e "${BLUE}# Frontend (in another terminal):${NC}"
echo "cd frontend && npm run dev"
echo ""
echo -e "${YELLOW}Don't forget to configure your .env file!${NC}"