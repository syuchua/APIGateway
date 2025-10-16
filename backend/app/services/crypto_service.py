"""
加解密服务
"""
from __future__ import annotations

import base64
import os
from typing import Optional, Dict, Any, Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config.settings import get_settings


class CryptoServiceError(Exception):
    """加解密相关异常"""


class CryptoService:
    """提供对称加密与密钥管理的工具类"""

    def __init__(self, master_key: str):
        if not master_key:
            raise CryptoServiceError("Master key is required for encryption service")

        self._base_key = self._normalize_key(master_key.encode("utf-8"))
        self._active_key: Optional[bytes] = None

    @staticmethod
    def _normalize_key(key_bytes: bytes) -> bytes:
        if len(key_bytes) < 32:
            digest = hashes.Hash(hashes.SHA256())
            digest.update(key_bytes)
            return digest.finalize()
        return key_bytes[:32]

    @staticmethod
    def generate_key() -> bytes:
        """生成随机会话密钥"""
        return os.urandom(32)

    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """从密码派生密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))

    def encrypt_data(self, data: bytes, key: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """使用AES-GCM加密数据"""
        active_key = key or self._get_effective_key()
        if len(active_key) < 32:
            raise CryptoServiceError("Encryption key must be at least 32 bytes for AES-256")

        aesgcm = AESGCM(active_key[:32])
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return ciphertext, nonce

    def decrypt_data(self, ciphertext: bytes, nonce: bytes, key: Optional[bytes] = None) -> bytes:
        """解密数据"""
        active_key = key or self._get_effective_key()
        if len(active_key) < 32:
            raise CryptoServiceError("Encryption key must be at least 32 bytes for AES-256")

        aesgcm = AESGCM(active_key[:32])
        return aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt_message(self, message_data: bytes) -> Dict[str, str]:
        """加密消息payload"""
        session_key = self.generate_key()
        ciphertext, nonce = self.encrypt_data(message_data, session_key)
        encrypted_key, key_nonce = self.encrypt_data(session_key)

        return {
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
            "nonce": base64.b64encode(nonce).decode("utf-8"),
            "encrypted_key": base64.b64encode(encrypted_key).decode("utf-8"),
            "key_nonce": base64.b64encode(key_nonce).decode("utf-8"),
            "algorithm": "AES-256-GCM",
        }

    def decrypt_message(self, encrypted_message: Dict[str, Any]) -> bytes:
        """解密消息payload"""
        try:
            ciphertext = base64.b64decode(encrypted_message["ciphertext"])
            nonce = base64.b64decode(encrypted_message["nonce"])
            encrypted_key = base64.b64decode(encrypted_message["encrypted_key"])
            key_nonce = base64.b64decode(encrypted_message["key_nonce"])
        except KeyError as exc:
            raise CryptoServiceError(f"encrypted_message missing field: {exc}") from exc
        except Exception as exc:  # pragma: no cover - base64异常
            raise CryptoServiceError(f"Invalid encrypted payload: {exc}") from exc

        session_key = self.decrypt_data(encrypted_key, key_nonce)
        return self.decrypt_data(ciphertext, nonce, session_key)

    def wrap_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """加密后的统一包裹格式"""
        raw = self.encrypt_message(self._encode_json(payload))
        return {"encrypted_payload": raw}

    def unwrap_payload(self, encrypted_payload: Dict[str, Any]) -> Dict[str, Any]:
        """解密包裹格式"""
        raw_bytes = self.decrypt_message(encrypted_payload)
        return self._decode_json(raw_bytes)

    @staticmethod
    def _encode_json(payload: Dict[str, Any]) -> bytes:
        import json

        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def _decode_json(raw: bytes) -> Dict[str, Any]:
        import json

        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise CryptoServiceError("Decrypted payload must be a JSON object")
        return data

    def update_active_key(self, key_bytes: Optional[bytes]) -> None:
        """更新当前激活密钥"""
        if key_bytes is None:
            self._active_key = None
            return

        normalized = self._normalize_key(key_bytes)
        self._active_key = normalized

    def _get_effective_key(self) -> bytes:
        return self._active_key or self._base_key


_crypto_service: Optional[CryptoService] = None


def get_crypto_service() -> CryptoService:
    """获取全局加解密服务实例"""
    global _crypto_service
    if _crypto_service is None:
        settings = get_settings()
        _crypto_service = CryptoService(settings.ENCRYPTION_KEY)
    return _crypto_service
