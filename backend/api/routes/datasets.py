"""
Dataset management API routes.

Handles dataset upload, retrieval, updates, and deletions.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import Optional
import os
from backend.database.engine import get_db
from backend.database.models import User
from backend.services.dataset_service import DatasetService
from backend.services.auth_service import AuthService
from backend.schemas.dataset import DatasetCreate, DatasetResponse, DatasetListResponse
from backend.utils.file_handler import FileHandler
from backend.utils.logger import setup_logger
from backend.config import get_settings
from backend.api.dependencies import get_current_user

logger = setup_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])


@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a dataset file.

    Supports CSV, Excel, and JSON formats.

    Args:
        file: Dataset file to upload
        name: Dataset name
        description: Optional description
        current_user: Current authenticated user
        db: Database session

    Returns:
        DatasetResponse: Created dataset metadata

    Raises:
        HTTPException: If upload or validation fails
    """
    try:
        # Validate file extension
        if not FileHandler.validate_file_extension(file.filename):
            logger.warning(f"Invalid file type: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed: {settings.allowed_extensions}",
            )

        # Validate file size
        file_size = 0
        file_content = await file.read()
        file_size = len(file_content)

        if file_size > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds limit of {settings.max_upload_size_mb}MB",
            )

        # Save file
        upload_dir = FileHandler.ensure_upload_directory()
        unique_filename = FileHandler.get_unique_filename(file.filename, upload_dir)
        file_path = os.path.join(upload_dir, unique_filename)

        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File uploaded: {file_path}")

        # Create dataset record
        success, dataset, error = DatasetService.create_dataset(
            db=db,
            user_id=current_user.id,
            file_path=file_path,
            name=name,
            description=description,
        )

        if not success:
            FileHandler.delete_file(file_path)
            logger.error(f"Failed to create dataset: {error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        logger.info(f"Dataset uploaded successfully: {dataset.id}")
        return dataset

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload dataset",
        )


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List datasets for current user.

    Args:
        page: Page number (1-indexed)
        page_size: Items per page
        search: Optional search term
        current_user: Current authenticated user
        db: Database session

    Returns:
        DatasetListResponse: List of datasets with pagination info
    """
    try:
        total, datasets = DatasetService.list_datasets(
            db=db,
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            search=search,
        )

        return DatasetListResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=datasets,
        )

    except Exception as e:
        logger.error(f"Error listing datasets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list datasets",
        )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get dataset by ID.

    Args:
        dataset_id: Dataset ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        DatasetResponse: Dataset details

    Raises:
        HTTPException: If dataset not found
    """
    try:
        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)

        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        return dataset

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dataset",
        )


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: str,
    update_data: DatasetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update dataset metadata.

    Args:
        dataset_id: Dataset ID
        update_data: Updated dataset data
        current_user: Current authenticated user
        db: Database session

    Returns:
        DatasetResponse: Updated dataset

    Raises:
        HTTPException: If update fails
    """
    try:
        # Check ownership
        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        success, updated_dataset, error = DatasetService.update_dataset(
            db=db,
            dataset_id=dataset_id,
            name=update_data.name,
            description=update_data.description,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        return updated_dataset

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update dataset",
        )


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete dataset.

    Args:
        dataset_id: Dataset ID
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If deletion fails
    """
    try:
        # Check ownership
        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        success, error = DatasetService.delete_dataset(db, dataset_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        logger.info(f"Dataset deleted: {dataset_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete dataset",
        )


@router.get("/{dataset_id}/sample")
async def get_dataset_sample(
    dataset_id: str,
    rows: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get sample of dataset rows.

    Args:
        dataset_id: Dataset ID
        rows: Number of rows to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Sample data

    Raises:
        HTTPException: If dataset not found
    """
    try:
        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        sample_df = DatasetService.get_dataset_sample(db, dataset_id, rows)

        if sample_df is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to load dataset sample",
            )

        return {
            "dataset_id": dataset_id,
            "total_rows": len(sample_df),
            "columns": sample_df.columns.tolist(),
            "data": sample_df.to_dict(orient="records"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sample: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dataset sample",
        )


@router.get("/{dataset_id}/download")
async def download_dataset(
    dataset_id: str,
    format: str = Query("csv", regex="^(csv|xlsx|json)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Download dataset in specified format.

    Args:
        dataset_id: Dataset ID
        format: Export format (csv, xlsx, json)
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

        dataset = DatasetService.get_dataset(db, dataset_id, current_user.id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        success, file_bytes, error = DatasetService.export_dataset(db, dataset_id, format)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        filename = f"{dataset.name}.{format}"
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
        logger.error(f"Error downloading dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download dataset",
        )
