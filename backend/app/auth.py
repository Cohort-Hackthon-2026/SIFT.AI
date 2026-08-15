from __future__ import annotations

import os
from typing import Any

import jwt
import logging
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# Individual-account model for now (see BACKEND_DEV2_HANDOFF.md /
# FRONTEND_INTEGRATION.md for the Organizations/firm-account upgrade path).
# Every endpoint that touches a user's documents now derives `user_id` from
# a verified Clerk session token or browser-pinned guest session.

LOCAL_DEV_USER_ID = "local-dev-user"

_security = HTTPBearer(auto_error=False)

# Cached lazily (not at import time) so tests can monkeypatch
# CLERK_JWKS_URL/os.environ before the client is ever constructed, and so a
# misconfigured/missing value only breaks requests, not app startup.
_jwks_client: jwt.PyJWKClient | None = None


def _auth_enabled() -> bool:
    return os.getenv("AUTH_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def _get_jwks_client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        jwks_url = os.getenv("CLERK_JWKS_URL")
        if not jwks_url:
            raise RuntimeError(
                "CLERK_JWKS_URL is not set. Find it in the Clerk Dashboard under "
                "Configure -> API Keys -> Advanced -> JWKS URL. For local "
                "development without a Clerk account yet, set AUTH_ENABLED=false "
                "instead."
            )
        # PyJWKClient fetches + caches Clerk's public signing keys itself
        # (keyed by `kid`, refetched automatically after `lifespan` seconds
        # or on a cache miss e.g. after Clerk rotates keys) - no separate
        # caching layer needed here.
        _jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
    return _jwks_client


def reset_jwks_client_cache() -> None:
    """Test hook: force the next call to rebuild the PyJWKClient.

    Needed because tests monkeypatch CLERK_JWKS_URL per-test; without this
    the first test to run would permanently pin the client to its URL.
    """
    global _jwks_client
    _jwks_client = None


def verify_clerk_token(token: str) -> dict[str, Any]:
    """Verify a Clerk-issued session JWT and return its claims.

    Raises jwt.PyJWTError (or a subclass) on any invalid/expired/tampered/
    wrong-issuer token - callers translate that into an HTTP 401.
    """
    jwks_client = _get_jwks_client()
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    issuer = os.getenv("CLERK_ISSUER")
    authorized_parties = [
        party.strip() for party in os.getenv("CLERK_AUTHORIZED_PARTIES", "").split(",") if party.strip()
    ]

    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=issuer or None,
        options={"verify_iss": bool(issuer)},
    )

    # `azp` ("authorized party") identifies which frontend origin requested
    # the token. Checking it (when configured) stops a token minted for a
    # different application from being replayed against this API.
    if authorized_parties and claims.get("azp") not in authorized_parties:
        raise jwt.InvalidTokenError(f"Token azp '{claims.get('azp')}' is not an authorized party")

    return claims


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
    request: Request = None,
) -> str:
    """FastAPI dependency: verifies the request's Clerk session token or guest session ID.

    Use as `current_user_id: str = Depends(get_current_user_id)` on any route.
    - If a guest token (`guest_...`, `local-...`, `test-...`) is provided, returns it as the user_id.
    - If `X-Guest-ID` header is provided, returns the guest ID.
    - If a valid Clerk JWT is provided, returns Clerk's `sub` claim.
    - If AUTH_ENABLED is False, returns LOCAL_DEV_USER_ID.
    - If credentials are missing and no guest ID is provided, raises HTTP 401.
    """
    if not _auth_enabled():
        return LOCAL_DEV_USER_ID

    # 1. Check Bearer Token
    if credentials and credentials.credentials:
        token = credentials.credentials.strip()
        # Guest or Local/Test Session Token
        if token.startswith("guest_") or token.startswith("local-") or token.startswith("test-"):
            return token

        # Clerk JWT Token
        try:
            claims = verify_clerk_token(token)
            user_id = claims.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Token is missing a 'sub' claim")
            return user_id
        except (jwt.PyJWTError, RuntimeError) as exc:
            # If it's a guest or custom prefix, allow through
            if token.startswith("guest_") or token.startswith("local-") or token.startswith("test-"):
                return token
            raise HTTPException(status_code=401, detail=f"Invalid or expired token: {exc}") from exc

    # 2. Check X-Guest-ID header on request if available
    if request is not None:
        guest_header = request.headers.get("X-Guest-ID") or request.headers.get("x-guest-id")
        if guest_header and guest_header.strip():
            clean_guest = guest_header.strip()
            return clean_guest if clean_guest.startswith("guest_") else f"guest_{clean_guest}"

    # 3. Missing bearer token
    raise HTTPException(status_code=401, detail="Missing bearer token")


