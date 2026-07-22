"""
SQL Analytics service.

Executes SQL queries and returns results for analytics.
"""

from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
from sqlalchemy import text, create_engine
from sqlalchemy.orm import Session
from backend.config import get_settings
from backend.analytics.sql_queries import get_query, list_queries
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()


class SQLService:
    """Service for executing SQL analytics queries."""

    _engine = None

    @staticmethod
    def get_engine():
        """
        Get or create database engine.

        Returns:
            Engine: SQLAlchemy engine
        """
        if SQLService._engine is None:
            SQLService._engine = create_engine(settings.database_url)
        return SQLService._engine

    @staticmethod
    def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[pd.DataFrame], Optional[str]]:
        """
        Execute raw SQL query.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            Tuple of (success, dataframe, error_message)
        """
        try:
            engine = SQLService.get_engine()

            with engine.connect() as connection:
                if params:
                    result = connection.execute(text(query), params)
                else:
                    result = connection.execute(text(query))

                # Convert to DataFrame
                df = pd.DataFrame(result.fetchall(), columns=result.keys())

                logger.info(f"Query executed successfully, returned {len(df)} rows")
                return True, df, None

        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return False, None, str(e)

    @staticmethod
    def execute_predefined_query(query_name: str) -> Tuple[bool, Optional[pd.DataFrame], Optional[str]]:
        """
        Execute predefined query by name.

        Args:
            query_name: Name of predefined query

        Returns:
            Tuple of (success, dataframe, error_message)
        """
        try:
            query = get_query(query_name)

            if not query:
                return False, None, f"Query '{query_name}' not found"

            success, df, error = SQLService.execute_query(query)

            if success:
                logger.info(f"Predefined query '{query_name}' executed successfully")

            return success, df, error

        except Exception as e:
            logger.error(f"Error executing predefined query: {e}")
            return False, None, str(e)

    @staticmethod
    def get_available_queries() -> List[str]:
        """
        Get list of available predefined queries.

        Returns:
            list: Query names
        """
        return list_queries()

    @staticmethod
    def get_query_definition(query_name: str) -> Optional[str]:
        """
        Get SQL query definition.

        Args:
            query_name: Name of query

        Returns:
            Optional[str]: Query definition
        """
        return get_query(query_name)

    @staticmethod
    def test_connection() -> Tuple[bool, Optional[str]]:
        """
        Test database connection.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            engine = SQLService.get_engine()

            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                logger.info("Database connection test successful")
                return True, None

        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False, str(e)

    @staticmethod
    def get_table_stats() -> Dict[str, Any]:
        """
        Get statistics about database tables.

        Returns:
            dict: Table statistics
        """
        try:
            engine = SQLService.get_engine()
            stats = {}

            # Get table info
            inspector_query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """

            with engine.connect() as connection:
                result = connection.execute(text(inspector_query))
                tables = [row[0] for row in result.fetchall()]

                for table in tables:
                    count_query = f"SELECT COUNT(*) FROM {table}"
                    result = connection.execute(text(count_query))
                    count = result.fetchone()[0]

                    stats[table] = {
                        "row_count": count,
                    }

            logger.info(f"Retrieved statistics for {len(stats)} tables")
            return stats

        except Exception as e:
            logger.warning(f"Could not retrieve table stats: {e}")
            return {}

    @staticmethod
    def create_summary_table(table_name: str) -> Dict[str, Any]:
        """
        Create a summary of table contents.

        Args:
            table_name: Name of table

        Returns:
            dict: Table summary
        """
        try:
            engine = SQLService.get_engine()

            # Get column info
            with engine.connect() as connection:
                # Get row count
                count_query = f"SELECT COUNT(*) FROM {table_name}"
                result = connection.execute(text(count_query))
                row_count = result.fetchone()[0]

                # Get sample data
                sample_query = f"SELECT * FROM {table_name} LIMIT 5"
                df_sample = pd.read_sql(sample_query, connection)

                summary = {
                    "table_name": table_name,
                    "row_count": row_count,
                    "column_count": len(df_sample.columns),
                    "columns": df_sample.columns.tolist(),
                    "dtypes": {col: str(df_sample[col].dtype) for col in df_sample.columns},
                    "sample_rows": df_sample.to_dict(orient="records"),
                }

                logger.info(f"Created summary for table {table_name}")
                return summary

        except Exception as e:
            logger.error(f"Error creating table summary: {e}")
            return {}

    @staticmethod
    def export_query_results(query_name: str, format: str = "csv") -> Tuple[bool, Optional[bytes], Optional[str]]:
        """
        Export query results to file.

        Args:
            query_name: Query name
            format: Export format (csv, xlsx, json)

        Returns:
            Tuple of (success, file_bytes, error_message)
        """
        try:
            success, df, error = SQLService.execute_predefined_query(query_name)

            if not success:
                return False, None, error

            if format == "csv":
                return True, df.to_csv(index=False).encode(), None
            elif format == "xlsx":
                import io
                buffer = io.BytesIO()
                df.to_excel(buffer, index=False)
                return True, buffer.getvalue(), None
            elif format == "json":
                return True, df.to_json(orient="records").encode(), None
            else:
                return False, None, f"Unsupported format: {format}"

        except Exception as e:
            logger.error(f"Error exporting results: {e}")
            return False, None, str(e)
