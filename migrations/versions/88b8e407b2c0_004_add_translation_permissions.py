"""004_add_translation_permissions

Revision ID: 88b8e407b2c0
Revises: ce8927b9ce10
Create Date: 2025-12-12 15:26:07.580366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88b8e407b2c0'
down_revision: Union[str, None] = 'ce8927b9ce10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add translation permissions and assign to roles."""
    # Get connection
    connection = op.get_bind()

    # Insert translation permissions
    permissions_data = [
        {
            'name': 'translations:read',
            'description': 'View translation configuration and history',
            'resource': 'translations',
            'action': 'read'
        },
        {
            'name': 'translations:manage',
            'description': 'Manage translation providers and languages',
            'resource': 'translations',
            'action': 'manage'
        },
        {
            'name': 'translations:translate',
            'description': 'Use translation service',
            'resource': 'translations',
            'action': 'translate'
        }
    ]

    # Insert permissions and collect IDs
    permission_ids = {}
    for perm in permissions_data:
        result = connection.execute(
            sa.text("""
                INSERT INTO permissions (name, description, resource, action)
                VALUES (:name, :description, :resource, :action)
                RETURNING id
            """),
            perm
        )
        permission_ids[perm['name']] = result.fetchone()[0]

    # Get role IDs
    admin_role = connection.execute(
        sa.text("SELECT id FROM roles WHERE name = 'admin'")
    ).fetchone()

    user_role = connection.execute(
        sa.text("SELECT id FROM roles WHERE name = 'user'")
    ).fetchone()

    if not admin_role or not user_role:
        raise Exception("Required roles (admin, user) not found in database")

    admin_role_id = admin_role[0]
    user_role_id = user_role[0]

    # Assign ALL translation permissions to admin role
    for perm_name, perm_id in permission_ids.items():
        connection.execute(
            sa.text("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (:role_id, :permission_id)
            """),
            {'role_id': admin_role_id, 'permission_id': perm_id}
        )

    # Assign only translate permission to user role
    connection.execute(
        sa.text("""
            INSERT INTO role_permissions (role_id, permission_id)
            VALUES (:role_id, :permission_id)
        """),
        {'role_id': user_role_id, 'permission_id': permission_ids['translations:translate']}
    )


def downgrade() -> None:
    """Remove translation permissions and role assignments."""
    connection = op.get_bind()

    # Delete role_permissions entries for translation permissions
    connection.execute(
        sa.text("""
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions
                WHERE resource = 'translations'
            )
        """)
    )

    # Delete translation permissions
    connection.execute(
        sa.text("""
            DELETE FROM permissions
            WHERE resource = 'translations'
        """)
    )
