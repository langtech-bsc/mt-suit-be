"""008_consolidate_roles_to_admin_and_member

Revision ID: c7e8f9a0b1c2
Revises: a1b2c3d4e5f6
Create Date: 2025-12-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7e8f9a0b1c2"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename user -> member, remove viewer, and set member as default role."""
    connection = op.get_bind()

    user_role = connection.execute(sa.text("SELECT id FROM roles WHERE name = 'user'")).fetchone()
    member_role = connection.execute(sa.text("SELECT id FROM roles WHERE name = 'member'")).fetchone()
    viewer_role = connection.execute(sa.text("SELECT id FROM roles WHERE name = 'viewer'")).fetchone()

    member_id: int | None = None

    if user_role and not member_role:
        connection.execute(
            sa.text(
                """
                UPDATE roles
                SET name = 'member',
                    description = 'Standard member role'
                WHERE id = :role_id
                """
            ),
            {"role_id": user_role[0]},
        )
        member_id = user_role[0]
    elif user_role and member_role:
        member_id = member_role[0]

        # Merge permissions and users from the old user role into member
        connection.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT :member_id, rp.permission_id
                FROM role_permissions rp
                WHERE rp.role_id = :user_id
                ON CONFLICT DO NOTHING
                """
            ),
            {"member_id": member_id, "user_id": user_role[0]},
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO user_roles (user_id, role_id)
                SELECT ur.user_id, :member_id
                FROM user_roles ur
                WHERE ur.role_id = :user_id
                ON CONFLICT DO NOTHING
                """
            ),
            {"member_id": member_id, "user_id": user_role[0]},
        )

        # Remove the old user role
        connection.execute(
            sa.text("DELETE FROM role_permissions WHERE role_id = :user_id"),
            {"user_id": user_role[0]},
        )
        connection.execute(
            sa.text("DELETE FROM user_roles WHERE role_id = :user_id"),
            {"user_id": user_role[0]},
        )
        connection.execute(
            sa.text("DELETE FROM roles WHERE id = :user_id"),
            {"user_id": user_role[0]},
        )
    elif member_role:
        member_id = member_role[0]
    else:
        # Create the member role if neither user nor member exists
        result = connection.execute(
            sa.text(
                """
                INSERT INTO roles (name, description, is_default)
                VALUES ('member', 'Standard member role', true)
                RETURNING id
                """
            )
        )
        member_id = result.fetchone()[0]

    if member_id is None:
        raise Exception("Failed to ensure member role exists")

    # Reassign any viewer users to member, then remove viewer role completely
    if viewer_role:
        connection.execute(
            sa.text(
                """
                INSERT INTO user_roles (user_id, role_id)
                SELECT ur.user_id, :member_id
                FROM user_roles ur
                WHERE ur.role_id = :viewer_id
                ON CONFLICT DO NOTHING
                """
            ),
            {"member_id": member_id, "viewer_id": viewer_role[0]},
        )
        connection.execute(
            sa.text("DELETE FROM user_roles WHERE role_id = :viewer_id"),
            {"viewer_id": viewer_role[0]},
        )
        connection.execute(
            sa.text("DELETE FROM role_permissions WHERE role_id = :viewer_id"),
            {"viewer_id": viewer_role[0]},
        )
        connection.execute(
            sa.text("DELETE FROM roles WHERE id = :viewer_id"),
            {"viewer_id": viewer_role[0]},
        )

    # Ensure default flags reflect the new setup
    connection.execute(sa.text("UPDATE roles SET is_default = false"))
    connection.execute(
        sa.text(
            """
            UPDATE roles
            SET is_default = true,
                description = COALESCE(description, 'Standard member role')
            WHERE id = :member_id
            """
        ),
        {"member_id": member_id},
    )

    # Make sure admin description is consistent
    connection.execute(
        sa.text(
            """
            UPDATE roles
            SET description = 'Administrator with full access'
            WHERE name = 'admin'
            """
        )
    )

    # Ensure member keeps translation access after rename/merge
    connection.execute(
        sa.text(
            """
            WITH member_role AS (
                SELECT :member_id AS id
            ), translate_perm AS (
                SELECT id FROM permissions WHERE name = 'translations:translate'
            )
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT member_role.id, translate_perm.id
            FROM member_role, translate_perm
            ON CONFLICT DO NOTHING
            """
        ),
        {"member_id": member_id},
    )


