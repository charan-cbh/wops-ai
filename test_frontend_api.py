#!/usr/bin/env python3
"""
Test script to simulate the frontend API call and see what error occurs
"""
import requests
import json
import sys

def test_chat_endpoint():
    url = "http://localhost:8000/api/v1/chat"
    
    # Test data similar to what the frontend sends
    test_data = {
        "message": "Show me all available tables",
        "conversation_history": [
            {
                "role": "assistant",
                "content": "Hello! I'm your Worker Operations BI assistant.",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        ],
        "ai_provider": "openai",
        "model": "gpt-4"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print("🔍 Testing Frontend API Call")
    print("=" * 50)
    print(f"URL: {url}")
    print(f"Data: {json.dumps(test_data, indent=2)}")
    print()
    
    try:
        response = requests.post(url, json=test_data, headers=headers, timeout=30)
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Response Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Response Success!")
            print(f"Response: {result.get('response', 'No response')}")
            print(f"Success: {result.get('success')}")
            print(f"AI Provider: {result.get('ai_provider')}")
            print(f"Model: {result.get('model')}")
            
        else:
            print(f"❌ Error Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Backend server not running on localhost:8000")
        print("Make sure you run: cd backend && source venv/bin/activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        
    except requests.exceptions.Timeout:
        print("❌ Timeout Error: Request took too long")
        
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
        import traceback
        traceback.print_exc()

def test_health_check():
    url = "http://localhost:8000/health"
    print("\n🔍 Testing Health Check")
    print("=" * 50)
    
    try:
        response = requests.get(url, timeout=10)
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Response: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Health Check Failed: {str(e)}")
        return False

def test_providers_endpoint():
    url = "http://localhost:8000/api/v1/providers"
    print("\n🔍 Testing Providers Endpoint")
    print("=" * 50)
    
    try:
        response = requests.get(url, timeout=10)
        print(f"✅ Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Available Providers: {list(result.get('providers', {}).keys())}")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Providers Test Failed: {str(e)}")

if __name__ == "__main__":
    print("🤖 WOPS AI - Frontend API Test")
    print("=" * 50)
    
    # Test health check first
    if test_health_check():
        test_providers_endpoint()
        test_chat_endpoint()
    else:
        print("\n❌ Backend server is not running. Please start it first:")
        print("cd backend && source venv/bin/activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")