#!/usr/bin/env python3
"""
快速UDP测试 - 发送10条测试数据
"""
import socket
import json
import time
import random
from datetime import datetime

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("=" * 60)
    print("开始发送UDP测试数据到 127.0.0.1:8001")
    print("=" * 60)
    print()

    for i in range(10):
        data = {
            "timestamp": datetime.now().isoformat(),
            "device_id": f"sensor-{random.randint(1, 3)}",
            "temperature": round(random.uniform(20.0, 35.0), 1),
            "humidity": round(random.uniform(40.0, 80.0), 1),
            "pressure": round(random.uniform(990.0, 1020.0), 1),
            "seq": i + 1
        }

        json_bytes = json.dumps(data).encode('utf-8')
        sock.sendto(json_bytes, ("127.0.0.1", 8001))

        print(f"[{i+1:2d}] {datetime.now().strftime('%H:%M:%S')} - "
              f"Sensor-{data['device_id'][-1]}: {data['temperature']}℃, {data['humidity']}%")

        time.sleep(0.5)

    sock.close()

    print()
    print("=" * 60)
    print("✓ 已发送 10 条测试数据")
    print("=" * 60)
    print()
    print("提示: 请检查前端监控页面查看日志")

if __name__ == "__main__":
    main()
