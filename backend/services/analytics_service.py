"""
Analytics service for EDA and KPI generation.

Orchestrates exploratory data analysis and key performance indicator calculation.
"""

from datetime import datetime
from typing import Optional, Tuple, Dict, Any
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from backend.database.models import Dataset, Analytics
from backend.analytics.eda_engine import EDAEngine
from backend.utils.file_handler import FileHandler
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class AnalyticsService:
    """Service for analytics and EDA operations."""

    @staticmethod
    def generate_eda_analysis(
        db: Session,
        dataset_id: str,
    ) -> Tuple[bool, Optional[Analytics], Optional[str]]:
        """
        Generate EDA analysis for dataset.

        Args:
            db: Database session
            dataset_id: Dataset ID

        Returns:
            Tuple of (success, analytics_object, error_message)
        """
        try:
            # Get dataset
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

            if not dataset:
                return False, None, "Dataset not found"

            # Load data
            df = FileHandler.load_dataframe(dataset.file_path)

            # Generate EDA report
            report = EDAEngine.generate_eda_report(df)

            # Create analytics record
            analytics = Analytics(
                dataset_id=dataset_id,
                summary_stats=report["summary_statistics"],
                correlation_matrix=report["correlation_matrix"],
                column_distributions=report["distributions"],
                top_categories=report["top_categories"],
                growth_trends=report["growth_trends"],
                generated_insights=report["generated_insights"],
            )

            db.add(analytics)
            db.commit()
            db.refresh(analytics)

            logger.info(f"EDA analysis created: {analytics.id}")
            return True, analytics, None

        except Exception as e:
            db.rollback()
            logger.error(f"EDA analysis error: {e}")
            return False, None, str(e)

    @staticmethod
    def get_eda_analysis(db: Session, analytics_id: str) -> Optional[Analytics]:
        """
        Get EDA analysis by ID.

        Args:
            db: Database session
            analytics_id: Analytics ID

        Returns:
            Optional[Analytics]: Analytics object or None
        """
        try:
            return db.query(Analytics).filter(Analytics.id == analytics_id).first()
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return None

    @staticmethod
    def get_latest_eda_analysis(db: Session, dataset_id: str) -> Optional[Analytics]:
        """
        Get latest EDA analysis for dataset.

        Args:
            db: Database session
            dataset_id: Dataset ID

        Returns:
            Optional[Analytics]: Latest analytics object
        """
        try:
            return db.query(Analytics).filter(
                Analytics.dataset_id == dataset_id
            ).order_by(Analytics.created_at.desc()).first()
        except Exception as e:
            logger.error(f"Error getting latest analytics: {e}")
            return None

    @staticmethod
    def calculate_kpis(
        df: pd.DataFrame,
        date_column: Optional[str] = None,
        amount_column: Optional[str] = None,
        quantity_column: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate business KPIs from dataset.

        Args:
            df: DataFrame to analyze
            date_column: Date column name
            amount_column: Amount/revenue column name
            quantity_column: Quantity column name

        Returns:
            dict: Calculated KPIs
        """
        kpis = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
        }

        # Try to find date column if not provided
        if not date_column:
            date_cols = [col for col in df.columns if "date" in col.lower()]
            if date_cols:
                date_column = date_cols[0]

        # Try to find amount column if not provided
        if not amount_column:
            amount_cols = [col for col in df.columns if "amount" in col.lower() or "revenue" in col.lower() or "total" in col.lower()]
            if amount_cols:
                amount_column = amount_cols[0]

        # Try to find quantity column if not provided
        if not quantity_column:
            qty_cols = [col for col in df.columns if "quantity" in col.lower() or "qty" in col.lower()]
            if qty_cols:
                quantity_column = qty_cols[0]

        # Financial KPIs
        if amount_column and amount_column in df.columns:
            numeric_amount = pd.to_numeric(df[amount_column], errors="coerce")
            kpis["total_revenue"] = float(numeric_amount.sum())
            kpis["average_transaction_value"] = float(numeric_amount.mean())
            kpis["max_transaction"] = float(numeric_amount.max())
            kpis["min_transaction"] = float(numeric_amount.min())

        # Time-based KPIs
        if date_column and date_column in df.columns:
            try:
                df_temp = df.copy()
                df_temp[date_column] = pd.to_datetime(df_temp[date_column], errors="coerce")

                # Date range
                min_date = df_temp[date_column].min()
                max_date = df_temp[date_column].max()

                if pd.notna(min_date) and pd.notna(max_date):
                    kpis["date_range_start"] = str(min_date.date())
                    kpis["date_range_end"] = str(max_date.date())
                    kpis["days_covered"] = (max_date - min_date).days

                    # Monthly metrics
                    if amount_column and amount_column in df.columns:
                        df_temp["month"] = df_temp[date_column].dt.to_period("M")
                        monthly_revenue = df_temp.groupby("month")[amount_column].sum()
                        kpis["monthly_average_revenue"] = float(monthly_revenue.mean())

            except Exception as e:
                logger.warning(f"Could not calculate time-based KPIs: {e}")

        # Quantity KPIs
        if quantity_column and quantity_column in df.columns:
            numeric_qty = pd.to_numeric(df[quantity_column], errors="coerce")
            kpis["total_quantity"] = float(numeric_qty.sum())
            kpis["average_quantity"] = float(numeric_qty.mean())

        logger.info(f"Calculated {len(kpis)} KPIs")
        return kpis

    @staticmethod
    def get_column_insights(df: pd.DataFrame, column: str) -> Dict[str, Any]:
        """
        Get detailed insights for a specific column.

        Args:
            df: DataFrame
            column: Column name

        Returns:
            dict: Column-specific insights
        """
        if column not in df.columns:
            return {"error": "Column not found"}

        insights = {
            "column_name": column,
            "data_type": str(df[column].dtype),
            "non_null_count": int(df[column].notna().sum()),
            "null_count": int(df[column].isnull().sum()),
            "unique_values": int(df[column].nunique()),
        }

        if pd.api.types.is_numeric_dtype(df[column]):
            numeric_col = pd.to_numeric(df[column], errors="coerce")
            insights.update({
                "mean": float(numeric_col.mean()),
                "median": float(numeric_col.median()),
                "std": float(numeric_col.std()),
                "min": float(numeric_col.min()),
                "max": float(numeric_col.max()),
                "q25": float(numeric_col.quantile(0.25)),
                "q75": float(numeric_col.quantile(0.75)),
            })

        elif pd.api.types.is_object_dtype(df[column]):
            value_counts = df[column].value_counts().head(5)
            insights["top_values"] = value_counts.to_dict()

        return insights

    @staticmethod
    def compare_columns(
        df: pd.DataFrame,
        column1: str,
        column2: str,
    ) -> Dict[str, Any]:
        """
        Compare two columns in dataset.

        Args:
            df: DataFrame
            column1: First column name
            column2: Second column name

        Returns:
            dict: Comparison results
        """
        if column1 not in df.columns or column2 not in df.columns:
            return {"error": "One or both columns not found"}

        comparison = {
            "column1": column1,
            "column2": column2,
        }

        # Calculate correlation if both numeric
        if pd.api.types.is_numeric_dtype(df[column1]) and pd.api.types.is_numeric_dtype(df[column2]):
            correlation = df[column1].corr(df[column2])
            comparison["correlation"] = float(correlation)

        # Compare value distributions
        comp1_unique = df[column1].nunique()
        comp2_unique = df[column2].nunique()

        comparison["column1_unique_values"] = int(comp1_unique)
        comparison["column2_unique_values"] = int(comp2_unique)
        comparison["column1_null_count"] = int(df[column1].isnull().sum())
        comparison["column2_null_count"] = int(df[column2].isnull().sum())

        return comparison
