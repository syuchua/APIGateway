"""
数据转换器实现
根据配置转换数据格式，支持字段映射、添加/删除字段等
"""
import logging
from typing import Dict, Any, List, Callable, Optional, Union
from copy import deepcopy

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TransformConfig(BaseModel):
    """数据转换配置"""
    field_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="字段映射，格式：{'source.field': 'target.field'}"
    )
    remove_fields: List[str] = Field(
        default_factory=list,
        description="要移除的字段列表"
    )
    add_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="要添加的字段，值可以是常量或函数"
    )
    flatten_parsed_data: bool = Field(
        default=False,
        description="是否将parsed_data展平到根级别"
    )


class DataTransformer:
    """
    数据转换器

    功能：
    - 字段映射（支持嵌套字段）
    - 添加/删除字段
    - 展平parsed_data
    - 批量转换
    """

    def __init__(self, config: TransformConfig):
        """
        初始化数据转换器

        Args:
            config: 转换配置
        """
        self.config = config

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换单条数据

        Args:
            data: 输入数据

        Returns:
            转换后的数据
        """
        # 深拷贝避免修改原始数据
        result = deepcopy(data)

        # 0. 移除不能JSON序列化的字段（bytes类型）
        # 这很重要，因为raw_data等字段不应该被发送到目标系统
        self._sanitize_for_json(result)

        # 1. 展平parsed_data（如果配置）
        if self.config.flatten_parsed_data and "parsed_data" in result:
            parsed = result.pop("parsed_data")
            if isinstance(parsed, dict):
                # 将parsed_data的内容合并到根级别
                for key, value in parsed.items():
                    if key not in result:  # 避免覆盖已有字段
                        result[key] = value

        # 2. 字段映射
        if self.config.field_mapping:
            result = self._apply_field_mapping(result)

        # 3. 移除字段
        if self.config.remove_fields:
            for field in self.config.remove_fields:
                self._remove_field(result, field)

        # 4. 添加字段
        if self.config.add_fields:
            for field, value in self.config.add_fields.items():
                # 如果值是函数，调用它
                if callable(value):
                    value = value()
                self._set_field(result, field, value)

        return result

    def transform_batch(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量转换数据

        Args:
            data_list: 数据列表

        Returns:
            转换后的数据列表
        """
        return [self.transform(data) for data in data_list]

    def _apply_field_mapping(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用字段映射

        Args:
            data: 输入数据

        Returns:
            映射后的数据
        """
        result = deepcopy(data)

        for source_path, target_path in self.config.field_mapping.items():
            # 获取源字段值
            value = self._get_field(data, source_path)

            if value is not None:
                # 设置目标字段值
                self._set_field(result, target_path, value)

                # 移除源字段
                self._remove_field(result, source_path)

        return result

    def _get_field(self, data: Dict[str, Any], path: str) -> Any:
        """
        获取嵌套字段的值

        Args:
            data: 数据字典
            path: 字段路径（用点分隔）

        Returns:
            字段值，如果不存在返回None
        """
        parts = path.split('.')
        current = data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def _set_field(self, data: Dict[str, Any], path: str, value: Any):
        """
        设置嵌套字段的值

        Args:
            data: 数据字典
            path: 字段路径（用点分隔）
            value: 要设置的值
        """
        parts = path.split('.')

        if len(parts) == 1:
            # 简单字段
            data[parts[0]] = value
        else:
            # 嵌套字段
            current = data

            # 创建嵌套结构
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    # 如果路径上的值不是字典，无法继续
                    logger.warning(f"无法设置嵌套字段 {path}: {part} 不是字典")
                    return
                current = current[part]

            # 设置最终值
            current[parts[-1]] = value

    def _remove_field(self, data: Dict[str, Any], path: str):
        """
        移除嵌套字段

        Args:
            data: 数据字典
            path: 字段路径（用点分隔）
        """
        parts = path.split('.')

        if len(parts) == 1:
            # 简单字段
            data.pop(parts[0], None)
        else:
            # 嵌套字段
            current = data

            # 导航到父级
            for part in parts[:-1]:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    # 路径不存在，无需删除
                    return

            # 删除最终字段
            if isinstance(current, dict):
                current.pop(parts[-1], None)

    def _sanitize_for_json(self, data: Dict[str, Any]):
        """
        清理数据中不能JSON序列化的字段

        主要处理bytes类型的字段，直接移除它们
        因为这些字段（如raw_data）不应该被发送到目标系统

        Args:
            data: 数据字典
        """
        # 直接移除raw_data字段（bytes类型）
        if "raw_data" in data:
            del data["raw_data"]

        # 递归处理嵌套字典中的bytes字段
        for key in list(data.keys()):
            value = data[key]
            if isinstance(value, bytes):
                # 移除bytes类型的字段
                del data[key]
            elif isinstance(value, dict):
                # 递归处理嵌套字典
                self._sanitize_for_json(value)
            elif isinstance(value, list):
                # 处理列表中的字典
                for item in value:
                    if isinstance(item, dict):
                        self._sanitize_for_json(item)
