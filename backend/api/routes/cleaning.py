"""
Data cleaning API routes.

Provides endpoints for cleaning datasets and retrieving cleaned results.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel
from backend.database.engine import get_db
from backend.database.models import User
from backend.services.cleaning_service import CleaningService
from backend.services.dataset_service import DatasetService
from backend.utils.logger import setup_logger
from backend.api.dependencies import get_current_user

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/cleaning", tags=["Cleaning"])


class CleaningRules(BaseModel):
    """Schema for cleaning rules."""

    remove_duplicates: bool = True
    fill_missing: bool = True
    fill_strategy: str = "mean"
    normalize_text: bool = True
    standardize_dates: bool = True
    standardize_categorical: bool = False
    remove_invalid: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "remove_duplicates": True,
                "fill_missing": True,
                "fill_strategy": "mean",
                "normalize_text": True,
                "standardize_dates": True,
            }
        }


@router.post("/datasets/{dataset_id}/clean")
async def clean_dataset(
    dataset_id: str,
    rules: CleaningRules,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start a data cleaning task.

    Args:
        dataset_id: Dataset ID
        rules: Cleaning rules to apply
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Cleaning task status

    Raises:
        HTTPException: If cleaning fails
    """
    try:
        # Check ownership
        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        # Create cleaning task
        success, cleaning_task, error = CleaningService.create_cleaning_task(
            db=db,
            dataset_id=dataset_id,
            rules=rules.model_dump(),
        )

        if not success:
            logger.error(f"Cleaning failed: {error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        logger.info(f"Cleaning task started: {cleaning_task.id}")

        return {
            "status": "success",
            "cleaning_id": cleaning_task.id,
            "task_status": cleaning_task.status,
            "created_at": cleaning_task.created_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting cleaning: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start cleaning task",
        )


@router.get("/tasks/{cleaning_id}")
async def get_cleaning_status(
    cleaning_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get cleaning task status.

    Args:
        cleaning_id: Cleaning task ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Task status and results

    Raises:
        HTTPException: If task not found
    """
    try:
        cleaning_task = CleaningService.get_cleaning_task(db, cleaning_id)

        if not cleaning_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cleaning task not found",
            )

        # Check ownership via dataset
        dataset = DatasetService.get_dataset(
            db, cleaning_task.dataset_id, current_user.id
        )
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        result = {
            "id": cleaning_task.id,
            "dataset_id": cleaning_task.dataset_id,
            "status": cleaning_task.status,
            "created_at": cleaning_task.created_at,
            "completed_at": cleaning_task.completed_at,
        }

        if cleaning_task.status == "completed":
            result.update({
                "removed_duplicates": cleaning_task.removed_duplicates,
                "filled_missing_values": cleaning_task.filled_missing_values,
                "removed_invalid_records": cleaning_task.removed_invalid_records,
                "normalized_text_columns": cleaning_task.normalized_text_columns,
                "standardized_dates": cleaning_task.standardized_dates,
                "cleaned_rows": cleaning_task.cleaned_rows,
                "cleaning_rules": cleaning_task.cleaning_rules,
            })
        elif cleaning_task.status == "failed":
            result["error_message"] = cleaning_task.error_message

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cleaning status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cleaning status",
        )


@router.get("/datasets/{dataset_id}/history")
async def get_cleaning_history(
    dataset_id: str,
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get cleaning history for dataset.

    Args:
        dataset_id: Dataset ID
        limit: Number of records
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Cleaning history

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

        cleaning_tasks = CleaningService.get_cleaning_history(
            db, dataset_id, limit
        )

        return {
            "dataset_id": dataset_id,
            "total_tasks": len(cleaning_tasks),
            "tasks": [
                {
                    "id": task.id,
                    "status": task.status,
                    "created_at": task.created_at,
                    "completed_at": task.completed_at,
                    "removed_duplicates": task.removed_duplicates,
                    "cleaned_rows": task.cleaned_rows,
                }
                for task in cleaning_tasks
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cleaning history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cleaning history",
        )


@router.get("/tasks/{cleaning_id}/download")
async def download_cleaned_dataset(
    cleaning_id: str,
    format: str = Query("csv", regex="^(csv|xlsx|json)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Download cleaned dataset.

    Args:
        cleaning_id: Cleaning task ID
        format: Export format
        current_user: Current authenticated user
        db: Database session

    Returns:
        StreamingResponse: File data

    Raises:
        HTTPException: If download fails
    """
    try:
        from fastapi.responses import StreamingResponse
        import io

        cleaning_task = CleaningService.get_cleaning_task(db, cleaning_id)

        if not cleaning_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cleaning task not found",
            )

        # Check ownership
        dataset = DatasetService.get_dataset(
            db, cleaning_task.dataset_id, current_user.id
        )
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        success, file_bytes, error = CleaningService.download_cleaned_dataset(
            db, cleaning_id, format
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        filename = f"{dataset.name}_cleaned.{format}"
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
        logger.error(f"Error downloading cleaned dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download cleaned dataset",
        )