def downgrade() -> None:
    """Recreate viewer and revert member back to user as default."""
    connection = op.get_bind()

    member_role = connection.execute(sa.text("SELECT id FROM roles WHERE name = 'member'")).fetchone()
    user_role = connection.execute(sa.text("SELECT id FROM roles WHERE name = 'user'")).fetchone()

    user_id: int | None = None

    if member_role and not user_role:
        connection.execute(
            sa.text(
                """
                UPDATE roles
                SET name = 'user',
                    description = 'Standard user with basic access'
                WHERE id = :role_id
                """
            ),
            {"role_id": member_role[0]},
        )
        user_id = member_role[0]
    elif member_role and user_role:
        user_id = user_role[0]

        # Merge member into existing user role
        connection.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT :user_id, rp.permission_id
                FROM role_permissions rp
                WHERE rp.role_id = :member_id
                ON CONFLICT DO NOTHING
                """
            ),
            {"user_id": user_id, "member_id": member_role[0]},
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO user_roles (user_id, role_id)
                SELECT ur.user_id, :user_id
                FROM user_roles ur
                WHERE ur.role_id = :member_id
                ON CONFLICT DO NOTHING
                """
            ),
            {"user_id": user_id, "member_id": member_role[0]},
        )

        connection.execute(
            sa.text("DELETE FROM role_permissions WHERE role_id = :member_id"),
            {"member_id": member_role[0]},
        )
        connection.execute(
            sa.text("DELETE FROM user_roles WHERE role_id = :member_id"),
            {"member_id": member_role[0]},
        )
        connection.execute(
            sa.text("DELETE FROM roles WHERE id = :member_id"),
            {"member_id": member_role[0]},
        )
    elif user_role:
        user_id = user_role[0]
        connection.execute(
            sa.text(
                """
                UPDATE roles
                SET description = 'Standard user with basic access'
                WHERE id = :role_id
                """
            ),
            {"role_id": user_id},
        )
    else:
        # Recreate the legacy user role
        result = connection.execute(
            sa.text(
                """
                INSERT INTO roles (name, description, is_default)
                VALUES ('user', 'Standard user with basic access', true)
                RETURNING id
                """
            )
        )
        user_id = result.fetchone()[0]

    if user_id is None:
        raise Exception("Failed to restore user role during downgrade")

    # Restore default flags (user as default)
    connection.execute(sa.text("UPDATE roles SET is_default = false"))
    connection.execute(
        sa.text(
            """
            UPDATE roles
            SET is_default = true
            WHERE id = :user_id
            """
        ),
        {"user_id": user_id},
    )

    # Recreate viewer role with read-only permissions
    viewer = connection.execute(sa.text("SELECT id FROM roles WHERE name = 'viewer'")).fetchone()
    if not viewer:
        result = connection.execute(
            sa.text(
                """
                INSERT INTO roles (name, description, is_default)
                VALUES ('viewer', 'Read-only access', false)
                RETURNING id
                """
            )
        )
        viewer_id = result.fetchone()[0]
    else:
        viewer_id = viewer.id

    # Assign read-only permissions to viewer
    connection.execute(
        sa.text(
            """
            WITH perms AS (
                SELECT id FROM permissions WHERE name IN ('users:read', 'roles:read', 'permissions:read')
            )
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT :viewer_id, perms.id
            FROM perms
            ON CONFLICT DO NOTHING
            """
        ),
        {"viewer_id": viewer_id},
    )
