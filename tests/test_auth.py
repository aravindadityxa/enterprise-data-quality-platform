"""
Tests for authentication service and routes.

Tests user registration, login, and token management.
"""

import pytest
from fastapi import status
from backend.services.auth_service import AuthService


class TestAuthService:
    """Tests for AuthService."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        assert hashed != password
        assert AuthService.verify_password(password, hashed)

    def test_verify_password_invalid(self):
        """Test password verification with wrong password."""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)
        wrong_password = "WrongPassword456!"

        assert not AuthService.verify_password(wrong_password, hashed)

    def test_create_access_token(self):
        """Test access token creation."""
        user_id = "test-user-123"
        token = AuthService.create_access_token(user_id)

        assert token is not None
        assert len(token) > 0
        assert AuthService.verify_token(token) == user_id

    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"
        assert AuthService.verify_token(invalid_token) is None

    def test_register_user(self, db):
        """Test user registration."""
        success, user, error = AuthService.register_user(
            db=db,
            username="newuser",
            email="new@example.com",
            password="SecurePassword123!",
            full_name="New User",
        )

        assert success
        assert user is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert error is None

    def test_register_user_duplicate_username(self, db, test_user):
        """Test registration with duplicate username."""
        success, user, error = AuthService.register_user(
            db=db,
            username=test_user.username,
            email="different@example.com",
            password="SecurePassword123!",
        )

        assert not success
        assert user is None
        assert "already exists" in error

    def test_authenticate_user(self, db, test_user, test_user_data):
        """Test user authentication."""
        success, user, error = AuthService.authenticate_user(
            db=db,
            username=test_user_data["username"],
            password=test_user_data["password"],
        )

        assert success
        assert user is not None
        assert user.username == test_user_data["username"]
        assert error is None

    def test_authenticate_user_wrong_password(self, db, test_user_data):
        """Test authentication with wrong password."""
        success, user, error = AuthService.authenticate_user(
            db=db,
            username=test_user_data["username"],
            password="WrongPassword123!",
        )

        assert not success
        assert user is None
        assert "Invalid" in error

    def test_get_user_by_id(self, db, test_user):
        """Test getting user by ID."""
        user = AuthService.get_user_by_id(db, test_user.id)

        assert user is not None
        assert user.id == test_user.id
        assert user.username == test_user.username


class TestAuthRoutes:
    """Tests for authentication routes."""

    def test_register_user_route(self, client):
        """Test user registration route."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "SecurePassword123!",
                "full_name": "New User",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"

    def test_register_user_duplicate(self, client, test_user_data):
        """Test registration with duplicate username."""
        # First registration
        client.post(
            "/api/auth/register",
            json=test_user_data,
        )

        # Duplicate registration
        response = client.post(
            "/api/auth/register",
            json=test_user_data,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_success(self, client, test_user_data):
        """Test successful login."""
        # Register first
        client.post("/api/auth/register", json=test_user_data)

        # Login
        response = client.post(
            "/api/auth/login",
            json={
                "username": test_user_data["username"],
                "password": test_user_data["password"],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client, test_user_data):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "nonexistent",
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, client, test_user_data):
        """Test token refresh."""
        # Register and login
        client.post("/api/auth/register", json=test_user_data)
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": test_user_data["username"],
                "password": test_user_data["password"],
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = client.post(
            "/api/auth/refresh",
            json={"token": refresh_token},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
