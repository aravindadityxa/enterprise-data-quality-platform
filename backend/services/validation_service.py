"""
Data validation service.

Orchestrates validation checks and stores results in database.
"""

from datetime import datetime
from typing import Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from backend.database.models import Dataset, DataValidation
from backend.validation.quality_engine import QualityEngine
from backend.utils.file_handler import FileHandler
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class ValidationService:
    """Service for dataset validation."""

    @staticmethod
    def validate_dataset(
        db: Session,
        dataset_id: str,
    ) -> Tuple[bool, Optional[DataValidation], Optional[str]]:
        """
        Validate a dataset and store results.

        Args:
            db: Database session
            dataset_id: Dataset ID to validate

        Returns:
            Tuple of (success, validation_object, error_message)
        """
        try:
            # Get dataset
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

            if not dataset:
                return False, None, "Dataset not found"

            # Load data
            df = FileHandler.load_dataframe(dataset.file_path)

            # Run validation
            report = QualityEngine.generate_validation_report(df)

            # Extract key metrics
            completeness = report["dimensions"]["completeness"]
            uniqueness = report["dimensions"]["uniqueness"]
            consistency = report["dimensions"]["consistency"]
            emails = report["detailed_checks"]["email_validation"]
            phones = report["detailed_checks"]["phone_validation"]
            dates = report["detailed_checks"]["date_validation"]
            negative_qty = report["detailed_checks"]["negative_quantities"]
            outliers = report["detailed_checks"]["outliers"]
            data_types = report["detailed_checks"]["data_types"]

            # Create validation record
            validation = DataValidation(
                dataset_id=dataset_id,
                created_by_id=dataset.owner_id,
                missing_values_count=completeness["total_null_cells"],
                missing_values_percentage=round(100 - completeness["score"], 2),
                duplicates_count=uniqueness["duplicate_rows"],
                duplicates_percentage=uniqueness["duplicate_percentage"],
                null_percentage=round(100 - completeness["score"], 2),
                unique_values_count=dataset.profile_report.get("unique_values", {}) if dataset.profile_report else {},
                invalid_emails=emails["invalid_emails"],
                invalid_phones=phones["invalid_phones"],
                invalid_dates=dates["invalid_dates"],
                negative_quantities=negative_qty["negative_quantities"],
                data_type_mismatches=data_types["type_mismatches"],
                outliers=outliers["outliers"],
                quality_score=report["overall_quality_score"],
                validation_status=report["validation_status"],
                validation_report=report,
            )

            db.add(validation)

            # Update dataset quality score
            dataset.quality_score = report["overall_quality_score"]
            dataset.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(validation)

            logger.info(
                f"Dataset validated: {dataset_id}, Quality Score: {report['overall_quality_score']}"
            )

            return True, validation, None

        except Exception as e:
            db.rollback()
            logger.error(f"Validation error: {e}")
            return False, None, str(e)

    @staticmethod
    def get_validation(
        db: Session, validation_id: str
    ) -> Optional[DataValidation]:
        """
        Get validation record by ID.

        Args:
            db: Database session
            validation_id: Validation ID

        Returns:
            Optional[DataValidation]: Validation object or None
        """
        try:
            return db.query(DataValidation).filter(
                DataValidation.id == validation_id
            ).first()
        except Exception as e:
            logger.error(f"Error getting validation: {e}")
            return None

    @staticmethod
    def get_latest_validation(
        db: Session, dataset_id: str
    ) -> Optional[DataValidation]:
        """
        Get latest validation for dataset.

        Args:
            db: Database session
            dataset_id: Dataset ID

        Returns:
            Optional[DataValidation]: Latest validation object
        """
        try:
            return db.query(DataValidation).filter(
                DataValidation.dataset_id == dataset_id
            ).order_by(DataValidation.created_at.desc()).first()
        except Exception as e:
            logger.error(f"Error getting latest validation: {e}")
            return None

    @staticmethod
    def get_validations_for_dataset(
        db: Session, dataset_id: str, limit: int = 10
    ) -> list:
        """
        Get validation history for dataset.

        Args:
            db: Database session
            dataset_id: Dataset ID
            limit: Number of records to return

        Returns:
            list: List of validation objects
        """
        try:
            return db.query(DataValidation).filter(
                DataValidation.dataset_id == dataset_id
            ).order_by(DataValidation.created_at.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting validation history: {e}")
            return []

    @staticmethod
    def generate_quality_summary(
        db: Session, dataset_id: str
    ) -> Optional[dict]:
        """
        Generate summary of data quality for dataset.

        Args:
            db: Database session
            dataset_id: Dataset ID

        Returns:
            Optional[dict]: Quality summary or None
        """
        try:
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

            if not dataset:
                return None

            latest_validation = ValidationService.get_latest_validation(db, dataset_id)

            if not latest_validation:
                return None

            report = latest_validation.validation_report

            summary = {
                "dataset_id": dataset_id,
                "dataset_name": dataset.name,
                "analysis_date": latest_validation.created_at,
                "overall_quality_score": latest_validation.quality_score,
                "validation_status": latest_validation.validation_status,
                "completeness_score": report["dimensions"]["completeness"]["score"],
                "uniqueness_score": report["dimensions"]["uniqueness"]["score"],
                "consistency_score": report["dimensions"]["consistency"]["score"],
                "validity_score": report["dimensions"]["validity"]["score"],
                "accuracy_issues": report["dimensions"]["accuracy"]["outliers_count"],
                "total_rows": dataset.total_rows,
                "total_columns": dataset.total_columns,
                "critical_issues": report["summary"]["critical_issues"],
                "warning_issues": report["summary"]["warning_issues"],
                "recommendations": ValidationService._generate_recommendations(report),
            }

            return summary

        except Exception as e:
            logger.error(f"Error generating quality summary: {e}")
            return None

    @staticmethod
    def _generate_recommendations(report: dict) -> list:
        """
        Generate recommendations based on validation report.

        Args:
            report: Validation report

        Returns:
            list: List of recommendations
        """
        recommendations = []

        completeness = report["dimensions"]["completeness"]
        uniqueness = report["dimensions"]["uniqueness"]
        emails = report["detailed_checks"]["email_validation"]
        phones = report["detailed_checks"]["phone_validation"]
        dates = report["detailed_checks"]["date_validation"]
        negative_qty = report["detailed_checks"]["negative_quantities"]
        outliers = report["detailed_checks"]["outliers"]

        # Completeness recommendations
        if completeness["score"] < 90:
            critical_cols = [
                col for col, pct in completeness["null_percentage_by_column"].items()
                if pct > 20
            ]
            if critical_cols:
                recommendations.append(
                    f"Address missing values in columns: {', '.join(critical_cols[:3])}"
                )

        # Uniqueness recommendations
        if uniqueness["duplicate_rows"] > 0:
            recommendations.append(
                f"Remove {uniqueness['duplicate_rows']} duplicate records found in dataset"
            )

        # Email validation
        if emails["invalid_emails_count"] > 0:
            recommendations.append(
                f"Fix {emails['invalid_emails_count']} invalid email addresses"
            )

        # Phone validation
        if phones["invalid_phones_count"] > 0:
            recommendations.append(
                f"Correct {phones['invalid_phones_count']} invalid phone numbers"
            )

        # Date validation
        if dates["invalid_dates_count"] > 0:
            recommendations.append(
                f"Standardize {dates['invalid_dates_count']} invalid date formats"
            )

        # Negative quantities
        if negative_qty["negative_quantities_count"] > 0:
            recommendations.append(
                f"Review {negative_qty['negative_quantities_count']} negative quantity records"
            )

        # Outliers
        if outliers["outliers_count"] > 0:
            recommendations.append(
                f"Investigate {outliers['outliers_count']} potential outliers in numeric columns"
            )

        return recommendations

    @staticmethod
    def batch_validate_datasets(
        db: Session, dataset_ids: list
    ) -> Tuple[int, int]:
        """
        Validate multiple datasets.

        Args:
            db: Database session
            dataset_ids: List of dataset IDs

        Returns:
            Tuple of (successful_count, failed_count)
        """
        successful = 0
        failed = 0

        for dataset_id in dataset_ids:
            success, _, _ = ValidationService.validate_dataset(db, dataset_id)
            if success:
                successful += 1
            else:
                failed += 1

        logger.info(f"Batch validation: {successful} successful, {failed} failed")

        return successful, failed
