"""User CRUD endpoints protected with JWT authentication."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_current_superuser
from app.crud import user as crud_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()

# Error message constants
ERR_USERNAME_REGISTERED = "ERR_USERNAME_REGISTERED"
ERR_EMAIL_REGISTERED = "ERR_EMAIL_REGISTERED"
ERR_USER_NOT_FOUND = "ERR_USER_NOT_FOUND"


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Create a new user (public endpoint for registration).

    Args:
        user_in: User creation data
        db: Database session

    Returns:
        Created user data

    Raises:
        HTTPException: If username or email already exists
    """
    existing_user = await crud_user.get_user_by_username(db, user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ERR_USERNAME_REGISTERED"
        )

    existing_email = await crud_user.get_user_by_email(db, user_in.email)
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ERR_EMAIL_REGISTERED")

    user = await crud_user.create_user(db, user_in)
    return user


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def read_user_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user data
    """
    return current_user


@router.put("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_user_me(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Update current authenticated user information.

    Args:
        user_update: User update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated user data

    Raises:
        HTTPException: If username or email already exists
    """
    if user_update.username:
        existing_user = await crud_user.get_user_by_username(db, user_update.username)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="ERR_USERNAME_REGISTERED"
            )

    if user_update.email:
        existing_email = await crud_user.get_user_by_email(db, user_update.email)
        if existing_email and existing_email.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ERR_EMAIL_REGISTERED")

    updated_user = await crud_user.update_user(db, current_user.id, user_update)
    return updated_user


@router.get("", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
async def read_users(
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_superuser)],
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
):
    """
    Get list of users (superuser only).

    Args:
        db: Database session
        current_user: Current superuser
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of users
    """
    users = await crud_user.get_users(db, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def read_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_superuser)],
):
    """
    Get user by ID (superuser only).

    Args:
        user_id: User ID to retrieve
        db: Database session
        current_user: Current superuser

    Returns:
        User data

    Raises:
        HTTPException: If user not found
    """
    user = await crud_user.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ERR_USER_NOT_FOUND")
    return user


@router.put("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_superuser)],
):
    """
    Update user by ID (superuser only).

    Args:
        user_id: User ID to update
        user_update: User update data
        db: Database session
        current_user: Current superuser

    Returns:
        Updated user data

    Raises:
        HTTPException: If user not found or username/email already exists
    """
    if user_update.username:
        existing_user = await crud_user.get_user_by_username(db, user_update.username)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="ERR_USERNAME_REGISTERED"
            )

    if user_update.email:
        existing_email = await crud_user.get_user_by_email(db, user_update.email)
        if existing_email and existing_email.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ERR_EMAIL_REGISTERED")

    updated_user = await crud_user.update_user(db, user_id, user_update)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ERR_USER_NOT_FOUND")
    return updated_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_superuser)],
):
    """
    Delete user by ID (superuser only).

    Args:
        user_id: User ID to delete
        db: Database session
        current_user: Current superuser

    Raises:
        HTTPException: If user not found
    """
    success = await crud_user.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ERR_USER_NOT_FOUND")
    return None
