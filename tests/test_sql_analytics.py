"""
Tests for SQL Analytics service and routes.

Tests SQL query execution, predefined queries, and query management.
"""

import pytest
from fastapi import status
from backend.analytics.sql_queries import (
    get_query,
    list_queries,
    get_queries_by_category,
    SQL_QUERIES,
)
from backend.services.sql_service import SQLService


class TestSQLQueries:
    """Tests for SQL query definitions."""

    def test_query_count(self):
        """Test that we have 50+ queries."""
        queries = list_queries()
        assert len(queries) >= 50

    def test_get_query(self):
        """Test getting a specific query."""
        query = get_query("total_revenue")
        assert query is not None
        assert "SELECT" in query.upper()

    def test_get_nonexistent_query(self):
        """Test getting non-existent query."""
        query = get_query("nonexistent_query")
        assert query == ""

    def test_list_queries(self):
        """Test listing all queries."""
        queries = list_queries()
        assert isinstance(queries, list)
        assert len(queries) > 0
        assert "total_revenue" in queries
        assert "customer_segmentation" in queries

    def test_query_categories(self):
        """Test query categorization."""
        # Test that we have queries with specific keywords
        aggregation_queries = get_queries_by_category("SELECT")
        assert len(aggregation_queries) > 0

    def test_cte_queries(self):
        """Test CTE queries are present."""
        queries = list_queries()
        cte_queries = [q for q in queries if "cohort" in q or "churn" in q]
        assert len(cte_queries) > 0

    def test_window_function_queries(self):
        """Test window function queries are present."""
        queries = list_queries()
        window_queries = [q for q in queries if "rank" in q or "lag" in q or "percentile" in q]
        assert len(window_queries) > 0

    def test_join_queries(self):
        """Test JOIN queries are present."""
        queries = list_queries()
        assert any("customer" in q and "product" in q for q in queries)

    def test_all_queries_have_select(self):
        """Test all queries start with SELECT."""
        for query_name, query in SQL_QUERIES.items():
            if not query_name.startswith("create_"):
                assert "SELECT" in query.upper(), f"Query {query_name} doesn't have SELECT"

    def test_aggregation_queries(self):
        """Test aggregation queries."""
        aggregation_queries = [
            "total_revenue",
            "average_transaction_value",
            "transaction_count",
        ]
        for query_name in aggregation_queries:
            assert query_name in SQL_QUERIES

    def test_customer_analytics_queries(self):
        """Test customer analytics queries."""
        customer_queries = [
            "customer_segmentation",
            "repeat_customers",
            "customer_lifetime_value",
        ]
        for query_name in customer_queries:
            assert query_name in SQL_QUERIES

    def test_sales_queries(self):
        """Test sales analytics queries."""
        sales_queries = [
            "sales_by_region",
            "sales_by_category",
            "top_products",
            "top_customers",
        ]
        for query_name in sales_queries:
            assert query_name in SQL_QUERIES

    def test_time_series_queries(self):
        """Test time series queries."""
        time_queries = [
            "monthly_sales_trend",
            "month_over_month_growth",
            "year_over_year_growth",
        ]
        for query_name in time_queries:
            assert query_name in SQL_QUERIES


class TestSQLService:
    """Tests for SQLService."""

    def test_get_available_queries(self):
        """Test getting available queries."""
        queries = SQLService.get_available_queries()
        assert isinstance(queries, list)
        assert len(queries) >= 50

    def test_get_query_definition(self):
        """Test getting query definition."""
        definition = SQLService.get_query_definition("total_revenue")
        assert definition is not None
        assert "SELECT" in definition.upper()

    def test_get_nonexistent_query_definition(self):
        """Test getting non-existent query definition."""
        definition = SQLService.get_query_definition("nonexistent")
        assert definition is None or definition == ""


