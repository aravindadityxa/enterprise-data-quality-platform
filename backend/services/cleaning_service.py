"""
Data cleaning service.

Handles data cleaning operations including deduplication, imputation, normalization, and standardization.
"""

from datetime import datetime
from typing import Optional, Tuple, Dict, Any
import pandas as pd
import numpy as np
import os
from sqlalchemy.orm import Session
from backend.database.models import Dataset, DataCleaning
from backend.utils.file_handler import FileHandler
from backend.utils.logger import setup_logger
from backend.config import get_settings

logger = setup_logger(__name__)
settings = get_settings()


class CleaningService:
    """Service for data cleaning operations."""

    @staticmethod
    def remove_duplicates(
        df: pd.DataFrame,
        subset: Optional[list] = None,
        keep: str = "first",
    ) -> Tuple[pd.DataFrame, int]:
        """
        Remove duplicate rows from DataFrame.

        Args:
            df: DataFrame to clean
            subset: Columns to consider for duplicates
            keep: Which duplicates to keep ('first', 'last', False)

        Returns:
            Tuple of (cleaned_dataframe, duplicates_removed_count)
        """
        initial_rows = len(df)
        df_cleaned = df.drop_duplicates(subset=subset, keep=keep)
        duplicates_removed = initial_rows - len(df_cleaned)

        logger.info(f"Removed {duplicates_removed} duplicate rows")
        return df_cleaned, duplicates_removed

    @staticmethod
    def fill_missing_values(
        df: pd.DataFrame,
        strategy: str = "mean",
        fill_value: Optional[Any] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """
        Fill missing values in DataFrame.

        Args:
            df: DataFrame to fill
            strategy: Strategy for filling ('mean', 'median', 'mode', 'forward_fill', 'backward_fill', 'value')
            fill_value: Value to use if strategy is 'value'

        Returns:
            Tuple of (cleaned_dataframe, filled_counts_by_column)
        """
        df_filled = df.copy()
        filled_counts = {}

        for col in df_filled.columns:
            if df_filled[col].isnull().any():
                initial_nulls = df_filled[col].isnull().sum()

                if strategy == "mean" and pd.api.types.is_numeric_dtype(df_filled[col]):
                    df_filled[col].fillna(df_filled[col].mean(), inplace=True)
                elif strategy == "median" and pd.api.types.is_numeric_dtype(df_filled[col]):
                    df_filled[col].fillna(df_filled[col].median(), inplace=True)
                elif strategy == "mode":
                    mode_value = df_filled[col].mode()
                    if not mode_value.empty:
                        df_filled[col].fillna(mode_value[0], inplace=True)
                elif strategy == "forward_fill":
                    df_filled[col].fillna(method="ffill", inplace=True)
                elif strategy == "backward_fill":
                    df_filled[col].fillna(method="bfill", inplace=True)
                elif strategy == "value" and fill_value is not None:
                    df_filled[col].fillna(fill_value, inplace=True)

                filled_counts[col] = int(initial_nulls)

        logger.info(f"Filled missing values: {filled_counts}")
        return df_filled, filled_counts

    @staticmethod
    def normalize_text(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """
        Normalize text columns (strip, lowercase, etc).

        Args:
            df: DataFrame to normalize

        Returns:
            Tuple of (normalized_dataframe, columns_normalized_count)
        """
        df_normalized = df.copy()
        normalized_count = 0

        for col in df_normalized.columns:
            if df_normalized[col].dtype == "object":
                # Strip whitespace
                df_normalized[col] = df_normalized[col].str.strip()

                # Check if column should be lowercased
                if any(keyword in col.lower() for keyword in ["email", "name", "category", "type"]):
                    df_normalized[col] = df_normalized[col].str.lower()
                    normalized_count += 1

        logger.info(f"Normalized {normalized_count} text columns")
        return df_normalized, normalized_count

    @staticmethod
    def standardize_dates(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """
        Standardize date columns to consistent format.

        Args:
            df: DataFrame to standardize

        Returns:
            Tuple of (standardized_dataframe, date_columns_standardized)
        """
        df_standardized = df.copy()
        standardized_count = 0

        date_keywords = ["date", "time", "created", "updated", "timestamp"]

        for col in df_standardized.columns:
            if any(keyword in col.lower() for keyword in date_keywords):
                if not pd.api.types.is_datetime64_any_dtype(df_standardized[col]):
                    try:
                        df_standardized[col] = pd.to_datetime(
                            df_standardized[col],
                            errors="coerce",
                        )
                        standardized_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to standardize {col}: {e}")

        logger.info(f"Standardized {standardized_count} date columns")
        return df_standardized, standardized_count

    @staticmethod
    def handle_categorical_values(
        df: pd.DataFrame,
        mapping: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Handle categorical value standardization.

        Args:
            df: DataFrame to process
            mapping: Optional mapping dict {column: {old_value: new_value}}

        Returns:
            Tuple of (processed_dataframe, standardization_info)
        """
        df_processed = df.copy()
        standardization_info = {}

        for col in df_processed.columns:
            if df_processed[col].dtype == "object":
                unique_count = df_processed[col].nunique()

                # Only process columns with reasonable number of unique values
                if unique_count < 100:
                    if mapping and col in mapping:
                        df_processed[col] = df_processed[col].replace(mapping[col])
                        standardization_info[col] = {
                            "type": "mapped",
                            "mappings": mapping[col],
                        }
                    else:
                        # Record the categories for reference
                        standardization_info[col] = {
                            "type": "categorical",
                            "unique_values": df_processed[col].unique().tolist()[:50],
                            "value_counts": df_processed[col].value_counts().to_dict(),
                        }

        logger.info(f"Processed {len(standardization_info)} categorical columns")
        return df_processed, standardization_info

    @staticmethod
    def remove_invalid_records(
        df: pd.DataFrame,
        validation_rules: Optional[Dict[str, callable]] = None,
    ) -> Tuple[pd.DataFrame, int]:
        """
        Remove records that don't meet validation criteria.

        Args:
            df: DataFrame to clean
            validation_rules: Dict of {column: validation_function}

        Returns:
            Tuple of (cleaned_dataframe, records_removed_count)
        """
        df_cleaned = df.copy()
        initial_rows = len(df_cleaned)

        if validation_rules:
            for col, validation_func in validation_rules.items():
                if col in df_cleaned.columns:
                    valid_mask = df_cleaned[col].apply(validation_func)
                    df_cleaned = df_cleaned[valid_mask]

        removed_count = initial_rows - len(df_cleaned)
        logger.info(f"Removed {removed_count} invalid records")
        return df_cleaned, removed_count

    @staticmethod
    def apply_cleaning_rules(
        df: pd.DataFrame,
        rules: Dict[str, Any],
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Apply a set of cleaning rules to DataFrame.

        Args:
            df: DataFrame to clean
            rules: Dict with cleaning rules

        Returns:
            Tuple of (cleaned_dataframe, cleaning_summary)
        """
        df_cleaned = df.copy()
        summary = {
            "removed_duplicates": 0,
            "filled_missing_values": {},
            "normalized_text_columns": 0,
            "standardized_dates": 0,
            "removed_invalid_records": 0,
            "categorical_standardization": {},
            "initial_rows": len(df),
            "final_rows": len(df),
        }

        try:
            # Remove duplicates
            if rules.get("remove_duplicates", False):
                df_cleaned, removed = CleaningService.remove_duplicates(df_cleaned)
                summary["removed_duplicates"] = removed

            # Fill missing values
            if rules.get("fill_missing", False):
                strategy = rules.get("fill_strategy", "mean")
                df_cleaned, filled = CleaningService.fill_missing_values(
                    df_cleaned, strategy
                )
                summary["filled_missing_values"] = filled

            # Normalize text
            if rules.get("normalize_text", False):
                df_cleaned, normalized = CleaningService.normalize_text(df_cleaned)
                summary["normalized_text_columns"] = normalized

            # Standardize dates
            if rules.get("standardize_dates", False):
                df_cleaned, standardized = CleaningService.standardize_dates(df_cleaned)
                summary["standardized_dates"] = standardized

            # Handle categorical values
            if rules.get("standardize_categorical", False):
                mapping = rules.get("categorical_mapping", None)
                df_cleaned, cat_info = CleaningService.handle_categorical_values(
                    df_cleaned, mapping
                )
                summary["categorical_standardization"] = cat_info

            # Remove invalid records
            if rules.get("remove_invalid", False):
                validation_rules = rules.get("validation_rules", None)
                df_cleaned, removed = CleaningService.remove_invalid_records(
                    df_cleaned, validation_rules
                )
                summary["removed_invalid_records"] = removed

            summary["final_rows"] = len(df_cleaned)

            logger.info(f"Cleaning complete. Summary: {summary}")
            return df_cleaned, summary

        except Exception as e:
            logger.error(f"Error during cleaning: {e}")
            raise

    @staticmethod
    def create_cleaning_task(
        db: Session,
        dataset_id: str,
        rules: Dict[str, Any],
    ) -> Tuple[bool, Optional[DataCleaning], Optional[str]]:
        """
        Create and execute a cleaning task.

        Args:
            db: Database session
            dataset_id: Dataset ID to clean
            rules: Cleaning rules to apply

        Returns:
            Tuple of (success, cleaning_task, error_message)
        """
        try:
            # Get dataset
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

            if not dataset:
                return False, None, "Dataset not found"

            # Create cleaning record
            cleaning_task = DataCleaning(
                dataset_id=dataset_id,
                status="processing",
                cleaning_rules=rules,
            )

            db.add(cleaning_task)
            db.commit()

            try:
                # Load data
                df = FileHandler.load_dataframe(dataset.file_path)

                # Apply cleaning rules
                df_cleaned, summary = CleaningService.apply_cleaning_rules(df, rules)

                # Save cleaned dataset
                cleaned_filename = f"{dataset_id}_cleaned.csv"
                cleaned_dir = os.path.join(settings.upload_directory, "cleaned")
                os.makedirs(cleaned_dir, exist_ok=True)
                cleaned_path = os.path.join(cleaned_dir, cleaned_filename)

                FileHandler.save_dataframe(df_cleaned, cleaned_path, "csv")

                # Update cleaning record
                cleaning_task.status = "completed"
                cleaning_task.cleaned_rows = len(df_cleaned)
                cleaning_task.cleaned_file_path = cleaned_path
                cleaning_task.removed_duplicates = summary["removed_duplicates"]
                cleaning_task.filled_missing_values = summary["filled_missing_values"].get(
                    "total", len(summary["filled_missing_values"])
                )
                cleaning_task.removed_invalid_records = summary["removed_invalid_records"]
                cleaning_task.normalized_text_columns = summary["normalized_text_columns"]
                cleaning_task.standardized_dates = summary["standardized_dates"]
                cleaning_task.completed_at = datetime.utcnow()

                db.commit()
                db.refresh(cleaning_task)

                logger.info(f"Cleaning task completed: {cleaning_task.id}")
                return True, cleaning_task, None

            except Exception as e:
                cleaning_task.status = "failed"
                cleaning_task.error_message = str(e)
                db.commit()
                logger.error(f"Cleaning task failed: {e}")
                return False, None, str(e)

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating cleaning task: {e}")
            return False, None, str(e)

    @staticmethod
    def get_cleaning_task(db: Session, cleaning_id: str) -> Optional[DataCleaning]:
        """
        Get cleaning task by ID.

        Args:
            db: Database session
            cleaning_id: Cleaning task ID

        Returns:
            Optional[DataCleaning]: Cleaning task or None
        """
        try:
            return db.query(DataCleaning).filter(DataCleaning.id == cleaning_id).first()
        except Exception as e:
            logger.error(f"Error getting cleaning task: {e}")
            return None

    @staticmethod
    def get_cleaning_history(
        db: Session, dataset_id: str, limit: int = 10
    ) -> list:
        """
        Get cleaning task history for dataset.

        Args:
            db: Database session
            dataset_id: Dataset ID
            limit: Number of records to return

        Returns:
            list: List of cleaning tasks
        """
        try:
            return db.query(DataCleaning).filter(
                DataCleaning.dataset_id == dataset_id
            ).order_by(DataCleaning.created_at.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting cleaning history: {e}")
            return []

    @staticmethod
    def download_cleaned_dataset(
        db: Session, cleaning_id: str, format: str = "csv"
    ) -> Tuple[bool, Optional[bytes], Optional[str]]:
        """
        Download cleaned dataset.

        Args:
            db: Database session
            cleaning_id: Cleaning task ID
            format: Export format (csv, xlsx, json)

        Returns:
            Tuple of (success, file_bytes, error_message)
        """
        try:
            cleaning_task = db.query(DataCleaning).filter(
                DataCleaning.id == cleaning_id
            ).first()

            if not cleaning_task:
                return False, None, "Cleaning task not found"

            if cleaning_task.status != "completed":
                return False, None, "Cleaning task not completed"

            df = FileHandler.load_dataframe(cleaning_task.cleaned_file_path)

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
            logger.error(f"Error downloading cleaned dataset: {e}")
            return False, None, str(e)
