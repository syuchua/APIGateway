#!/usr/bin/env python3
"""
帧格式管理工具链

示例：
    # 列出所有帧格式
    uv run python scripts/manage_frame_schemas.py list

    # 仅列出 UDP 帧格式
    uv run python scripts/manage_frame_schemas.py list --protocol UDP

    # 从 JSON 文件批量导入帧格式（文件可包含单个对象或数组）
    uv run python scripts/manage_frame_schemas.py import ./examples/frame_schemas.json --publish
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from app.db.database import AsyncSessionLocal
from app.repositories.frame_schema import FrameSchemaRepository
from app.schemas.common import ChecksumType, FrameType, ProtocolType


def _normalize_protocol(value: str) -> str:
    try:
        return ProtocolType(value.upper()).value.lower()
    except ValueError as exc:
        raise ValueError(f"不支持的协议类型: {value}") from exc


def _normalize_frame_type(value: str) -> str:
    try:
        return FrameType(value.upper()).value.lower()
    except ValueError as exc:
        raise ValueError(f"不支持的帧类型: {value}") from exc


def _normalize_checksum(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not data:
        return None
    checksum_type = data.get("type") or data.get("checksum_type") or ChecksumType.NONE.value
    try:
        checksum_type = ChecksumType(checksum_type.upper()).value
    except ValueError:
        checksum_type = ChecksumType.NONE.value
    payload: Dict[str, Any] = {"type": checksum_type}
    if data.get("offset") is not None:
        payload["offset"] = int(data["offset"])
    if data.get("length") is not None:
        payload["length"] = int(data["length"])
    if checksum_type == ChecksumType.NONE.value:
        return None
    return payload


async def list_schemas(protocol: Optional[str]) -> None:
    """列出帧格式"""
    filters: Dict[str, Any] = {}
    if protocol:
        filters["protocol_type"] = _normalize_protocol(protocol)

    async with AsyncSessionLocal() as session:
        repo = FrameSchemaRepository(session)
        schemas = await repo.get_all(**filters)

        if not schemas:
            print("⚠️ 未找到符合条件的帧格式")
            return

        for fs in schemas:
            checksum = fs.checksum or {}
            print(
                f"- {fs.name} v{fs.version} ({fs.protocol_type}/{fs.frame_type}) "
                f"{'已发布' if fs.is_published else '未发布'} "
                f"[fields={len(fs.fields)}, checksum={checksum.get('type', 'NONE')}]"
            )


async def import_schemas(path: Path, publish: bool = False) -> None:
    """从文件导入帧格式定义"""
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)

    if isinstance(payload, dict):
        payloads: Iterable[Dict[str, Any]] = [payload]
    elif isinstance(payload, list):
        payloads = payload
    else:
        raise ValueError("文件内容必须是对象或对象数组")

    async with AsyncSessionLocal() as session:
        repo = FrameSchemaRepository(session)

        for item in payloads:
            name = item["name"]
            version = item.get("version", "1.0.0")
            protocol_type = _normalize_protocol(item.get("protocol_type", "UDP"))
            frame_type = _normalize_frame_type(item.get("frame_type", "FIXED"))
            total_length = item.get("total_length")
            fields = item.get("fields") or []
            checksum = _normalize_checksum(item.get("checksum"))
            description = item.get("description")

            if not fields:
                print(f"⚠️ 跳过 {name} v{version}：字段定义为空")
                continue

            existing = await repo.get_by_name_version(name, version)
            if existing:
                print(f"⚠️ 跳过 {name} v{version}：已存在")
                continue

            fs = await repo.create(
                name=name,
                description=description,
                version=version,
                protocol_type=protocol_type,
                frame_type=frame_type,
                total_length=total_length,
                fields=fields,
                checksum=checksum,
                is_published=publish,
            )
            if publish and not fs.is_published:
                await repo.publish(fs.id)

            print(f"✅ 导入帧格式: {name} v{version}")

        await session.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="帧格式管理工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="列出帧格式")
    list_parser.add_argument("--protocol", help="按协议过滤（例如：UDP、TCP）", default=None)

    import_parser = subparsers.add_parser("import", help="从 JSON 文件导入帧格式")
    import_parser.add_argument("path", type=Path, help="帧格式定义 JSON 文件路径")
    import_parser.add_argument(
        "--publish",
        action="store_true",
        help="导入后立即标记为已发布",
    )

    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    if args.command == "list":
        await list_schemas(args.protocol)
    elif args.command == "import":
        await import_schemas(args.path, publish=args.publish)
    else:
        raise ValueError(f"未知命令: {args.command}")


if __name__ == "__main__":
    asyncio.run(main())
