"""
Pytest configuration and fixtures.
"""

import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.engine import Base
from backend.database.engine import get_db
from backend.services.auth_service import AuthService

# Use in-memory SQLite for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Provide test database session."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Provide test client with test database."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
    }


@pytest.fixture
def test_user(db, test_user_data):
    """Create test user in database."""
    from backend.database.models import User

    user = User(
        username=test_user_data["username"],
        email=test_user_data["email"],
        hashed_password=AuthService.hash_password(test_user_data["password"]),
        full_name=test_user_data["full_name"],
        is_active=True,
        role="analyst",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user_data):
    """Get authentication headers."""
    response = client.post(
        "/api/auth/login",
        json={
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_csv_file(tmp_path):
    """Create sample CSV file for testing."""
    import csv

    file_path = tmp_path / "sample.csv"
    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "email", "amount"])
        writer.writerow([1, "John Doe", "john@example.com", 100.50])
        writer.writerow([2, "Jane Smith", "jane@example.com", 200.75])
        writer.writerow([3, "Bob Johnson", "bob@example.com", 150.25])

    return file_path
