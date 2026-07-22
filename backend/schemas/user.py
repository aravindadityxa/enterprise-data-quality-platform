"""User-related schemas."""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, Literal


class UserCreate(BaseModel):
    """Schema for user creation."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = Field(None, max_length=100)

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_analyst",
                "email": "john@example.com",
                "password": "SecurePassword123!",
                "full_name": "John Analyst",
            }
        }


class UserUpdate(BaseModel):
    """Schema for user updates."""

    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Updated",
                "email": "john.updated@example.com",
            }
        }


class UserResponse(BaseModel):
    """Schema for user responses."""

    id: str
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "john_analyst",
                "email": "john@example.com",
                "full_name": "John Analyst",
                "role": "analyst",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class TokenResponse(BaseModel):
    """Schema for token responses."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
            }
        }


class LoginRequest(BaseModel):
    """Schema for login request."""

    username: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_analyst",
                "password": "SecurePassword123!",
            }
        }
