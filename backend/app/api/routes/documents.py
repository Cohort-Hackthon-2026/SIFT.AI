from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import fitz
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

from app.auth import get_current_user_id
from app.rate_limit import rate_limited_user_id

router = APIRouter(prefix="/api/v1")

# Defense-in-depth: the frontend's react-dropzone config caps uploads at
# 20MB client-side, but that's trivially bypassed (curl, a modified client,
# etc.), so it also has to be enforced here. Read lazily (not at import
# time) so it stays configurable/testable at runtime.
DEFAULT_MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024


def _max_upload_size_bytes() -> int:
    return int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(DEFAULT_MAX_UPLOAD_SIZE_BYTES)))


class DocumentUploadRequest(BaseModel):
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
    # JSON-serialised list of {x0, y0, x1, y1} dicts from the source page.
    # Stored as a string because Ahnlich MetadataValue only supports raw_string.
    bounding_boxes: str = "[]"
    # Source type: "pdf", "image", or "chat_text" — used by the FE to decide
    # whether to render a PDF viewer link or a plain-text citation.
    source: str = "pdf"


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
    file_url: str | None = None
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
    file_url: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]


class DocumentDeleteResponse(BaseModel):
    document_id: str
    deleted: bool


class StrictSearchRequest(BaseModel):
    query: str = Field(default="")
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


