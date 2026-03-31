"""User schemas for API requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Field description constants
DESC_USER_PASSWORD = "DESC_USER_PASSWORD"


class UserBase(BaseModel):
    """Base user schema with common attributes."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="User email address")


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, max_length=100, description="DESC_USER_PASSWORD")

    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        """Validate password doesn't exceed bcrypt's 72 byte limit."""
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password cannot exceed 72 bytes when encoded in UTF-8')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    username: str | None = Field(None, min_length=3, max_length=50, description="Username")
    email: EmailStr | None = Field(None, description="User email address")
    password: str | None = Field(None, min_length=8, max_length=100, description="DESC_USER_PASSWORD")
    is_active: bool | None = Field(None, description="User active status")
    is_superuser: bool | None = Field(None, description="Superuser status")

    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v: str | None) -> str | None:
        """Validate password doesn't exceed bcrypt's 72 byte limit."""
        if v and len(v.encode('utf-8')) > 72:
            raise ValueError('Password cannot exceed 72 bytes when encoded in UTF-8')
        return v


class UserResponse(UserBase):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    roles: list[RoleResponse] = []


class UserInDB(UserResponse):
    """Schema for user stored in database."""

    hashed_password: str


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for JWT token data."""

    username: str | None = None


class LoginRequest(BaseModel):
    """Schema for login request."""

    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="DESC_USER_PASSWORD")


# Import at the end to avoid circular imports
from app.schemas.role import RoleResponse  # noqa: E402

# Rebuild the model to resolve forward references
UserResponse.model_rebuild()
