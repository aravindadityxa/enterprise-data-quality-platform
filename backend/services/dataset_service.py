"""
Dataset upload and management service.

Handles file uploads, data profiling, and dataset metadata management.
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from backend.database.models import Dataset, User
from backend.utils.file_handler import FileHandler
from backend.utils.logger import setup_logger
from backend.config import get_settings

logger = setup_logger(__name__)
settings = get_settings()


class DatasetService:
    """Service for dataset operations."""

    @staticmethod
    def analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze DataFrame and extract profile information.

        Args:
            df: Pandas DataFrame to analyze

        Returns:
            dict: Profile information including stats and metadata

        Note:
            Provides comprehensive profiling without modifying the data.
        """
        profile = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "column_names": df.columns.tolist(),
            "data_types": {col: str(df[col].dtype) for col in df.columns},
            "null_counts": df.isnull().sum().to_dict(),
            "null_percentage": round((df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100, 2),
            "duplicate_rows": len(df[df.duplicated()]),
            "duplicate_percentage": round((len(df[df.duplicated()]) / len(df)) * 100, 2) if len(df) > 0 else 0,
            "memory_usage_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
            "unique_values": {col: df[col].nunique() for col in df.columns},
            "missing_columns": [],  # Track columns with missing values
            "numeric_columns": df.select_dtypes(include=[np.number]).columns.tolist(),
            "categorical_columns": df.select_dtypes(include=["object"]).columns.tolist(),
        }

        # Identify columns with missing values
        profile["missing_columns"] = [
            col for col in df.columns if df[col].isnull().any()
        ]

        # Calculate additional statistics for numeric columns
        numeric_df = df.select_dtypes(include=[np.number])
        if not numeric_df.empty:
            profile["numeric_stats"] = {
                col: {
                    "mean": float(df[col].mean()) if not pd.isna(df[col].mean()) else None,
                    "median": float(df[col].median()) if not pd.isna(df[col].median()) else None,
                    "std": float(df[col].std()) if not pd.isna(df[col].std()) else None,
                    "min": float(df[col].min()) if not pd.isna(df[col].min()) else None,
                    "max": float(df[col].max()) if not pd.isna(df[col].max()) else None,
                    "q25": float(df[col].quantile(0.25)) if not pd.isna(df[col].quantile(0.25)) else None,
                    "q75": float(df[col].quantile(0.75)) if not pd.isna(df[col].quantile(0.75)) else None,
                }
                for col in numeric_df.columns
            }

        return profile

    @staticmethod
    def create_dataset(
        db: Session,
        user_id: str,
        file_path: str,
        name: str,
        description: Optional[str] = None,
    ) -> Tuple[bool, Dataset, Optional[str]]:
        """
        Create dataset record after file upload.

        Args:
            db: Database session
            user_id: Owner user ID
            file_path: Path to uploaded file
            name: Dataset name
            description: Optional description

        Returns:
            Tuple of (success, dataset_object, error_message)
        """
        try:
            # Get file info
            file_size = FileHandler.get_file_size(file_path)
            file_type = FileHandler.get_file_extension(file_path)

            # Load and analyze
            df = FileHandler.load_dataframe(file_path)
            profile = DatasetService.analyze_dataframe(df)

            # Create dataset record
            dataset = Dataset(
                name=name,
                description=description,
                owner_id=user_id,
                file_path=file_path,
                file_type=file_type,
                file_size_bytes=file_size,
                total_rows=profile["total_rows"],
                total_columns=profile["total_columns"],
                column_names=profile["column_names"],
                data_types=profile["data_types"],
                null_counts=profile["null_counts"],
                null_percentage=profile["null_percentage"],
                duplicate_rows=profile["duplicate_rows"],
                duplicate_percentage=profile["duplicate_percentage"],
                profile_report=profile,
                quality_score=None,  # Will be calculated after validation
            )

            db.add(dataset)
            db.commit()
            db.refresh(dataset)

            logger.info(f"Dataset created: {dataset.id} for user {user_id}")
            return True, dataset, None

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating dataset: {e}")
            return False, None, str(e)

    @staticmethod
    def get_dataset(db: Session, dataset_id: str, user_id: Optional[str] = None) -> Optional[Dataset]:
        """
        Get dataset by ID with optional owner verification.

        Args:
            db: Database session
            dataset_id: Dataset ID
            user_id: Optional user ID for ownership check

        Returns:
            Optional[Dataset]: Dataset object or None
        """
        query = db.query(Dataset).filter(Dataset.id == dataset_id)

        if user_id:
            query = query.filter(Dataset.owner_id == user_id)

        return query.first()

    @staticmethod
    def list_datasets(
        db: Session,
        user_id: str,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
    ) -> Tuple[int, list]:
        """
        List datasets for a user with pagination.

        Args:
            db: Database session
            user_id: Owner user ID
            page: Page number (1-indexed)
            page_size: Items per page
            search: Optional search term for dataset name

        Returns:
            Tuple of (total_count, datasets_list)
        """
        query = db.query(Dataset).filter(Dataset.owner_id == user_id)

        if search:
            query = query.filter(Dataset.name.ilike(f"%{search}%"))

        total = query.count()
        datasets = (
            query.order_by(Dataset.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return total, datasets

    @staticmethod
    def update_dataset(
        db: Session,
        dataset_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dataset], Optional[str]]:
        """
        Update dataset metadata.

        Args:
            db: Database session
            dataset_id: Dataset ID
            name: Optional new name
            description: Optional new description

        Returns:
            Tuple of (success, dataset_object, error_message)
        """
        try:
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

            if not dataset:
                return False, None, "Dataset not found"

            if name:
                dataset.name = name
            if description is not None:
                dataset.description = description

            dataset.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(dataset)

            logger.info(f"Dataset updated: {dataset_id}")
            return True, dataset, None

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating dataset: {e}")
            return False, None, str(e)

    @staticmethod
    def delete_dataset(db: Session, dataset_id: str) -> Tuple[bool, Optional[str]]:
        """
        Delete dataset and associated files.

        Args:
            db: Database session
            dataset_id: Dataset ID

        Returns:
            Tuple of (success, error_message)
        """
        try:
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

            if not dataset:
                return False, "Dataset not found"

            # Delete file
            if os.path.exists(dataset.file_path):
                FileHandler.delete_file(dataset.file_path)

            # Delete from database (cascade will handle validations and analytics)
            db.delete(dataset)
            db.commit()

            logger.info(f"Dataset deleted: {dataset_id}")
            return True, None

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting dataset: {e}")
            return False, str(e)

    @staticmethod
    def get_dataset_dataframe(dataset_id: str) -> Optional[pd.DataFrame]:
        """
        Load dataset into DataFrame.

        Args:
            dataset_id: Dataset ID
            db: Database session (would be added if needed)

        Returns:
            Optional[pd.DataFrame]: DataFrame or None
        """
        try:
            # This would normally fetch from DB first
            # Placeholder for getting file path from dataset
            return None
        except Exception as e:
            logger.error(f"Error loading dataset DataFrame: {e}")
            return None

    @staticmethod
    def get_dataset_sample(
        db: Session, dataset_id: str, rows: int = 100
    ) -> Optional[pd.DataFrame]:
        """
        Get sample of dataset rows.

        Args:
            db: Database session
            dataset_id: Dataset ID
            rows: Number of rows to return

        Returns:
            Optional[pd.DataFrame]: Sample DataFrame
        """
        try:
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

            if not dataset:
                return None

            df = FileHandler.load_dataframe(dataset.file_path)
            return df.head(rows)

        except Exception as e:
            logger.error(f"Error getting dataset sample: {e}")
            return None

    @staticmethod
    def export_dataset(
        db: Session, dataset_id: str, format: str = "csv"
    ) -> Tuple[bool, Optional[bytes], Optional[str]]:
        """
        Export dataset in specified format.

        Args:
            db: Database session
            dataset_id: Dataset ID
            format: Export format (csv, xlsx, json)

        Returns:
            Tuple of (success, file_bytes, error_message)
        """
        try:
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

            if not dataset:
                return False, None, "Dataset not found"

            df = FileHandler.load_dataframe(dataset.file_path)

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
            logger.error(f"Error exporting dataset: {e}")
            return False, None, str(e)

    @staticmethod
    def detect_encoding(file_path: str) -> str:
        """
        Detect file encoding.

        Args:
            file_path: Path to file

        Returns:
            str: Detected encoding
        """
        try:
            import chardet
            with open(file_path, "rb") as f:
                result = chardet.detect(f.read())
            return result.get("encoding", "utf-8")
        except Exception:
            return "utf-8"

    @staticmethod
    def infer_data_types(df: pd.DataFrame) -> Dict[str, str]:
        """
        Infer and suggest appropriate data types.

        Args:
            df: DataFrame to analyze

        Returns:
            dict: Suggested data types per column
        """
        inferred_types = {}

        for col in df.columns:
            # Skip empty columns
            if df[col].isnull().all():
                inferred_types[col] = "unknown"
                continue

            # Get non-null values
            non_null = df[col].dropna()

            if non_null.empty:
                inferred_types[col] = "unknown"
                continue

            # Try to infer type
            if pd.api.types.is_numeric_dtype(df[col]):
                if pd.api.types.is_integer_dtype(df[col]):
                    inferred_types[col] = "integer"
                else:
                    inferred_types[col] = "float"
            elif pd.api.types.is_bool_dtype(df[col]):
                inferred_types[col] = "boolean"
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                inferred_types[col] = "datetime"
            else:
                # Try to convert to datetime
                try:
                    pd.to_datetime(non_null.iloc[:5])
                    inferred_types[col] = "datetime"
                except Exception:
                    inferred_types[col] = "string"

        return inferred_types
