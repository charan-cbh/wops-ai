#!/usr/bin/env python3
"""
Test script to diagnose Snowflake connection issues
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load environment variables
load_dotenv()

def test_environment():
    """Test if all required environment variables are set"""
    print("🔍 Testing Environment Variables...")
    
    required_vars = [
        'SNOWFLAKE_ACCOUNT',
        'SNOWFLAKE_USER',
        'SNOWFLAKE_WAREHOUSE',
        'SNOWFLAKE_DATABASE',
        'SNOWFLAKE_SCHEMA'
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET")
    
    # Check private key
    key_path = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH')
    if key_path:
        if os.path.exists(key_path):
            print(f"✅ SNOWFLAKE_PRIVATE_KEY_PATH: {key_path} (exists)")
        else:
            print(f"❌ SNOWFLAKE_PRIVATE_KEY_PATH: {key_path} (NOT FOUND)")
    else:
        print("❌ SNOWFLAKE_PRIVATE_KEY_PATH: NOT SET")
    
    passphrase = os.getenv('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE')
    if passphrase:
        print(f"✅ SNOWFLAKE_PRIVATE_KEY_PASSPHRASE: ****** (set)")
    else:
        print("⚠️  SNOWFLAKE_PRIVATE_KEY_PASSPHRASE: NOT SET")

def test_private_key():
    """Test if private key can be loaded"""
    print("\n🔑 Testing Private Key Loading...")
    
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        from cryptography.hazmat.primitives import serialization
        
        key_path = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH')
        if not key_path:
            print("❌ No private key path specified")
            return False
            
        if not os.path.exists(key_path):
            print(f"❌ Private key file not found: {key_path}")
            return False
        
        with open(key_path, 'rb') as key_file:
            private_key_data = key_file.read()
        
        # Try to load the private key
        passphrase = os.getenv('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE')
        if passphrase:
            passphrase = passphrase.encode('utf-8')
        
        private_key = load_pem_private_key(
            private_key_data,
            password=passphrase,
        )
        
        # Serialize for Snowflake
        private_key_der = private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        print("✅ Private key loaded successfully")
        print(f"✅ Key size: {len(private_key_der)} bytes")
        return True
        
    except Exception as e:
        print(f"❌ Failed to load private key: {str(e)}")
        return False

def test_snowflake_connection():
    """Test direct Snowflake connection"""
    print("\n❄️  Testing Snowflake Connection...")
    
    try:
        import snowflake.connector
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        from cryptography.hazmat.primitives import serialization
        
        # Load private key
        key_path = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH')
        with open(key_path, 'rb') as key_file:
            private_key_data = key_file.read()
        
        passphrase = os.getenv('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE')
        if passphrase:
            passphrase = passphrase.encode('utf-8')
        
        private_key = load_pem_private_key(
            private_key_data,
            password=passphrase,
        )
        
        private_key_der = private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Test connection
        conn = snowflake.connector.connect(
            user=os.getenv('SNOWFLAKE_USER'),
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
            database=os.getenv('SNOWFLAKE_DATABASE'),
            schema=os.getenv('SNOWFLAKE_SCHEMA'),
            private_key=private_key_der
        )
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_VERSION()")
        result = cursor.fetchone()
        
        print(f"✅ Connection successful!")
        print(f"✅ Snowflake version: {result[0]}")
        
        # Test a simple query
        cursor.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE(), CURRENT_SCHEMA()")
        result = cursor.fetchone()
        print(f"✅ User: {result[0]}")
        print(f"✅ Role: {result[1]}")
        print(f"✅ Database: {result[2]}")
        print(f"✅ Schema: {result[3]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

def test_sqlalchemy_connection():
    """Test SQLAlchemy connection"""
    print("\n🔗 Testing SQLAlchemy Connection...")
    
    try:
        from app.db.snowflake_connection import SnowflakeConnection
        
        # Try to create connection
        sf_conn = SnowflakeConnection()
        
        # Test query
        result = sf_conn.execute_query("SELECT CURRENT_VERSION()")
        print(f"✅ SQLAlchemy connection successful!")
        print(f"✅ Query result: {result.iloc[0, 0] if not result.empty else 'No result'}")
        
        return True
        
    except Exception as e:
        print(f"❌ SQLAlchemy connection failed: {str(e)}")
        return False

def main():
    print("🤖 WOPS AI - Snowflake Connection Diagnostic")
    print("=" * 50)
    
    # Test environment
    test_environment()
    
    # Test private key
    if test_private_key():
        # Test direct connection
        if test_snowflake_connection():
            # Test SQLAlchemy connection
            test_sqlalchemy_connection()
    
    print("\n" + "=" * 50)
    print("🏁 Diagnostic Complete!")

if __name__ == "__main__":
    main()