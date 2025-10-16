"""加密密钥管理API"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.schemas.encryption_key import (
    EncryptionKeyCreate,
    EncryptionKeyResponse,
)
from app.schemas.response import success_response
from app.services.encryption_key_service import (
    EncryptionKeyError,
    get_encryption_key_service,
)


router = APIRouter()


@router.get("/", response_model=List[EncryptionKeyResponse])
async def list_encryption_keys():
    service = get_encryption_key_service()
    records = await service.list_keys()
    return [EncryptionKeyResponse(**key.to_dict()) for key in records]


@router.post("/", response_model=EncryptionKeyResponse)
async def create_encryption_key(payload: EncryptionKeyCreate):
    service = get_encryption_key_service()
    key_bytes = None
    if payload.key_material:
        import base64

        try:
            key_bytes = base64.b64decode(payload.key_material)
        except Exception as exc:  # pragma: no cover - base64异常
            raise HTTPException(status_code=400, detail=f"Invalid key material: {exc}") from exc

    try:
        record = await service.create_key(
            name=payload.name,
            description=payload.description,
            key_material=key_bytes,
            is_active=payload.is_active,
            metadata=payload.metadata,
            expires_at=payload.expires_at,
        )
    except EncryptionKeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return EncryptionKeyResponse(**record.to_dict())


@router.post("/{key_id}/activate")
async def activate_encryption_key(key_id: UUID):
    service = get_encryption_key_service()
    try:
        record = await service.activate_key(key_id)
    except EncryptionKeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return success_response(EncryptionKeyResponse(**record.to_dict()))


@router.post("/{key_id}/deactivate")
async def deactivate_encryption_key(key_id: UUID):
    service = get_encryption_key_service()
    try:
        record = await service.deactivate_key(key_id)
    except EncryptionKeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return success_response(EncryptionKeyResponse(**record.to_dict()))


@router.delete("/{key_id}")
async def delete_encryption_key(key_id: UUID):
    service = get_encryption_key_service()
    try:
        await service.delete_key(key_id)
    except EncryptionKeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return success_response()
