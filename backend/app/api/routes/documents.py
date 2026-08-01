from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import fitz
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1")

# Defense-in-depth: the frontend's react-dropzone config caps uploads at
# 20MB client-side, but that's trivially bypassed (curl, a modified client,
# etc.), so it also has to be enforced here. Read lazily (not at import
# time) so it stays configurable/testable at runtime.
DEFAULT_MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024


def _max_upload_size_bytes() -> int:
    return int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(DEFAULT_MAX_UPLOAD_SIZE_BYTES)))


class DocumentUploadRequest(BaseModel):
    user_id: str | None = Field(default=None)
    document_name: str | None = Field(default=None)
    source_type: str = Field(default="pdf")


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class PageExtraction(BaseModel):
    page_number: int
    text: str
    bounding_boxes: list[BoundingBox]
    paragraph_index: int


class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    page_number: int
    user_id: str


class TextChunk(BaseModel):
    chunk_id: str
    text: str
    page_number: int
    metadata: ChunkMetadata


class DocumentUploadResponse(BaseModel):
    document_id: str
    user_id: str
    document_name: str
    source_type: str
    pages: list[PageExtraction]
    chunks: list[TextChunk]
    warnings: list[str] = Field(default_factory=list)


class DocumentSummary(BaseModel):
    document_id: str
    user_id: str
    document_name: str
    source_type: str
    page_count: int
    chunk_count: int
    file_size_bytes: int
    uploaded_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]


class DocumentDeleteResponse(BaseModel):
    document_id: str
    deleted: bool


class StrictSearchRequest(BaseModel):
    query: str = Field(default="")
    user_id: str | None = Field(default=None)
    document_id: str | None = Field(default=None)
    top_k: int = Field(default=5, ge=1, le=20)


class StrictSearchResult(BaseModel):
    text: str
    score: float
    metadata: ChunkMetadata


class StrictSearchResponse(BaseModel):
    results: list[StrictSearchResult]
    provider: str = "fallback"
    used_fallback: bool = True
    cached: bool = False
    last_error: str | None = None


def _extract_pdf_pages(file_bytes: bytes) -> list[PageExtraction]:
    document = fitz.open(stream=file_bytes, filetype="pdf")
    pages: list[PageExtraction] = []

    for page_number, page in enumerate(document, start=1):
        raw_text = page.get_text("text").strip()
        blocks = [block for block in page.get_text("blocks") if block[4].strip()]
        bounding_boxes = [
            BoundingBox(x0=round(block[0], 2), y0=round(block[1], 2), x1=round(block[2], 2), y1=round(block[3], 2))
            for block in blocks
        ]
        paragraph_index = len(bounding_boxes) or 1

        pages.append(
            PageExtraction(
                page_number=page_number,
                text=raw_text,
                bounding_boxes=bounding_boxes,
                paragraph_index=paragraph_index,
            )
        )

    document.close()
    return pages


