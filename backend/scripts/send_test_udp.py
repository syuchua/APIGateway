#!/usr/bin/env python3
"""
UDP测试数据发送器 - 发送到测试数据源端口8001
"""
import socket
import struct
import time
import random
import json
from datetime import datetime


def send_binary_data(target_port: int = 8001):
    """发送二进制传感器数据（温度+湿度）"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    temp = random.uniform(20.0, 30.0)
    hum = random.uniform(40.0, 70.0)

    # 打包数据（小端序，2个float32）
    data = struct.pack('<ff', temp, hum)

    sock.sendto(data, ("127.0.0.1", target_port))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 发送二进制数据到端口 {target_port}")
    print(f"  温度={temp:.1f}℃, 湿度={hum:.1f}%")
    print(f"  原始数据: {data.hex()}")

    sock.close()


def send_json_data(target_port: int = 8001):
    """发送JSON格式数据"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    data = {
        "timestamp": datetime.now().isoformat(),
        "device_id": f"sensor-{random.randint(1, 5)}",
        "temperature": round(random.uniform(20.0, 30.0), 1),
        "humidity": round(random.uniform(40.0, 70.0), 1),
        "status": "online"
    }

    json_bytes = json.dumps(data).encode('utf-8')

    sock.sendto(json_bytes, ("127.0.0.1", target_port))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 发送JSON数据到端口 {target_port}")
    print(f"  数据: {json.dumps(data, ensure_ascii=False)}")

    sock.close()


def send_text_data(target_port: int = 8001):
    """发送纯文本数据"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    temp = round(random.uniform(20.0, 30.0), 1)
    hum = round(random.uniform(40.0, 70.0), 1)

    text = f"TEMP:{temp},HUM:{hum},TIME:{datetime.now().strftime('%H:%M:%S')}"

    sock.sendto(text.encode('utf-8'), ("127.0.0.1", target_port))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 发送文本数据到端口 {target_port}")
    print(f"  数据: {text}")

    sock.close()


def main():
    """主函数"""
    print("=" * 70)
    print("UDP测试数据发送器")
    print("=" * 70)
    print("目标端口: 8001 (UDP监听数据源)")
    print("=" * 70)
    print()

    try:
        while True:
            print("\n请选择发送数据类型:")
            print("  1. 二进制数据 (温度+湿度, float32)")
            print("  2. JSON数据")
            print("  3. 文本数据")
            print("  4. 连续发送测试 (每秒发送一次JSON数据)")
            print("  5. 退出")

            choice = input("\n请输入选项 (1-5): ").strip()

            if choice == '1':
                send_binary_data()
            elif choice == '2':
                send_json_data()
            elif choice == '3':
                send_text_data()
            elif choice == '4':
                print("\n开始连续发送测试 (按 Ctrl+C 停止)...")
                try:
                    count = 0
                    while True:
                        count += 1
                        print(f"\n--- 第 {count} 次发送 ---")
                        send_json_data()
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n\n✓ 已停止发送")
            elif choice == '5':
                print("\n再见!")
                break
            else:
                print("\n⚠️  无效选项，请重新选择")

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 发送失败: {e}")


if __name__ == "__main__":
    main()
