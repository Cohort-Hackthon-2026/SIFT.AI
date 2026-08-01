# app/main.py
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# The Vite dev server (frontend/) runs on a different origin than this API,
# so the browser blocks every request unless CORS is explicitly allowed.
# CORS_ALLOWED_ORIGINS is a comma-separated list; defaults cover the two
# ports the frontend README/Dockerfile actually use.
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", _default_origins).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(documents_router)
app.include_router(audio_router)

# test