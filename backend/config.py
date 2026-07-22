"""
Application configuration settings.

Uses environment variables with Pydantic for type validation and IDE support.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal
import os


class Settings(BaseSettings):
    """Application configuration."""

    # Application
    app_name: str = "Enterprise Data Quality Platform"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    reload: bool = True

    # Database
    database_url: str = "sqlite:///./database.db"
    database_echo: bool = False

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # File Upload
    max_upload_size_mb: int = 100
    upload_directory: str = "backend/uploads"
    allowed_extensions: str = "csv,xlsx,xls,json"

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    # Feature Flags
    enable_powerbi_export: bool = True
    enable_anomaly_detection: bool = True
    enable_forecasting: bool = True
    enable_authentication: bool = True

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    cors_credentials: bool = True
    cors_methods: list[str] = ["*"]
    cors_headers: list[str] = ["*"]

    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False
        extra = "allow"

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB to bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_extensions_list(self) -> list[str]:
        """Convert comma-separated string to list."""
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Application configuration

    Note:
        Cached to avoid re-reading environment variables on every access.
    """
    return Settings()
