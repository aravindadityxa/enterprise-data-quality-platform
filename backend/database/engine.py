"""SQLAlchemy engine and session configuration."""

from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from backend.config import get_settings
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

# Determine if using SQLite for development
is_sqlite = "sqlite" in settings.database_url

# Configure engine based on database type
if is_sqlite:
    # SQLite doesn't need connection pooling in development
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.database_echo,
    )
else:
    # MySQL/PostgreSQL with connection pooling
    engine = create_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign keys for SQLite."""
    if is_sqlite:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Declarative base for models
Base = declarative_base()


def get_db():
    """Provide database session for dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
