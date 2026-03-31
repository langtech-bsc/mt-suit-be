"""Role and Permission schemas for API requests and responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PermissionBase(BaseModel):
    """Base permission schema with common attributes."""

    name: str = Field(..., min_length=3, max_length=100, description="Permission name")
    description: str | None = Field(None, max_length=255, description="Permission description")
    resource: str = Field(..., min_length=1, max_length=100, description="Resource this permission applies to")
    action: str = Field(..., min_length=1, max_length=50, description="Action this permission allows")


class PermissionCreate(PermissionBase):
    """Schema for creating a new permission."""

    pass


class PermissionUpdate(BaseModel):
    """Schema for updating permission information."""

    name: str | None = Field(None, min_length=3, max_length=100, description="Permission name")
    description: str | None = Field(None, max_length=255, description="Permission description")
    resource: str | None = Field(None, min_length=1, max_length=100, description="Resource")
    action: str | None = Field(None, min_length=1, max_length=50, description="Action")


class PermissionResponse(PermissionBase):
    """Schema for permission response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class RoleBase(BaseModel):
    """Base role schema with common attributes."""

    name: str = Field(..., min_length=2, max_length=50, description="Role name")
    description: str | None = Field(None, max_length=255, description="Role description")
    is_default: bool = Field(False, description="Whether this role is assigned by default to new users")


class RoleCreate(RoleBase):
    """Schema for creating a new role."""

    permission_ids: list[int] = Field(default_factory=list, description="List of permission IDs to assign to this role")


class RoleUpdate(BaseModel):
    """Schema for updating role information."""

    name: str | None = Field(None, min_length=2, max_length=50, description="Role name")
    description: str | None = Field(None, max_length=255, description="Role description")
    is_default: bool | None = Field(None, description="Whether this role is assigned by default")
    permission_ids: list[int] | None = Field(None, description="List of permission IDs to assign to this role")


class RoleResponse(RoleBase):
    """Schema for role response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    permissions: list[PermissionResponse] = []


class RoleWithUsers(RoleResponse):
    """Schema for role response with user count."""

    user_count: int = Field(0, description="Number of users with this role")


class AssignRoleRequest(BaseModel):
    """Schema for assigning a role to a user."""

    user_id: int = Field(..., description="User ID")
    role_id: int = Field(..., description="Role ID")


class RemoveRoleRequest(BaseModel):
    """Schema for removing a role from a user."""

    user_id: int = Field(..., description="User ID")
    role_id: int = Field(..., description="Role ID")
