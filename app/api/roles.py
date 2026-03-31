"""API endpoints for role and permission management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PermissionChecker, get_current_active_user
from app.crud import role as crud_role
from app.db.session import get_session
from app.models.user import User
from app.schemas.role import (
    AssignRoleRequest,
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
    RemoveRoleRequest,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)

router = APIRouter()

# Error message constants
PERMISSION_NOT_FOUND = "PERMISSION_NOT_FOUND"
ROLE_NOT_FOUND = "ROLE_NOT_FOUND"


# Permission endpoints
@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["permissions:read"]))],
    skip: int = 0,
    limit: int = 100,
):
    """List all permissions with pagination."""
    permissions = await crud_role.get_permissions(db, skip=skip, limit=limit)
    return permissions


@router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["permissions:read"]))],
):
    """Get a specific permission by ID."""
    permission = await crud_role.get_permission(db, permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PERMISSION_NOT_FOUND")
    return permission


@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    permission: PermissionCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["permissions:create"]))],
):
    """Create a new permission."""
    # Check if permission with same name already exists
    existing = await crud_role.get_permission_by_name(db, permission.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission with this name already exists",
        )

    return await crud_role.create_permission(db, permission)


@router.put("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: int,
    permission_update: PermissionUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["permissions:update"]))],
):
    """Update a permission."""
    permission = await crud_role.update_permission(db, permission_id, permission_update)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PERMISSION_NOT_FOUND")
    return permission


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["permissions:delete"]))],
):
    """Delete a permission."""
    success = await crud_role.delete_permission(db, permission_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PERMISSION_NOT_FOUND")


# Role endpoints
@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["roles:read"]))],
    skip: int = 0,
    limit: int = 100,
):
    """List all roles with pagination."""
    roles = await crud_role.get_roles(db, skip=skip, limit=limit)
    return roles


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["roles:read"]))],
):
    """Get a specific role by ID."""
    role = await crud_role.get_role(db, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROLE_NOT_FOUND")
    return role


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role: RoleCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["roles:create"]))],
):
    """Create a new role."""
    # Check if role with same name already exists
    existing = await crud_role.get_role_by_name(db, role.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists",
        )

    return await crud_role.create_role(db, role)


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_update: RoleUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["roles:update"]))],
):
    """Update a role."""
    role = await crud_role.update_role(db, role_id, role_update)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROLE_NOT_FOUND")
    return role


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["roles:delete"]))],
):
    """Delete a role."""
    success = await crud_role.delete_role(db, role_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROLE_NOT_FOUND")


# User-Role assignment endpoints
@router.post("/roles/assign", response_model=dict)
async def assign_role_to_user(
    request: AssignRoleRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["roles:update", "users:update"]))],
):
    """Assign a role to a user, replacing any previously assigned roles."""
    user = await crud_role.assign_role_to_user(db, request.user_id, request.role_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User or role not found",
        )

    return {"message": "Role assigned successfully", "user_id": user.id}


@router.post("/roles/remove", response_model=dict)
async def remove_role_from_user(
    request: RemoveRoleRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["roles:update", "users:update"]))],
):
    """Remove a role from a user."""
    user = await crud_role.remove_role_from_user(db, request.user_id, request.role_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User or role not found",
        )

    return {"message": "Role removed successfully", "user_id": user.id}


@router.get("/users/{user_id}/roles", response_model=list[RoleResponse])
async def get_user_roles(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get all roles for a specific user."""
    # Users can view their own roles, or need permissions to view others
    if current_user.id != user_id and not current_user.has_permission("users:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    roles = await crud_role.get_user_roles(db, user_id)
    return roles


@router.get("/roles/{role_id}/users")
async def get_users_by_role(
    role_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(PermissionChecker(["users:read", "roles:read"]))],
    skip: int = 0,
    limit: int = 100,
):
    """Get all users with a specific role."""
    users = await crud_role.get_users_by_role(db, role_id, skip=skip, limit=limit)
    return users
