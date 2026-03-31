"""Role and Permission model definitions."""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Table, func
from sqlalchemy.orm import relationship

from app.db.base import Base


# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", BigInteger, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


# Association table for many-to-many relationship between users and roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(Base):
    """Permission model for granular access control."""

    __tablename__ = "permissions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    resource = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
    )

    def __repr__(self) -> str:
        # Use __dict__ to avoid triggering lazy loading if instance is detached
        id_val = self.__dict__.get('id', 'Unknown')
        name_val = self.__dict__.get('name', 'Unknown')
        resource_val = self.__dict__.get('resource', 'Unknown')
        action_val = self.__dict__.get('action', 'Unknown')
        return f"<Permission(id={id_val}, name={name_val}, resource={resource_val}, action={action_val})>"


class Role(Base):
    """Role model for grouping permissions."""

    __tablename__ = "roles"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )
    users = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
    )

    def __repr__(self) -> str:
        # Use __dict__ to avoid triggering lazy loading if instance is detached
        id_val = self.__dict__.get('id', 'Unknown')
        name_val = self.__dict__.get('name', 'Unknown')
        return f"<Role(id={id_val}, name={name_val})>"
