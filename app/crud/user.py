"""CRUD operations for User model."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """
    Get a user by ID.

    Args:
        db: Database session
        user_id: User ID to search for

    Returns:
        User object or None if not found
    """
    from app.models.role import Role

    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.roles).selectinload(Role.permissions)
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """
    Get a user by username.

    Args:
        db: Database session
        username: Username to search for

    Returns:
        User object or None if not found
    """
    from app.models.role import Role

    result = await db.execute(
        select(User)
        .where(User.username == username)
        .options(
            selectinload(User.roles).selectinload(Role.permissions)
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """
    Get a user by email.

    Args:
        db: Database session
        email: Email to search for

    Returns:
        User object or None if not found
    """
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username_or_email(db: AsyncSession, identifier: str) -> User | None:
    """
    Get a user by username or email.

    Args:
        db: Database session
        identifier: Username or email to search for

    Returns:
        User object or None if not found
    """
    result = await db.execute(select(User).where(or_(User.username == identifier, User.email == identifier)))
    return result.scalar_one_or_none()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
    """
    Get a list of users with pagination.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of User objects
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """
    Create a new user.

    Args:
        db: Database session
        user: User creation data

    Returns:
        Created User object
    """
    from app.crud import role as crud_role

    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, email=user.email, hashed_password=hashed_password)

    # Assign default role if exists
    default_role = await crud_role.get_default_role(db)
    if default_role:
        db_user.roles.append(default_role)

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user, ["roles"])
    return db_user


async def update_user(db: AsyncSession, user_id: int, user_update: UserUpdate) -> User | None:
    """
    Update a user.

    Args:
        db: Database session
        user_id: ID of user to update
        user_update: User update data

    Returns:
        Updated User object or None if not found
    """
    db_user = await get_user_by_id(db, user_id)
    if not db_user:
        return None

    update_data = user_update.model_dump(exclude_unset=True)

    if "password" in update_data:
        hashed_password = get_password_hash(update_data.pop("password"))
        update_data["hashed_password"] = hashed_password

    for field, value in update_data.items():
        setattr(db_user, field, value)

    await db.commit()
    await db.refresh(db_user)
    return db_user


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """
    Delete a user.

    Args:
        db: Database session
        user_id: ID of user to delete

    Returns:
        True if user was deleted, False if not found
    """
    db_user = await get_user_by_id(db, user_id)
    if not db_user:
        return False

    await db.delete(db_user)
    await db.commit()
    return True


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    """
    Authenticate a user by username/email and password.

    Args:
        db: Database session
        username: Username or email
        password: Plain text password

    Returns:
        User object if authentication successful, None otherwise
    """
    user = await get_user_by_username_or_email(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
