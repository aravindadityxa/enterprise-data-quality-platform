"""
Tests for data validation service and routes.

Tests data quality checking, validation reports, and scoring.
"""

import pytest
import pandas as pd
from fastapi import status
from backend.validation.quality_engine import QualityEngine
from backend.services.validation_service import ValidationService


class TestQualityEngine:
    """Tests for QualityEngine."""

    def test_validate_completeness(self):
        """Test completeness validation."""
        df = pd.DataFrame({
            "id": [1, 2, 3, None],
            "name": ["Alice", "Bob", None, "Dave"],
            "email": ["a@test.com", "b@test.com", "c@test.com", "d@test.com"],
        })

        result = QualityEngine.validate_completeness(df)

        assert "score" in result
        assert result["total_null_cells"] == 2
        assert result["score"] < 100

    def test_validate_uniqueness(self):
        """Test uniqueness validation."""
        df = pd.DataFrame({
            "id": [1, 1, 2, 3],
            "name": ["Alice", "Alice", "Bob", "Charlie"],
        })

        result = QualityEngine.validate_uniqueness(df)

        assert result["duplicate_rows"] == 1
        assert result["duplicate_percentage"] > 0

    def test_validate_consistency(self):
        """Test consistency validation."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "amount": [100.5, "200", 300.5],  # Mixed types
        })

        result = QualityEngine.validate_consistency(df)

        assert "issues" in result
        assert len(result["issues"]) >= 0

    def test_validate_emails(self):
        """Test email validation."""
        df = pd.DataFrame({
            "email": ["valid@test.com", "invalid-email", "another@test.com"],
        })

        result = QualityEngine.validate_emails(df)

        assert "invalid_emails_count" in result

    def test_validate_outliers(self):
        """Test outlier detection."""
        df = pd.DataFrame({
            "amount": [100, 105, 110, 115, 1000],  # 1000 is outlier
        })

        result = QualityEngine.validate_outliers(df)

        assert "outliers_count" in result

    def test_generate_validation_report(self):
        """Test complete validation report generation."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "email": ["a@test.com", "b@test.com", "c@test.com"],
            "amount": [100.5, 200.75, 150.25],
        })

        report = QualityEngine.generate_validation_report(df)

        assert "overall_quality_score" in report
        assert "validation_status" in report
        assert "dimensions" in report
        assert "detailed_checks" in report
        assert report["overall_quality_score"] >= 0
        assert report["overall_quality_score"] <= 100
        assert report["validation_status"] in ["pass", "warning", "fail"]

    def test_validation_report_with_issues(self):
        """Test validation report with data quality issues."""
        df = pd.DataFrame({
            "id": [1, 1, None, None],  # Duplicates and nulls
            "email": ["invalid", None, None, None],  # Invalid email
            "amount": [-100, 200, 300, 5000],  # Negative and outlier
        })

        report = QualityEngine.generate_validation_report(df)

        assert report["summary"]["critical_issues"] > 0 or report["summary"]["warning_issues"] > 0


