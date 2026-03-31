"""CRUD operations for roles and permissions."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Permission, Role
from app.models.user import User
from app.schemas.role import PermissionCreate, PermissionUpdate, RoleCreate, RoleUpdate


# Permission CRUD operations
async def get_permission(db: AsyncSession, permission_id: int) -> Permission | None:
    """Get a permission by ID."""
    result = await db.execute(select(Permission).where(Permission.id == permission_id))
    return result.scalar_one_or_none()


async def get_permission_by_name(db: AsyncSession, name: str) -> Permission | None:
    """Get a permission by name."""
    result = await db.execute(select(Permission).where(Permission.name == name))
    return result.scalar_one_or_none()


async def get_permissions(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Permission]:
    """Get all permissions with pagination."""
    result = await db.execute(select(Permission).offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_permissions_by_resource(db: AsyncSession, resource: str) -> list[Permission]:
    """Get all permissions for a specific resource."""
    result = await db.execute(select(Permission).where(Permission.resource == resource))
    return list(result.scalars().all())


async def create_permission(db: AsyncSession, permission: PermissionCreate) -> Permission:
    """Create a new permission."""
    db_permission = Permission(**permission.model_dump())
    db.add(db_permission)
    await db.commit()
    await db.refresh(db_permission)
    return db_permission


async def update_permission(
    db: AsyncSession, permission_id: int, permission_update: PermissionUpdate
) -> Permission | None:
    """Update a permission."""
    db_permission = await get_permission(db, permission_id)
    if not db_permission:
        return None

    update_data = permission_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_permission, field, value)

    await db.commit()
    await db.refresh(db_permission)
    return db_permission


async def delete_permission(db: AsyncSession, permission_id: int) -> bool:
    """Delete a permission."""
    db_permission = await get_permission(db, permission_id)
    if not db_permission:
        return False

    await db.delete(db_permission)
    await db.commit()
    return True


# Role CRUD operations
async def get_role(db: AsyncSession, role_id: int) -> Role | None:
    """Get a role by ID with its permissions."""
    result = await db.execute(
        select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
    )
    return result.scalar_one_or_none()


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    """Get a role by name with its permissions."""
    result = await db.execute(
        select(Role).where(Role.name == name).options(selectinload(Role.permissions))
    )
    return result.scalar_one_or_none()


async def get_roles(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Role]:
    """Get all roles with pagination."""
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_default_role(db: AsyncSession) -> Role | None:
    """Get the default role."""
    result = await db.execute(
        select(Role).where(Role.is_default == True).options(selectinload(Role.permissions))
    )
    return result.scalar_one_or_none()


async def create_role(db: AsyncSession, role: RoleCreate) -> Role:
    """Create a new role with permissions."""
    # Extract permission_ids before creating the role
    permission_ids = role.permission_ids
    role_data = role.model_dump(exclude={"permission_ids"})

    # Create the role
    db_role = Role(**role_data)

    # Add permissions if provided
    if permission_ids:
        permissions = await db.execute(select(Permission).where(Permission.id.in_(permission_ids)))
        db_role.permissions = list(permissions.scalars().all())

    db.add(db_role)
    await db.commit()
    await db.refresh(db_role, ["permissions"])
    return db_role


async def update_role(db: AsyncSession, role_id: int, role_update: RoleUpdate) -> Role | None:
    """Update a role."""
    db_role = await get_role(db, role_id)
    if not db_role:
        return None

    update_data = role_update.model_dump(exclude_unset=True, exclude={"permission_ids"})
    for field, value in update_data.items():
        setattr(db_role, field, value)

    # Update permissions if provided
    if role_update.permission_ids is not None:
        permissions = await db.execute(
            select(Permission).where(Permission.id.in_(role_update.permission_ids))
        )
        db_role.permissions = list(permissions.scalars().all())

    await db.commit()
    await db.refresh(db_role, ["permissions"])
    return db_role


async def delete_role(db: AsyncSession, role_id: int) -> bool:
    """Delete a role."""
    db_role = await get_role(db, role_id)
    if not db_role:
        return False

    await db.delete(db_role)
    await db.commit()
    return True


# User-Role operations
async def assign_role_to_user(db: AsyncSession, user_id: int, role_id: int) -> User | None:
    """Assign a role to a user, replacing any previously assigned roles."""
    # Get user with roles loaded
    result = await db.execute(select(User).where(User.id == user_id).options(selectinload(User.roles)))
    user = result.scalar_one_or_none()
    if not user:
        return None

    # Get role
    role = await get_role(db, role_id)
    if not role:
        return None

    # Replace any existing roles with the new one
    user.roles = [role]
    await db.commit()
    await db.refresh(user, ["roles"])

    return user


async def remove_role_from_user(db: AsyncSession, user_id: int, role_id: int) -> User | None:
    """Remove a role from a user."""
    # Get user with roles loaded
    result = await db.execute(select(User).where(User.id == user_id).options(selectinload(User.roles)))
    user = result.scalar_one_or_none()
    if not user:
        return None

    # Get role
    role = await get_role(db, role_id)
    if not role:
        return None

    # Remove role if user has it
    if role in user.roles:
        user.roles.remove(role)
        await db.commit()
        await db.refresh(user, ["roles"])

    return user


async def get_user_roles(db: AsyncSession, user_id: int) -> list[Role]:
    """Get all roles for a user."""
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.roles).selectinload(Role.permissions))
    )
    user = result.scalar_one_or_none()
    if not user:
        return []

    return user.roles


async def get_users_by_role(db: AsyncSession, role_id: int, skip: int = 0, limit: int = 100) -> list[User]:
    """Get all users with a specific role."""
    result = await db.execute(
        select(User)
        .join(User.roles)
        .where(Role.id == role_id)
        .options(selectinload(User.roles))
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())
