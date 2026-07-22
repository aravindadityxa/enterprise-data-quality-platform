"""Dataset-related schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List


class DatasetCreate(BaseModel):
    """Schema for dataset creation."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    file_type: str = Field(..., description="File type: csv, xlsx, json")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Sales Dataset 2024",
                "description": "Annual sales data with customer information",
                "file_type": "csv",
            }
        }


class DatasetUpdate(BaseModel):
    """Schema for dataset updates."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=500)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Sales Dataset",
                "description": "Updated annual sales data",
            }
        }


class DataProfileReport(BaseModel):
    """Schema for dataset profile report."""

    total_rows: int
    total_columns: int
    column_names: List[str]
    data_types: Dict[str, str]
    null_counts: Dict[str, int]
    null_percentage: float
    duplicate_rows: int
    duplicate_percentage: float

    class Config:
        json_schema_extra = {
            "example": {
                "total_rows": 10000,
                "total_columns": 15,
                "column_names": ["id", "name", "email", "amount"],
                "data_types": {"id": "int64", "name": "object", "email": "object"},
                "null_counts": {"id": 0, "name": 5, "email": 10},
                "null_percentage": 0.15,
                "duplicate_rows": 50,
                "duplicate_percentage": 0.5,
            }
        }


class DatasetResponse(BaseModel):
    """Schema for dataset responses."""

    id: str
    name: str
    description: Optional[str]
    owner_id: str
    file_type: str
    file_size_bytes: Optional[int]
    total_rows: Optional[int]
    total_columns: Optional[int]
    column_names: Optional[List[str]]
    data_types: Optional[Dict[str, str]]
    null_percentage: Optional[float]
    duplicate_rows: Optional[int]
    duplicate_percentage: Optional[float]
    quality_score: Optional[float]
    is_cleaned: bool
    profile_report: Optional[DataProfileReport]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Sales Dataset 2024",
                "description": "Annual sales data",
                "owner_id": "550e8400-e29b-41d4-a716-446655440001",
                "file_type": "csv",
                "file_size_bytes": 1048576,
                "total_rows": 10000,
                "total_columns": 15,
                "column_names": ["id", "name", "email", "amount"],
                "data_types": {"id": "int64", "name": "object"},
                "null_percentage": 0.15,
                "duplicate_rows": 50,
                "duplicate_percentage": 0.5,
                "quality_score": 85.5,
                "is_cleaned": False,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class DatasetListResponse(BaseModel):
    """Schema for dataset list response."""

    total: int
    page: int
    page_size: int
    items: List[DatasetResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "total": 50,
                "page": 1,
                "page_size": 10,
                "items": [],
            }
        }
