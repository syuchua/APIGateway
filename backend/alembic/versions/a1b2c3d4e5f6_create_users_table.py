"""create users table

Revision ID: a1b2c3d4e5f6
Revises: 956573355384
Create Date: 2025-10-16 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "956573355384"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table."""
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("email", sa.String(length=255), nullable=True, unique=True),
        sa.Column("full_name", sa.String(length=128), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("avatar", sa.Text(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        schema="gateway",
    )

    op.create_index(
        "ix_users_username",
        "users",
        ["username"],
        unique=True,
        schema="gateway",
    )
    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
        unique=True,
        schema="gateway",
    )


def downgrade() -> None:
    """Drop users table."""
    op.drop_index("ix_users_email", table_name="users", schema="gateway")
    op.drop_index("ix_users_username", table_name="users", schema="gateway")
    op.drop_table("users", schema="gateway")
