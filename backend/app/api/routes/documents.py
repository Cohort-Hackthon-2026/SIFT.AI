from uuid import uuid4

import fitz
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1")


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

    try:
        pages = _extract_pdf_pages(file_bytes)
    except Exception as exc:  # pragma: no cover - defensive path
        raise HTTPException(status_code=400, detail=f"Unable to process PDF: {exc}") from exc

    document_id = str(uuid4())
    chunks = _chunk_pages(pages, document_id=document_id, user_id=resolved_user_id)

    return DocumentUploadResponse(
        document_id=document_id,
        user_id=resolved_user_id,
        document_name=resolved_document_name,
        source_type=payload.source_type,
        pages=pages,
        chunks=chunks,
    )
