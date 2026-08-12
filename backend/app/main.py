# app/main.py
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.audio import router as audio_router
from app.api.routes.audit import router as audit_router
from app.api.routes.billing import router as billing_router
from app.api.routes.chambers import router as chambers_router
from app.api.routes.chat import router as chat_router
from app.api.routes.chats import router as chats_router
from app.api.routes.documents import router as documents_router
from app.api.routes.exports import router as exports_router
from app.api.routes.health import router as health_router
from app.api.routes.matters import router as matters_router
from app.api.routes.me import router as me_router
from app.api.routes.privacy import router as privacy_router
from app.config import get_settings
from app.db.audit_registry import create_audit_registry
from app.db.billing_registry import create_billing_registry
from app.db.chambers_registry import create_chambers_registry
from app.db.chat_registry import create_chat_registry
from app.db.matter_registry import create_matter_registry
from app.db.profile_registry import create_profile_registry
from app.db.registry import create_document_registry
from app.services.cache import create_search_cache
from app.services.storage import create_storage_service
from app.services.vector_store import create_vector_store_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate + report configuration up front so missing critical keys
    # (e.g. GEMINI_API_KEY) surface in the logs at boot rather than deep
    # inside the first chat stream.
    app.state.settings = get_settings()
    app.state.settings.log_startup_report()

    # Initialize Ahnlich store on server startup
    app.state.vector_store = create_vector_store_service()
    await app.state.vector_store.initialize()

    # Initialize the document registry (Postgres/Neon if DATABASE_URL is
    # set, otherwise an in-memory fallback so the API still boots locally).
    app.state.document_registry = create_document_registry()
    await app.state.document_registry.initialize()

    # Initialize the chat registry for managing chat sessions & message histories
    app.state.chat_registry = create_chat_registry()
    await app.state.chat_registry.initialize()

    # Platform registries (BE2, plan §6): profiles, chambers/teams, matters,
    # billing/usage meter, and the audit trail. Each is Postgres-backed when
    # DATABASE_URL is set, else an in-memory fallback so the API boots locally.
    app.state.profile_registry = create_profile_registry()
    await app.state.profile_registry.initialize()

    app.state.chambers_registry = create_chambers_registry()
    await app.state.chambers_registry.initialize()

    app.state.matter_registry = create_matter_registry()
    await app.state.matter_registry.initialize()

    app.state.billing_registry = create_billing_registry()
    await app.state.billing_registry.initialize()

    app.state.audit_registry = create_audit_registry()
    await app.state.audit_registry.initialize()

    # Initialize the search-result cache (Redis if REDIS_URL is set,
    # otherwise a no-op cache).
    app.state.search_cache = create_search_cache()

    # Initialize Cloudflare R2 storage for PDF file serving.
    # Falls back to NoopStorageService when credentials are absent.
    app.state.storage = create_storage_service()

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
app.include_router(chat_router)
app.include_router(chats_router)
# Platform routes (BE2, plan §6).
app.include_router(me_router)
app.include_router(privacy_router)
app.include_router(matters_router)
app.include_router(chambers_router)
app.include_router(exports_router)
app.include_router(billing_router)
app.include_router(audit_router)
