"""Tests for JWT and password security utilities."""

from app.core.security import create_access_token, verify_token, hash_password, verify_password


def test_create_and_verify_token():
    token = create_access_token({"sub": "user-123", "type": "user"})
    payload = verify_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "user"


def test_expired_token():
    from datetime import timedelta
    import pytest
    token = create_access_token({"sub": "user-123"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(Exception):
        verify_token(token)


def test_password_hash():
    hashed = hash_password("test123")
    assert verify_password("test123", hashed)
    assert not verify_password("wrong", hashed)


def test_password_hash_different_each_time():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # different salts
    assert verify_password("same", h1)
    assert verify_password("same", h2)
