"""添加routing_rules的source_config和pipeline字段

Revision ID: add_routing_rule_v2_fields
Revises:
Create Date: 2025-10-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'add_routing_rule_v2_fields'
down_revision = None
depends_on = None


def upgrade() -> None:
    """添加新字段到routing_rules表"""
    # 添加source_config字段（如果不存在）
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema='gateway'
                  AND table_name='routing_rules'
                  AND column_name='source_config'
            ) THEN
                ALTER TABLE gateway.routing_rules
                ADD COLUMN source_config JSONB NOT NULL DEFAULT '{}';
            END IF;
        END$$;
    """)

    # 添加pipeline字段（如果不存在）
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema='gateway'
                  AND table_name='routing_rules'
                  AND column_name='pipeline'
            ) THEN
                ALTER TABLE gateway.routing_rules
                ADD COLUMN pipeline JSONB NOT NULL DEFAULT '{}';
            END IF;
        END$$;
    """)

    # 添加target_systems字段（如果不存在）
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema='gateway'
                  AND table_name='routing_rules'
                  AND column_name='target_systems'
            ) THEN
                ALTER TABLE gateway.routing_rules
                ADD COLUMN target_systems JSONB NOT NULL DEFAULT '[]';
            END IF;
        END$$;
    """)

    # 如果存在数据，将target_system_ids迁移到target_systems
    op.execute("""
        UPDATE gateway.routing_rules
        SET target_systems = (
            SELECT jsonb_agg(jsonb_build_object('id', elem::text, 'enabled', true))
            FROM jsonb_array_elements_text(COALESCE(target_system_ids, '[]'::jsonb)) elem
        )
        WHERE target_system_ids IS NOT NULL
          AND target_system_ids != 'null'::jsonb
          AND jsonb_array_length(target_system_ids) > 0;
    """)

    print("✅ 成功添加 source_config, pipeline, target_systems 字段")


def downgrade() -> None:
    """删除添加的字段"""
    op.execute("""
        ALTER TABLE gateway.routing_rules
        DROP COLUMN IF EXISTS source_config;
    """)

    op.execute("""
        ALTER TABLE gateway.routing_rules
        DROP COLUMN IF EXISTS pipeline;
    """)

    op.execute("""
        ALTER TABLE gateway.routing_rules
        DROP COLUMN IF EXISTS target_systems;
    """)

    print("✅ 成功删除 source_config, pipeline, target_systems 字段")
