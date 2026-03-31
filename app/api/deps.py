"""API dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.crud import user as crud_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import TokenData

security = HTTPBearer()


async def _get_user_from_token(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession,
    *,
    verify_exp: bool
) -> User:
    """Resolve a user from a JWT token with optional expiration verification."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token, verify_exp=verify_exp)

    if payload is None:
        raise credentials_exception

    username: str | None = payload.get("sub")
    if username is None:
        raise credentials_exception

    token_data = TokenData(username=username)

    user = await crud_user.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """
    Get the current authenticated user from a valid (non-expired) JWT token.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        Current authenticated User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    return await _get_user_from_token(credentials, db, verify_exp=True)


async def get_current_user_allow_expired(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """
    Get the current authenticated user allowing expired JWT tokens.

    Useful for refresh flows where the caller presents an expired access token.
    """
    return await _get_user_from_token(credentials, db, verify_exp=False)


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get the current active user.

    Args:
        current_user: Current authenticated user

    Returns:
        Current active User object

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


def get_current_active_user_allow_expired(
    current_user: Annotated[User, Depends(get_current_user_allow_expired)],
) -> User:
    """Allow expired tokens but still enforce active status."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    Get the current superuser.

    Args:
        current_user: Current active user

    Returns:
        Current superuser User object

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn't have enough privileges"
        )
    return current_user


class PermissionChecker:
    """Dependency class to check if user has required permissions."""

    def __init__(self, required_permissions: list[str]):
        """
        Initialize permission checker.

        Args:
            required_permissions: List of permission names required (any of them)
        """
        self.required_permissions = required_permissions

    async def __call__(self, current_user: Annotated[User, Depends(get_current_active_user)]) -> User:
        """
        Check if current user has any of the required permissions.

        Args:
            current_user: Current active user

        Returns:
            Current user if they have permission

        Raises:
            HTTPException: If user doesn't have required permissions
        """
        # Superusers have all permissions
        if current_user.is_superuser:
            return current_user

        # Check if user has any of the required permissions
        for permission_name in self.required_permissions:
            if current_user.has_permission(permission_name):
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permissions. Need one of: {', '.join(self.required_permissions)}",
        )


class RoleChecker:
    """Dependency class to check if user has required roles."""

    def __init__(self, required_roles: list[str]):
        """
        Initialize role checker.

        Args:
            required_roles: List of role names required (any of them)
        """
        self.required_roles = required_roles

    async def __call__(self, current_user: Annotated[User, Depends(get_current_active_user)]) -> User:
        """
        Check if current user has any of the required roles.

        Args:
            current_user: Current active user

        Returns:
            Current user if they have role

        Raises:
            HTTPException: If user doesn't have required roles
        """
        # Superusers have all roles
        if current_user.is_superuser:
            return current_user

        # Check if user has any of the required roles
        for role_name in self.required_roles:
            if current_user.has_role(role_name):
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required roles. Need one of: {', '.join(self.required_roles)}",
        )
