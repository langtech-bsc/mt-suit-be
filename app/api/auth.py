"""Authentication endpoints for login and logout."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user_allow_expired
from app.core.config import settings
from app.core.security import create_access_token
from app.crud import user as crud_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import LoginRequest, Token

router = APIRouter()


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(
    credentials: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Login endpoint to authenticate users and return a JWT token.

    Args:
        credentials: Login credentials (username/email and password)
        db: Database session

    Returns:
        JWT access token

    Raises:
        HTTPException: If credentials are invalid
    """
    user = await crud_user.authenticate_user(db, credentials.username, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    return Token(access_token=access_token, token_type="bearer")


@router.post("/refresh", response_model=Token, status_code=status.HTTP_200_OK)
async def refresh_access_token(
    current_user: Annotated[User, Depends(get_current_active_user_allow_expired)],
):
    """
    Refresh the JWT access token for the current user.

    Allows expired bearer tokens (signature checked) to support refresh after expiry.
    """
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(data={"sub": current_user.username}, expires_delta=access_token_expires)

    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout():
    """
    Logout endpoint.

    Note: With JWT, logout is primarily handled client-side by removing the token.
    This endpoint serves as a confirmation and can be extended for token blacklisting.

    Returns:
        Success message
    """
    return {"message": "Successfully logged out"}
