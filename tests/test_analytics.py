"""
Tests for analytics and EDA services.

Tests exploratory data analysis, summary statistics, correlations, and insights generation.
"""

import pytest
import pandas as pd
import numpy as np
from fastapi import status
from backend.analytics.eda_engine import EDAEngine
from backend.services.analytics_service import AnalyticsService
from backend.services.dataset_service import DatasetService


class TestEDAEngine:
    """Tests for EDAEngine."""

    def test_calculate_summary_statistics(self):
        """Test summary statistics calculation."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "amount": [100.5, 200.75, 150.25, 300.0, 250.5],
            "quantity": [5, 10, 8, 12, 15],
        })

        stats = EDAEngine.calculate_summary_statistics(df)

        assert "amount" in stats
        assert "quantity" in stats
        assert "mean" in stats["amount"]
        assert stats["amount"]["count"] == 5
        assert stats["amount"]["mean"] > 0

    def test_calculate_correlation_matrix(self):
        """Test correlation matrix calculation."""
        df = pd.DataFrame({
            "x": [1, 2, 3, 4, 5],
            "y": [2, 4, 6, 8, 10],  # Perfect correlation
            "z": [5, 4, 3, 2, 1],   # Negative correlation
        })

        corr = EDAEngine.calculate_correlation_matrix(df)

        assert "x" in corr
        assert "x" in corr["x"]
        assert corr["x"]["x"] == 1.0  # Self correlation
        assert corr["x"]["y"] > 0.9  # Strong positive correlation

    def test_analyze_distributions(self):
        """Test distribution analysis."""
        df = pd.DataFrame({
            "normal": np.random.normal(0, 1, 100),
            "uniform": np.random.uniform(0, 10, 100),
        })

        distributions = EDAEngine.analyze_distributions(df)

        assert "normal" in distributions
        assert "distribution_type" in distributions["normal"]

    def test_analyze_categorical_distributions(self):
        """Test categorical distribution analysis."""
        df = pd.DataFrame({
            "category": ["A", "B", "A", "C", "B", "A"],
            "status": ["Active", "Inactive", "Active", "Active"],
        })

        dist = EDAEngine.analyze_categorical_distributions(df)

        assert "category" in dist
        assert "top_categories" in dist["category"]

    def test_calculate_top_categories(self):
        """Test top categories extraction."""
        df = pd.DataFrame({
            "product": ["A", "B", "A", "C", "A", "B", "A", "D"],
        })

        top = EDAEngine.calculate_top_categories(df, top_n=3)

        assert "product" in top
        assert len(top["product"]) <= 3
        assert top["product"][0]["category"] == "A"

    def test_analyze_growth_trends(self):
        """Test growth trend analysis."""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=90, freq="D"),
            "revenue": np.random.uniform(100, 1000, 90),
        })

        trends = EDAEngine.analyze_growth_trends(df, "date", "revenue")

        assert "monthly" in trends or "yearly" in trends

    def test_generate_insights(self):
        """Test insight generation."""
        df = pd.DataFrame({
            "id": range(100),
            "amount": np.random.uniform(100, 1000, 100),
            "category": np.random.choice(["A", "B", "C"], 100),
        })

        summary_stats = EDAEngine.calculate_summary_statistics(df)
        correlations = EDAEngine.calculate_correlation_matrix(df)

        insights = EDAEngine.generate_insights(df, summary_stats, correlations)

        assert isinstance(insights, list)
        assert len(insights) > 0
        assert any("Dataset contains" in insight for insight in insights)

    def test_generate_eda_report_complete(self):
        """Test complete EDA report generation."""
        df = pd.DataFrame({
            "id": range(1, 101),
            "date": pd.date_range("2024-01-01", periods=100, freq="D"),
            "amount": np.random.uniform(100, 1000, 100),
            "category": np.random.choice(["A", "B", "C"], 100),
            "quantity": np.random.randint(1, 20, 100),
        })

        report = EDAEngine.generate_eda_report(df)

        assert "dataset_shape" in report
        assert "summary_statistics" in report
        assert "correlation_matrix" in report
        assert "distributions" in report
        assert "generated_insights" in report
        assert report["dataset_shape"]["rows"] == 100
        assert report["dataset_shape"]["columns"] == 5


class TestAnalyticsService:
    """Tests for AnalyticsService."""

    def test_generate_eda_analysis(self, db, test_user, sample_csv_file):
        """Test EDA analysis generation."""
        # Create dataset first
        success, dataset, _ = DatasetService.create_dataset(
            db=db,
            user_id=test_user.id,
            file_path=str(sample_csv_file),
            name="Test",
        )

        success, analytics, error = AnalyticsService.generate_eda_analysis(
            db, dataset.id
        )

        assert success
        assert analytics is not None
        assert analytics.summary_stats is not None
        assert error is None

    def test_get_latest_eda_analysis(self, db, test_user, sample_csv_file):
        """Test getting latest EDA analysis."""
        success, dataset, _ = DatasetService.create_dataset(
            db=db,
            user_id=test_user.id,
            file_path=str(sample_csv_file),
            name="Test",
        )

        AnalyticsService.generate_eda_analysis(db, dataset.id)

        analytics = AnalyticsService.get_latest_eda_analysis(db, dataset.id)

        assert analytics is not None
        assert analytics.dataset_id == dataset.id

    def test_calculate_kpis(self):
        """Test KPI calculation."""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30, freq="D"),
            "amount": np.random.uniform(100, 1000, 30),
            "quantity": np.random.randint(1, 20, 30),
        })

        kpis = AnalyticsService.calculate_kpis(
            df, "date", "amount", "quantity"
        )

        assert "total_rows" in kpis
        assert "total_revenue" in kpis
        assert "average_transaction_value" in kpis
        assert "total_quantity" in kpis
        assert kpis["total_rows"] == 30

    def test_get_column_insights(self):
        """Test column insights extraction."""
        df = pd.DataFrame({
            "amount": [100, 200, 150, 300, 250],
            "category": ["A", "B", "A", "C", "B"],
        })

        numeric_insights = AnalyticsService.get_column_insights(df, "amount")
        assert "mean" in numeric_insights
        assert numeric_insights["unique_values"] == 5

        categorical_insights = AnalyticsService.get_column_insights(df, "category")
        assert "top_values" in categorical_insights

    def test_compare_columns(self):
        """Test column comparison."""
        df = pd.DataFrame({
            "x": [1, 2, 3, 4, 5],
            "y": [2, 4, 6, 8, 10],
        })

        comparison = AnalyticsService.compare_columns(df, "x", "y")

        assert "correlation" in comparison
        assert comparison["column1"] == "x"
        assert comparison["column2"] == "y"


class TestAnalyticsRoutes:
    """Tests for analytics API routes."""

    def test_generate_eda_analysis_route(self, client, auth_headers, sample_csv_file):
        """Test EDA analysis route."""
        # Upload dataset
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        # Generate EDA
        response = client.post(
            f"/api/analytics/datasets/{dataset_id}/eda",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "analytics_id" in data
        assert "summary_statistics" in data
        assert "insights" in data

    def test_get_eda_analysis_route(self, client, auth_headers, sample_csv_file):
        """Test getting EDA analysis."""
        # Upload and generate EDA
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        client.post(
            f"/api/analytics/datasets/{dataset_id}/eda",
            headers=auth_headers,
        )

        # Get EDA
        response = client.get(
            f"/api/analytics/datasets/{dataset_id}/eda",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "summary_statistics" in data
        assert "generated_insights" in data

    def test_get_data_summary_route(self, client, auth_headers, sample_csv_file):
        """Test data summary route."""
        # Upload dataset
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        # Get summary
        response = client.get(
            f"/api/analytics/datasets/{dataset_id}/summary",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_rows" in data
        assert "total_columns" in data
        assert "column_names" in data

    def test_get_column_analysis_route(self, client, auth_headers, sample_csv_file):
        """Test column analysis route."""
        # Upload dataset
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        # Get column analysis
        response = client.get(
            f"/api/analytics/datasets/{dataset_id}/column/id",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "column_analysis" in data

    def test_compare_columns_route(self, client, auth_headers, sample_csv_file):
        """Test column comparison route."""
        # Upload dataset
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        # Compare columns
        response = client.get(
            f"/api/analytics/datasets/{dataset_id}/compare?column1=id&column2=amount",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "comparison" in data

    def test_get_insights_route(self, client, auth_headers, sample_csv_file):
        """Test insights route."""
        # Upload and generate EDA
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
                data={"name": "Test"},
                headers=auth_headers,
            )

        dataset_id = upload_response.json()["id"]

        client.post(
            f"/api/analytics/datasets/{dataset_id}/eda",
            headers=auth_headers,
        )

        # Get insights
        response = client.get(
            f"/api/analytics/datasets/{dataset_id}/insights",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "insights" in data
        assert isinstance(data["insights"], list)

    def test_analytics_nonexistent_dataset(self, client, auth_headers):
        """Test analytics on non-existent dataset."""
        response = client.post(
            "/api/analytics/datasets/nonexistent/eda",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_analytics_without_auth(self, client, sample_csv_file):
        """Test analytics without authentication."""
        response = client.post(
            "/api/analytics/datasets/some-id/eda",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
