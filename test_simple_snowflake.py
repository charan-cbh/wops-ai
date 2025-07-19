#!/usr/bin/env python3
"""
Test script for the simplified Snowflake connection
"""
import os
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Set up environment
os.environ['PYTHONPATH'] = str(Path(__file__).parent / "backend")

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_simple_connection():
    try:
        from backend.app.db.snowflake_simple import simple_snowflake_db
        
        print("🤖 WOPS AI - Simple Snowflake Connection Test")
        print("=" * 50)
        
        # Test basic connection
        print("🔍 Testing basic connection...")
        if simple_snowflake_db.test_connection():
            print("✅ Connection successful!")
        else:
            print("❌ Connection failed!")
            return False
        
        # Test getting tables
        print("\n🔍 Testing table retrieval...")
        tables = simple_snowflake_db.get_available_tables()
        print(f"✅ Found {len(tables)} tables")
        
        if tables:
            print(f"✅ Sample tables: {tables[:5]}")
            
            # Test table schema
            print(f"\n🔍 Testing schema for table: {tables[0]}")
            schema = simple_snowflake_db.get_table_schema(tables[0])
            print(f"✅ Found {len(schema)} columns")
            
            # Test sample data
            print(f"\n🔍 Testing sample data for table: {tables[0]}")
            sample_df = simple_snowflake_db.get_table_sample(tables[0], 3)
            print(f"✅ Retrieved {len(sample_df)} rows")
            print(f"✅ Columns: {list(sample_df.columns)}")
            
        print("\n🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_connection()
    sys.exit(0 if success else 1)