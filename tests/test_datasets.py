"""
Tests for dataset management service and routes.

Tests dataset upload, retrieval, and profile generation.
"""

import pytest
from io import BytesIO
from fastapi import status
import pandas as pd
from backend.services.dataset_service import DatasetService


class TestDatasetService:
    """Tests for DatasetService."""

    def test_analyze_dataframe(self):
        """Test DataFrame analysis."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "email": ["alice@example.com", "bob@example.com", None],
            "amount": [100.5, 200.75, 150.25],
        })

        profile = DatasetService.analyze_dataframe(df)

        assert profile["total_rows"] == 3
        assert profile["total_columns"] == 4
        assert "id" in profile["column_names"]
        assert profile["duplicate_rows"] == 0
        assert profile["null_percentage"] > 0  # email has one null

    def test_analyze_dataframe_with_duplicates(self):
        """Test DataFrame analysis with duplicates."""
        df = pd.DataFrame({
            "id": [1, 1, 2],
            "name": ["Alice", "Alice", "Bob"],
        })

        profile = DatasetService.analyze_dataframe(df)

        assert profile["duplicate_rows"] == 1
        assert profile["duplicate_percentage"] > 0

    def test_create_dataset(self, db, test_user, sample_csv_file):
        """Test dataset creation."""
        success, dataset, error = DatasetService.create_dataset(
            db=db,
            user_id=test_user.id,
            file_path=str(sample_csv_file),
            name="Test Dataset",
            description="Test Description",
        )

        assert success
        assert dataset is not None
        assert dataset.name == "Test Dataset"
        assert dataset.owner_id == test_user.id
        assert dataset.total_rows == 3
        assert dataset.total_columns == 4
        assert error is None

    def test_get_dataset(self, db, test_user, sample_csv_file):
        """Test getting dataset."""
        success, created_dataset, _ = DatasetService.create_dataset(
            db=db,
            user_id=test_user.id,
            file_path=str(sample_csv_file),
            name="Test",
        )

        retrieved_dataset = DatasetService.get_dataset(
            db, created_dataset.id, test_user.id
        )

        assert retrieved_dataset is not None
        assert retrieved_dataset.id == created_dataset.id

    def test_get_dataset_not_found(self, db, test_user):
        """Test getting non-existent dataset."""
        dataset = DatasetService.get_dataset(db, "nonexistent", test_user.id)
        assert dataset is None

    def test_list_datasets(self, db, test_user, sample_csv_file):
        """Test listing datasets."""
        # Create multiple datasets
        for i in range(3):
            DatasetService.create_dataset(
                db=db,
                user_id=test_user.id,
                file_path=str(sample_csv_file),
                name=f"Dataset {i}",
            )

        total, datasets = DatasetService.list_datasets(
            db=db, user_id=test_user.id, page=1, page_size=10
        )

        assert total == 3
        assert len(datasets) == 3

    def test_list_datasets_pagination(self, db, test_user, sample_csv_file):
        """Test dataset listing with pagination."""
        # Create 15 datasets
        for i in range(15):
            DatasetService.create_dataset(
                db=db,
                user_id=test_user.id,
                file_path=str(sample_csv_file),
                name=f"Dataset {i}",
            )

        # Get first page
        total, page1 = DatasetService.list_datasets(
            db=db, user_id=test_user.id, page=1, page_size=10
        )
        assert total == 15
        assert len(page1) == 10

        # Get second page
        total, page2 = DatasetService.list_datasets(
            db=db, user_id=test_user.id, page=2, page_size=10
        )
        assert len(page2) == 5

    def test_update_dataset(self, db, test_user, sample_csv_file):
        """Test dataset update."""
        success, dataset, _ = DatasetService.create_dataset(
            db=db,
            user_id=test_user.id,
            file_path=str(sample_csv_file),
            name="Original Name",
        )

        success, updated, error = DatasetService.update_dataset(
            db=db,
            dataset_id=dataset.id,
            name="Updated Name",
            description="New Description",
        )

        assert success
        assert updated.name == "Updated Name"
        assert updated.description == "New Description"

    def test_delete_dataset(self, db, test_user, sample_csv_file):
        """Test dataset deletion."""
        success, dataset, _ = DatasetService.create_dataset(
            db=db,
            user_id=test_user.id,
            file_path=str(sample_csv_file),
            name="To Delete",
        )

        success, error = DatasetService.delete_dataset(db, dataset.id)

        assert success
        assert error is None

        # Verify deletion
        deleted = DatasetService.get_dataset(db, dataset.id, test_user.id)
        assert deleted is None

    def test_infer_data_types(self):
        """Test data type inference."""
        df = pd.DataFrame({
            "int_col": [1, 2, 3],
            "float_col": [1.5, 2.5, 3.5],
            "str_col": ["a", "b", "c"],
            "date_col": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
        })

        inferred = DatasetService.infer_data_types(df)

        assert "integer" in inferred["int_col"]
        assert "float" in inferred["float_col"]
        assert "string" in inferred["str_col"]


class TestDatasetRoutes:
    """Tests for dataset API routes."""

    def test_upload_dataset(self, client, auth_headers, sample_csv_file):
        """Test dataset upload."""
        with open(sample_csv_file, "rb") as f:
            response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Uploaded Dataset", "description": "Test upload"},
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Uploaded Dataset"
        assert data["total_rows"] == 3

    def test_upload_dataset_invalid_format(self, client, auth_headers, tmp_path):
        """Test upload with invalid file format."""
        # Create invalid file
        file_path = tmp_path / "invalid.txt"
        file_path.write_text("invalid content")

        with open(file_path, "rb") as f:
            response = client.post(
                "/api/datasets/upload",
                files={"file": ("invalid.txt", f, "text/plain")},
                data={"name": "Invalid", "file_type": "txt"},
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_datasets(self, client, auth_headers, sample_csv_file, test_user):
        """Test listing datasets."""
        # Upload a dataset first
        with open(sample_csv_file, "rb") as f:
            client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test Dataset"},
                headers=auth_headers,
            )

        # List datasets
        response = client.get("/api/datasets", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) > 0

    def test_get_dataset(self, client, auth_headers, sample_csv_file):
        """Test getting dataset by ID."""
        # Upload dataset
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        # Get dataset
        response = client.get(f"/api/datasets/{dataset_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == dataset_id

    def test_get_dataset_not_found(self, client, auth_headers):
        """Test getting non-existent dataset."""
        response = client.get("/api/datasets/nonexistent", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_dataset(self, client, auth_headers, sample_csv_file):
        """Test updating dataset."""
        # Upload dataset
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Original"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        # Update dataset
        response = client.put(
            f"/api/datasets/{dataset_id}",
            json={"name": "Updated", "description": "New description"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated"

    def test_delete_dataset(self, client, auth_headers, sample_csv_file):
        """Test deleting dataset."""
        # Upload dataset
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "To Delete"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        # Delete dataset
        response = client.delete(f"/api/datasets/{dataset_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_get_dataset_sample(self, client, auth_headers, sample_csv_file):
        """Test getting dataset sample."""
        # Upload dataset
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Sample Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        # Get sample
        response = client.get(
            f"/api/datasets/{dataset_id}/sample?rows=2",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) <= 2

    def test_download_dataset(self, client, auth_headers, sample_csv_file):
        """Test dataset download."""
        # Upload dataset
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Download Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        # Download as CSV
        response = client.get(
            f"/api/datasets/{dataset_id}/download?format=csv",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "text/csv" in response.headers["content-type"]

    def test_unauthenticated_access(self, client, sample_csv_file):
        """Test unauthenticated access is rejected."""
        with open(sample_csv_file, "rb") as f:
            response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Unauthorized"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN
