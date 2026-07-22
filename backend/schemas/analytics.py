"""Analytics-related schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List


class AnalyticsResponse(BaseModel):
    """Schema for analytics responses."""

    id: str
    dataset_id: str
    summary_stats: Optional[Dict[str, Any]]
    correlation_matrix: Optional[Dict[str, Any]]
    column_distributions: Optional[Dict[str, Any]]
    top_categories: Optional[Dict[str, Any]]
    growth_trends: Optional[Dict[str, Any]]
    monthly_analysis: Optional[Dict[str, Any]]
    yearly_analysis: Optional[Dict[str, Any]]
    generated_insights: Optional[List[str]]
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "dataset_id": "550e8400-e29b-41d4-a716-446655440001",
                "summary_stats": {
                    "amount": {"mean": 1500, "median": 1200, "std": 500},
                },
                "correlation_matrix": {"amount_quantity": 0.85},
                "generated_insights": ["Average transaction increased by 15% YoY"],
                "created_at": "2024-01-15T10:30:00Z",
            }
        }


class KPIResponse(BaseModel):
    """Schema for KPI responses."""

    id: str
    dataset_id: str
    total_revenue: Optional[float]
    total_profit: Optional[float]
    profit_margin: Optional[float]
    total_sales: Optional[float]
    average_order_value: Optional[float]
    sales_by_region: Optional[Dict[str, float]]
    sales_by_category: Optional[Dict[str, float]]
    customer_retention_rate: Optional[float]
    repeat_customers: Optional[int]
    new_customers: Optional[int]
    growth_rate: Optional[float]
    month_over_month_growth: Optional[float]
    year_over_year_growth: Optional[float]
    inventory_turnover: Optional[float]
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    calculation_date: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "dataset_id": "550e8400-e29b-41d4-a716-446655440001",
                "total_revenue": 1500000.00,
                "total_profit": 450000.00,
                "profit_margin": 30.0,
                "total_sales": 5000,
                "average_order_value": 300.00,
                "customer_retention_rate": 72.5,
                "growth_rate": 15.5,
                "calculation_date": "2024-01-15T10:30:00Z",
            }
        }


class AnomalyResponse(BaseModel):
    """Schema for anomaly responses."""

    id: str
    dataset_id: str
    column_name: str
    anomaly_type: str
    detection_method: str
    value: float
    threshold: float
    score: float = Field(..., ge=0, le=1)
    severity: str
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "dataset_id": "550e8400-e29b-41d4-a716-446655440001",
                "column_name": "transaction_amount",
                "anomaly_type": "spike",
                "detection_method": "isolation_forest",
                "value": 50000.0,
                "threshold": 5000.0,
                "score": 0.95,
                "severity": "high",
                "created_at": "2024-01-15T10:30:00Z",
            }
        }


class ForecastResponse(BaseModel):
    """Schema for forecast responses."""

    id: str
    dataset_id: str
    forecast_type: str
    forecast_column: str
    model_type: str
    forecast_periods: int
    forecast_values: List[float]
    confidence_intervals: Optional[Dict[str, Any]]
    r_squared: Optional[float]
    rmse: Optional[float]
    mape: Optional[float]
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "dataset_id": "550e8400-e29b-41d4-a716-446655440001",
                "forecast_type": "sales",
                "forecast_column": "monthly_sales",
                "model_type": "linear_regression",
                "forecast_periods": 12,
                "forecast_values": [100000, 105000, 110000],
                "r_squared": 0.92,
                "rmse": 5000.0,
                "mape": 2.5,
                "created_at": "2024-01-15T10:30:00Z",
            }
        }