def _chunk_pages(pages: list[PageExtraction], document_id: str, user_id: str) -> list[TextChunk]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100, separators=["\n\n", "\n", " "])
    chunks: list[TextChunk] = []

    for page in pages:
        if not page.text.strip():
            continue

        split_texts = splitter.split_text(page.text)
        for index, chunk_text in enumerate(split_texts, start=1):
            chunk_id = f"{document_id}-p{page.page_number}-c{index}"
            chunks.append(
                TextChunk(
                    chunk_id=chunk_id,
                    text=chunk_text.strip(),
                    page_number=page.page_number,
                    metadata=ChunkMetadata(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        page_number=page.page_number,
                        user_id=user_id,
                    ),
                )
            )

    return chunks


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user_id: str | None = Form(default=None),
    document_name: str | None = Form(default=None),
    source_type: str = Form(default="pdf"),
) -> DocumentUploadResponse:
    payload = DocumentUploadRequest(
        user_id=user_id,
        document_name=document_name,
        source_type=source_type,
    )

    resolved_user_id = payload.user_id or f"anonymous-{uuid4().hex[:8]}"
    resolved_document_name = payload.document_name or file.filename or "uploaded-document.pdf"

    if not resolved_document_name.lower().endswith(".pdf") and file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if len(file_bytes) > _max_upload_size_bytes():
        max_mb = _max_upload_size_bytes() / (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"File exceeds the {max_mb:.0f}MB upload limit")

    try:
        pages = _extract_pdf_pages(file_bytes)
    except Exception as exc:  # pragma: no cover - defensive path
        raise HTTPException(status_code=400, detail=f"Unable to process PDF: {exc}") from exc

    document_id = str(uuid4())
    chunks = _chunk_pages(pages, document_id=document_id, user_id=resolved_user_id)

    warnings: list[str] = []
    if pages and not chunks:
        # Common with scanned/image-only PDFs: PyMuPDF finds pages but no
        # extractable text layer, so there is nothing to embed or search.
        # We still register the document (the user uploaded something real)
        # but the frontend should surface this rather than silently showing
        # "Ready" for a document that will never appear in search results.
        warnings.append(
            "No extractable text was found in this PDF (it may be a scanned image). "
            "It was saved, but won't appear in search results until OCR support is added."
        )

    vector_store = request.app.state.vector_store
    await vector_store.initialize()
    await vector_store.upsert_chunks(
        chunks=[chunk.text for chunk in chunks],
        metadata=[chunk.metadata.model_dump() for chunk in chunks],
    )

    document_registry = request.app.state.document_registry
    await document_registry.initialize()
    await document_registry.create_document(
        {
            "document_id": document_id,
            "user_id": resolved_user_id,
            "document_name": resolved_document_name,
            "source_type": payload.source_type,
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "file_size_bytes": len(file_bytes),
            "uploaded_at": datetime.now(timezone.utc),
        }
    )

    return DocumentUploadResponse(
        document_id=document_id,
        user_id=resolved_user_id,
        document_name=resolved_document_name,
        source_type=payload.source_type,
        pages=pages,
        chunks=chunks,
        warnings=warnings,
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(request: Request, user_id: str | None = Query(default=None)) -> DocumentListResponse:
    document_registry = request.app.state.document_registry
    await document_registry.initialize()
    documents = await document_registry.list_documents(user_id=user_id)
    return DocumentListResponse(documents=[DocumentSummary(**doc) for doc in documents])


@router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(request: Request, document_id: str) -> DocumentDeleteResponse:
    document_registry = request.app.state.document_registry
    await document_registry.initialize()

    existing = await document_registry.get_document(document_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' was not found")

    vector_store = request.app.state.vector_store
    await vector_store.delete_document(document_id)
    deleted = await document_registry.delete_document(document_id)

    return DocumentDeleteResponse(document_id=document_id, deleted=deleted)


@router.post("/search/strict", response_model=StrictSearchResponse)
async def strict_search(request: Request, payload: StrictSearchRequest) -> StrictSearchResponse:
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    search_cache = request.app.state.search_cache
    cache_key = None
    if hasattr(search_cache, "get"):
        from app.services.cache import build_cache_key

        cache_key = build_cache_key(payload.query, payload.user_id, payload.document_id, payload.top_k)
        cached_results = await search_cache.get(cache_key)
        if cached_results is not None:
            return StrictSearchResponse(
                results=[StrictSearchResult(**item) for item in cached_results],
                provider="cache",
                used_fallback=False,
                cached=True,
            )

    # Filter at the Ahnlich query level via metadata predicates, rather than
    # fetching top_k globally and discarding non-matching rows in Python -
    # the build plan calls for "Queries Ahnlich Vector DB using metadata
    # predicates (user_id, specific document_id)".
    predicates: dict[str, str] = {}
    if payload.user_id:
        predicates["user_id"] = payload.user_id
    if payload.document_id:
        predicates["document_id"] = payload.document_id

    vector_store = request.app.state.vector_store
    results = await vector_store.search(payload.query, top_k=payload.top_k, predicates=predicates or None)

    provider = "fallback"
    used_fallback = True
    last_error = None
    if hasattr(vector_store, "_has_connection_target") and vector_store._has_connection_target():
        provider = "ahnlich"
        used_fallback = False
    if hasattr(vector_store, "_last_error"):
        last_error = vector_store._last_error
        if last_error:
            used_fallback = True
            provider = "fallback"

    search_results = [
        StrictSearchResult(
            text=result["text"],
            score=result["score"],
            metadata=ChunkMetadata(**result["metadata"]),
        )
        for result in results
    ]

    if cache_key is not None and not used_fallback:
        await search_cache.set(cache_key, [result.model_dump() for result in search_results])

    return StrictSearchResponse(
        results=search_results,
        provider=provider,
        used_fallback=used_fallback,
        cached=False,
        last_error=last_error,
    )
