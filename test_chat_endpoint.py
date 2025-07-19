#!/usr/bin/env python3
"""
Test the chat endpoint to verify it's working
"""
import requests
import json
import time

def test_chat():
    print("🤖 Testing Chat Endpoint")
    print("=" * 30)
    
    # Wait for server to be ready
    print("⏳ Waiting for server to be ready...")
    time.sleep(2)
    
    # Test health endpoint first
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        print(f"✅ Health check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test chat endpoint
    try:
        chat_data = {
            "message": "Show me all available tables",
            "ai_provider": "openai"
        }
        
        print(f"🔄 Sending chat request...")
        response = requests.post("http://localhost:8001/api/v1/chat", json=chat_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Chat response received!")
            print(f"📝 Response: {result.get('response', 'No response')[:200]}...")
            print(f"🎯 Success: {result.get('success', False)}")
            print(f"🤖 AI Provider: {result.get('ai_provider', 'Unknown')}")
            
            if result.get('query_results'):
                print(f"📊 Query results: {len(result['query_results'])} records")
                
            return True
        else:
            print(f"❌ Chat request failed: {response.status_code}")
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Chat test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_chat()
    if success:
        print("\n🎉 Chat endpoint is working!")
    else:
        print("\n❌ Chat endpoint has issues!")