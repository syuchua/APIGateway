"""add encryption key table

Revision ID: 956573355384
Revises: add_routing_rule_v2_fields
Create Date: 2025-10-15 20:08:33.895960

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '956573355384'
down_revision: Union[str, Sequence[str], None] = 'add_routing_rule_v2_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "encryption_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("key_material", sa.LargeBinary(length=96), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra", postgresql.JSONB(), nullable=True),
        schema="gateway",
    )

    op.create_index(
        "ix_encryption_keys_active",
        "encryption_keys",
        ["is_active"],
        unique=False,
        schema="gateway",
    )
    op.create_index(
        "ix_encryption_keys_created_at",
        "encryption_keys",
        ["created_at"],
        unique=False,
        schema="gateway",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_encryption_keys_created_at", table_name="encryption_keys", schema="gateway")
    op.drop_index("ix_encryption_keys_active", table_name="encryption_keys", schema="gateway")
    op.drop_table("encryption_keys", schema="gateway")
