"""
Authentication API routes.

Handles user registration, login, and token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.engine import get_db
from backend.services.auth_service import AuthService
from backend.schemas.user import UserCreate, UserResponse, TokenResponse, LoginRequest
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    Args:
        user: User registration data
        db: Database session

    Returns:
        UserResponse: Created user data

    Raises:
        HTTPException: If registration fails
    """
    success, created_user, error = AuthService.register_user(
        db=db,
        username=user.username,
        email=user.email,
        password=user.password,
        full_name=user.full_name,
    )

    if not success:
        logger.warning(f"Registration failed: {error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return created_user


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return tokens.

    Args:
        credentials: Login credentials
        db: Database session

    Returns:
        TokenResponse: Access and refresh tokens

    Raises:
        HTTPException: If authentication fails
    """
    success, user, error = AuthService.authenticate_user(
        db=db,
        username=credentials.username,
        password=credentials.password,
    )

    if not success:
        logger.warning(f"Login failed for user {credentials.username}: {error}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
        )

    # Generate tokens
    access_token = AuthService.create_access_token(user.id)
    refresh_token = AuthService.create_refresh_token(user.id)

    logger.info(f"User logged in: {user.username}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=1800,  # 30 minutes
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token: str, db: Session = Depends(get_db)):
    """
    Refresh access token.

    Args:
        token: Refresh token
        db: Database session

    Returns:
        TokenResponse: New access token

    Raises:
        HTTPException: If token is invalid
    """
    user_id = AuthService.verify_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user = AuthService.get_user_by_id(db, user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token = AuthService.create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=token,
        token_type="bearer",
        expires_in=1800,
    )
