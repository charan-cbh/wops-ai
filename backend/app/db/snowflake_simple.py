import snowflake.connector
import pandas as pd
from typing import Dict, Any, List, Optional
from ..core.config import settings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import logging
import os
import time
from dotenv import load_dotenv

# Force reload .env to override system variables
load_dotenv(override=True)

logger = logging.getLogger(__name__)

class SimpleSnowflakeConnection:
    """Simplified Snowflake connection using direct connector (no SQLAlchemy)"""
    
    def __init__(self):
        # Debug logging
        logger.info(f"Initializing Snowflake connection...")
        logger.info(f"Account: {settings.snowflake_account}")
        logger.info(f"User: {settings.snowflake_user}")
        logger.info(f"Database: {settings.snowflake_database}")
        logger.info(f"Schema: {settings.snowflake_schema}")
        logger.info(f"Warehouse: {settings.snowflake_warehouse}")
        
        # Check for required settings
        if not settings.snowflake_user:
            logger.error("SNOWFLAKE_USER is empty!")
            raise ValueError("SNOWFLAKE_USER is required but empty")
        
        if not settings.snowflake_account:
            logger.error("SNOWFLAKE_ACCOUNT is empty!")
            raise ValueError("SNOWFLAKE_ACCOUNT is required but empty")
        
        self.connection_params = {
            'account': settings.snowflake_account,
            'user': settings.snowflake_user,
            'warehouse': settings.snowflake_warehouse,
            'database': settings.snowflake_database,
            'schema': settings.snowflake_schema,
            'insecure_mode': True  # Skip SSL certificate validation
        }
        
        # Add private key authentication if configured
        if settings.snowflake_private_key_path:
            private_key = self._load_private_key()
            self.connection_params['private_key'] = private_key
        
        self.connection = None
        
        # Schema and data caching
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._table_list_cache: Optional[List[str]] = None
        self._cache_timestamp: float = 0
        self._cache_ttl: int = 3600  # 1 hour cache TTL
        
        self._initialize_connection()
    
    def _load_private_key(self):
        """Load the private key for Snowflake authentication"""
        try:
            # Check if file exists
            if not os.path.exists(settings.snowflake_private_key_path):
                raise FileNotFoundError(f"Private key file not found: {settings.snowflake_private_key_path}")
            
            with open(settings.snowflake_private_key_path, 'rb') as key_file:
                private_key_data = key_file.read()
            
            # Load the private key with optional passphrase
            passphrase = settings.snowflake_private_key_passphrase
            if passphrase:
                passphrase = passphrase.encode('utf-8')
            
            private_key = load_pem_private_key(
                private_key_data,
                password=passphrase,
            )
            
            # Serialize the private key to DER format for Snowflake
            private_key_der = private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            return private_key_der
            
        except Exception as e:
            logger.error(f"Failed to load private key: {str(e)}")
            raise
    
    def _initialize_connection(self):
        """Initialize direct Snowflake connection"""
        try:
            self.connection = snowflake.connector.connect(**self.connection_params)
            logger.info("Snowflake connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Snowflake connection: {str(e)}")
            raise
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        return (time.time() - self._cache_timestamp) < self._cache_ttl
    
    def _invalidate_cache(self):
        """Invalidate all caches"""
        logger.info("Invalidating schema cache")
        self._schema_cache.clear()
        self._table_list_cache = None
        self._cache_timestamp = 0
    
    def _update_cache_timestamp(self):
        """Update cache timestamp"""
        self._cache_timestamp = time.time()
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame with 200 row limit"""
        try:
            # Add LIMIT 200 if not present
            query_upper = query.upper().strip()
            if 'LIMIT' not in query_upper:
                # Remove semicolon if present, add LIMIT, then add semicolon back
                if query.strip().endswith(';'):
                    query = query.strip()[:-1] + ' LIMIT 200;'
                else:
                    query += ' LIMIT 200'
                logger.info("Added LIMIT 200 to query")
            
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            
            # Fetch all results
            results = cursor.fetchall()
            
            # Create DataFrame
            df = pd.DataFrame(results, columns=columns)
            cursor.close()
            
            logger.info(f"Query executed successfully, returned {len(df)} rows")
            return df
            
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def get_available_tables(self) -> List[str]:
        """Get list of available tables - restricted to specific Worker Operations tables with caching"""
        # Check cache first
        if self._table_list_cache is not None and self._is_cache_valid():
            logger.info("Returning cached table list")
            return self._table_list_cache
        
        # Only return the 6 tables specified by the user
        allowed_tables = [
            'RPT_WOPS_AGENT_PERFORMANCE',
            'ZENDESK_TICKET_AGENT__HANDLE_TIME',
            'RPT_WOPS_TICKETS',
            'RPT_WOPS_TL_PERFORMANCE', 
            'RPT_AGENT_SCHEDULE_ADHERENCE'
        ]
        
        try:
            logger.info("Fetching and caching table list")
            # Verify these tables exist in the database
            existing_tables = []
            for table in allowed_tables:
                try:
                    # Test if table exists by trying to describe it
                    query = f"SELECT 1 FROM {self.connection_params['database']}.{self.connection_params['schema']}.{table} LIMIT 1"
                    self.execute_query(query)
                    existing_tables.append(table)
                except Exception:
                    logger.warning(f"Table {table} not found or not accessible")
            
            # Cache the result
            self._table_list_cache = existing_tables
            self._update_cache_timestamp()
            
            logger.info(f"Available tables cached: {existing_tables}")
            return existing_tables
            
        except Exception as e:
            logger.error(f"Failed to get available tables: {str(e)}")
            # Return the allowed tables list even if verification fails
            return allowed_tables
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get schema information for a table with caching"""
        # Check cache first
        if table_name in self._schema_cache and self._is_cache_valid():
            logger.info(f"Returning cached schema for {table_name}")
            return self._schema_cache[table_name]
        
        try:
            logger.info(f"Fetching and caching schema for {table_name}")
            # Use DESCRIBE TABLE which is more reliable
            query = f"DESCRIBE TABLE {self.connection_params['database']}.{self.connection_params['schema']}.{table_name}"
            
            # Execute query directly without adding LIMIT
            cursor = self.connection.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            results = cursor.fetchall()
            df = pd.DataFrame(results, columns=columns)
            cursor.close()
            
            schema = {}
            for _, row in df.iterrows():
                schema[row['name']] = {
                    'type': row['type'],
                    'nullable': row['null?'] == 'Y',
                    'default': row['default']
                }
            
            # Cache the schema
            self._schema_cache[table_name] = schema
            self._update_cache_timestamp()
            
            logger.info(f"Schema cached for {table_name}: {len(schema)} columns")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to get table schema for {table_name}: {str(e)}")
            
            # Fallback: try to get columns from a sample query
            try:
                query = f"SELECT * FROM {self.connection_params['database']}.{self.connection_params['schema']}.{table_name} LIMIT 1"
                cursor = self.connection.cursor()
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                results = cursor.fetchall()
                df = pd.DataFrame(results, columns=columns)
                cursor.close()
                schema = {}
                for col in df.columns:
                    schema[col] = {
                        'type': 'VARCHAR',  # Default type
                        'nullable': True,
                        'default': None
                    }
                
                # Cache the fallback schema too
                self._schema_cache[table_name] = schema
                self._update_cache_timestamp()
                
                logger.info(f"Got schema from sample query for {table_name}: {list(schema.keys())}")
                return schema
            except Exception as e2:
                logger.error(f"Fallback schema query also failed for {table_name}: {str(e2)}")
                return {}
    
    def get_table_sample(self, table_name: str, limit: int = 10) -> pd.DataFrame:
        """Get sample data from a table"""
        try:
            query = f"SELECT * FROM {self.connection_params['database']}.{self.connection_params['schema']}.{table_name} LIMIT {limit}"
            return self.execute_query(query)
            
        except Exception as e:
            logger.error(f"Failed to get table sample: {str(e)}")
            return pd.DataFrame()
    
    def get_table_sample_ordered(self, table_name: str, limit: int = 10) -> pd.DataFrame:
        """Get sample data from a table ordered by audit/timestamp columns for latest data"""
        try:
            # Get table schema to identify audit/timestamp columns
            schema = self.get_table_schema(table_name)
            
            # Common audit/timestamp column patterns to look for
            audit_patterns = [
                'CREATED_AT', 'UPDATED_AT', 'CREATED_DATE', 'UPDATED_DATE',
                'TIMESTAMP', 'DATE_CREATED', 'DATE_UPDATED', 'AUDIT_DATE',
                'CREATED_TIME', 'UPDATED_TIME', 'LAST_MODIFIED', 'RECORD_DATE',
                'ETL_TIMESTAMP', 'LOAD_DATE', 'SOLVED_WEEK', 'ADHERENCE_DATE'
            ]
            
            # Find the best audit column
            order_column = None
            for pattern in audit_patterns:
                for col_name in schema.keys():
                    if pattern in col_name.upper():
                        order_column = col_name
                        break
                if order_column:
                    break
            
            # If no specific audit column found, look for any date/timestamp column
            if not order_column:
                for col_name, col_info in schema.items():
                    col_type = col_info.get('type', '').upper()
                    if any(date_type in col_type for date_type in ['DATE', 'TIMESTAMP', 'TIME']):
                        order_column = col_name
                        break
            
            # Build query with ordering
            if order_column:
                query = f"""
                SELECT * FROM {self.connection_params['database']}.{self.connection_params['schema']}.{table_name} 
                ORDER BY {order_column} DESC 
                LIMIT {limit}
                """
                logger.info(f"Ordering {table_name} by {order_column} DESC for latest data")
            else:
                # Fallback to regular sample if no audit column found
                query = f"SELECT * FROM {self.connection_params['database']}.{self.connection_params['schema']}.{table_name} LIMIT {limit}"
                logger.info(f"No audit column found for {table_name}, using regular sample")
            
            return self.execute_query(query)
            
        except Exception as e:
            logger.error(f"Failed to get ordered table sample: {str(e)}")
            # Fallback to regular sample
            return self.get_table_sample(table_name, limit)
    
    def test_connection(self) -> bool:
        """Test the connection"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            cursor.close()
            return result[0] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def validate_query(self, query: str) -> bool:
        """Validate that the query is safe to execute"""
        try:
            # Convert to uppercase for checking
            query_upper = query.upper().strip()
            
            logger.info(f"Validating query: {query[:100]}...")
            
            # Allow SELECT queries and CTEs starting with WITH
            if not (query_upper.startswith('SELECT') or query_upper.startswith('WITH')):
                logger.warning(f"Non-SELECT/WITH query rejected: {query}")
                return False
            
            # Check for dangerous keywords (whole words only)
            import re
            dangerous_keywords = ['DELETE', 'DROP', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE']
            for keyword in dangerous_keywords:
                # Use word boundary regex to match whole words only
                if re.search(r'\b' + keyword + r'\b', query_upper):
                    logger.warning(f"Query contains dangerous keyword '{keyword}': {query}")
                    return False
            
            # Add LIMIT if not present
            if 'LIMIT' not in query_upper:
                logger.info("Adding LIMIT 200 to query")
            
            logger.info("Query validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Query validation error: {str(e)}")
            return False
    
    def close(self):
        """Close the connection"""
        if self.connection:
            self.connection.close()


# Create a global instance
simple_snowflake_db = SimpleSnowflakeConnection()