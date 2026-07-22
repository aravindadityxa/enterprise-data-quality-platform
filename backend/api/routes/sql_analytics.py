"""
SQL Analytics API routes.

Provides endpoints for executing SQL queries and retrieving analytics results.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
from backend.database.models import User
from backend.services.sql_service import SQLService
from backend.utils.logger import setup_logger
from backend.api.dependencies import get_current_user, get_analyst_user

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/sql", tags=["SQL Analytics"])


class QueryExecutionRequest(BaseModel):
    """Schema for query execution request."""

    query: str
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "query": "SELECT COUNT(*) as total FROM transactions",
                "description": "Get total transaction count"
            }
        }


class PredefinedQueryRequest(BaseModel):
    """Schema for predefined query request."""

    query_name: str

    class Config:
        json_schema_extra = {
            "example": {
                "query_name": "top_customers"
            }
        }


@router.get("/health")
async def sql_health_check(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Check SQL database connection.

    Args:
        current_user: Current authenticated user

    Returns:
        dict: Connection status

    Raises:
        HTTPException: If connection fails
    """
    try:
        success, error = SQLService.test_connection()

        if not success:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database connection failed: {error}",
            )

        return {
            "status": "healthy",
            "message": "Database connection successful"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed",
        )


@router.get("/queries")
async def list_queries(
    current_user: User = Depends(get_analyst_user),
) -> dict:
    """
    List all available predefined queries.

    Args:
        current_user: Current authenticated analyst user

    Returns:
        dict: Available queries

    Raises:
        HTTPException: If user is not analyst
    """
    try:
        queries = SQLService.get_available_queries()

        return {
            "total_queries": len(queries),
            "queries": queries,
        }

    except Exception as e:
        logger.error(f"Error listing queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list queries",
        )


@router.get("/queries/{query_name}")
async def get_query_definition(
    query_name: str,
    current_user: User = Depends(get_analyst_user),
) -> dict:
    """
    Get SQL definition for a specific query.

    Args:
        query_name: Query name
        current_user: Current authenticated analyst user

    Returns:
        dict: Query definition

    Raises:
        HTTPException: If query not found
    """
    try:
        definition = SQLService.get_query_definition(query_name)

        if not definition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Query '{query_name}' not found",
            )

        return {
            "query_name": query_name,
            "query_definition": definition,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting query definition: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get query definition",
        )


@router.post("/execute/predefined")
async def execute_predefined_query(
    request: PredefinedQueryRequest,
    current_user: User = Depends(get_analyst_user),
    format: str = Query("json", regex="^(json|csv|xlsx)$"),
):
    """
    Execute a predefined query.

    Args:
        request: Query execution request
        current_user: Current authenticated analyst user
        format: Response format

    Returns:
        dict or file: Query results

    Raises:
        HTTPException: If query fails
    """
    try:
        logger.info(f"Executing predefined query: {request.query_name}")

        success, df, error = SQLService.execute_predefined_query(request.query_name)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        if format == "json":
            return {
                "query_name": request.query_name,
                "row_count": len(df),
                "columns": df.columns.tolist(),
                "data": df.to_dict(orient="records"),
            }
        else:
            # Export formats handled separately
            from fastapi.responses import StreamingResponse
            import io

            success, file_bytes, export_error = SQLService.export_query_results(
                request.query_name, format
            )

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=export_error,
                )

            filename = f"{request.query_name}.{format}"
            media_type = {
                "csv": "text/csv",
                "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }.get(format, "application/octet-stream")

            return StreamingResponse(
                io.BytesIO(file_bytes),
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing predefined query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute query",
        )


@router.post("/execute/custom")
async def execute_custom_query(
    request: QueryExecutionRequest,
    current_user: User = Depends(get_analyst_user),
):
    """
    Execute a custom SQL query.

    Args:
        request: Query execution request
        current_user: Current authenticated analyst user

    Returns:
        dict: Query results

    Raises:
        HTTPException: If query fails
    """
    try:
        # Validate query (basic security check)
        query_upper = request.query.upper()
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE"]

        if any(keyword in query_upper for keyword in dangerous_keywords):
            logger.warning(f"Dangerous query attempted by {current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Query contains restricted operations",
            )

        logger.info(f"Executing custom query for {current_user.username}")

        success, df, error = SQLService.execute_query(request.query)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query execution failed: {error}",
            )

        return {
            "description": request.description,
            "row_count": len(df),
            "columns": df.columns.tolist(),
            "data": df.to_dict(orient="records")[:1000],  # Limit to 1000 rows
            "total_rows": len(df),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing custom query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute query",
        )


@router.get("/tables/stats")
async def get_table_statistics(
    current_user: User = Depends(get_analyst_user),
) -> dict:
    """
    Get database table statistics.

    Args:
        current_user: Current authenticated analyst user

    Returns:
        dict: Table statistics
    """
    try:
        stats = SQLService.get_table_stats()

        return {
            "table_count": len(stats),
            "tables": stats,
        }

    except Exception as e:
        logger.error(f"Error getting table stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get table statistics",
        )


@router.get("/tables/{table_name}/summary")
async def get_table_summary(
    table_name: str,
    current_user: User = Depends(get_analyst_user),
) -> dict:
    """
    Get summary of table contents.

    Args:
        table_name: Name of table
        current_user: Current authenticated analyst user

    Returns:
        dict: Table summary

    Raises:
        HTTPException: If table not found
    """
    try:
        # Validate table name to prevent SQL injection
        if not table_name.replace("_", "").isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid table name",
            )

        summary = SQLService.create_summary_table(table_name)

        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table '{table_name}' not found",
            )

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get table summary",
        )


@router.get("/query/{query_name}/export")
async def export_query_results(
    query_name: str,
    format: str = Query("csv", regex="^(csv|xlsx|json)$"),
    current_user: User = Depends(get_analyst_user),
):
    """
    Export query results to file.

    Args:
        query_name: Name of predefined query
        format: Export format
        current_user: Current authenticated analyst user

    Returns:
        StreamingResponse: File download

    Raises:
        HTTPException: If query or export fails
    """
    try:
        from fastapi.responses import StreamingResponse
        import io

        success, file_bytes, error = SQLService.export_query_results(query_name, format)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        filename = f"{query_name}.{format}"
        media_type = {
            "csv": "text/csv",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "json": "application/json",
        }.get(format, "application/octet-stream")

        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export results",
        )
