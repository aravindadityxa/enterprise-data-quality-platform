"""
Data validation API routes.

Provides endpoints for validating datasets and retrieving validation reports.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from backend.database.engine import get_db
from backend.database.models import User
from backend.services.validation_service import ValidationService
from backend.services.dataset_service import DatasetService
from backend.schemas.validation import ValidationResponse, DataQualityReport
from backend.utils.logger import setup_logger
from backend.api.dependencies import get_current_user

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/validation", tags=["Validation"])


@router.post("/datasets/{dataset_id}/validate")
async def validate_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Validate a dataset.

    Args:
        dataset_id: Dataset ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Validation result status

    Raises:
        HTTPException: If validation fails
    """
    try:
        # Check ownership
        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        success, validation, error = ValidationService.validate_dataset(db, dataset_id)

        if not success:
            logger.error(f"Validation failed: {error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        logger.info(f"Dataset validated: {dataset_id}")

        return {
            "status": "success",
            "validation_id": validation.id,
            "quality_score": validation.quality_score,
            "validation_status": validation.validation_status,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate dataset",
        )


@router.get("/datasets/{dataset_id}/latest", response_model=ValidationResponse)
async def get_latest_validation(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get latest validation for dataset.

    Args:
        dataset_id: Dataset ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        ValidationResponse: Latest validation details

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

        validation = ValidationService.get_latest_validation(db, dataset_id)

        if not validation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No validation found for dataset",
            )

        return validation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get validation",
        )


@router.get("/datasets/{dataset_id}/history")
async def get_validation_history(
    dataset_id: str,
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get validation history for dataset.

    Args:
        dataset_id: Dataset ID
        limit: Number of records
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Validation history

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

        validations = ValidationService.get_validations_for_dataset(
            db, dataset_id, limit
        )

        return {
            "dataset_id": dataset_id,
            "total_validations": len(validations),
            "validations": [
                {
                    "id": v.id,
                    "quality_score": v.quality_score,
                    "validation_status": v.validation_status,
                    "created_at": v.created_at,
                }
                for v in validations
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting validation history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get validation history",
        )


@router.get("/datasets/{dataset_id}/report", response_model=DataQualityReport)
async def get_quality_report(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get comprehensive quality report for dataset.

    Args:
        dataset_id: Dataset ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        DataQualityReport: Quality report

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

        summary = ValidationService.generate_quality_summary(db, dataset_id)

        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No validation data available",
            )

        # Convert to DataQualityReport format
        report = DataQualityReport(
            dataset_id=dataset_id,
            dataset_name=summary["dataset_name"],
            analysis_date=summary["analysis_date"],
            overall_quality_score=summary["overall_quality_score"],
            total_rows=summary["total_rows"],
            total_columns=summary["total_columns"],
            completeness=summary["completeness_score"],
            uniqueness=summary["uniqueness_score"],
            consistency=summary["consistency_score"],
            validity=summary["validity_score"],
            accuracy=100 - min(summary["accuracy_issues"] / max(summary["total_rows"], 1) * 100, 100),
            critical_issues=summary["critical_issues"],
            warning_issues=summary["warning_issues"],
            info_messages=0,
            findings={},
            recommendations=summary["recommendations"],
        )

        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report",
        )


@router.get("/validations/{validation_id}")
async def get_validation_details(
    validation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed validation results.

    Args:
        validation_id: Validation ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Detailed validation results

    Raises:
        HTTPException: If validation not found
    """
    try:
        validation = ValidationService.get_validation(db, validation_id)

        if not validation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation not found",
            )

        # Check ownership via dataset
        dataset = DatasetService.get_dataset(db, validation.dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        return {
            "id": validation.id,
            "dataset_id": validation.dataset_id,
            "quality_score": validation.quality_score,
            "validation_status": validation.validation_status,
            "created_at": validation.created_at,
            "validation_report": validation.validation_report,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting validation details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get validation details",
        )


@router.post("/batch-validate")
async def batch_validate(
    dataset_ids: list,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Validate multiple datasets.

    Args:
        dataset_ids: List of dataset IDs
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Batch validation results

    Raises:
        HTTPException: If batch fails
    """
    try:
        # Verify ownership of all datasets
        for dataset_id in dataset_ids:
            dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
            if not dataset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Dataset {dataset_id} not found",
                )

        successful, failed = ValidationService.batch_validate_datasets(
            db, dataset_ids
        )

        logger.info(f"Batch validation complete: {successful} success, {failed} failed")

        return {
            "status": "complete",
            "total_datasets": len(dataset_ids),
            "successful": successful,
            "failed": failed,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to batch validate datasets",
        )
