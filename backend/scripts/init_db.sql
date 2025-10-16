-- API网关数据库初始化脚本
-- PostgreSQL 15+

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 设置时区
SET timezone = 'Asia/Shanghai';

-- 创建Schema
CREATE SCHEMA IF NOT EXISTS gateway;

-- 设置搜索路径
SET search_path TO gateway, public;

-- 创建数据源表
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    protocol_type VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT true,

    -- 连接配置（JSON格式）
    connection_config JSONB NOT NULL,

    -- 帧格式ID（可选，用于二进制协议）
    frame_schema_id UUID,

    -- 统计信息
    total_messages BIGINT DEFAULT 0,
    last_message_at TIMESTAMP WITH TIME ZONE,

    -- 审计字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),

    CONSTRAINT data_sources_protocol_check CHECK (protocol_type IN ('udp', 'http', 'websocket', 'tcp', 'mqtt'))
);

-- 创建目标系统表
CREATE TABLE IF NOT EXISTS target_systems (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    protocol_type VARCHAR(20) NOT NULL,
    endpoint TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,

    -- 转发器配置（JSON格式）
    forwarder_config JSONB NOT NULL,

    -- 数据转换配置（JSON格式）
    transform_config JSONB,

    -- 统计信息
    total_forwarded BIGINT DEFAULT 0,
    total_failed BIGINT DEFAULT 0,
    last_forward_at TIMESTAMP WITH TIME ZONE,

    -- 审计字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),

    CONSTRAINT target_systems_protocol_check CHECK (protocol_type IN ('http', 'websocket', 'tcp', 'udp', 'mqtt'))
);

-- 创建路由规则表
CREATE TABLE IF NOT EXISTS routing_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    priority INT DEFAULT 50,

    -- 条件配置（JSON数组）
    conditions JSONB NOT NULL DEFAULT '[]',
    logical_operator VARCHAR(10) DEFAULT 'AND',

    -- 目标系统ID列表（JSON数组）
    target_system_ids JSONB NOT NULL,

    -- 数据转换配置（JSON格式）
    data_transformation JSONB,

    -- 状态
    is_active BOOLEAN DEFAULT true,
    is_published BOOLEAN DEFAULT false,

    -- 统计信息
    match_count BIGINT DEFAULT 0,
    last_match_at TIMESTAMP WITH TIME ZONE,

    -- 审计字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),

    CONSTRAINT routing_rules_priority_check CHECK (priority BETWEEN 1 AND 100),
    CONSTRAINT routing_rules_logical_operator_check CHECK (logical_operator IN ('AND', 'OR'))
);

-- 创建帧格式表
CREATE TABLE IF NOT EXISTS frame_schemas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    description TEXT,
    protocol_type VARCHAR(20) NOT NULL,
    frame_type VARCHAR(20) NOT NULL,

    -- 帧总长度（固定长度帧）
    total_length INT,

    -- 字段定义（JSON数组）
    fields JSONB NOT NULL,

    -- 校验配置（JSON格式）
    checksum JSONB,

    -- 状态
    is_published BOOLEAN DEFAULT false,

    -- 审计字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),

    CONSTRAINT frame_schemas_protocol_check CHECK (protocol_type IN ('udp', 'tcp')),
    CONSTRAINT frame_schemas_type_check CHECK (frame_type IN ('fixed', 'variable', 'delimited')),
    UNIQUE (name, version)
);

-- 创建消息日志表（分区表）
CREATE TABLE IF NOT EXISTS message_logs (
    id UUID DEFAULT uuid_generate_v4(),
    message_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- 来源信息
    source_protocol VARCHAR(20) NOT NULL,
    source_id UUID,
    source_address TEXT,

    -- 原始数据
    raw_data BYTEA,
    raw_data_size INT,

    -- 解析后数据
    parsed_data JSONB,

    -- 处理状态
    processing_status VARCHAR(20) DEFAULT 'received',

    -- 路由信息
    matched_rules JSONB,
    target_systems JSONB,

    -- 错误信息
    error_message TEXT,
    error_stack TEXT,

    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- 创建消息日志分区（按月）
CREATE TABLE IF NOT EXISTS message_logs_2025_01 PARTITION OF message_logs
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE IF NOT EXISTS message_logs_2025_02 PARTITION OF message_logs
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- 创建转发日志表
CREATE TABLE IF NOT EXISTS forward_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id VARCHAR(100) NOT NULL,
    target_id UUID NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- 转发数据
    forward_data JSONB,

    -- 转发结果
    status VARCHAR(20) NOT NULL,
    retry_count INT DEFAULT 0,
    duration_ms INT,

    -- 错误信息
    error_message TEXT,

    CONSTRAINT forward_logs_status_check CHECK (status IN ('success', 'failed', 'pending', 'retrying'))
);