class TestSQLRoutes:
    """Tests for SQL Analytics routes."""

    def test_list_queries_route(self, client, auth_headers):
        """Test listing queries route."""
        response = client.get("/api/sql/queries", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_queries" in data
        assert "queries" in data
        assert data["total_queries"] >= 50

    def test_get_query_definition_route(self, client, auth_headers):
        """Test getting query definition route."""
        response = client.get(
            "/api/sql/queries/total_revenue",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "query_name" in data
        assert "query_definition" in data
        assert data["query_name"] == "total_revenue"

    def test_get_nonexistent_query_route(self, client, auth_headers):
        """Test getting non-existent query."""
        response = client.get(
            "/api/sql/queries/nonexistent_query",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_sql_query_requires_analyst_role(self, client):
        """Test that SQL queries require analyst role."""
        # Register as viewer
        client.post(
            "/api/auth/register",
            json={
                "username": "viewer_user",
                "email": "viewer@test.com",
                "password": "ViewerPass123!",
            },
        )

        # Login as viewer
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "viewer_user",
                "password": "ViewerPass123!",
            },
        )

        viewer_token = login_response.json()["access_token"]
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        # Try to access SQL endpoints
        response = client.get("/api/sql/queries", headers=viewer_headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_sql_requires_auth(self, client):
        """Test SQL endpoints require authentication."""
        response = client.get("/api/sql/queries")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_predefined_query_list_format(self, client, auth_headers):
        """Test predefined query list contains expected queries."""
        response = client.get("/api/sql/queries", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        queries = data["queries"]

        # Check for expected query types
        assert "total_revenue" in queries
        assert "customer_segmentation" in queries
        assert "sales_by_region" in queries
        assert "monthly_sales_trend" in queries

    def test_multiple_query_definitions(self, client, auth_headers):
        """Test retrieving multiple query definitions."""
        queries_to_test = [
            "total_revenue",
            "customer_segmentation",
            "sales_by_region",
        ]

        for query_name in queries_to_test:
            response = client.get(
                f"/api/sql/queries/{query_name}",
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["query_name"] == query_name
            assert "SELECT" in data["query_definition"].upper()

    def test_query_definition_contains_sql(self, client, auth_headers):
        """Test that query definitions contain valid SQL."""
        response = client.get(
            "/api/sql/queries/customer_segmentation",
            headers=auth_headers,
        )

        data = response.json()
        definition = data["query_definition"]

        # Check for SQL keywords
        assert "WITH" in definition or "SELECT" in definition
        assert "FROM" in definition
        assert "GROUP BY" in definition or "SELECT" in definition


class TestQueryCoverage:
    """Tests to verify query coverage."""

    def test_basic_aggregation_queries_present(self):
        """Verify basic aggregation queries are present."""
        required = ["total_revenue", "average_transaction_value", "transaction_count"]
        queries = list_queries()
        for q in required:
            assert q in queries

    def test_customer_queries_present(self):
        """Verify customer analytics queries are present."""
        required = [
            "customer_segmentation",
            "repeat_customers",
            "customer_lifetime_value",
            "customer_retention",
        ]
        queries = list_queries()
        for q in required:
            assert q in queries

    def test_sales_queries_present(self):
        """Verify sales analytics queries are present."""
        required = [
            "sales_by_region",
            "sales_by_category",
            "top_products",
            "top_customers",
        ]
        queries = list_queries()
        for q in required:
            assert q in queries

    def test_time_series_queries_present(self):
        """Verify time series queries are present."""
        required = [
            "monthly_sales_trend",
            "month_over_month_growth",
            "year_over_year_growth",
            "daily_sales_summary",
        ]
        queries = list_queries()
        for q in required:
            assert q in queries

    def test_window_function_queries_present(self):
        """Verify window function queries are present."""
        required = [
            "running_total_sales",
            "sales_rank_by_customer",
            "percentile_sales",
            "lag_lead_analysis",
        ]
        queries = list_queries()
        for q in required:
            assert q in queries

    def test_advanced_queries_present(self):
        """Verify advanced queries are present."""
        required = [
            "cohort_analysis",
            "customer_churn_analysis",
            "profit_analysis",
            "inventory_turnover",
        ]
        queries = list_queries()
        for q in required:
            assert q in queries

    def test_view_queries_present(self):
        """Verify VIEW creation queries are present."""
        queries = list_queries()
        view_queries = [q for q in queries if "view" in q.lower()]
        assert len(view_queries) > 0
