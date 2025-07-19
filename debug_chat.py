#!/usr/bin/env python3
"""
Debug script to test the chat functionality
"""
import os
import sys
from pathlib import Path
import asyncio
import json

# Ensure we're in the right directory
os.chdir(Path(__file__).parent)

# Clear any existing Snowflake environment variables
snowflake_vars = [k for k in os.environ.keys() if k.startswith('SNOWFLAKE_')]
for var in snowflake_vars:
    del os.environ[var]

from dotenv import load_dotenv
load_dotenv(override=True)

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

async def test_chat_endpoint():
    """Test the chat endpoint functionality"""
    print("🔍 Testing Chat Endpoint...")
    
    try:
        from app.services.bi_service import bi_service
        
        # Test a simple query
        test_query = "Show me all available tables"
        
        print(f"Testing query: '{test_query}'")
        result = await bi_service.process_natural_language_query(test_query)
        
        print("✅ Query processed successfully!")
        print(f"✅ Success: {result.get('success', 'Unknown')}")
        print(f"✅ Has explanation: {bool(result.get('explanation'))}")
        print(f"✅ Has SQL query: {bool(result.get('sql_query'))}")
        
        if result.get('error'):
            print(f"❌ Error in result: {result['error']}")
        
        if result.get('explanation'):
            print(f"📝 Explanation: {result['explanation'][:200]}...")
        
        if result.get('sql_query'):
            print(f"🔍 SQL Query: {result['sql_query']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Chat test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_simple_snowflake_query():
    """Test a simple Snowflake query"""
    print("\n❄️  Testing Simple Snowflake Query...")
    
    try:
        from app.db.snowflake_connection import snowflake_db
        
        # Test getting tables
        tables = snowflake_db.get_available_tables()
        print(f"✅ Found {len(tables)} tables")
        
        if tables:
            # Test getting schema for first table
            table_name = tables[0]
            schema = snowflake_db.get_table_schema(table_name)
            print(f"✅ Got schema for {table_name}: {len(schema)} columns")
            
            # Test sample data
            sample = snowflake_db.get_table_sample(table_name, 3)
            print(f"✅ Got sample data: {len(sample)} rows")
        
        return True
        
    except Exception as e:
        print(f"❌ Snowflake query test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_ai_provider():
    """Test AI provider directly"""
    print("\n🤖 Testing AI Provider...")
    
    try:
        from app.core.ai_provider import ai_manager
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello!"}
        ]
        
        response = await ai_manager.generate_response(messages)
        print(f"✅ AI Response: {response.content[:100]}...")
        print(f"✅ Provider: {response.provider}")
        print(f"✅ Model: {response.model}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI provider test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🔧 WOPS AI - Chat Debug")
    print("=" * 50)
    
    success = True
    
    # Test simple Snowflake query
    if not await test_simple_snowflake_query():
        success = False
    
    # Test AI provider
    if not await test_ai_provider():
        success = False
    
    # Test chat endpoint
    if not await test_chat_endpoint():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All chat tests passed!")
    else:
        print("❌ Some chat tests failed.")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)