-- 创建索引
-- 数据源索引
CREATE INDEX idx_data_sources_protocol ON data_sources(protocol_type);
CREATE INDEX idx_data_sources_active ON data_sources(is_active);
CREATE INDEX idx_data_sources_created_at ON data_sources(created_at);

-- 目标系统索引
CREATE INDEX idx_target_systems_protocol ON target_systems(protocol_type);
CREATE INDEX idx_target_systems_active ON target_systems(is_active);
CREATE INDEX idx_target_systems_created_at ON target_systems(created_at);

-- 路由规则索引
CREATE INDEX idx_routing_rules_priority ON routing_rules(priority DESC);
CREATE INDEX idx_routing_rules_active ON routing_rules(is_active);
CREATE INDEX idx_routing_rules_published ON routing_rules(is_published);

-- 帧格式索引
CREATE INDEX idx_frame_schemas_protocol ON frame_schemas(protocol_type);
CREATE INDEX idx_frame_schemas_published ON frame_schemas(is_published);
CREATE INDEX idx_frame_schemas_name_version ON frame_schemas(name, version);

-- 消息日志索引
CREATE INDEX idx_message_logs_message_id ON message_logs(message_id);
CREATE INDEX idx_message_logs_source_id ON message_logs(source_id);
CREATE INDEX idx_message_logs_timestamp ON message_logs(timestamp);
CREATE INDEX idx_message_logs_status ON message_logs(processing_status);

-- 转发日志索引
CREATE INDEX idx_forward_logs_message_id ON forward_logs(message_id);
CREATE INDEX idx_forward_logs_target_id ON forward_logs(target_id);
CREATE INDEX idx_forward_logs_timestamp ON forward_logs(timestamp);
CREATE INDEX idx_forward_logs_status ON forward_logs(status);

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为各表创建更新时间触发器
CREATE TRIGGER update_data_sources_updated_at BEFORE UPDATE ON data_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_target_systems_updated_at BEFORE UPDATE ON target_systems
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_routing_rules_updated_at BEFORE UPDATE ON routing_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_frame_schemas_updated_at BEFORE UPDATE ON frame_schemas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 创建视图：活跃的路由规则
CREATE OR REPLACE VIEW active_routing_rules AS
SELECT * FROM routing_rules
WHERE is_active = true AND is_published = true
ORDER BY priority DESC;

-- 创建视图：系统统计
CREATE OR REPLACE VIEW system_statistics AS
SELECT
    (SELECT COUNT(*) FROM data_sources WHERE is_active = true) as active_data_sources,
    (SELECT COUNT(*) FROM target_systems WHERE is_active = true) as active_target_systems,
    (SELECT COUNT(*) FROM routing_rules WHERE is_active = true) as active_routing_rules,
    (SELECT COUNT(*) FROM frame_schemas WHERE is_published = true) as published_frame_schemas,
    (SELECT COUNT(*) FROM message_logs WHERE timestamp > NOW() - INTERVAL '24 hours') as messages_last_24h,
    (SELECT COUNT(*) FROM forward_logs WHERE timestamp > NOW() - INTERVAL '24 hours' AND status = 'success') as successful_forwards_24h,
    (SELECT COUNT(*) FROM forward_logs WHERE timestamp > NOW() - INTERVAL '24 hours' AND status = 'failed') as failed_forwards_24h;

-- 插入初始数据（可选）
COMMENT ON TABLE data_sources IS 'API网关数据源配置表';
COMMENT ON TABLE target_systems IS 'API网关目标系统配置表';
COMMENT ON TABLE routing_rules IS 'API网关路由规则配置表';
COMMENT ON TABLE frame_schemas IS 'API网关帧格式定义表';
COMMENT ON TABLE message_logs IS 'API网关消息日志表（分区表）';
COMMENT ON TABLE forward_logs IS 'API网关转发日志表';

-- 完成
SELECT 'Database initialization completed successfully!' as status;
