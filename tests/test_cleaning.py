"""
Tests for data cleaning service and routes.

Tests data cleaning operations including deduplication, imputation, and normalization.
"""

import pytest
import pandas as pd
import numpy as np
from fastapi import status
from backend.services.cleaning_service import CleaningService
from backend.services.dataset_service import DatasetService


class TestCleaningService:
    """Tests for CleaningService."""

    def test_remove_duplicates(self):
        """Test duplicate removal."""
        df = pd.DataFrame({
            "id": [1, 1, 2, 3],
            "name": ["Alice", "Alice", "Bob", "Charlie"],
        })

        df_cleaned, removed = CleaningService.remove_duplicates(df)

        assert len(df_cleaned) == 3
        assert removed == 1

    def test_remove_duplicates_empty(self):
        """Test duplicate removal on dataset without duplicates."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
        })

        df_cleaned, removed = CleaningService.remove_duplicates(df)

        assert len(df_cleaned) == 3
        assert removed == 0

    def test_fill_missing_values_mean(self):
        """Test filling missing numeric values with mean."""
        df = pd.DataFrame({
            "amount": [100.0, 200.0, np.nan, 400.0],
        })

        df_filled, filled = CleaningService.fill_missing_values(df, "mean")

        assert df_filled["amount"].isnull().sum() == 0
        assert "amount" in filled

    def test_fill_missing_values_mode(self):
        """Test filling missing categorical values with mode."""
        df = pd.DataFrame({
            "category": ["A", "B", "A", None],
        })

        df_filled, filled = CleaningService.fill_missing_values(df, "mode")

        assert df_filled["category"].isnull().sum() == 0

    def test_normalize_text(self):
        """Test text normalization."""
        df = pd.DataFrame({
            "email": ["  JOHN@TEST.COM  ", "jane@test.com"],
            "name": ["  John Doe  ", "  Jane Smith  "],
        })

        df_normalized, count = CleaningService.normalize_text(df)

        assert df_normalized["email"][0] == "john@test.com"
        assert count > 0

    def test_standardize_dates(self):
        """Test date standardization."""
        df = pd.DataFrame({
            "created_date": ["2024-01-15", "2024-01-16", "2024-01-17"],
        })

        df_standardized, count = CleaningService.standardize_dates(df)

        assert pd.api.types.is_datetime64_any_dtype(df_standardized["created_date"])
        assert count == 1

    def test_handle_categorical_values(self):
        """Test categorical value handling."""
        df = pd.DataFrame({
            "status": ["Active", "Inactive", "Active", "pending"],
        })

        df_processed, info = CleaningService.handle_categorical_values(df)

        assert "status" in info
        assert "unique_values" in info["status"]

    def test_remove_invalid_records(self):
        """Test invalid record removal."""
        df = pd.DataFrame({
            "amount": [100, -50, 200, 0],  # Negative amount is invalid
        })

        validation_rules = {"amount": lambda x: x >= 0}
        df_cleaned, removed = CleaningService.remove_invalid_records(df, validation_rules)

        assert len(df_cleaned) == 3
        assert removed == 1

    def test_apply_cleaning_rules(self):
        """Test applying multiple cleaning rules."""
        df = pd.DataFrame({
            "id": [1, 1, 2, None],
            "name": ["  alice  ", "  alice  ", "  bob  ", "  charlie  "],
            "amount": [100.0, 100.0, 200.0, np.nan],
        })

        rules = {
            "remove_duplicates": True,
            "fill_missing": True,
            "normalize_text": True,
        }

        df_cleaned, summary = CleaningService.apply_cleaning_rules(df, rules)

        assert summary["removed_duplicates"] > 0
        assert summary["filled_missing_values"]
        assert len(df_cleaned) <= len(df)

    def test_apply_all_cleaning_rules(self):
        """Test comprehensive cleaning with all rules."""
        df = pd.DataFrame({
            "id": [1, 1, None, None],
            "name": ["  ALICE  ", "  ALICE  ", "  Bob  ", "  charlie  "],
            "email": ["alice@TEST.COM", "alice@TEST.COM", "bob@test.com", None],
            "created": ["2024-01-15", "2024-01-15", "2024-01-16", "2024-01-17"],
            "amount": [100.0, 100.0, 200.0, np.nan],
        })

        rules = {
            "remove_duplicates": True,
            "fill_missing": True,
            "fill_strategy": "mean",
            "normalize_text": True,
            "standardize_dates": True,
            "standardize_categorical": False,
            "remove_invalid": False,
        }

        df_cleaned, summary = CleaningService.apply_cleaning_rules(df, rules)

        assert df_cleaned.isnull().sum().sum() == 0
        assert "final_rows" in summary
        assert summary["final_rows"] <= summary["initial_rows"]


class TestCleaningServiceDB:
    """Tests for CleaningService with database."""

    def test_create_cleaning_task(self, db, test_user, sample_csv_file):
        """Test creating cleaning task."""
        # Create dataset first
        success, dataset, _ = DatasetService.create_dataset(
            db=db,
            user_id=test_user.id,
            file_path=str(sample_csv_file),
            name="Test",
        )

        rules = {
            "remove_duplicates": True,
            "fill_missing": True,
            "normalize_text": True,
        }

        success, cleaning_task, error = CleaningService.create_cleaning_task(
            db, dataset.id, rules
        )

        assert success
        assert cleaning_task is not None
        assert cleaning_task.status == "completed"
        assert cleaning_task.dataset_id == dataset.id

    def test_get_cleaning_task(self, db, test_user, sample_csv_file):
        """Test getting cleaning task."""
        success, dataset, _ = DatasetService.create_dataset(
            db=db,
            user_id=test_user.id,
            file_path=str(sample_csv_file),
            name="Test",
        )

        rules = {"remove_duplicates": True}
        success, task, _ = CleaningService.create_cleaning_task(db, dataset.id, rules)

        retrieved = CleaningService.get_cleaning_task(db, task.id)

        assert retrieved is not None
        assert retrieved.id == task.id

    def test_get_cleaning_history(self, db, test_user, sample_csv_file):
        """Test cleaning history retrieval."""
        success, dataset, _ = DatasetService.create_dataset(
            db=db,
            user_id=test_user.id,
            file_path=str(sample_csv_file),
            name="Test",
        )

        # Create multiple cleaning tasks
        for i in range(3):
            rules = {"remove_duplicates": i % 2 == 0}
            CleaningService.create_cleaning_task(db, dataset.id, rules)

        history = CleaningService.get_cleaning_history(db, dataset.id)

        assert len(history) == 3


class TestCleaningRoutes:
    """Tests for cleaning API routes."""

    def test_clean_dataset_route(self, client, auth_headers, sample_csv_file):
        """Test dataset cleaning route."""
        # Upload dataset
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        # Clean dataset
        response = client.post(
            f"/api/cleaning/datasets/{dataset_id}/clean",
            json={
                "remove_duplicates": True,
                "fill_missing": True,
                "normalize_text": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "cleaning_id" in data

    def test_get_cleaning_status(self, client, auth_headers, sample_csv_file):
        """Test getting cleaning status."""
        # Upload and clean
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        clean_response = client.post(
            f"/api/cleaning/datasets/{dataset_id}/clean",
            json={"remove_duplicates": True},
            headers=auth_headers,
        )

        cleaning_id = clean_response.json()["cleaning_id"]

        # Get status
        response = client.get(
            f"/api/cleaning/tasks/{cleaning_id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == cleaning_id
        assert data["status"] == "completed"

    def test_get_cleaning_history_route(self, client, auth_headers, sample_csv_file):
        """Test cleaning history route."""
        # Upload dataset
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        # Clean multiple times
        for _ in range(2):
            client.post(
                f"/api/cleaning/datasets/{dataset_id}/clean",
                json={"remove_duplicates": True},
                headers=auth_headers,
            )

        # Get history
        response = client.get(
            f"/api/cleaning/datasets/{dataset_id}/history",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_tasks"] >= 2

    def test_download_cleaned_dataset(self, client, auth_headers, sample_csv_file):
        """Test downloading cleaned dataset."""
        # Upload and clean
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        clean_response = client.post(
            f"/api/cleaning/datasets/{dataset_id}/clean",
            json={"remove_duplicates": True},
            headers=auth_headers,
        )

        cleaning_id = clean_response.json()["cleaning_id"]

        # Download
        response = client.get(
            f"/api/cleaning/tasks/{cleaning_id}/download?format=csv",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "text/csv" in response.headers["content-type"]

    def test_clean_nonexistent_dataset(self, client, auth_headers):
        """Test cleaning non-existent dataset."""
        response = client.post(
            "/api/cleaning/datasets/nonexistent/clean",
            json={"remove_duplicates": True},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cleaning_without_auth(self, client, sample_csv_file):
        """Test cleaning without authentication."""
        response = client.post(
            "/api/cleaning/datasets/some-id/clean",
            json={"remove_duplicates": True},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
