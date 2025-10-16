"""
UDP测试数据发送器

发送温度和湿度数据到网关进行测试
"""
import socket
import struct
import time
import random
from datetime import datetime


def send_sensor_data(temperature: float, humidity: float, target_host: str = "127.0.0.1", target_port: int = 9999):
    """
    发送传感器数据

    Args:
        temperature: 温度值（摄氏度）
        humidity: 湿度值（百分比）
        target_host: 目标主机
        target_port: 目标端口
    """
    # 创建UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 打包数据（小端序，2个float32）
    data = struct.pack('<ff', temperature, humidity)

    # 发送数据
    sock.sendto(data, (target_host, target_port))

    # 打印信息
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 发送数据: 温度={temperature:.1f}℃, 湿度={humidity:.1f}%")
    print(f"原始数据: {data.hex()}")

    # 关闭socket
    sock.close()


def main():
    """主函数"""
    print("=" * 60)
    print("UDP传感器数据发送器")
    print("=" * 60)
    print("目标: 127.0.0.1:9999")
    print("数据格式: 温度(float32) + 湿度(float32)")
    print("=" * 60)
    print("")

    try:
        # 测试场景1: 正常温度
        print("【场景1】发送正常温度数据（应该路由到正常系统）")
        for i in range(3):
            temp = random.uniform(18.0, 28.0)
            hum = random.uniform(40.0, 70.0)
            send_sensor_data(temp, hum)
            time.sleep(1)

        print("")
        time.sleep(2)

        # 测试场景2: 高温报警
        print("【场景2】发送高温数据（应该触发报警系统）")
        for i in range(3):
            temp = random.uniform(31.0, 40.0)
            hum = random.uniform(40.0, 70.0)
            send_sensor_data(temp, hum)
            time.sleep(1)

        print("")
        time.sleep(2)

        # 测试场景3: 临界值测试
        print("【场景3】发送临界温度数据")
        send_sensor_data(30.0, 60.0)  # 刚好30度，应该路由到正常系统
        time.sleep(1)
        send_sensor_data(30.1, 60.0)  # 超过30度，应该路由到报警系统
        time.sleep(1)

        print("")
        print("=" * 60)
        print("✓ 所有测试数据已发送")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 发送失败: {e}")


if __name__ == "__main__":
    main()
