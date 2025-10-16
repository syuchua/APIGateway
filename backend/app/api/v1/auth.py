"""
认证相关API
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.core.security.auth import auth_service, permission_service
from app.db.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    UserProfile,
)

router = APIRouter(tags=["认证"])


def _build_user_profile(user: User) -> UserProfile:
    """构建用户档案信息"""
    return UserProfile(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        permissions=permission_service.list_permissions(user.role),
        avatar=user.avatar,
        created_at=user.created_at or datetime.utcnow(),
        updated_at=user.updated_at or datetime.utcnow(),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """用户登录"""
    repo = UserRepository(db)
    user = await repo.get_by_username(payload.username)

    if not user or not auth_service.verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled",
        )

    user.mark_login()
    await db.flush()

    claims = {"sub": str(user.id), "username": user.username, "role": user.role}
    access_token = auth_service.create_access_token(claims)
    refresh_token = auth_service.create_refresh_token({"sub": str(user.id), "username": user.username})

    await db.commit()

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_build_user_profile(user),
    )


@router.post("/logout")
async def logout() -> dict:
    """用户登出（无状态，前端清理Token即可）"""
    return {"message": "Logged out"}


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    """刷新访问令牌"""
    refresh_payload = auth_service.verify_token(payload.refresh_token, token_type="refresh")
    subject = refresh_payload.get("sub")

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    repo = UserRepository(db)
    try:
        user = await repo.get_by_id(UUID(subject))
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    claims = {"sub": str(user.id), "username": user.username, "role": user.role}
    access_token = auth_service.create_access_token(claims)
    new_refresh_token = auth_service.create_refresh_token({"sub": str(user.id), "username": user.username})

    return RefreshResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/profile", response_model=UserProfile)
async def get_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserProfile:
    """获取当前用户信息"""
    return _build_user_profile(current_user)
