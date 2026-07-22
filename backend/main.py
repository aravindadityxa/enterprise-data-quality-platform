"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from backend.config import get_settings
from backend.utils.logger import setup_logger
from backend.database import Base, engine
import logging

logger = setup_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    # Startup
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Application started")

    yield

    # Shutdown
    logger.info("Application shutting down...")


app = FastAPI(
    title=settings.app_name,
    description="Enterprise Data Quality & Business Intelligence Platform",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.example.com"],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Return health status."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "app_version": settings.app_version,
    }


@app.get("/", tags=["Root"])
async def root():
    """Return API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


# Import and include routers
from backend.api.routes import auth, datasets, validation, cleaning, analytics, sql_analytics, anomaly, forecasting

app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(validation.router)
app.include_router(cleaning.router)
app.include_router(analytics.router)
app.include_router(sql_analytics.router)
app.include_router(anomaly.router)
app.include_router(forecasting.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
