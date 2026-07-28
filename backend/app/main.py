from fastapi import FastAPI

from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.services.vector_store import create_vector_store_service


app = FastAPI(title="SIFT.AI API", version="0.1.0")
app.state.vector_store = create_vector_store_service()

app.include_router(health_router)
app.include_router(documents_router)