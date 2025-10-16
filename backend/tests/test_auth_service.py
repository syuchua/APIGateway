from datetime import datetime

import pytest
from fastapi import HTTPException

from app.core.security.auth import auth_service


def test_password_hash_roundtrip():
    raw_password = "Secret123!"
    hashed = auth_service.get_password_hash(raw_password)

    assert hashed != raw_password
    assert auth_service.verify_password(raw_password, hashed)
    assert not auth_service.verify_password("wrong", hashed)


def test_access_token_creation_and_validation():
    payload = {"sub": "user-id", "username": "tester"}
    token = auth_service.create_access_token(payload)

    decoded = auth_service.verify_token(token, token_type="access")
    assert decoded["sub"] == payload["sub"]
    assert decoded["username"] == payload["username"]
    assert decoded["type"] == "access"


def test_refresh_token_rejection_for_access_validation():
    payload = {"sub": "user-id", "username": "tester"}
    refresh_token = auth_service.create_refresh_token(payload)

    with pytest.raises(HTTPException) as exc:
        auth_service.verify_token(refresh_token, token_type="access")

    assert exc.value.status_code == 401
