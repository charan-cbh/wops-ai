import pandas as pd
import numpy as np
import re
from typing import Dict, Any, List, Optional
from ..db.snowflake_simple import simple_snowflake_db
from ..db.snowflake_connection import SnowflakeQueryBuilder
from ..core.ai_provider import ai_manager
from .confluence_service import confluence_service
from .file_service import file_service
from .chat_history_service import chat_history_service
import json
import logging

logger = logging.getLogger(__name__)


class BIService:
    def __init__(self):
        self.snowflake_db = simple_snowflake_db
        self.query_builder = SnowflakeQueryBuilder(simple_snowflake_db)
        self.ai_manager = ai_manager
    
    async def process_natural_language_query(self, user_query: str, context: Optional[Dict[str, Any]] = None, conversation_history: Optional[List[Dict[str, str]]] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Process natural language query and return business insights"""
        try:
            # Get or create user session for chat history
            user_session = chat_history_service.get_or_create_user(session_id)
            user_id = user_session["user_id"]
            current_session_id = user_session["session_id"]
            
            # Save user message to chat history
            try:
                chat_history_service.save_message(
                    user_id=user_id,
                    session_id=current_session_id,
                    role="user",
                    content=user_query
                )
            except Exception as e:
                logger.warning(f"Failed to save user message to history: {str(e)}")
            
            # Build enhanced user message with context
            enhanced_query = user_query
            
            # Add dynamic schema information
            tables = self.snowflake_db.get_available_tables()
            schema_info = self._get_dynamic_schema_context(tables)
            enhanced_query += f"\n\nDATABASE SCHEMA INFORMATION:\n{schema_info}"
            
            # Add Confluence context if configured
            if await confluence_service.is_configured():
                confluence_context = await confluence_service.get_context_for_query(user_query)
                if confluence_context:
                    enhanced_query += f"\n\nBusiness context from Confluence:\n{confluence_context}"
            
            # Add file context if provided
            if context and "file_ids" in context:
                file_contexts = []
                for file_id in context["file_ids"]:
                    file_content = await file_service.get_file_content_for_context(file_id)
                    if file_content:
                        file_contexts.append(file_content)
                
                if file_contexts:
                    enhanced_query += f"\n\nAdditional file context:\n" + "\n---\n".join(file_contexts)
            
            # Add additional context if provided
            if context:
                enhanced_query += f"\n\nAdditional context: {json.dumps(context, indent=2)}"
            
            # Use Assistant API with vector store for better context and larger token limit
            logger.info("Using Assistant API with vector store")
            
            # Use Assistant API exclusively - no fallback to chat completions
            ai_response = await self.ai_manager.generate_response_with_assistant(
                user_message=enhanced_query,
                user_id=user_id
            )
            logger.info("Assistant API response received successfully")
            
            # Parse AI response to extract SQL query and explanation
            logger.info(f"Raw AI response: {ai_response.content}")
            result = self._parse_ai_response(ai_response.content)
            logger.info(f"Parsed result: {result}")
            
            # Execute the query if valid
            if result.get("sql_query"):
                logger.info(f"Executing SQL query: {result['sql_query']}")
                query_result = await self._execute_and_analyze_query(result["sql_query"])
                logger.info(f"Query result: {query_result}")
                result.update(query_result)
                
                # Generate charts if appropriate
                if result.get("data") and len(result["data"]) > 0:
                    try:
                        # Convert data to DataFrame for chart generation
                        df = pd.DataFrame(result["data"])
                        
                        # Check if charts would be beneficial
                        if self.should_generate_charts(user_query, df):
                            logger.info("Generating charts for visualization")
                            charts = self.generate_charts_from_data(df, user_query, result.get("insights", []))
                            if charts:
                                result["charts"] = charts
                                logger.info(f"Generated {len(charts)} charts")
                    except Exception as e:
                        logger.warning(f"Error generating charts: {str(e)}")
            else:
                logger.warning("No SQL query found in response")
            
            logger.info(f"Final result: {result}")
            
            # Save assistant response to chat history
            try:
                assistant_message_id = chat_history_service.save_message(
                    user_id=user_id,
                    session_id=current_session_id,
                    role="assistant",
                    content=ai_response.content,
                    query_results=result.get("data"),
                    insights=result.get("insights"),
                    sql_query=result.get("sql_query")
                )
                
                # Add session info to result for frontend
                result["session_info"] = {
                    "user_id": user_id,
                    "session_id": current_session_id,
                    "message_id": assistant_message_id
                }
                
            except Exception as e:
                logger.warning(f"Failed to save assistant response to history: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing natural language query: {str(e)}")
            
            # Try to save error to chat history if we have session info
            try:
                if 'user_id' in locals() and 'current_session_id' in locals():
                    chat_history_service.save_message(
                        user_id=user_id,
                        session_id=current_session_id,
                        role="assistant",
                        content=f"I encountered an error: {str(e)}"
                    )
            except:
                pass  # Don't let history saving errors break the main error handling
            
            return {
                "error": str(e),
                "success": False
            }
    
    def _build_system_prompt(self, tables: List[str]) -> str:
        """Build system prompt with database schema information"""
        
        # Get schema information for key tables
        schema_info = {}
        for table in tables[:3]:  # Limit to first 3 tables to avoid token limit
            try:
                schema = self.snowflake_db.get_table_schema(table)
                # Only keep essential schema info
                schema_info[table] = {k: v.get('type', 'VARCHAR') for k, v in schema.items()}
            except Exception as e:
                logger.warning(f"Could not get schema for table {table}: {str(e)}")
        
        # Get sample data only for key tables with latest data first
        sample_data = {}
        key_tables = ['RPT_AGENT_SCHEDULE_ADHERENCE', 'RPT_WOPS_AGENT_PERFORMANCE']
        for table in key_tables:
            if table in tables:
                try:
                    # Get sample data ordered by audit/timestamp columns for latest data
                    sample_df = self.snowflake_db.get_table_sample_ordered(table, 3)
                    if not sample_df.empty:
                        # Include more relevant columns for better context
                        if table == 'RPT_AGENT_SCHEDULE_ADHERENCE':
                            key_cols = ['AGENT_NAME', 'ADHERENCE_PERCENTAGE', 'ADHERENCE_DATE', 'SCHEDULED_MINUTES', 'ADHERENT_MINUTES']
                        elif table == 'RPT_WOPS_AGENT_PERFORMANCE':
                            key_cols = ['ASSIGNEE_NAME', 'ASSIGNEE_SUPERVISOR', 'SOLVED_WEEK', 'NUM_TICKETS', 'AHT_MINUTES']
                        else:
                            key_cols = list(sample_df.columns)[:6]  # First 6 columns for other tables
                            
                        available_cols = [col for col in key_cols if col in sample_df.columns]
                        if not available_cols:  # If none of the key columns exist, use first few columns
                            available_cols = list(sample_df.columns)[:5]
                        
                        if available_cols:
                            sample_data[table] = sample_df[available_cols].to_dict('records')
                except Exception as e:
                    logger.warning(f"Could not get sample for table {table}: {str(e)}")
                    # Fallback to regular sample if ordered sample fails
                    try:
                        sample_df = self.snowflake_db.get_table_sample_ordered(table, 2)
                        if not sample_df.empty:
                            available_cols = list(sample_df.columns)[:5]
                            sample_data[table] = sample_df[available_cols].to_dict('records')
                    except Exception as e2:
                        logger.warning(f"Fallback sample also failed for table {table}: {str(e2)}")
        
        prompt = f"""
You are a business intelligence assistant for Clipboard Health's Worker Operations team. 
Your role is to help analyze data and provide insights from the Snowflake database.

Available tables: {', '.join(tables)}

Schema (column names and types):
{json.dumps(schema_info, indent=1)}

Sample data examples:
{json.dumps(sample_data, indent=1, default=str)}

CRITICAL: When a user asks a question about data, you MUST:
1. Generate a SELECT query that will be EXECUTED against the database
2. The query will be run and the actual results returned to the user
3. Always provide specific data answers, not just query explanations
4. Only use SELECT statements - no INSERT, UPDATE, DELETE, etc.
5. All queries are automatically limited to 200 rows
6. IMPORTANT: Only use column names that EXACTLY match those in the schema above
7. IMPORTANT: Look at the sample data to understand the actual data format and values
8. If a user asks about a column that doesn't exist, suggest alternatives or explain what's available

For questions about data, generate SQL queries that will retrieve the actual data to answer the question.

KEY TABLES AND COLUMNS:
- RPT_AGENT_SCHEDULE_ADHERENCE: AGENT_NAME, ADHERENCE_PERCENTAGE, SCHEDULED_MINUTES, ADHERENT_MINUTES, ADHERENCE_DATE
- RPT_WOPS_AGENT_PERFORMANCE: ASSIGNEE_NAME, ASSIGNEE_SUPERVISOR, NUM_TICKETS, AHT_MINUTES, FCR_PERCENTAGE, QA_SCORE

IMPORTANT: For joining tables to find agents under supervisors:
- Use ASSIGNEE_NAME from RPT_WOPS_AGENT_PERFORMANCE to match with AGENT_NAME from RPT_AGENT_SCHEDULE_ADHERENCE
- Use ASSIGNEE_SUPERVISOR from RPT_WOPS_AGENT_PERFORMANCE to filter by supervisor

IMPORTANT: For numeric comparisons with ADHERENCE_PERCENTAGE, use TRY_TO_NUMBER() because some values may contain '-' or other non-numeric characters:
- Correct: WHERE TRY_TO_NUMBER(ADHERENCE_PERCENTAGE) >= 90
- Incorrect: WHERE ADHERENCE_PERCENTAGE >= 90

The schema information below shows the exact column names and types for each table.

Response format (JSON):
{{
    "sql_query": "SELECT column_name FROM table_name WHERE condition ORDER BY column_name",
    "explanation": "Clear explanation of what the query does and what results it will return",
    "business_context": "Business context explaining why this analysis is valuable",
    "expected_insights": ["List of key insights the query will provide"]
}}

IMPORTANT: Always provide complete, valid SQL queries that can be executed. Include proper FROM clauses and ensure all column names exist in the schema.

Guidelines:
- Only use SELECT statements (no INSERT, UPDATE, DELETE, DROP)
- Use proper Snowflake SQL syntax
- Include appropriate WHERE clauses and filters
- Use aggregation functions for summary statistics
- Consider time-based analysis for trends
- Focus on Worker Operations metrics like productivity, scheduling, performance

DATE/TIME QUERIES - IMPORTANT:
- For "this week" queries, use simple date comparisons: WHERE date_column >= '2025-07-14' AND date_column < '2025-07-21'
- For "today" queries, use: WHERE date_column = CURRENT_DATE()
- Avoid complex timezone conversions and DATE_TRUNC with timezones
- Keep date filtering simple and straightforward
- If you need current date, use CURRENT_DATE() or GETDATE()

EXAMPLE DATE QUERIES:
- This week: WHERE CREATED_DATE >= '2025-07-14' AND CREATED_DATE < '2025-07-21'
- Last 7 days: WHERE CREATED_DATE >= DATEADD(day, -7, CURRENT_DATE())
- This month: WHERE MONTH(CREATED_DATE) = MONTH(CURRENT_DATE()) AND YEAR(CREATED_DATE) = YEAR(CURRENT_DATE())
"""
        
        return prompt
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response to extract structured information"""
        try:
            # Try to parse as JSON first
            if response.strip().startswith('{'):
                return json.loads(response)
            
            # For assistant responses, extract SQL from code blocks or lines
            sql_query = None
            explanation = []
            
            # Look for SQL in code blocks first
            import re
            sql_blocks = re.findall(r'```sql\s*\n(.*?)\n```', response, re.DOTALL | re.IGNORECASE)
            if sql_blocks:
                sql_query = sql_blocks[0].strip()
            else:
                # Look for SQL queries in the text
                lines = response.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.upper().startswith('SELECT') or line.upper().startswith('WITH'):
                        sql_query = line
                        break
            
            # Use the entire response as explanation
            explanation = response.strip()
            
            return {
                "sql_query": sql_query,
                "explanation": explanation,
                "business_context": "Analysis requested by user",
                "expected_insights": []
            }
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return {
                "explanation": response,
                "business_context": "Analysis requested by user",
                "expected_insights": []
            }
    
    async def _execute_and_analyze_query(self, sql_query: str) -> Dict[str, Any]:
        """Execute SQL query and analyze results"""
        try:
            # Validate query safety
            logger.info(f"About to validate query: {sql_query[:200]}...")
            validation_result = self.snowflake_db.validate_query(sql_query)
            logger.info(f"Query validation result: {validation_result}")
            
            if not validation_result:
                logger.error(f"Query validation failed for: {sql_query}")
                return {
                    "error": "Query contains forbidden operations",
                    "success": False
                }
            
            # Execute query
            df = self.snowflake_db.execute_query(sql_query)
            
            # Clean data for JSON serialization
            df_cleaned = self._clean_dataframe_for_json(df)
            
            # Generate insights from results
            logger.info(f"Generating insights for {len(df_cleaned)} rows")
            try:
                insights = await self._generate_insights_from_data(df_cleaned, sql_query)
                logger.info(f"Generated {len(insights)} insights")
            except Exception as e:
                logger.error(f"Error generating insights: {str(e)}")
                insights = []
            
            return {
                "data": df_cleaned.to_dict('records'),
                "row_count": len(df_cleaned),
                "columns": df_cleaned.columns.tolist(),
                "insights": insights,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            return {
                "error": str(e),
                "success": False
            }
    
    def _clean_dataframe_for_json(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean DataFrame to ensure JSON serialization compatibility"""
        import numpy as np
        
        # Create a copy to avoid modifying original
        df_cleaned = df.copy()
        
        # Replace NaN, infinity, and other non-JSON-compliant values
        df_cleaned = df_cleaned.replace([np.inf, -np.inf], np.nan)
        
        # Convert all columns to JSON-safe types
        for col in df_cleaned.columns:
            if df_cleaned[col].dtype == 'object':
                # Convert to string and replace nan with None
                df_cleaned[col] = df_cleaned[col].astype(str).replace('nan', None)
            elif np.issubdtype(df_cleaned[col].dtype, np.integer):
                # Convert to regular int, handling NaN
                df_cleaned[col] = df_cleaned[col].astype('Int64')
            elif np.issubdtype(df_cleaned[col].dtype, np.floating):
                # Convert to regular float, handling NaN
                df_cleaned[col] = df_cleaned[col].astype('Float64')
        
        # Final pass to replace any remaining NaN values
        df_cleaned = df_cleaned.where(pd.notnull(df_cleaned), None)
        
        return df_cleaned
    
    async def _generate_insights_from_data(self, df: pd.DataFrame, sql_query: str) -> List[str]:
        """Generate business insights from query results"""
        try:
            # Prepare data summary for AI
            data_summary = {
                "row_count": len(df),
                "columns": df.columns.tolist(),
                "sample_data": df.head(5).to_dict('records') if len(df) > 0 else [],
                "data_types": df.dtypes.to_dict(),
                "null_counts": df.isnull().sum().to_dict()
            }
            
            # Add basic statistics for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                data_summary["numeric_statistics"] = df[numeric_cols].describe().to_dict()
            
            # Build prompt for insight generation
            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_year = datetime.now().year
            current_month = datetime.now().strftime("%B")
            
            insight_prompt = f"""
CURRENT DATE: {current_date} (Today's date is {current_date}, current year is {current_year}, current month is {current_month})

Based on the following query results, provide 3-5 TLDR-style bullet points as the direct answer:

SQL Query: {sql_query}
Data Summary: {json.dumps(data_summary, indent=2, default=str)}

CRITICAL REQUIREMENTS:
- Each point is the direct answer to the user's question
- Maximum 20 words per bullet point
- Start with the actual number/metric
- No fluff words like "indicates" or "suggests"
- If a finding is complex, break it into multiple simple points
- Focus on WHAT the data shows, not WHY it matters
- Use current date context when interpreting time references

Format like a TLDR summary:
- "291 agents have 95%+ adherence"
- "This represents 68% of total workforce"
- "Top performer: John Smith with 99% adherence"

Return ONLY a JSON array of direct answer points.
"""
            
            # Use Assistant API for insight generation too
            ai_response = await self.ai_manager.generate_response_with_assistant(
                user_message=insight_prompt,
                user_id="insight_generation"  # Special user ID for insight generation
            )
            
            # Parse insights from AI response
            try:
                # First try direct JSON parsing
                insights = json.loads(ai_response.content)
                if isinstance(insights, list):
                    return insights
                elif isinstance(insights, dict) and 'insights' in insights:
                    return insights['insights'] if isinstance(insights['insights'], list) else [str(insights['insights'])]
                else:
                    return [str(insights)]
            except json.JSONDecodeError:
                # Try to extract JSON array from the response text
                import re
                # Look for JSON array patterns
                array_match = re.search(r'\[[\s\S]*?\]', ai_response.content)
                if array_match:
                    try:
                        insights = json.loads(array_match.group(0))
                        return insights if isinstance(insights, list) else [ai_response.content]
                    except json.JSONDecodeError:
                        pass
                
                # If no JSON found, return the content as a single insight
                return [ai_response.content]
                
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return ["Unable to generate insights from the data"]
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get key metrics for the dashboard"""
        try:
            # This would be customized based on your specific Worker Operations metrics
            metrics = {}
            
            # Example queries - replace with actual business metrics
            tables = self.snowflake_db.get_available_tables()
            
            if tables:
                # Get basic counts and recent activity
                for table in tables[:3]:  # Limit to avoid performance issues
                    try:
                        sample_df = self.snowflake_db.get_table_sample_ordered(table, 5)
                        metrics[f"{table}_sample_count"] = len(sample_df)
                        metrics[f"{table}_columns"] = sample_df.columns.tolist()
                    except Exception as e:
                        logger.warning(f"Could not get metrics for table {table}: {str(e)}")
            
            return {
                "metrics": metrics,
                "available_tables": tables,
                "last_updated": pd.Timestamp.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {str(e)}")
            return {"error": str(e)}
    
    def _get_dynamic_schema_context(self, tables: List[str]) -> str:
        """Generate dynamic schema context from database metadata"""
        try:
            schema_info = []
            
            # Focus on key tables for Worker Operations
            priority_tables = [
                'RPT_AGENT_SCHEDULE_ADHERENCE', 
                'RPT_WOPS_AGENT_PERFORMANCE',
                'RPT_AGENT_METRICS',
                'RPT_SCHEDULE_DATA'
            ]
            
            # Process priority tables first, then others
            ordered_tables = []
            for table in priority_tables:
                if table in tables:
                    ordered_tables.append(table)
            
            # Add remaining tables (limited to avoid token overflow)
            for table in tables:
                if table not in ordered_tables and len(ordered_tables) < 5:
                    ordered_tables.append(table)
            
            for table in ordered_tables:
                try:
                    # Get table schema
                    schema = self.snowflake_db.get_table_schema(table)
                    
                    if schema:
                        # Build column info with types and special notes
                        columns_info = []
                        for col_name, col_info in schema.items():
                            col_type = col_info.get('type', 'VARCHAR')
                            
                            # Add special notes for key columns
                            notes = []
                            if 'ADHERENCE_PERCENTAGE' in col_name.upper():
                                notes.append("use TRY_TO_NUMBER() - may contain '-'")
                            elif 'DATE' in col_name.upper():
                                notes.append("date column")
                            elif 'SUPERVISOR' in col_name.upper():
                                notes.append("for filtering by supervisor")
                            elif col_name.upper() in ['AGENT_NAME', 'ASSIGNEE_NAME']:
                                notes.append("for joining tables")
                            
                            col_desc = f"{col_name} ({col_type})"
                            if notes:
                                col_desc += f" - {', '.join(notes)}"
                            
                            columns_info.append(col_desc)
                        
                        # Add table info to schema context - include ALL columns
                        table_context = f"- {table}: {', '.join(columns_info)}"
                        schema_info.append(table_context)
                        
                except Exception as e:
                    logger.warning(f"Could not get schema for table {table}: {str(e)}")
                    # Add basic info if schema fetch fails
                    schema_info.append(f"- {table}: Schema not available")
            
            # Add important join information
            join_info = """

KEY RELATIONSHIPS:
- Join tables using: RPT_AGENT_SCHEDULE_ADHERENCE.AGENT_NAME = RPT_WOPS_AGENT_PERFORMANCE.ASSIGNEE_NAME
- Filter by supervisor: Use ASSIGNEE_SUPERVISOR column in RPT_WOPS_AGENT_PERFORMANCE (no JOIN needed)
- For date filtering: Use appropriate date columns (ADHERENCE_DATE, SOLVED_WEEK, etc.)

CRITICAL SEARCH RULES:
- ALWAYS use LIKE or ILIKE for name searches, NEVER exact equals (=)
- For agent names: WHERE AGENT_NAME ILIKE '%John%' (not WHERE AGENT_NAME = 'John')
- For supervisors: WHERE ASSIGNEE_SUPERVISOR ILIKE '%Kim%' (not WHERE ASSIGNEE_SUPERVISOR = 'Kim')
- Use % wildcards before and after search terms to catch partial matches
- ILIKE is case-insensitive, LIKE is case-sensitive - prefer ILIKE for names

IMPORTANT NOTES:
- ADHERENCE_PERCENTAGE may contain '-' or text, always use TRY_TO_NUMBER() for numeric operations
- When filtering by supervisor, use ASSIGNEE_SUPERVISOR directly - no JOIN required
- All date columns should be filtered appropriately for time-based analysis
- Names in database may be full names while users provide nicknames/short names"""
            
            return '\n'.join(schema_info) + join_info
            
        except Exception as e:
            logger.error(f"Error generating dynamic schema context: {str(e)}")
            # Fallback to minimal schema info
            return """- RPT_AGENT_SCHEDULE_ADHERENCE: AGENT_NAME, ADHERENCE_PERCENTAGE (use TRY_TO_NUMBER), ADHERENCE_DATE
- RPT_WOPS_AGENT_PERFORMANCE: ASSIGNEE_NAME, ASSIGNEE_SUPERVISOR, NUM_TICKETS
Join: AGENT_NAME = ASSIGNEE_NAME"""
    
    def get_available_analyses(self) -> List[Dict[str, str]]:
        """Get list of available pre-built analyses"""
        return [
            {
                "name": "Worker Productivity Trends",
                "description": "Analyze productivity metrics over time",
                "category": "productivity"
            },
            {
                "name": "Scheduling Efficiency",
                "description": "Review scheduling patterns and efficiency metrics",
                "category": "scheduling"
            },
            {
                "name": "Performance Metrics",
                "description": "Worker performance analysis and benchmarking",
                "category": "performance"
            },
            {
                "name": "Operational Costs",
                "description": "Cost analysis and optimization opportunities",
                "category": "finance"
            },
            {
                "name": "Regional Analysis",
                "description": "Geographic performance and regional trends",
                "category": "geography"
            }
        ]
    
    def should_generate_charts(self, user_query: str, data: pd.DataFrame) -> bool:
        """Determine if the query would benefit from visual charts"""
        if data.empty or len(data) < 2:
            return False
            
        # Keywords that suggest visualization would be helpful
        chart_keywords = [
            'trend', 'trends', 'trending', 'over time', 'timeline',
            'compare', 'comparison', 'versus', 'vs', 'against',
            'top', 'bottom', 'highest', 'lowest', 'best', 'worst',
            'distribution', 'breakdown', 'split', 'by',
            'chart', 'graph', 'plot', 'visualize', 'show',
            'performance', 'productivity', 'efficiency',
            'weekly', 'monthly', 'daily', 'quarterly',
            'growth', 'decline', 'increase', 'decrease'
        ]
        
        query_lower = user_query.lower()
        has_chart_keywords = any(keyword in query_lower for keyword in chart_keywords)
        
        # Check if data has numeric columns suitable for charting
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        has_numeric_data = len(numeric_columns) > 0
        
        # Check if data has categorical/time columns for grouping
        has_groupable_data = len(data.columns) >= 2
        
        return has_chart_keywords and has_numeric_data and has_groupable_data
    
    def generate_charts_from_data(self, data: pd.DataFrame, query: str, insights: List[str]) -> List[Dict[str, Any]]:
        """Generate appropriate charts based on the data and query context"""
        if data.empty:
            return []
            
        charts = []
        
        try:
            # Limit data size for performance
            if len(data) > 50:
                data_sample = data.head(50)
            else:
                data_sample = data.copy()
            
            numeric_columns = data_sample.select_dtypes(include=[np.number]).columns.tolist()
            categorical_columns = data_sample.select_dtypes(include=['object']).columns.tolist()
            
            # Generate different chart types based on data structure
            charts.extend(self._generate_trend_charts(data_sample, numeric_columns, categorical_columns, query))
            charts.extend(self._generate_comparison_charts(data_sample, numeric_columns, categorical_columns, query))
            charts.extend(self._generate_distribution_charts(data_sample, numeric_columns, categorical_columns, query))
            
            # Limit to 3 charts maximum to avoid overwhelming the user
            return charts[:3]
            
        except Exception as e:
            logger.error(f"Error generating charts: {str(e)}")
            return []
    
    def _generate_trend_charts(self, data: pd.DataFrame, numeric_cols: List[str], categorical_cols: List[str], query: str) -> List[Dict[str, Any]]:
        """Generate line charts for trend analysis"""
        charts = []
        
        # Look for date/time columns
        date_columns = [col for col in data.columns if any(date_word in col.upper() for date_word in ['DATE', 'TIME', 'WEEK', 'MONTH', 'DAY'])]
        
        if date_columns and numeric_cols:
            date_col = date_columns[0]
            
            for numeric_col in numeric_cols[:2]:  # Limit to 2 metrics
                try:
                    # Sort by date and aggregate if needed
                    trend_data = data.groupby(date_col)[numeric_col].mean().reset_index()
                    
                    if len(trend_data) >= 2:
                        chart_data = {
                            "type": "line",
                            "title": f"{numeric_col} Trend Over Time",
                            "data": {
                                "labels": [str(x) for x in trend_data[date_col].tolist()],
                                "datasets": [{
                                    "label": numeric_col,
                                    "data": trend_data[numeric_col].tolist()
                                }]
                            }
                        }
                        charts.append(chart_data)
                        
                except Exception as e:
                    logger.warning(f"Error generating trend chart for {numeric_col}: {str(e)}")
                    
        return charts
    
    def _generate_comparison_charts(self, data: pd.DataFrame, numeric_cols: List[str], categorical_cols: List[str], query: str) -> List[Dict[str, Any]]:
        """Generate bar charts for comparisons"""
        charts = []
        
        if categorical_cols and numeric_cols:
            cat_col = categorical_cols[0]
            
            for numeric_col in numeric_cols[:2]:  # Limit to 2 metrics
                try:
                    # Group by categorical column and aggregate
                    comparison_data = data.groupby(cat_col)[numeric_col].mean().reset_index()
                    
                    # Sort by value for better visualization
                    comparison_data = comparison_data.sort_values(numeric_col, ascending=False)
                    
                    # Limit to top 10 categories
                    if len(comparison_data) > 10:
                        comparison_data = comparison_data.head(10)
                    
                    if len(comparison_data) >= 2:
                        chart_data = {
                            "type": "bar",
                            "title": f"{numeric_col} by {cat_col}",
                            "data": {
                                "labels": comparison_data[cat_col].tolist(),
                                "datasets": [{
                                    "label": numeric_col,
                                    "data": comparison_data[numeric_col].tolist()
                                }]
                            }
                        }
                        charts.append(chart_data)
                        
                except Exception as e:
                    logger.warning(f"Error generating comparison chart for {numeric_col}: {str(e)}")
                    
        return charts
    
    def _generate_distribution_charts(self, data: pd.DataFrame, numeric_cols: List[str], categorical_cols: List[str], query: str) -> List[Dict[str, Any]]:
        """Generate pie/doughnut charts for distributions"""
        charts = []
        
        if categorical_cols and len(data) <= 20:  # Only for smaller datasets
            cat_col = categorical_cols[0]
            
            try:
                # Count occurrences of each category
                distribution_data = data[cat_col].value_counts().head(8)  # Top 8 categories
                
                if len(distribution_data) >= 2:
                    chart_data = {
                        "type": "doughnut",
                        "title": f"Distribution by {cat_col}",
                        "data": {
                            "labels": distribution_data.index.tolist(),
                            "datasets": [{
                                "label": "Count",
                                "data": distribution_data.values.tolist()
                            }]
                        }
                    }
                    charts.append(chart_data)
                    
            except Exception as e:
                logger.warning(f"Error generating distribution chart for {cat_col}: {str(e)}")
                
        return charts


# Global instance
bi_service = BIService()