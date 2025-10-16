#!/usr/bin/env python3
"""
简单UDP测试流程

1. 直接发送UDP数据到指定端口（不需要启动适配器）
2. 检查数据是否被记录到数据库
"""
import socket
import json
import time
from datetime import datetime

def send_udp_test():
    """发送UDP测试数据"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("=" * 70)
    print("UDP测试数据发送 - 发送到 127.0.0.1:8001")
    print("=" * 70)
    print()
    print("注意: 当前系统架构下，需要手动启动UDP适配器才能接收数据")
    print("      或者使用 complete_demo.py 演示完整流程")
    print()
    print("发送10条JSON测试数据...")
    print()

    for i in range(10):
        data = {
            "timestamp": datetime.now().isoformat(),
            "device_id": f"sensor-{(i % 3) + 1}",
            "temperature": round(20.0 + i * 1.5, 1),
            "humidity": round(50.0 + i * 2, 1),
            "seq": i + 1
        }

        json_bytes = json.dumps(data).encode('utf-8')

        try:
            sock.sendto(json_bytes, ("127.0.0.1", 8001))
            print(f"✓ [{i+1:2d}] {datetime.now().strftime('%H:%M:%S')} - "
                  f"Sensor-{data['device_id'][-1]}: {data['temperature']}℃")
            time.sleep(0.3)
        except Exception as e:
            print(f"✗ [{i+1:2d}] 发送失败: {e}")

    sock.close()

    print()
    print("=" * 70)
    print("发送完成！")
    print()
    print("下一步:")
    print("  1. 由于UDP适配器未启动，数据不会被处理")
    print("  2. 要测试完整流程，请运行: uv run python examples/complete_demo.py")
    print("  3. 然后在另一个终端运行: uv run python examples/udp_sender.py")
    print()
    print("或者通过前端页面:")
    print("  1. 访问 http://localhost:3001/data-sources")
    print("  2. 找到UDP数据源，点击'启用'按钮启动适配器")
    print("  3. 然后运行此脚本发送数据")
    print("=" * 70)

if __name__ == "__main__":
    send_udp_test()
