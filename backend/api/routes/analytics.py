"""
Analytics API routes.

Provides endpoints for EDA analysis, KPI calculation, and insights generation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from backend.database.engine import get_db
from backend.database.models import User
from backend.services.analytics_service import AnalyticsService
from backend.services.dataset_service import DatasetService
from backend.utils.file_handler import FileHandler
from backend.utils.logger import setup_logger
from backend.api.dependencies import get_current_user

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.post("/datasets/{dataset_id}/eda")
async def generate_eda_analysis(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate exploratory data analysis for dataset.

    Args:
        dataset_id: Dataset ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: EDA analysis results

    Raises:
        HTTPException: If analysis fails
    """
    try:
        # Check ownership
        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        success, analytics, error = AnalyticsService.generate_eda_analysis(db, dataset_id)

        if not success:
            logger.error(f"EDA analysis failed: {error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        logger.info(f"EDA analysis generated: {analytics.id}")

        return {
            "status": "success",
            "analytics_id": analytics.id,
            "dataset_id": dataset_id,
            "summary_statistics": analytics.summary_stats,
            "correlation_matrix": analytics.correlation_matrix,
            "insights": analytics.generated_insights[:10],  # Top 10 insights
            "created_at": analytics.created_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating EDA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate EDA analysis",
        )


@router.get("/datasets/{dataset_id}/eda")
async def get_eda_analysis(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get latest EDA analysis for dataset.

    Args:
        dataset_id: Dataset ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: EDA analysis details

    Raises:
        HTTPException: If analysis not found
    """
    try:
        # Check ownership
        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        analytics = AnalyticsService.get_latest_eda_analysis(db, dataset_id)

        if not analytics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No EDA analysis found",
            )

        return {
            "id": analytics.id,
            "dataset_id": dataset_id,
            "summary_statistics": analytics.summary_stats,
            "correlation_matrix": analytics.correlation_matrix,
            "distributions": analytics.column_distributions,
            "categorical_distributions": analytics.top_categories,
            "growth_trends": analytics.growth_trends,
            "generated_insights": analytics.generated_insights,
            "created_at": analytics.created_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting EDA analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get EDA analysis",
        )


@router.get("/datasets/{dataset_id}/summary")
async def get_data_summary(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get data summary including basic statistics.

    Args:
        dataset_id: Dataset ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Data summary

    Raises:
        HTTPException: If dataset not found
    """
    try:
        # Check ownership
        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        # Load data
        df = FileHandler.load_dataframe(dataset.file_path)

        # Get latest EDA if available
        analytics = AnalyticsService.get_latest_eda_analysis(db, dataset_id)

        summary = {
            "dataset_id": dataset_id,
            "dataset_name": dataset.name,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "column_names": df.columns.tolist(),
            "data_types": {col: str(df[col].dtype) for col in df.columns},
            "numeric_columns": df.select_dtypes(include=["number"]).columns.tolist(),
            "categorical_columns": df.select_dtypes(include=["object"]).columns.tolist(),
            "null_counts": df.isnull().sum().to_dict(),
        }

        if analytics:
            summary["summary_statistics"] = analytics.summary_stats
            summary["insights"] = analytics.generated_insights[:5]

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get data summary",
        )


@router.get("/datasets/{dataset_id}/column/{column_name}")
async def get_column_analysis(
    dataset_id: str,
    column_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed analysis for specific column.

    Args:
        dataset_id: Dataset ID
        column_name: Column name
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Column analysis

    Raises:
        HTTPException: If dataset or column not found
    """
    try:
        # Check ownership
        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        # Load data
        df = FileHandler.load_dataframe(dataset.file_path)

        # Get column insights
        insights = AnalyticsService.get_column_insights(df, column_name)

        if "error" in insights:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=insights["error"],
            )

        return {
            "dataset_id": dataset_id,
            "column_analysis": insights,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing column: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze column",
        )


@router.get("/datasets/{dataset_id}/compare")
async def compare_columns(
    dataset_id: str,
    column1: str = Query(...),
    column2: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compare two columns in dataset.

    Args:
        dataset_id: Dataset ID
        column1: First column name
        column2: Second column name
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Comparison results

    Raises:
        HTTPException: If dataset or columns not found
    """
    try:
        # Check ownership
        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        # Load data
        df = FileHandler.load_dataframe(dataset.file_path)

        # Compare columns
        comparison = AnalyticsService.compare_columns(df, column1, column2)

        if "error" in comparison:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=comparison["error"],
            )

        return {
            "dataset_id": dataset_id,
            "comparison": comparison,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing columns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare columns",
        )


@router.get("/datasets/{dataset_id}/insights")
async def get_data_insights(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get automatically generated data insights.

    Args:
        dataset_id: Dataset ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Generated insights

    Raises:
        HTTPException: If dataset not found
    """
    try:
        # Check ownership
        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        analytics = AnalyticsService.get_latest_eda_analysis(db, dataset_id)

        if not analytics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No analysis available yet",
            )

        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset.name,
            "total_insights": len(analytics.generated_insights),
            "insights": analytics.generated_insights,
            "analysis_date": analytics.created_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get insights",
        )
