#!/usr/bin/env python3
"""
Test script to verify the app can start and connect to Snowflake
"""
import os
import sys
from pathlib import Path

# Ensure we're in the right directory and using the local .env file
os.chdir(Path(__file__).parent)

# Clear any existing Snowflake environment variables to ensure we use .env
snowflake_vars = [k for k in os.environ.keys() if k.startswith('SNOWFLAKE_')]
for var in snowflake_vars:
    del os.environ[var]

from dotenv import load_dotenv
# Force reload of .env file
load_dotenv(override=True)

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def test_basic_imports():
    """Test that basic imports work"""
    print("📦 Testing basic imports...")
    try:
        from app.core.config import settings
        print(f"✅ Settings loaded")
        print(f"✅ Snowflake account: {settings.snowflake_account}")
        print(f"✅ Snowflake user: {settings.snowflake_user}")
        print(f"✅ Snowflake schema: {settings.snowflake_schema}")
        print(f"✅ Private key path: {settings.snowflake_private_key_path}")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_snowflake_connection():
    """Test Snowflake connection using our app code"""
    print("\n❄️  Testing Snowflake connection...")
    try:
        from app.db.snowflake_connection import SnowflakeConnection
        
        # Create connection
        conn = SnowflakeConnection()
        print("✅ Connection object created")
        
        # Test simple query
        result = conn.execute_query("SELECT CURRENT_VERSION(), CURRENT_USER(), CURRENT_DATABASE(), CURRENT_SCHEMA() LIMIT 1")
        print("✅ Query executed successfully")
        print(f"✅ Result: {result.iloc[0].to_dict()}")
        
        # Test getting tables
        tables = conn.get_available_tables()
        print(f"✅ Found {len(tables)} tables")
        if tables:
            print(f"✅ Sample tables: {tables[:5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_ai_provider():
    """Test AI provider connection"""
    print("\n🤖 Testing AI provider...")
    try:
        from app.core.ai_provider import ai_manager
        
        providers = ai_manager.get_available_providers()
        print(f"✅ Available providers: {providers}")
        
        if "openai" in providers:
            print("✅ OpenAI provider is available")
            return True
        else:
            print("❌ OpenAI provider not available")
            return False
            
    except Exception as e:
        print(f"❌ AI provider test failed: {e}")
        return False

def test_bi_service():
    """Test BI service"""
    print("\n📊 Testing BI service...")
    try:
        from app.services.bi_service import bi_service
        
        # Test dashboard metrics
        metrics = bi_service.get_dashboard_metrics()
        print("✅ Dashboard metrics retrieved")
        print(f"✅ Available tables: {len(metrics.get('available_tables', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ BI service test failed: {e}")
        return False

def main():
    print("🤖 WOPS AI - Application Test")
    print("=" * 50)
    
    success = True
    
    # Test basic imports
    if not test_basic_imports():
        success = False
    
    # Test Snowflake connection
    if not test_snowflake_connection():
        success = False
    
    # Test AI provider
    if not test_ai_provider():
        success = False
    
    # Test BI service
    if not test_bi_service():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Your app should work correctly.")
    else:
        print("❌ Some tests failed. Check the errors above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)