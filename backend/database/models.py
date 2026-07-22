"""
SQLAlchemy ORM models for the application.

Includes models for datasets, validations, cleaning, analytics, and users.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, Text, 
    ForeignKey, Enum, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.database.engine import Base
import enum
import uuid


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True, index=True)
    role = Column(String(20), default="viewer", nullable=False)  # admin, analyst, viewer
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    datasets = relationship("Dataset", back_populates="owner")
    validations = relationship("DataValidation", back_populates="created_by_user")

    __table_args__ = (
        Index("idx_user_username", "username"),
        Index("idx_user_email", "email"),
    )


class Dataset(Base):
    """Dataset model for uploaded files."""

    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(10), nullable=False)  # csv, xlsx, json
    file_size_bytes = Column(Integer)
    total_rows = Column(Integer)
    total_columns = Column(Integer)
    column_names = Column(JSON)
    data_types = Column(JSON)
    null_counts = Column(JSON)
    null_percentage = Column(Float)
    duplicate_rows = Column(Integer)
    duplicate_percentage = Column(Float)
    profile_report = Column(JSON)
    is_cleaned = Column(Boolean, default=False)
    quality_score = Column(Float)  # 0-100
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="datasets")
    validations = relationship("DataValidation", back_populates="dataset", cascade="all, delete-orphan")
    cleaning_tasks = relationship("DataCleaning", back_populates="dataset", cascade="all, delete-orphan")
    analytics = relationship("Analytics", back_populates="dataset", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_dataset_owner_id", "owner_id"),
        Index("idx_dataset_created_at", "created_at"),
    )


class DataValidation(Base):
    """Data validation results."""

    __tablename__ = "data_validations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False, index=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Validation metrics
    missing_values_count = Column(Integer)
    missing_values_percentage = Column(Float)
    duplicates_count = Column(Integer)
    duplicates_percentage = Column(Float)
    null_percentage = Column(Float)
    unique_values_count = Column(JSON)
    
    # Data quality checks
    invalid_emails = Column(JSON)
    invalid_phones = Column(JSON)
    invalid_dates = Column(JSON)
    negative_quantities = Column(JSON)
    data_type_mismatches = Column(JSON)
    outliers = Column(JSON)
    
    # Overall score
    quality_score = Column(Float)  # 0-100
    validation_status = Column(String(20))  # pass, warning, fail
    validation_report = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    dataset = relationship("Dataset", back_populates="validations")
    created_by_user = relationship("User", back_populates="validations")

    __table_args__ = (
        Index("idx_validation_dataset_id", "dataset_id"),
        Index("idx_validation_created_at", "created_at"),
    )


class DataCleaning(Base):
    """Data cleaning operations and results."""

    __tablename__ = "data_cleaning"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False, index=True)
    
    # Cleaning operations
    removed_duplicates = Column(Integer, default=0)
    filled_missing_values = Column(Integer, default=0)
    normalized_text_columns = Column(JSON)
    standardized_dates = Column(JSON)
    removed_invalid_records = Column(Integer, default=0)
    
    # Cleaned dataset info
    cleaned_rows = Column(Integer)
    cleaned_file_path = Column(String(500))
    cleaning_rules = Column(JSON)
    
    # Status
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)

    # Relationships
    dataset = relationship("Dataset", back_populates="cleaning_tasks")

    __table_args__ = (
        Index("idx_cleaning_dataset_id", "dataset_id"),
    )


class Analytics(Base):
    """Analytics and EDA results."""

    __tablename__ = "analytics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False, index=True)
    
    # Summary statistics
    summary_stats = Column(JSON)  # mean, median, std, min, max
    correlation_matrix = Column(JSON)
    
    # Distributions
    column_distributions = Column(JSON)
    top_categories = Column(JSON)
    
    # Trends
    growth_trends = Column(JSON)
    monthly_analysis = Column(JSON)
    yearly_analysis = Column(JSON)
    
    # Insights
    generated_insights = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    dataset = relationship("Dataset", back_populates="analytics")

    __table_args__ = (
        Index("idx_analytics_dataset_id", "dataset_id"),
    )


class KPI(Base):
    """Business Key Performance Indicators."""

    __tablename__ = "kpis"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False, index=True)
    
    # Financial KPIs
    total_revenue = Column(Float)
    total_profit = Column(Float)
    profit_margin = Column(Float)
    
    # Sales KPIs
    total_sales = Column(Float)
    average_order_value = Column(Float)
    sales_by_region = Column(JSON)
    sales_by_category = Column(JSON)
    
    # Customer KPIs
    customer_retention_rate = Column(Float)
    repeat_customers = Column(Integer)
    new_customers = Column(Integer)
    customer_lifetime_value = Column(Float)
    
    # Growth KPIs
    growth_rate = Column(Float)
    month_over_month_growth = Column(Float)
    year_over_year_growth = Column(Float)
    
    # Inventory
    inventory_turnover = Column(Float)
    
    # Metadata
    calculation_date = Column(DateTime, default=datetime.utcnow)
    period_start = Column(DateTime)
    period_end = Column(DateTime)

    __table_args__ = (
        Index("idx_kpi_dataset_id", "dataset_id"),
    )


class Anomaly(Base):
    """Detected anomalies in data."""

    __tablename__ = "anomalies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False, index=True)
    
    # Anomaly info
    column_name = Column(String(255), nullable=False)
    anomaly_type = Column(String(50), nullable=False)  # spike, dip, outlier, fraud_like
    detection_method = Column(String(50), nullable=False)  # isolation_forest, zscore, iqr
    
    # Values
    value = Column(Float)
    threshold = Column(Float)
    score = Column(Float)  # 0-1 anomaly score
    
    # Row reference
    row_index = Column(Integer)
    
    severity = Column(String(20))  # low, medium, high
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_anomaly_dataset_id", "dataset_id"),
        Index("idx_anomaly_created_at", "created_at"),
    )


class Forecast(Base):
    """Forecasted values."""

    __tablename__ = "forecasts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False, index=True)
    
    # Forecast info
    forecast_type = Column(String(50), nullable=False)  # sales, revenue, demand, inventory
    forecast_column = Column(String(255), nullable=False)
    model_type = Column(String(50), nullable=False)  # linear_regression, random_forest, arima
    
    # Forecast data
    forecast_periods = Column(Integer)
    forecast_values = Column(JSON)
    confidence_intervals = Column(JSON)
    
    # Model metrics
    r_squared = Column(Float)
    rmse = Column(Float)
    mape = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    period_start = Column(DateTime)
    period_end = Column(DateTime)

    __table_args__ = (
        Index("idx_forecast_dataset_id", "dataset_id"),
    )


class Report(Base):
    """Generated reports."""

    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False, index=True)
    
    # Report info
    report_type = Column(String(50), nullable=False)  # pdf, csv, excel, business
    title = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer)
    
    # Content
    includes_quality_summary = Column(Boolean, default=True)
    includes_insights = Column(Boolean, default=True)
    includes_forecast = Column(Boolean, default=False)
    includes_recommendations = Column(Boolean, default=True)
    
    # Metadata
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_report_dataset_id", "dataset_id"),
    )
