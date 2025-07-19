#!/usr/bin/env python3
"""
Simple development server startup script for WOPS AI
This script helps you start the application with minimal dependencies
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def check_python_dependencies():
    """Check if Python dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import openai
        import snowflake.connector
        import pandas
        print("✅ Python dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing Python dependencies: {e}")
        print("Please run: cd backend && pip install -r requirements.txt")
        return False

def check_node_dependencies():
    """Check if Node.js dependencies are installed"""
    frontend_dir = Path("frontend")
    if (frontend_dir / "node_modules").exists():
        print("✅ Node.js dependencies are installed")
        return True
    else:
        print("❌ Node.js dependencies not found")
        print("Please run: cd frontend && npm install")
        return False

def check_env_file():
    """Check if .env file exists and has required variables"""
    if not os.path.exists(".env"):
        print("❌ .env file not found")
        print("Please copy .env.example to .env and configure your credentials")
        return False
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'OPENAI_API_KEY',
        'SNOWFLAKE_ACCOUNT',
        'SNOWFLAKE_USER',
        'SNOWFLAKE_WAREHOUSE',
        'SNOWFLAKE_DATABASE'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print('❌ Missing required environment variables:')
        for var in missing:
            print(f'  - {var}')
        print('\nPlease update your .env file')
        return False
    
    # Check if private key path exists
    key_path = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH')
    if key_path and not os.path.exists(key_path):
        print(f'❌ Snowflake private key not found at: {key_path}')
        return False
    
    print("✅ Environment configuration is valid")
    return True

def start_backend():
    """Start the backend server"""
    print("🚀 Starting backend server...")
    backend_dir = Path("backend")
    
    # Change to backend directory and start uvicorn
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "app.main:app", 
        "--reload", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ]
    
    return subprocess.Popen(cmd, cwd=backend_dir)

def start_frontend():
    """Start the frontend server"""
    print("🚀 Starting frontend server...")
    frontend_dir = Path("frontend")
    
    # Start Next.js development server
    cmd = ["npm", "run", "dev"]
    
    return subprocess.Popen(cmd, cwd=frontend_dir)

def main():
    print("🤖 WOPS AI Development Server Startup")
    print("=" * 50)
    
    # Check all prerequisites
    if not check_env_file():
        sys.exit(1)
    
    if not check_python_dependencies():
        sys.exit(1)
    
    if not check_node_dependencies():
        sys.exit(1)
    
    print("\n✅ All prerequisites met!")
    print("🚀 Starting development servers...\n")
    
    # Start backend
    backend_process = start_backend()
    time.sleep(3)  # Give backend time to start
    
    # Start frontend
    frontend_process = start_frontend()
    
    print("\n" + "=" * 50)
    print("🎉 WOPS AI is now running!")
    print("📡 Backend API: http://localhost:8000")
    print("📋 API Docs: http://localhost:8000/docs")
    print("🌐 Frontend: http://localhost:3000")
    print("=" * 50)
    print("\nPress Ctrl+C to stop both servers")
    
    try:
        # Wait for both processes
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
        backend_process.terminate()
        frontend_process.terminate()
        backend_process.wait()
        frontend_process.wait()
        print("✅ Servers stopped successfully")

if __name__ == "__main__":
    main()