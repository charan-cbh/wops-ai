#!/usr/bin/env python3
"""
Debug script to check Snowflake schema configuration
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

def debug_schema():
    try:
        from backend.app.db.snowflake_simple import simple_snowflake_db
        
        print("🤖 WOPS AI - Snowflake Schema Debug")
        print("=" * 50)
        
        # Show connection parameters
        print("🔍 Connection Parameters:")
        print(f"Account: {simple_snowflake_db.connection_params['account']}")
        print(f"User: {simple_snowflake_db.connection_params['user']}")
        print(f"Database: {simple_snowflake_db.connection_params['database']}")
        print(f"Schema: {simple_snowflake_db.connection_params['schema']}")
        print(f"Warehouse: {simple_snowflake_db.connection_params['warehouse']}")
        
        # Test basic connection
        print("\n🔍 Testing basic connection...")
        if simple_snowflake_db.test_connection():
            print("✅ Connection successful!")
        else:
            print("❌ Connection failed!")
            return False
        
        # Check current database and schema
        print("\n🔍 Checking current database and schema...")
        current_db_query = "SELECT CURRENT_DATABASE() as current_db, CURRENT_SCHEMA() as current_schema"
        df = simple_snowflake_db.execute_query(current_db_query)
        print(f"✅ Current Database: {df.iloc[0]['CURRENT_DB']}")
        print(f"✅ Current Schema: {df.iloc[0]['CURRENT_SCHEMA']}")
        
        # Check available schemas
        print("\n🔍 Checking available schemas...")
        schemas_query = "SHOW SCHEMAS"
        df = simple_snowflake_db.execute_query(schemas_query)
        print(f"✅ Found {len(df)} schemas:")
        for schema in df['name'].head(10):
            print(f"  - {schema}")
        
        # Check tables in current schema
        print("\n🔍 Checking tables in current schema...")
        tables_query = "SHOW TABLES"
        df = simple_snowflake_db.execute_query(tables_query)
        print(f"✅ Found {len(df)} tables:")
        for table in df['name'].head(10):
            print(f"  - {table}")
        
        # Try the information_schema query
        print("\n🔍 Testing information_schema query...")
        info_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = CURRENT_SCHEMA()
        LIMIT 10
        """
        df = simple_snowflake_db.execute_query(info_query)
        print(f"✅ Found {len(df)} tables via information_schema")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_schema()
    sys.exit(0 if success else 1)