from __future__ import annotations

import os
from typing import Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Individual-account model for now (see BACKEND_DEV2_HANDOFF.md /
# FRONTEND_INTEGRATION.md for the Organizations/firm-account upgrade path).
# Every endpoint that touches a user's documents now derives `user_id` from
# a verified Clerk session token instead of trusting a client-supplied
# field - closing the "pass a different user_id and read someone else's
# documents" gap noted earlier in this project.

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
) -> str:
    """FastAPI dependency: verifies the request's Clerk session token.

    Use as `current_user_id: str = Depends(get_current_user_id)` on any
    route that should require a signed-in user. Returns Clerk's `sub` claim
    (the Clerk user ID) - this is what gets stored as `user_id` everywhere
    documents/search/audio already use that field.
    """
    if not _auth_enabled():
        return LOCAL_DEV_USER_ID

    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        claims = verify_clerk_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {exc}") from exc
    except RuntimeError as exc:
        # Misconfiguration (e.g. CLERK_JWKS_URL not set) - this is an ops
        # problem, not the caller's fault, but the safe default is still to
        # reject the request rather than let it through unauthenticated.
        raise HTTPException(status_code=401, detail=f"Auth is misconfigured: {exc}") from exc

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token is missing a 'sub' claim")

    return user_id
