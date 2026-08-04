from __future__ import annotations

import time
from dataclasses import dataclass

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

import app.auth as auth_module
from app.auth import get_current_user_id, verify_clerk_token


@dataclass
class _FakeSigningKey:
    key: object


class _FakeJWKSClient:
    """Stands in for jwt.PyJWKClient so tests never hit the network.

    Clerk's real verification flow is: fetch JWKS -> pick the key matching
    the token's `kid` header -> verify the signature with that key. This
    fakes only the network fetch; the actual jwt.decode() call below (in
    verify_clerk_token) is the real PyJWT verification logic, so a bug in
    signature/expiry/issuer checking would still be caught here.
    """

    def __init__(self, public_key) -> None:
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return _FakeSigningKey(key=self._public_key)


@pytest.fixture()
def clerk_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture()
def mock_jwks(monkeypatch, clerk_keypair):
    """Point app.auth at our fake JWKS client and clean up after."""
    private_key, public_key = clerk_keypair
    monkeypatch.setattr(auth_module, "_get_jwks_client", lambda: _FakeJWKSClient(public_key))
    auth_module.reset_jwks_client_cache()
    yield private_key
    auth_module.reset_jwks_client_cache()


def _make_token(private_key, **claim_overrides) -> str:
    now = int(time.time())
    claims = {
        "sub": "user_2abcXYZ",  # Clerk user IDs look like this
        "iss": "https://test-instance.clerk.accounts.dev",
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(claim_overrides)
    return jwt.encode(claims, private_key, algorithm="RS256")


def test_verify_clerk_token_accepts_a_valid_token(mock_jwks) -> None:
    token = _make_token(mock_jwks)
    claims = verify_clerk_token(token)
    assert claims["sub"] == "user_2abcXYZ"


def test_verify_clerk_token_rejects_expired_token(mock_jwks) -> None:
    token = _make_token(mock_jwks, exp=int(time.time()) - 10)
    with pytest.raises(jwt.PyJWTError):
        verify_clerk_token(token)


def test_verify_clerk_token_rejects_tampered_signature(mock_jwks, clerk_keypair) -> None:
    other_private_key, _ = rsa.generate_private_key(public_exponent=65537, key_size=2048), None
    token_signed_by_someone_else = _make_token(other_private_key)
    with pytest.raises(jwt.PyJWTError):
        verify_clerk_token(token_signed_by_someone_else)


def test_verify_clerk_token_checks_issuer_when_configured(mock_jwks, monkeypatch) -> None:
    monkeypatch.setenv("CLERK_ISSUER", "https://the-real-clerk-instance.clerk.accounts.dev")
    token = _make_token(mock_jwks, iss="https://a-different-clerk-instance.clerk.accounts.dev")
    with pytest.raises(jwt.PyJWTError):
        verify_clerk_token(token)


def test_verify_clerk_token_checks_authorized_parties_when_configured(mock_jwks, monkeypatch) -> None:
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", "https://app.siftai.example")
    token = _make_token(mock_jwks, azp="https://some-other-frontend.example")
    with pytest.raises(jwt.PyJWTError):
        verify_clerk_token(token)


def test_verify_clerk_token_allows_matching_authorized_party(mock_jwks, monkeypatch) -> None:
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", "https://app.siftai.example,https://staging.siftai.example")
    token = _make_token(mock_jwks, azp="https://app.siftai.example")
    claims = verify_clerk_token(token)
    assert claims["sub"] == "user_2abcXYZ"


@pytest.mark.asyncio
async def test_get_current_user_id_rejects_missing_token(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    with pytest.raises(Exception) as exc_info:
        await get_current_user_id(credentials=None)
    assert "401" in str(exc_info.value) or getattr(exc_info.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_get_current_user_id_falls_back_to_dev_user_when_auth_disabled(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "false")
    user_id = await get_current_user_id(credentials=None)
    assert user_id == auth_module.LOCAL_DEV_USER_ID


def test_raw_client_rejects_request_without_bearer_token(raw_client, monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    response = raw_client.get("/api/v1/documents")
    assert response.status_code == 401
