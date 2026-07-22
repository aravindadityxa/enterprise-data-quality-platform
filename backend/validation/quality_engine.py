"""
Data quality validation engine.

Performs comprehensive data validation checks and generates quality scores.
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
from backend.utils.validators import (
    validate_email,
    validate_phone,
    validate_date,
    validate_negative_quantity,
)
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class QualityEngine:
    """Engine for data quality validation and scoring."""

    # Quality score weights
    WEIGHTS = {
        "completeness": 0.25,      # Non-null percentage
        "uniqueness": 0.15,        # Duplicate rows
        "consistency": 0.20,       # Data type consistency
        "validity": 0.25,          # Valid format data
        "accuracy": 0.15,          # Outliers and anomalies
    }

    @staticmethod
    def validate_completeness(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Check data completeness (null values).

        Args:
            df: DataFrame to validate

        Returns:
            dict: Completeness metrics
        """
        total_cells = len(df) * len(df.columns)
        null_cells = df.isnull().sum().sum()
        completeness_score = ((total_cells - null_cells) / total_cells * 100) if total_cells > 0 else 100

        null_by_column = df.isnull().sum().to_dict()
        null_percentage_by_column = {
            col: round((df[col].isnull().sum() / len(df)) * 100, 2)
            for col in df.columns
        }

        return {
            "score": round(completeness_score, 2),
            "total_null_cells": int(null_cells),
            "null_count_by_column": null_by_column,
            "null_percentage_by_column": null_percentage_by_column,
            "severity": "critical" if completeness_score < 70 else "warning" if completeness_score < 90 else "ok",
        }

    @staticmethod
    def validate_uniqueness(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Check data uniqueness (duplicates).

        Args:
            df: DataFrame to validate

        Returns:
            dict: Uniqueness metrics
        """
        duplicates = df.duplicated().sum()
        uniqueness_score = ((len(df) - duplicates) / len(df) * 100) if len(df) > 0 else 100

        # Find duplicate rows
        duplicate_mask = df.duplicated(keep=False)
        duplicate_indices = df[duplicate_mask].index.tolist()

        return {
            "score": round(uniqueness_score, 2),
            "duplicate_rows": int(duplicates),
            "duplicate_indices": duplicate_indices[:100],  # Limit to first 100
            "duplicate_percentage": round((duplicates / len(df) * 100), 2) if len(df) > 0 else 0,
            "severity": "critical" if duplicates / len(df) > 0.1 else "warning" if duplicates > 0 else "ok",
        }

    @staticmethod
    def validate_consistency(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Check data consistency (type consistency).

        Args:
            df: DataFrame to validate

        Returns:
            dict: Consistency metrics
        """
        consistency_issues = []
        consistent_columns = 0

        for col in df.columns:
            non_null = df[col].dropna()

            if non_null.empty:
                continue

            # Check if column has mixed types (excluding None/NaN)
            unique_types = set(type(x).__name__ for x in non_null)

            if len(unique_types) > 1:
                consistency_issues.append({
                    "column": col,
                    "issue": "mixed_types",
                    "types_found": list(unique_types),
                    "count": len(non_null),
                })
            else:
                consistent_columns += 1

        consistency_score = (consistent_columns / len(df.columns) * 100) if len(df.columns) > 0 else 100

        return {
            "score": round(consistency_score, 2),
            "consistent_columns": consistent_columns,
            "total_columns": len(df.columns),
            "issues": consistency_issues,
            "severity": "critical" if len(consistency_issues) > len(df.columns) * 0.3 else "warning" if consistency_issues else "ok",
        }

    @staticmethod
    def validate_emails(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate email format in dataset.

        Args:
            df: DataFrame to validate

        Returns:
            dict: Email validation results
        """
        invalid_emails = []

        for col in df.columns:
            if not any(df[col].astype(str).str.contains("@", na=False)):
                continue

            for idx, value in df[col].items():
                if pd.isna(value):
                    continue

                if not validate_email(str(value)):
                    invalid_emails.append({
                        "column": col,
                        "row_index": int(idx),
                        "value": str(value),
                    })

        return {
            "invalid_emails_count": len(invalid_emails),
            "invalid_emails": invalid_emails[:100],  # Limit results
            "severity": "warning" if invalid_emails else "ok",
        }

    @staticmethod
    def validate_phones(df: pd.DataFrame, region: str = "US") -> Dict[str, Any]:
        """
        Validate phone number format.

        Args:
            df: DataFrame to validate
            region: Phone region code

        Returns:
            dict: Phone validation results
        """
        invalid_phones = []

        for col in df.columns:
            # Simple heuristic: look for phone-like columns
            if "phone" not in col.lower() and "tel" not in col.lower():
                continue

            for idx, value in df[col].items():
                if pd.isna(value):
                    continue

                if not validate_phone(str(value), region):
                    invalid_phones.append({
                        "column": col,
                        "row_index": int(idx),
                        "value": str(value),
                    })

        return {
            "invalid_phones_count": len(invalid_phones),
            "invalid_phones": invalid_phones[:100],
            "severity": "warning" if invalid_phones else "ok",
        }

    @staticmethod
    def validate_dates(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate date format.

        Args:
            df: DataFrame to validate

        Returns:
            dict: Date validation results
        """
        invalid_dates = []

        for col in df.columns:
            # Skip if already datetime
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                continue

            # Simple heuristic for date columns
            if not any(date_keyword in col.lower() for date_keyword in ["date", "time", "created", "updated"]):
                continue

            for idx, value in df[col].items():
                if pd.isna(value):
                    continue

                if not validate_date(str(value)):
                    invalid_dates.append({
                        "column": col,
                        "row_index": int(idx),
                        "value": str(value),
                    })

        return {
            "invalid_dates_count": len(invalid_dates),
            "invalid_dates": invalid_dates[:100],
            "severity": "warning" if invalid_dates else "ok",
        }

    @staticmethod
    def validate_negative_quantities(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Check for negative quantities where they shouldn't exist.

        Args:
            df: DataFrame to validate

        Returns:
            dict: Negative quantity results
        """
        negative_quantities = []

        for col in df.columns:
            # Check numeric columns with quantity-like names
            if not pd.api.types.is_numeric_dtype(df[col]):
                continue

            if not any(q in col.lower() for q in ["quantity", "amount", "count", "price"]):
                continue

            neg_mask = df[col] < 0
            neg_rows = df[neg_mask].index.tolist()

            for idx in neg_rows:
                negative_quantities.append({
                    "column": col,
                    "row_index": int(idx),
                    "value": float(df.loc[idx, col]),
                })

        return {
            "negative_quantities_count": len(negative_quantities),
            "negative_quantities": negative_quantities[:100],
            "severity": "warning" if negative_quantities else "ok",
        }

    @staticmethod
    def validate_outliers(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect outliers using IQR method.

        Args:
            df: DataFrame to validate

        Returns:
            dict: Outlier detection results
        """
        outliers = []

        numeric_df = df.select_dtypes(include=[np.number])

        for col in numeric_df.columns:
            Q1 = numeric_df[col].quantile(0.25)
            Q3 = numeric_df[col].quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outlier_mask = (numeric_df[col] < lower_bound) | (numeric_df[col] > upper_bound)
            outlier_indices = numeric_df[outlier_mask].index.tolist()

            for idx in outlier_indices:
                outliers.append({
                    "column": col,
                    "row_index": int(idx),
                    "value": float(df.loc[idx, col]),
                    "lower_bound": float(lower_bound),
                    "upper_bound": float(upper_bound),
                })

        return {
            "outliers_count": len(outliers),
            "outliers": outliers[:100],
            "severity": "info" if outliers else "ok",
        }

    @staticmethod
    def validate_data_types(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Check for data type mismatches.

        Args:
            df: DataFrame to validate

        Returns:
            dict: Data type validation results
        """
        type_issues = []

        for col in df.columns:
            dtype = df[col].dtype

            # Check for object columns that might be numeric
            if dtype == "object":
                non_null = df[col].dropna()
                if not non_null.empty:
                    try:
                        pd.to_numeric(non_null, errors="coerce")
                        non_numeric_count = pd.to_numeric(
                            non_null, errors="coerce"
                        ).isnull().sum()

                        if non_numeric_count == 0:
                            type_issues.append({
                                "column": col,
                                "issue": "should_be_numeric",
                                "current_type": str(dtype),
                                "suggested_type": "numeric",
                            })
                    except Exception:
                        pass

        return {
            "type_mismatches_count": len(type_issues),
            "type_mismatches": type_issues,
            "severity": "warning" if type_issues else "ok",
        }

    @staticmethod
    def calculate_validity_score(
        df: pd.DataFrame,
        email_issues: int = 0,
        phone_issues: int = 0,
        date_issues: int = 0,
        total_records: int = 1,
    ) -> float:
        """
        Calculate overall validity score.

        Args:
            df: DataFrame
            email_issues: Count of invalid emails
            phone_issues: Count of invalid phones
            date_issues: Count of invalid dates
            total_records: Total number of records

        Returns:
            float: Validity score (0-100)
        """
        if total_records == 0:
            return 100.0

        total_issues = email_issues + phone_issues + date_issues
        validity_score = max(0, 100 - (total_issues / total_records * 100))

        return round(validity_score, 2)

    @staticmethod
    def generate_validation_report(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate comprehensive validation report.

        Args:
            df: DataFrame to validate

        Returns:
            dict: Complete validation report
        """
        logger.info(f"Starting validation for dataset with {len(df)} rows, {len(df.columns)} columns")

        # Run all validations
        completeness = QualityEngine.validate_completeness(df)
        uniqueness = QualityEngine.validate_uniqueness(df)
        consistency = QualityEngine.validate_consistency(df)
        emails = QualityEngine.validate_emails(df)
        phones = QualityEngine.validate_phones(df)
        dates = QualityEngine.validate_dates(df)
        negative_qty = QualityEngine.validate_negative_quantities(df)
        outliers = QualityEngine.validate_outliers(df)
        data_types = QualityEngine.validate_data_types(df)

        # Calculate validity score
        validity_score = QualityEngine.calculate_validity_score(
            df,
            email_issues=emails["invalid_emails_count"],
            phone_issues=phones["invalid_phones_count"],
            date_issues=dates["invalid_dates_count"],
            total_records=len(df),
        )

        # Calculate overall quality score
        overall_score = (
            completeness["score"] * QualityEngine.WEIGHTS["completeness"] +
            uniqueness["score"] * QualityEngine.WEIGHTS["uniqueness"] +
            consistency["score"] * QualityEngine.WEIGHTS["consistency"] +
            validity_score * QualityEngine.WEIGHTS["validity"] +
            (100 - min(len(outliers["outliers"]) / max(len(df), 1) * 100, 100)) * QualityEngine.WEIGHTS["accuracy"]
        )

        overall_score = round(overall_score, 2)

        # Determine overall status
        if overall_score >= 80:
            status = "pass"
        elif overall_score >= 60:
            status = "warning"
        else:
            status = "fail"

        report = {
            "overall_quality_score": overall_score,
            "validation_status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "dimensions": {
                "completeness": completeness,
                "uniqueness": uniqueness,
                "consistency": consistency,
                "validity": {"score": validity_score},
                "accuracy": {"outliers_count": outliers["outliers_count"]},
            },
            "detailed_checks": {
                "email_validation": emails,
                "phone_validation": phones,
                "date_validation": dates,
                "negative_quantities": negative_qty,
                "outliers": outliers,
                "data_types": data_types,
            },
            "summary": {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "critical_issues": sum(
                    1 for dim in [completeness, uniqueness, consistency]
                    if dim.get("severity") == "critical"
                ),
                "warning_issues": sum(
                    1 for check in [emails, phones, dates, negative_qty, data_types]
                    if check.get("severity") == "warning"
                ),
                "info_messages": 1 if outliers["severity"] == "info" else 0,
            },
        }

        logger.info(f"Validation complete. Overall score: {overall_score}")

        return report
