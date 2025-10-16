"""
认证与授权服务
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import HTTPException, status
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from passlib.context import CryptContext

from app.config.settings import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """认证服务"""

    def __init__(self) -> None:
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """生成密码哈希"""
        return pwd_context.hash(password)

    def _create_token(self, data: Dict[str, Any], expires_delta: timedelta, token_type: str) -> str:
        """创建JWT令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire, "type": token_type})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_access_token(self, data: Dict[str, Any]) -> str:
        """创建访问令牌"""
        return self._create_token(
            data,
            expires_delta=timedelta(minutes=self.access_token_expire_minutes),
            token_type="access",
        )

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """创建刷新令牌"""
        return self._create_token(
            data,
            expires_delta=timedelta(days=self.refresh_token_expire_days),
            token_type="refresh",
        )

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """验证令牌并返回载荷"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        return payload


class PermissionService:
    """权限服务"""

    _PERMISSIONS: Dict[str, str] = {
        "data_source.read": "读取数据源",
        "data_source.write": "写入数据源",
        "data_source.delete": "删除数据源",
        "target_system.read": "读取目标系统",
        "target_system.write": "写入目标系统",
        "target_system.delete": "删除目标系统",
        "routing_rule.read": "读取路由规则",
        "routing_rule.write": "写入路由规则",
        "routing_rule.delete": "删除路由规则",
        "frame_schema.read": "读取帧格式",
        "frame_schema.write": "写入帧格式",
        "frame_schema.delete": "删除帧格式",
        "monitoring.read": "读取监控数据",
        "system.admin": "系统管理员",
    }

    _ROLE_PERMISSIONS: Dict[str, List[str]] = {
        "admin": list(_PERMISSIONS.keys()),
        "operator": [
            "data_source.read",
            "data_source.write",
            "target_system.read",
            "target_system.write",
            "routing_rule.read",
            "routing_rule.write",
            "frame_schema.read",
            "frame_schema.write",
            "monitoring.read",
        ],
        "viewer": [
            "data_source.read",
            "target_system.read",
            "routing_rule.read",
            "frame_schema.read",
            "monitoring.read",
        ],
    }

    def has_permission(self, role: str, permission: str) -> bool:
        """检查角色是否拥有某权限"""
        permissions = self._ROLE_PERMISSIONS.get(role, [])
        return permission in permissions or "system.admin" in permissions

    def list_permissions(self, role: str) -> List[str]:
        """列出角色拥有的权限"""
        return self._ROLE_PERMISSIONS.get(role, [])


auth_service = AuthService()
permission_service = PermissionService()

__all__ = ["auth_service", "permission_service"]
