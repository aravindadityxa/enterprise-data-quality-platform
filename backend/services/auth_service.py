"""
Authentication and authorization service.

Handles user registration, login, JWT token generation, and verification.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from backend.database.models import User
from backend.config import get_settings
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication and authorization."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            str: Hashed password
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            bool: True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token.

        Args:
            user_id: User ID for token
            expires_delta: Optional token expiration time

        Returns:
            str: JWT token
        """
        if expires_delta is None:
            expires_delta = timedelta(
                minutes=settings.access_token_expire_minutes
            )

        expire = datetime.utcnow() + expires_delta
        to_encode = {"sub": user_id, "exp": expire}

        encoded_jwt = jwt.encode(
            to_encode, settings.secret_key, algorithm=settings.algorithm
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """
        Create JWT refresh token.

        Args:
            user_id: User ID for token

        Returns:
            str: JWT refresh token
        """
        expires_delta = timedelta(days=settings.refresh_token_expire_days)
        expire = datetime.utcnow() + expires_delta
        to_encode = {"sub": user_id, "type": "refresh", "exp": expire}

        encoded_jwt = jwt.encode(
            to_encode, settings.secret_key, algorithm=settings.algorithm
        )
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        """
        Verify JWT token and extract user ID.

        Args:
            token: JWT token to verify

        Returns:
            Optional[str]: User ID if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            return user_id
        except JWTError:
            return None

    @staticmethod
    def register_user(
        db: Session,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: str = "viewer",
    ) -> Tuple[bool, Optional[User], Optional[str]]:
        """
        Register new user.

        Args:
            db: Database session
            username: Username
            email: Email address
            password: Plain text password
            full_name: Optional full name
            role: User role (admin, analyst, viewer)

        Returns:
            Tuple of (success, user_object, error_message)
        """
        try:
            # Check if user exists
            existing = db.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()

            if existing:
                return False, None, "Username or email already exists"

            # Create user
            user = User(
                username=username,
                email=email,
                hashed_password=AuthService.hash_password(password),
                full_name=full_name,
                role=role,
                is_active=True,
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            logger.info(f"User registered: {username}")
            return True, user, None

        except Exception as e:
            db.rollback()
            logger.error(f"Error registering user: {e}")
            return False, None, str(e)

    @staticmethod
    def authenticate_user(
        db: Session, username: str, password: str
    ) -> Tuple[bool, Optional[User], Optional[str]]:
        """
        Authenticate user with username and password.

        Args:
            db: Database session
            username: Username
            password: Plain text password

        Returns:
            Tuple of (success, user_object, error_message)
        """
        try:
            user = db.query(User).filter(User.username == username).first()

            if not user:
                return False, None, "Invalid username or password"

            if not user.is_active:
                return False, None, "User account is inactive"

            if not AuthService.verify_password(password, user.hashed_password):
                return False, None, "Invalid username or password"

            logger.info(f"User authenticated: {username}")
            return True, user, None

        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return False, None, str(e)

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Optional[User]: User object or None
        """
        try:
            return db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    @staticmethod
    def update_user_password(
        db: Session, user_id: str, old_password: str, new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Update user password.

        Args:
            db: Database session
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()

            if not user:
                return False, "User not found"

            if not AuthService.verify_password(old_password, user.hashed_password):
                return False, "Current password is incorrect"

            user.hashed_password = AuthService.hash_password(new_password)
            user.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"Password updated for user: {user_id}")
            return True, None

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating password: {e}")
            return False, str(e)

    @staticmethod
    def deactivate_user(db: Session, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Deactivate user account.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()

            if not user:
                return False, "User not found"

            user.is_active = False
            user.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"User deactivated: {user_id}")
            return True, None

        except Exception as e:
            db.rollback()
            logger.error(f"Error deactivating user: {e}")
            return False, str(e)

    @staticmethod
    def has_role(user: User, required_role: str) -> bool:
        """
        Check if user has required role.

        Args:
            user: User object
            required_role: Required role

        Returns:
            bool: True if user has role
        """
        role_hierarchy = {
            "admin": ["admin"],
            "analyst": ["admin", "analyst"],
            "viewer": ["admin", "analyst", "viewer"],
        }

        return user.role in role_hierarchy.get(required_role, [])

    @staticmethod
    def require_admin(user: User) -> bool:
        """Check if user is admin."""
        return user.role == "admin"

    @staticmethod
    def require_analyst(user: User) -> bool:
        """Check if user is analyst or admin."""
        return user.role in ["admin", "analyst"]

    @staticmethod
    def require_viewer(user: User) -> bool:
        """Check if user is any role (always true for authenticated users)."""
        return user.is_active
