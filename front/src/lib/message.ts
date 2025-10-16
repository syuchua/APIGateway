'use client';

import { notification } from 'antd';

// 创建一个兼容React 19的消息通知工具
class MessageHelper {
  static success(content: string) {
    setTimeout(() => {
      notification.success({
        message: '成功',
        description: content,
        placement: 'topRight',
        duration: 3,
      });
    }, 0);
  }

  static error(content: string) {
    setTimeout(() => {
      notification.error({
        message: '错误',
        description: content,
        placement: 'topRight',
        duration: 4,
      });
    }, 0);
  }

  static warning(content: string) {
    setTimeout(() => {
      notification.warning({
        message: '警告',
        description: content,
        placement: 'topRight',
        duration: 3,
      });
    }, 0);
  }

  static info(content: string) {
    setTimeout(() => {
      notification.info({
        message: '信息',
        description: content,
        placement: 'topRight',
        duration: 3,
      });
    }, 0);
  }
}

export { MessageHelper };