#!/usr/bin/env python3
"""
Test script to verify environment loading works correctly
"""
import os
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def test_env_loading():
    print("🤖 WOPS AI - Environment Loading Test")
    print("=" * 50)
    
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check if settings can be loaded
    try:
        from backend.app.core.config import settings
        
        print("✅ Settings loaded successfully")
        print(f"🔍 Snowflake Account: {settings.snowflake_account}")
        print(f"🔍 Snowflake User: {settings.snowflake_user}")
        print(f"🔍 Snowflake Database: {settings.snowflake_database}")
        print(f"🔍 Snowflake Schema: {settings.snowflake_schema}")
        print(f"🔍 Snowflake Warehouse: {settings.snowflake_warehouse}")
        print(f"🔍 Private Key Path: {settings.snowflake_private_key_path}")
        
        # Check if all required settings are present
        if not settings.snowflake_user:
            print("❌ ERROR: Snowflake user is empty!")
            return False
            
        if not settings.snowflake_account:
            print("❌ ERROR: Snowflake account is empty!")
            return False
            
        print("✅ All required settings are present")
        return True
        
    except Exception as e:
        print(f"❌ Error loading settings: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_env_loading()
    sys.exit(0 if success else 1)