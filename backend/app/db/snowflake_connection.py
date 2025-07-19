import snowflake.connector
from snowflake.sqlalchemy import URL
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd
from typing import Dict, Any, List, Optional
from ..core.config import settings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import logging
import os

logger = logging.getLogger(__name__)


class SnowflakeConnection:
    def __init__(self):
        self.connection_params = {
            'account': settings.snowflake_account,
            'user': settings.snowflake_user,
            'warehouse': settings.snowflake_warehouse,
            'database': settings.snowflake_database,
            'schema': settings.snowflake_schema
        }
        
        # Add private key authentication if configured
        if settings.snowflake_private_key_path:
            private_key = self._load_private_key()
            self.connection_params['private_key'] = private_key
        
        self.engine = None
        self.session = None
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
        """Initialize SQLAlchemy engine for Snowflake"""
        try:
            # Create connection parameters for SQLAlchemy
            connection_params = {
                'account': self.connection_params['account'],
                'user': self.connection_params['user'],
                'database': self.connection_params['database'],
                'schema': self.connection_params['schema'],
                'warehouse': self.connection_params['warehouse']
            }
            
            # Add private key if available
            if 'private_key' in self.connection_params:
                connection_params['private_key'] = self.connection_params['private_key']
            
            engine_url = URL(**connection_params)
            
            # Add connection arguments for snowflake-sqlalchemy
            connect_args = {}
            if 'private_key' in self.connection_params:
                connect_args['private_key'] = self.connection_params['private_key']
            
            self.engine = create_engine(engine_url, connect_args=connect_args)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            
            logger.info("Snowflake connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Snowflake connection: {str(e)}")
            raise
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame"""
        try:
            if params:
                result = self.session.execute(text(query), params)
            else:
                result = self.session.execute(text(query))
            
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, str]]:
        """Get schema information for a table"""
        try:
            query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                comment
            FROM information_schema.columns 
            WHERE table_name = :table_name
            AND table_schema = :schema_name
            ORDER BY ordinal_position
            """
            
            result = self.session.execute(
                text(query), 
                {'table_name': table_name.upper(), 'schema_name': settings.snowflake_schema}
            )
            
            return [dict(row) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get table schema: {str(e)}")
            raise
    
    def get_available_tables(self) -> List[str]:
        """Get list of available tables in the current schema"""
        try:
            query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = :schema_name
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
            
            result = self.session.execute(
                text(query), 
                {'schema_name': settings.snowflake_schema}
            )
            
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get available tables: {str(e)}")
            raise
    
    def get_table_sample(self, table_name: str, limit: int = 10) -> pd.DataFrame:
        """Get a sample of data from a table"""
        try:
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            return self.execute_query(query)
        except Exception as e:
            logger.error(f"Failed to get table sample: {str(e)}")
            raise
    
    def validate_query(self, query: str) -> bool:
        """Validate if a query is safe to execute"""
        # Basic safety checks using word boundaries
        import re
        forbidden_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE']
        query_upper = query.upper()
        
        for keyword in forbidden_keywords:
            # Use word boundary regex to match whole words only
            if re.search(r'\b' + keyword + r'\b', query_upper):
                return False
        
        return True
    
    def close(self):
        """Close the database connection"""
        if self.session:
            self.session.close()
        if self.engine:
            self.engine.dispose()


class SnowflakeQueryBuilder:
    """Helper class to build safe Snowflake queries"""
    
    def __init__(self, connection: SnowflakeConnection):
        self.connection = connection
    
    def build_analytics_query(self, table_name: str, metrics: List[str], 
                            dimensions: List[str], filters: Optional[Dict[str, Any]] = None,
                            date_range: Optional[Dict[str, str]] = None) -> str:
        """Build an analytics query with metrics, dimensions, and filters"""
        
        # Build SELECT clause
        select_parts = []
        select_parts.extend(dimensions)
        select_parts.extend(metrics)
        
        select_clause = "SELECT " + ", ".join(select_parts)
        
        # Build FROM clause
        from_clause = f"FROM {table_name}"
        
        # Build WHERE clause
        where_conditions = []
        
        if filters:
            for column, value in filters.items():
                if isinstance(value, str):
                    where_conditions.append(f"{column} = '{value}'")
                else:
                    where_conditions.append(f"{column} = {value}")
        
        if date_range:
            if 'start_date' in date_range:
                where_conditions.append(f"date_column >= '{date_range['start_date']}'")
            if 'end_date' in date_range:
                where_conditions.append(f"date_column <= '{date_range['end_date']}'")
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Build GROUP BY clause
        group_by_clause = ""
        if dimensions:
            group_by_clause = "GROUP BY " + ", ".join(dimensions)
        
        # Combine all parts
        query = " ".join([select_clause, from_clause, where_clause, group_by_clause])
        
        return query
    
    def build_trend_query(self, table_name: str, metric: str, time_dimension: str,
                         period: str = "daily", filters: Optional[Dict[str, Any]] = None) -> str:
        """Build a trend analysis query"""
        
        # Time grouping based on period
        time_group_map = {
            "daily": f"DATE_TRUNC('day', {time_dimension})",
            "weekly": f"DATE_TRUNC('week', {time_dimension})",
            "monthly": f"DATE_TRUNC('month', {time_dimension})",
            "yearly": f"DATE_TRUNC('year', {time_dimension})"
        }
        
        time_group = time_group_map.get(period, time_group_map["daily"])
        
        select_clause = f"SELECT {time_group} as time_period, {metric}"
        from_clause = f"FROM {table_name}"
        
        where_conditions = []
        if filters:
            for column, value in filters.items():
                if isinstance(value, str):
                    where_conditions.append(f"{column} = '{value}'")
                else:
                    where_conditions.append(f"{column} = {value}")
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        group_by_clause = f"GROUP BY {time_group}"
        order_by_clause = f"ORDER BY time_period"
        
        query = " ".join([select_clause, from_clause, where_clause, group_by_clause, order_by_clause])
        
        return query


# Global instance
snowflake_db = SnowflakeConnection()