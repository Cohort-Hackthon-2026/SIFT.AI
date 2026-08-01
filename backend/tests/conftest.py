import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    """Yield a TestClient inside a `with` block.

    FastAPI/Starlette only run lifespan startup/shutdown handlers when the
    TestClient is used as a context manager. The previous test files did
    `client = TestClient(app)` at module scope (no `with`), which meant
    `app.state.vector_store` (and friends) were never set, and every route
    touching them raised AttributeError. Centralizing the fixture here fixes
    that for every test module in one place.
    """
    with TestClient(app) as test_client:
        yield test_client
