"""Validation-related schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List


class ValidationIssue(BaseModel):
    """Schema for individual validation issues."""

    type: str
    column: Optional[str] = None
    count: int
    percentage: float
    examples: Optional[List[Any]] = Field(None, max_items=5)


class ValidationDetail(BaseModel):
    """Schema for validation details."""

    missing_values: Optional[Dict[str, int]] = None
    duplicates: Optional[int] = None
    invalid_emails: Optional[List[Dict[str, Any]]] = None
    invalid_phones: Optional[List[Dict[str, Any]]] = None
    invalid_dates: Optional[List[Dict[str, Any]]] = None
    negative_quantities: Optional[List[Dict[str, Any]]] = None
    data_type_mismatches: Optional[List[Dict[str, Any]]] = None
    outliers: Optional[List[Dict[str, Any]]] = None


class ValidationResponse(BaseModel):
    """Schema for validation responses."""

    id: str
    dataset_id: str
    quality_score: float = Field(..., ge=0, le=100)
    validation_status: str  # pass, warning, fail
    missing_values_count: Optional[int]
    missing_values_percentage: Optional[float]
    duplicates_count: Optional[int]
    duplicates_percentage: Optional[float]
    null_percentage: Optional[float]
    issues: Optional[List[ValidationIssue]]
    validation_report: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "dataset_id": "550e8400-e29b-41d4-a716-446655440001",
                "quality_score": 85.5,
                "validation_status": "warning",
                "missing_values_count": 150,
                "missing_values_percentage": 1.5,
                "duplicates_count": 50,
                "duplicates_percentage": 0.5,
                "null_percentage": 2.0,
                "issues": [
                    {
                        "type": "missing_values",
                        "column": "email",
                        "count": 100,
                        "percentage": 1.0,
                        "examples": ["row_1", "row_5", "row_10"],
                    }
                ],
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class DataQualityReport(BaseModel):
    """Schema for comprehensive data quality report."""

    dataset_id: str
    dataset_name: str
    analysis_date: datetime
    overall_quality_score: float = Field(..., ge=0, le=100)
    total_rows: int
    total_columns: int
    
    # Quality metrics
    completeness: float = Field(..., description="Non-null data percentage")
    uniqueness: float = Field(..., description="Unique values percentage")
    consistency: float = Field(..., description="Data consistency score")
    validity: float = Field(..., description="Valid data percentage")
    accuracy: float = Field(..., description="Data accuracy score")
    
    # Issues summary
    critical_issues: int
    warning_issues: int
    info_messages: int
    
    # Detailed findings
    findings: Dict[str, Any]
    
    # Recommendations
    recommendations: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
                "dataset_name": "Sales Data 2024",
                "analysis_date": "2024-01-15T10:30:00Z",
                "overall_quality_score": 82.5,
                "total_rows": 10000,
                "total_columns": 15,
                "completeness": 98.5,
                "uniqueness": 95.0,
                "consistency": 90.0,
                "validity": 88.0,
                "accuracy": 85.0,
                "critical_issues": 2,
                "warning_issues": 5,
                "info_messages": 10,
                "findings": {},
                "recommendations": [
                    "Remove 50 duplicate records",
                    "Fill missing email addresses",
                ],
            }
        }
