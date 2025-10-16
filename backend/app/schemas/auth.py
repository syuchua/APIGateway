"""
认证相关Pydantic Schemas
"""
from typing import List, Optional, Literal

from pydantic import Field

from .common import BaseSchema, UUIDMixin, TimestampMixin


class LoginRequest(BaseSchema):
    """登录请求"""

    username: str = Field(..., min_length=1, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


class RefreshRequest(BaseSchema):
    """刷新令牌请求"""

    refresh_token: str = Field(..., min_length=1, description="刷新令牌")


class UserProfile(UUIDMixin, TimestampMixin, BaseSchema):
    """用户档案信息"""

    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str
    permissions: List[str] = Field(default_factory=list)
    avatar: Optional[str] = None


class LoginResponse(BaseSchema):
    """登录响应"""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserProfile


class RefreshResponse(BaseSchema):
    """刷新令牌响应"""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


__all__ = [
    "LoginRequest",
    "RefreshRequest",
    "UserProfile",
    "LoginResponse",
    "RefreshResponse",
]
