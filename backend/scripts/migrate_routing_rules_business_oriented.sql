-- 路由规则表迁移脚本：添加业务导向字段
-- 执行时间: 2025-10-13
-- 目的: 将路由规则从技术导向转换为业务导向设计

-- 设置搜索路径
SET search_path TO gateway, public;

-- 1. 添加新的业务导向字段
ALTER TABLE routing_rules
ADD COLUMN IF NOT EXISTS source_config JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS pipeline JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS target_systems JSONB;

-- 2. 修改旧字段为可空（保持向后兼容）
ALTER TABLE routing_rules
ALTER COLUMN conditions DROP NOT NULL,
ALTER COLUMN conditions SET DEFAULT '[]',
ALTER COLUMN logical_operator DROP NOT NULL,
ALTER COLUMN target_system_ids DROP NOT NULL;

-- 3. 为已存在的记录迁移数据（如果有数据）
-- 将旧版target_system_ids转换为新版target_systems格式
UPDATE routing_rules
SET target_systems = (
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', target_id::text,
            'timeout', 5000,
            'retry', 3,
            'protocol_options', NULL
        )
    )
    FROM jsonb_array_elements_text(target_system_ids) AS target_id
)
WHERE target_systems IS NULL AND target_system_ids IS NOT NULL;

-- 4. 为已存在的记录设置默认source_config
UPDATE routing_rules
SET source_config = jsonb_build_object(
    'protocols', '[]'::jsonb,
    'pattern', NULL,
    'source_ids', NULL
)
WHERE source_config = '{}';

-- 5. 为已存在的记录设置默认pipeline
UPDATE routing_rules
SET pipeline = jsonb_build_object(
    'parser', jsonb_build_object(
        'type', 'JSON',
        'enabled', true,
        'options', NULL
    ),
    'validator', jsonb_build_object(
        'enabled', true,
        'rules', NULL
    ),
    'transformer', jsonb_build_object(
        'enabled', false,
        'script', NULL,
        'mappings', NULL
    )
)
WHERE pipeline = '{}';

-- 6. 创建注释
COMMENT ON COLUMN routing_rules.source_config IS '数据源配置（业务导向）：包含protocols（协议列表）、pattern（数据模式匹配）、source_ids（指定数据源ID）';
COMMENT ON COLUMN routing_rules.pipeline IS '处理管道配置（业务导向）：包含parser（解析器）、validator（验证器）、transformer（转换器）';
COMMENT ON COLUMN routing_rules.target_systems IS '目标系统配置列表（业务导向）：包含id、timeout、retry、protocol_options';
COMMENT ON COLUMN routing_rules.conditions IS '路由条件列表（兼容旧版API）';
COMMENT ON COLUMN routing_rules.logical_operator IS '逻辑运算符（兼容旧版API）';
COMMENT ON COLUMN routing_rules.target_system_ids IS '目标系统ID列表（兼容旧版API）';

-- 7. 更新视图（使用新字段）
CREATE OR REPLACE VIEW active_routing_rules_v2 AS
SELECT
    id,
    name,
    description,
    priority,
    source_config,
    pipeline,
    target_systems,
    is_active,
    is_published,
    match_count,
    last_match_at,
    created_at,
    updated_at
FROM routing_rules
WHERE is_active = true AND is_published = true
ORDER BY priority DESC;

COMMENT ON VIEW active_routing_rules_v2 IS '活跃的路由规则（业务导向版本）';

-- 8. 验证迁移
DO $$
DECLARE
    rule_count INTEGER;
    migrated_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO rule_count FROM routing_rules;
    SELECT COUNT(*) INTO migrated_count FROM routing_rules WHERE target_systems IS NOT NULL;

    RAISE NOTICE '总路由规则数: %', rule_count;
    RAISE NOTICE '已迁移规则数: %', migrated_count;

    IF rule_count > 0 AND migrated_count < rule_count THEN
        RAISE WARNING '有 % 条规则未完全迁移，请检查数据', (rule_count - migrated_count);
    END IF;
END $$;

-- 完成
SELECT 'Routing rules migration to business-oriented design completed!' as status;
