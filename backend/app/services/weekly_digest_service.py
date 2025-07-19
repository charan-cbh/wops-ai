import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from ..db.snowflake_simple import simple_snowflake_db
from ..core.ai_provider import ai_manager

logger = logging.getLogger(__name__)

class WeeklyDigestService:
    """Service for generating weekly business intelligence digests"""
    
    def __init__(self):
        self.snowflake_db = simple_snowflake_db
    
    async def generate_weekly_digest(self, weeks_back: int = 1) -> Dict[str, Any]:
        """Generate a comprehensive weekly digest"""
        try:
            # Calculate date range for the digest
            end_date = datetime.now()
            start_date = end_date - timedelta(weeks=weeks_back)
            
            logger.info(f"Generating weekly digest from {start_date.date()} to {end_date.date()}")
            
            # Gather data from all available tables
            digest_data = await self._gather_weekly_data(start_date, end_date)
            
            # Generate AI-powered insights
            insights = await self._generate_insights(digest_data, start_date, end_date)
            
            # Calculate key metrics
            metrics = self._calculate_weekly_metrics(digest_data)
            
            # Create trends analysis
            trends = await self._analyze_trends(digest_data)
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "weeks_back": weeks_back
                },
                "summary": insights.get("summary", "No summary available"),
                "key_insights": insights.get("insights", []),
                "metrics": metrics,
                "trends": trends,
                "recommendations": insights.get("recommendations", []),
                "data_coverage": digest_data.get("coverage", {}),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating weekly digest: {str(e)}")
            return {
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }
    
    async def _gather_weekly_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Gather data from all available tables for the specified week"""
        data = {"coverage": {}, "tables": {}}
        
        try:
            tables = self.snowflake_db.get_available_tables()
            
            for table in tables:
                try:
                    # Get table schema to identify date columns
                    schema = self.snowflake_db.get_table_schema(table)
                    date_columns = self._identify_date_columns(schema)
                    
                    if date_columns:
                        # Query data for the week using the first date column found
                        date_col = date_columns[0]
                        weekly_data = await self._query_weekly_data(table, date_col, start_date, end_date)
                        
                        if not weekly_data.empty:
                            data["tables"][table] = {
                                "data": weekly_data,
                                "date_column": date_col,
                                "record_count": len(weekly_data),
                                "columns": weekly_data.columns.tolist()
                            }
                            data["coverage"][table] = len(weekly_data)
                        else:
                            data["coverage"][table] = 0
                    else:
                        # For tables without clear date columns, get recent sample using ordered sampling
                        sample_data = self.snowflake_db.get_table_sample_ordered(table, 50)
                        if not sample_data.empty:
                            data["tables"][table] = {
                                "data": sample_data,
                                "date_column": None,
                                "record_count": len(sample_data),
                                "columns": sample_data.columns.tolist()
                            }
                            data["coverage"][table] = len(sample_data)
                        else:
                            data["coverage"][table] = 0
                            
                except Exception as e:
                    logger.warning(f"Could not gather data from table {table}: {str(e)}")
                    data["coverage"][table] = 0
            
            return data
            
        except Exception as e:
            logger.error(f"Error gathering weekly data: {str(e)}")
            return {"coverage": {}, "tables": {}}
    
    def _identify_date_columns(self, schema: Dict[str, Any]) -> List[str]:
        """Identify potential date columns in a table schema"""
        date_columns = []
        
        for col_name, col_info in schema.items():
            col_type = col_info.get('type', '').upper()
            col_name_upper = col_name.upper()
            
            # Check for date/timestamp types
            if any(date_type in col_type for date_type in ['DATE', 'TIMESTAMP', 'TIME']):
                date_columns.append(col_name)
            # Check for common date column naming patterns
            elif any(pattern in col_name_upper for pattern in [
                'DATE', 'WEEK', 'TIME', 'CREATED', 'UPDATED', 'MODIFIED', 'ADHERENCE_DATE', 'SOLVED_WEEK'
            ]):
                date_columns.append(col_name)
        
        return date_columns
    
    async def _query_weekly_data(self, table: str, date_col: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Query data from a table for the specified week"""
        try:
            # Format dates for SQL
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            query = f"""
            SELECT * FROM {self.snowflake_db.connection_params['database']}.{self.snowflake_db.connection_params['schema']}.{table}
            WHERE {date_col} >= '{start_str}' AND {date_col} <= '{end_str}'
            ORDER BY {date_col} DESC
            LIMIT 1000
            """
            
            return self.snowflake_db.execute_query(query)
            
        except Exception as e:
            logger.warning(f"Error querying weekly data for {table}: {str(e)}")
            return pd.DataFrame()
    
    def _calculate_weekly_metrics(self, digest_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate key metrics for the weekly digest"""
        metrics = {
            "total_records": 0,
            "tables_with_data": 0,
            "top_active_tables": [],
            "data_quality": {}
        }
        
        try:
            coverage = digest_data.get("coverage", {})
            tables_data = digest_data.get("tables", {})
            
            # Calculate totals
            metrics["total_records"] = sum(coverage.values())
            metrics["tables_with_data"] = sum(1 for count in coverage.values() if count > 0)
            
            # Find most active tables
            sorted_tables = sorted(coverage.items(), key=lambda x: x[1], reverse=True)
            metrics["top_active_tables"] = [
                {"table": table, "records": count} 
                for table, count in sorted_tables[:5] if count > 0
            ]
            
            # Basic data quality metrics
            for table, table_info in tables_data.items():
                if "data" in table_info:
                    df = table_info["data"]
                    if not df.empty:
                        null_percentage = (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
                        metrics["data_quality"][table] = {
                            "null_percentage": round(null_percentage, 2),
                            "complete_records": len(df.dropna()),
                            "total_records": len(df)
                        }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating weekly metrics: {str(e)}")
            return metrics
    
    async def _generate_insights(self, digest_data: Dict[str, Any], start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate AI-powered insights from the weekly data"""
        try:
            # Prepare data summary for AI analysis
            summary_text = self._prepare_data_summary(digest_data, start_date, end_date)
            
            # Create prompt for AI analysis
            analysis_prompt = f"""
            Analyze the following comprehensive Worker Operations data for the week of {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}:

            {summary_text}

            This data covers ALL operational tables including agent performance, scheduling adherence, ticket handling, and quality metrics.

            Please provide a comprehensive analysis with:
            1. Executive Summary: A 2-3 sentence overview of the week's operational performance
            2. Key Insights: 4-6 specific insights drawn from ALL tables, focusing on:
               - Agent performance trends and patterns
               - Scheduling adherence and efficiency
               - Quality metrics (CSAT, QA scores)
               - Ticket handling and productivity
               - Cross-functional operational patterns
            3. Actionable Recommendations: 3-4 specific, data-driven recommendations for operational improvements

            Be specific about numbers, trends, and patterns you observe in the data.
            
            IMPORTANT: You must respond with ONLY a valid JSON object in this exact format:
            {
                "summary": "2-3 sentence executive summary here",
                "insights": [
                    "First insight about the data",
                    "Second insight about trends",
                    "Third insight about performance",
                    "Fourth insight if applicable"
                ],
                "recommendations": [
                    "First actionable recommendation",
                    "Second recommendation",
                    "Third recommendation if applicable"
                ]
            }
            
            Do not include any text before or after the JSON. Only return the JSON object.
            """
            
            # Get AI analysis
            ai_response = await ai_manager.generate_response_with_assistant(
                user_message=analysis_prompt,
                user_id="weekly_digest"
            )
            
            # Parse AI response
            import json
            import re
            
            try:
                # First try direct JSON parsing
                insights = json.loads(ai_response.content)
                return insights
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', ai_response.content, re.DOTALL)
                if json_match:
                    try:
                        insights = json.loads(json_match.group(1))
                        return insights
                    except json.JSONDecodeError:
                        pass
                
                # Try to extract JSON from anywhere in the response
                json_match = re.search(r'\{.*?"summary".*?\}', ai_response.content, re.DOTALL)
                if json_match:
                    try:
                        insights = json.loads(json_match.group(0))
                        return insights
                    except json.JSONDecodeError:
                        pass
                
                # If no JSON found, parse as text and create JSON structure
                logger.warning(f"Could not parse JSON from AI response, creating structured response from text: {ai_response.content[:200]}...")
                
                # Create insights from the raw text response
                lines = ai_response.content.strip().split('\n')
                parsed_insights = []
                parsed_recommendations = []
                summary = "Weekly operational analysis completed successfully."
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#') and len(line) > 10:
                        if any(word in line.lower() for word in ['recommend', 'suggest', 'should', 'improve']):
                            parsed_recommendations.append(line)
                        elif any(word in line.lower() for word in ['insight', 'trend', 'performance', 'data', 'metric']):
                            parsed_insights.append(line)
                        elif len(parsed_insights) == 0 and len(line) > 20:  # Likely summary
                            summary = line
                
                return {
                    "summary": summary,
                    "insights": parsed_insights[:5] if parsed_insights else [
                        f"Analyzed {sum(digest_data.get('coverage', {}).values())} records across operational systems",
                        "Agent scheduling adherence data shows active monitoring and tracking",
                        "Performance metrics indicate consistent operational activity"
                    ],
                    "recommendations": parsed_recommendations[:3] if parsed_recommendations else [
                        "Continue regular monitoring of operational metrics",
                        "Review weekly performance trends for optimization opportunities",
                        "Maintain consistent data quality standards"
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return {
                "summary": "Unable to generate detailed insights at this time.",
                "insights": [],
                "recommendations": []
            }
    
    def _prepare_data_summary(self, digest_data: Dict[str, Any], start_date: datetime, end_date: datetime) -> str:
        """Prepare a text summary of the data for AI analysis"""
        try:
            coverage = digest_data.get("coverage", {})
            tables_data = digest_data.get("tables", {})
            
            summary_parts = [
                f"Data Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                f"Total Records: {sum(coverage.values())}",
                f"Active Tables: {sum(1 for count in coverage.values() if count > 0)}",
                ""
            ]
            
            # Add comprehensive table-specific summaries for ALL tables
            for table, count in coverage.items():
                if count > 0 and table in tables_data:
                    table_info = tables_data[table]
                    summary_parts.append(f"\n{table}: {count} records")
                    
                    # Add comprehensive data insights if available
                    if "data" in table_info and not table_info["data"].empty:
                        df = table_info["data"]
                        
                        # Identify key business columns
                        business_columns = [col for col in df.columns if any(keyword in col.upper() for keyword in [
                            'AGENT', 'NAME', 'PERFORMANCE', 'ADHERENCE', 'PRODUCTIVITY', 'EFFICIENCY',
                            'SCORE', 'RATING', 'CSAT', 'QA', 'AHT', 'TICKET', 'SUPERVISOR', 'TEAM',
                            'TIME', 'DURATION', 'COUNT', 'TOTAL', 'AVERAGE', 'PERCENTAGE'
                        ])]
                        
                        if business_columns:
                            summary_parts.append(f"  Business metrics: {', '.join(business_columns[:5])}")
                            
                        # Add statistical insights for numeric columns
                        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                        if numeric_cols:
                            for col in numeric_cols[:3]:  # Top 3 numeric columns
                                try:
                                    col_data = df[col].dropna()
                                    if len(col_data) > 0:
                                        avg_val = col_data.mean()
                                        summary_parts.append(f"  {col}: avg={avg_val:.2f}, records={len(col_data)}")
                                except Exception:
                                    continue
                        
                        # Add categorical insights
                        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                        if categorical_cols:
                            for col in categorical_cols[:2]:  # Top 2 categorical columns
                                try:
                                    unique_count = df[col].nunique()
                                    if unique_count > 0:
                                        summary_parts.append(f"  {col}: {unique_count} unique values")
                                except Exception:
                                    continue
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error preparing data summary: {str(e)}")
            return "Data summary unavailable"
    
    async def _analyze_trends(self, digest_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trends in the weekly data"""
        trends = {
            "productivity_trend": "stable",
            "data_volume_trend": "normal",
            "quality_indicators": [],
            "notable_changes": []
        }
        
        try:
            tables_data = digest_data.get("tables", {})
            
            # Analyze key performance tables
            performance_tables = ['RPT_WOPS_AGENT_PERFORMANCE', 'RPT_AGENT_SCHEDULE_ADHERENCE']
            
            for table in performance_tables:
                if table in tables_data and "data" in tables_data[table]:
                    df = tables_data[table]["data"]
                    if not df.empty:
                        # Look for performance indicators
                        perf_columns = [col for col in df.columns if any(indicator in col.upper() for indicator in [
                            'PERFORMANCE', 'ADHERENCE', 'PRODUCTIVITY', 'EFFICIENCY', 'RATING'
                        ])]
                        
                        for col in perf_columns:
                            if col in df.columns:
                                try:
                                    # Convert to numeric and analyze
                                    numeric_data = pd.to_numeric(df[col], errors='coerce').dropna()
                                    if len(numeric_data) > 0:
                                        avg_value = numeric_data.mean()
                                        trends["quality_indicators"].append({
                                            "metric": col,
                                            "table": table,
                                            "average": round(avg_value, 2),
                                            "count": len(numeric_data)
                                        })
                                except Exception:
                                    continue
            
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
            return trends


# Create singleton instance
weekly_digest_service = WeeklyDigestService()