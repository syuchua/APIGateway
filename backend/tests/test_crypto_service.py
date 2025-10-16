"""
CryptoService 单元测试
"""
import json

import pytest

from app.services.crypto_service import CryptoService, get_crypto_service, CryptoServiceError


class TestCryptoService:
    """测试加解密服务"""

    def test_generate_and_encrypt_decrypt(self):
        service = get_crypto_service()
        plaintext = b"hello-encryption"

        ciphertext, nonce = service.encrypt_data(plaintext)
        assert ciphertext != plaintext
        decrypted = service.decrypt_data(ciphertext, nonce)

        assert decrypted == plaintext

    def test_wrap_and_unwrap_payload(self):
        service = get_crypto_service()
        payload = {"message": "hello", "value": 42}

        wrapped = service.wrap_payload(payload)
        assert "encrypted_payload" in wrapped

        unwrapped = service.unwrap_payload(wrapped["encrypted_payload"])
        assert unwrapped == payload

    def test_invalid_encrypted_payload(self):
        service = get_crypto_service()
        with pytest.raises(CryptoServiceError):
            service.decrypt_message({"ciphertext": "invalid"})
