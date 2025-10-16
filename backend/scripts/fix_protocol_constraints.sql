-- 修复协议类型CHECK约束，改为大写
-- 用于修复API使用大写枚举值而数据库约束使用小写的问题

-- 1. 删除旧的CHECK约束
ALTER TABLE gateway.data_sources DROP CONSTRAINT IF EXISTS data_sources_protocol_check;
ALTER TABLE gateway.target_systems DROP CONSTRAINT IF EXISTS target_systems_protocol_check;
ALTER TABLE gateway.frame_schemas DROP CONSTRAINT IF EXISTS frame_schemas_protocol_check;

-- 2. 添加新的CHECK约束（大写）
ALTER TABLE gateway.data_sources
ADD CONSTRAINT data_sources_protocol_check
CHECK (protocol_type IN ('UDP', 'HTTP', 'WEBSOCKET', 'TCP', 'MQTT'));

ALTER TABLE gateway.target_systems
ADD CONSTRAINT target_systems_protocol_check
CHECK (protocol_type IN ('HTTP', 'WEBSOCKET', 'TCP', 'UDP', 'MQTT'));

ALTER TABLE gateway.frame_schemas
ADD CONSTRAINT frame_schemas_protocol_check
CHECK (protocol_type IN ('UDP', 'TCP'));

-- 3. 更新现有数据（如果有的话）将小写转为大写
UPDATE gateway.data_sources SET protocol_type = UPPER(protocol_type);
UPDATE gateway.target_systems SET protocol_type = UPPER(protocol_type);
UPDATE gateway.frame_schemas SET protocol_type = UPPER(protocol_type);