def _chunk_pages(
    pages: list[PageExtraction],
    document_id: str,
    user_id: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[TextChunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks: list[TextChunk] = []

    for page in pages:
        if not page.text.strip():
            continue
        splits = splitter.split_text(page.text)
        for split in splits:
            chunk_id = str(uuid4())
            # Serialise the page's bounding boxes into the chunk metadata so
            # the citation SSE payload can pass them to the FE highlight viewer.
            bb_json = json.dumps(
                [bb.model_dump() for bb in page.bounding_boxes]
            ) if page.bounding_boxes else "[]"
            chunks.append(
                TextChunk(
                    chunk_id=chunk_id,
                    text=split,
                    page_number=page.page_number,
                    metadata=ChunkMetadata(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        page_number=page.page_number,
                        user_id=user_id,
                        bounding_boxes=bb_json,
                        source="pdf",
                    ),
                )
            )

    return chunks

# Accepted file types: PDFs and common image formats.
ACCEPTED_PDF_TYPES = {"application/pdf", "application/octet-stream"}
ACCEPTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/tiff"}
ACCEPTED_FILE_TYPES = ACCEPTED_PDF_TYPES | ACCEPTED_IMAGE_TYPES


def _is_image_file(content_type: str | None, filename: str | None) -> bool:
    """Check if the uploaded file is an image based on MIME type or extension."""
    if content_type and content_type in ACCEPTED_IMAGE_TYPES:
        return True
    if filename:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return ext in {"png", "jpg", "jpeg", "webp", "tiff", "tif"}
    return False


def _is_pdf_file(content_type: str | None, filename: str | None) -> bool:
    """Check if the uploaded file is a PDF based on MIME type or extension."""
    if content_type and content_type in ACCEPTED_PDF_TYPES:
        return True
    if filename:
        return filename.lower().endswith(".pdf")
    return False


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    source_type: str = Form(default="auto"),
    document_name: str | None = Form(default=None),
    current_user_id: str = Depends(rate_limited_user_id),
) -> DocumentUploadResponse:
    resolved_document_name = document_name or file.filename or "uploaded-document"

    # Determine file type from MIME type and extension.
    is_image = _is_image_file(file.content_type, file.filename)
    is_pdf = _is_pdf_file(file.content_type, file.filename)

    if not is_image and not is_pdf:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Accepted formats: PDF, PNG, JPEG, WebP, TIFF.",
        )

    # Auto-detect source_type if the client didn't specify.
    resolved_source_type = source_type
    if source_type == "auto":
        resolved_source_type = "image" if is_image else "pdf"

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if len(file_bytes) > _max_upload_size_bytes():
        max_mb = _max_upload_size_bytes() / (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"File exceeds the {max_mb:.0f}MB upload limit")

    warnings: list[str] = []
    document_id = str(uuid4())

    if is_image:
        # Image upload: extract text via Gemini Vision, then chunk.
        from app.services.image_extraction import ImageExtractionService

        extractor = ImageExtractionService()
        extracted_text = await extractor.extract_text(
            file_bytes, content_type=file.content_type or "image/jpeg"
        )

        if not extracted_text.strip():
            warnings.append(
                "No text could be extracted from this image. "
                "The image was saved, but won't appear in search results."
            )

        pages = [
            PageExtraction(
                page_number=1,
                text=extracted_text,
                bounding_boxes=[],
                paragraph_index=1,
            )
        ]
        chunks = _chunk_pages(pages, document_id=document_id, user_id=current_user_id)
        # Override the source type on chunk metadata for image-sourced chunks.
        for chunk in chunks:
            chunk.metadata.source = "image"
    else:
        # PDF upload: existing extraction pipeline.
        try:
            def _process() -> tuple[list[PageExtraction], list[TextChunk]]:
                extracted_pages = _extract_pdf_pages(file_bytes)
                extracted_chunks = _chunk_pages(
                    extracted_pages, document_id=document_id, user_id=current_user_id
                )
                return extracted_pages, extracted_chunks

            pages, chunks = await asyncio.to_thread(_process)
        except Exception as exc:  # pragma: no cover - defensive path
            raise HTTPException(status_code=400, detail=f"Unable to process PDF: {exc}") from exc

        if pages and not chunks:
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

    file_url = f"/api/v1/documents/{document_id}/file"

    document_registry = request.app.state.document_registry
    await document_registry.initialize()
    await document_registry.create_document(
        {
            "document_id": document_id,
            "user_id": current_user_id,
            "document_name": resolved_document_name,
            "source_type": resolved_source_type,
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "file_size_bytes": len(file_bytes),
            "uploaded_at": datetime.now(timezone.utc),
            "file_url": file_url,
        }
    )

    storage = getattr(request.app.state, "storage", None)
    if storage is not None:
        await storage.upload_pdf(document_id, file_bytes)

    return DocumentUploadResponse(
        document_id=document_id,
        user_id=current_user_id,
        document_name=resolved_document_name,
        source_type=resolved_source_type,
        file_url=file_url,
        pages=pages,
        chunks=chunks,
        warnings=warnings,
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(request: Request, current_user_id: str = Depends(get_current_user_id)) -> DocumentListResponse:
    document_registry = request.app.state.document_registry
    await document_registry.initialize()
    documents = await document_registry.list_documents(user_id=current_user_id)
    return DocumentListResponse(
        documents=[
            DocumentSummary(
                document_id=doc["document_id"],
                user_id=doc["user_id"],
                document_name=doc["document_name"],
                source_type=doc.get("source_type", "pdf"),
                page_count=doc.get("page_count", 0),
                chunk_count=doc.get("chunk_count", 0),
                file_size_bytes=doc.get("file_size_bytes", 0),
                uploaded_at=doc["uploaded_at"],
                file_url=doc.get("file_url") or f"/api/v1/documents/{doc['document_id']}/file",
            )
            for doc in documents
        ]
    )


@router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    request: Request,
    document_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> DocumentDeleteResponse:
    document_registry = request.app.state.document_registry
    await document_registry.initialize()

    existing = await document_registry.get_document(document_id)
    # Same 404 whether the document doesn't exist at all or belongs to
    # someone else - a distinct "403 forbidden" would confirm to an
    # attacker that a given document_id exists, just not theirs.
    if existing is None or existing.get("user_id") != current_user_id:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' was not found")

    vector_store = request.app.state.vector_store
    await vector_store.delete_document(document_id)
    deleted = await document_registry.delete_document(document_id)

    # Also remove the raw PDF from R2 (best-effort; failure is non-fatal).
    storage = getattr(request.app.state, "storage", None)
    if storage is not None:
        await storage.delete_pdf(document_id)

    return DocumentDeleteResponse(document_id=document_id, deleted=deleted)


@router.get("/documents/{document_id}/file")
async def get_document_file(
    request: Request,
    document_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> Response:
    """Stream the raw PDF binary for a document from Cloudflare R2.

    The frontend PDF viewer calls this endpoint (with the Clerk bearer token)
    to render the document and deep-link to cited pages.
    Returns 404 if the document does not belong to the caller or the PDF is
    not yet stored in R2 (e.g. uploaded before R2 was configured).
    """
    document_registry = request.app.state.document_registry
    existing = await document_registry.get_document(document_id)
    # Same deliberate 404/403 conflation as DELETE - never confirm existence
    # of another user's document to a potential attacker.
    if existing is None or existing.get("user_id") != current_user_id:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' was not found")

    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        raise HTTPException(status_code=503, detail="File storage service is unavailable")

    pdf_bytes = await storage.get_pdf_bytes(document_id)
    if pdf_bytes is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "PDF file not found in storage. "
                "The document may have been uploaded before file storage was configured."
            ),
        )

    # Serve inline so the PDF viewer can render it directly in the browser.
    doc_name = existing.get("document_name", f"{document_id}.pdf")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{doc_name}"'},
    )

@router.post("/search/strict", response_model=StrictSearchResponse)
async def strict_search(
    request: Request,
    payload: StrictSearchRequest,
    current_user_id: str = Depends(rate_limited_user_id),
) -> StrictSearchResponse:
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    search_cache = request.app.state.search_cache
    cache_key = None
    if hasattr(search_cache, "get"):
        from app.services.cache import build_cache_key

        cache_key = build_cache_key(payload.query, current_user_id, payload.document_id, payload.top_k)
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
    # predicates (user_id, specific document_id)". user_id always comes from
    # the verified token now, never from the request body - a signed-in user
    # can only ever search their own documents.
    predicates: dict[str, str] = {"user_id": current_user_id}
    if payload.document_id:
        predicates["document_id"] = payload.document_id

    vector_store = request.app.state.vector_store
    results = await vector_store.search(payload.query, top_k=payload.top_k, predicates=predicates)

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