class TestValidationService:
    """Tests for ValidationService."""

    def test_validate_dataset(self, db, test_user, sample_csv_file):
        """Test dataset validation."""
        from backend.services.dataset_service import DatasetService

        # Create dataset first
        success, dataset, _ = DatasetService.create_dataset(
            db=db,
            user_id=test_user.id,
            file_path=str(sample_csv_file),
            name="Test",
        )

        # Validate
        success, validation, error = ValidationService.validate_dataset(
            db, dataset.id
        )

        assert success
        assert validation is not None
        assert validation.quality_score is not None
        assert error is None

    def test_get_latest_validation(self, db, test_user, sample_csv_file):
        """Test getting latest validation."""
        from backend.services.dataset_service import DatasetService

        success, dataset, _ = DatasetService.create_dataset(
            db=db,
            user_id=test_user.id,
            file_path=str(sample_csv_file),
            name="Test",
        )

        ValidationService.validate_dataset(db, dataset.id)

        validation = ValidationService.get_latest_validation(db, dataset.id)

        assert validation is not None
        assert validation.dataset_id == dataset.id

    def test_get_quality_summary(self, db, test_user, sample_csv_file):
        """Test quality summary generation."""
        from backend.services.dataset_service import DatasetService

        success, dataset, _ = DatasetService.create_dataset(
            db=db,
            user_id=test_user.id,
            file_path=str(sample_csv_file),
            name="Test",
        )

        ValidationService.validate_dataset(db, dataset.id)

        summary = ValidationService.generate_quality_summary(db, dataset.id)

        assert summary is not None
        assert "overall_quality_score" in summary
        assert "completeness_score" in summary
        assert "recommendations" in summary

    def test_batch_validate(self, db, test_user, sample_csv_file):
        """Test batch validation."""
        from backend.services.dataset_service import DatasetService

        # Create multiple datasets
        dataset_ids = []
        for i in range(3):
            success, dataset, _ = DatasetService.create_dataset(
                db=db,
                user_id=test_user.id,
                file_path=str(sample_csv_file),
                name=f"Dataset {i}",
            )
            dataset_ids.append(dataset.id)

        successful, failed = ValidationService.batch_validate_datasets(db, dataset_ids)

        assert successful == 3
        assert failed == 0


class TestValidationRoutes:
    """Tests for validation API routes."""

    def test_validate_dataset_route(self, client, auth_headers, sample_csv_file):
        """Test dataset validation route."""
        # Upload dataset
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        # Validate
        response = client.post(
            f"/api/validation/datasets/{dataset_id}/validate",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "validation_id" in data
        assert "quality_score" in data

    def test_get_latest_validation_route(self, client, auth_headers, sample_csv_file):
        """Test getting latest validation."""
        # Upload and validate
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        client.post(
            f"/api/validation/datasets/{dataset_id}/validate",
            headers=auth_headers,
        )

        # Get latest validation
        response = client.get(
            f"/api/validation/datasets/{dataset_id}/latest",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["dataset_id"] == dataset_id
        assert "quality_score" in data

    def test_get_validation_history(self, client, auth_headers, sample_csv_file):
        """Test getting validation history."""
        # Upload and validate
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        client.post(
            f"/api/validation/datasets/{dataset_id}/validate",
            headers=auth_headers,
        )

        # Get history
        response = client.get(
            f"/api/validation/datasets/{dataset_id}/history",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["dataset_id"] == dataset_id
        assert "validations" in data

    def test_get_quality_report_route(self, client, auth_headers, sample_csv_file):
        """Test quality report route."""
        # Upload and validate
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        client.post(
            f"/api/validation/datasets/{dataset_id}/validate",
            headers=auth_headers,
        )

        # Get report
        response = client.get(
            f"/api/validation/datasets/{dataset_id}/report",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "overall_quality_score" in data
        assert "completeness" in data
        assert "recommendations" in data

    def test_batch_validate_route(self, client, auth_headers, sample_csv_file):
        """Test batch validation route."""
        # Upload multiple datasets
        dataset_ids = []
        for i in range(2):
            with open(sample_csv_file, "rb") as f:
                upload_response = client.post(
                    "/api/datasets/upload",
                    files={"file": ("sample.csv", f, "text/csv")},
                    data={"name": f"Dataset {i}"},
                    headers=auth_headers,
                )
            dataset_ids.append(upload_response.json()["id"])

        # Batch validate
        response = client.post(
            "/api/validation/batch-validate",
            json={"dataset_ids": dataset_ids},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "complete"
        assert data["successful"] == 2

    def test_validate_nonexistent_dataset(self, client, auth_headers):
        """Test validating non-existent dataset."""
        response = client.post(
            "/api/validation/datasets/nonexistent/validate",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_validation_without_auth(self, client, sample_csv_file):
        """Test validation without authentication."""
        response = client.post(
            "/api/validation/datasets/some-id/validate",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
