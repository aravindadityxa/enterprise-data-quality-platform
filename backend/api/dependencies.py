"""
FastAPI dependencies for authentication and authorization.

Provides dependency functions for protecting routes.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
from backend.database.engine import get_db
from backend.database.models import User
from backend.services.auth_service import AuthService
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

# HTTP Bearer authentication
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        User: Current user object

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials

    user_id = AuthService.verify_token(token)

    if not user_id:
        logger.warning("Invalid token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = AuthService.get_user_by_id(db, user_id)

    if not user or not user.is_active:
        logger.warning(f"User not found or inactive: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user if they are admin.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Admin user

    Raises:
        HTTPException: If user is not admin
    """
    if not AuthService.require_admin(current_user):
        logger.warning(f"Non-admin user attempted admin action: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user


async def get_analyst_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user if they are analyst or admin.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Analyst or admin user

    Raises:
        HTTPException: If user does not have analyst role
    """
    if not AuthService.require_analyst(current_user):
        logger.warning(f"Non-analyst user attempted analyst action: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst access required",
        )

    return current_user
