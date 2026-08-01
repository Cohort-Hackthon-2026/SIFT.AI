# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.routes.audio import router as audio_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.db.registry import create_document_registry
from app.services.cache import create_search_cache
from app.services.vector_store import create_vector_store_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Ahnlich store on server startup
    app.state.vector_store = create_vector_store_service()
    await app.state.vector_store.initialize()

    # Initialize the document registry (Postgres/Neon if DATABASE_URL is
    # set, otherwise an in-memory fallback so the API still boots locally).
    app.state.document_registry = create_document_registry()
    await app.state.document_registry.initialize()

    # Initialize the search-result cache (Redis if REDIS_URL is set,
    # otherwise a no-op cache).
    app.state.search_cache = create_search_cache()

    yield


app = FastAPI(title="SIFT.AI API", version="0.1.0", lifespan=lifespan)

app.include_router(health_router)
app.include_router(documents_router)
app.include_router(audio_router)
