# 修复脚本中的状态码判断
import sys

# 修复 create_test_data_sources.py
with open('create_test_data_sources.py', 'r') as f:
    content = f.read()

# 1. 修复状态码判断
content = content.replace(
    'if response.status_code == 200:',
    'if response.status_code in (200, 201):'
)

# 2. 修复 frame_schema_id - 删除这个字段，让它为 None
content = content.replace(
    '                "frame_schema_id": "modbus-rtu-schema",',
    '                # "frame_schema_id": None,  # 如需指定帧格式，需要先创建帧格式并使用其UUID'
)

with open('create_test_data_sources.py', 'w') as f:
    f.write(content)

# 修复 create_test_target_systems.py
with open('create_test_target_systems.py', 'r') as f:
    content = f.read()

# 1. 修复状态码判断
content = content.replace(
    'if response.status_code == 200:',
    'if response.status_code in (200, 201):'
)

# 2. 修复 endpoint_path: null -> 空字符串或删除
content = content.replace(
    '                "endpoint_path": None,',
    '                # endpoint_path 对于 MQTT/UDP/TCP 不需要'
)

with open('create_test_target_systems.py', 'w') as f:
    f.write(content)

print("✅ 脚本修复完成")
