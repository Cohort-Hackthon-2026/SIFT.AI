import os

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.auth import get_current_user_id
from app.main import app
from app.rate_limit import get_rate_limiter
from app.services.storage import NoopStorageService

DEFAULT_TEST_USER_ID = "test-user-1"


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """Rate limiting is a process-wide singleton keyed by user_id; left on, a
    full suite run would exceed the per-minute quota for the shared test user
    and start returning 429s. Disable it by default and reset the window
    between tests. The dedicated rate-limit test re-enables it explicitly.
    """
    prev = os.environ.get("RATE_LIMIT_ENABLED")
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    get_rate_limiter().reset()
    yield
    get_rate_limiter().reset()
    if prev is None:
        os.environ.pop("RATE_LIMIT_ENABLED", None)
    else:
        os.environ["RATE_LIMIT_ENABLED"] = prev


@pytest.fixture(autouse=True)
def noop_storage():
    """Patch create_storage_service for every test so no test ever makes a
    real R2 network call.  Tests that specifically exercise R2StorageService
    instantiate it directly and mock boto3 themselves.
    """
    with patch("app.main.create_storage_service", return_value=NoopStorageService()):
        yield


@pytest.fixture()
def client():
    """Authenticated TestClient (auth dependency overridden to a fixed user).

    Most tests exercise document/search behavior, not the auth layer
    itself - real Clerk JWT verification (signature, expiry, issuer,
    missing token) is covered separately in test_auth.py. Overriding the
    dependency here is the standard FastAPI testing pattern
    (`app.dependency_overrides`) rather than minting real signed tokens for
    every test.

    FastAPI/Starlette only run lifespan startup/shutdown handlers when the
    TestClient is used as a context manager, which is why this is a `with`
    block rather than a bare `TestClient(app)`.
    """
    app.dependency_overrides[get_current_user_id] = lambda: DEFAULT_TEST_USER_ID
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_current_user_id, None)


@pytest.fixture()
def raw_client():
    """TestClient with no auth override - the real get_current_user_id dependency runs.

    Use this for testing 401s and the shape of unauthenticated requests.
    """
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_current_user_id, None)


@pytest.fixture()
def as_user(client):
    """Within a test, switch the already-authenticated `client` to a
    different user_id - useful for cross-user ownership tests (e.g. user A
    uploads a document, user B must not be able to see/delete it).
    """

    def _set(user_id: str) -> None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id

    yield _set
    app.dependency_overrides[get_current_user_id] = lambda: DEFAULT_TEST_USER_ID
