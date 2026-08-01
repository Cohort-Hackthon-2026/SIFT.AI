from io import BytesIO

import fitz

from app.api.routes.documents import PageExtraction, _chunk_pages


def _make_pdf_bytes(text: str) -> bytes:
    pdf_bytes = BytesIO()
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(pdf_bytes, garbage=4, deflate=True)
    document.close()
    pdf_bytes.seek(0)
    return pdf_bytes.getvalue()


def test_upload_endpoint_extracts_text_and_metadata(client) -> None:
    response = client.post(
        "/api/v1/documents/upload",
        data={"source_type": "pdf"},
        files={"file": ("sample.pdf", _make_pdf_bytes("Hello world"), "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_name"] == "sample.pdf"
    assert payload["user_id"].startswith("anonymous-")
    assert payload["pages"][0]["page_number"] == 1
    assert "Hello world" in payload["pages"][0]["text"]
    assert payload["pages"][0]["paragraph_index"] == 1
    assert payload["chunks"][0]["metadata"]["document_id"] == payload["document_id"]
    assert payload["chunks"][0]["metadata"]["user_id"] == payload["user_id"]
    assert payload["chunks"][0]["page_number"] == 1


def test_upload_rejects_file_over_size_limit(client, monkeypatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_SIZE_BYTES", "10")

    response = client.post(
        "/api/v1/documents/upload",
        data={"source_type": "pdf"},
        files={"file": ("sample.pdf", _make_pdf_bytes("Hello world"), "application/pdf")},
    )

    assert response.status_code == 413


def test_upload_warns_when_pdf_has_no_extractable_text(client) -> None:
    blank_pdf = BytesIO()
    document = fitz.open()
    document.new_page()  # a real page with no text layer (e.g. scanned image)
    document.save(blank_pdf)
    document.close()
    blank_pdf.seek(0)

    response = client.post(
        "/api/v1/documents/upload",
        data={"source_type": "pdf"},
        files={"file": ("scanned.pdf", blank_pdf.getvalue(), "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["chunks"] == []
    assert payload["warnings"]
    assert "No extractable text" in payload["warnings"][0]


def test_chunk_pages_splits_long_text_into_multiple_chunks() -> None:
    long_text = " ".join([f"sentence-{index}" for index in range(700)])
    pages = [PageExtraction(page_number=1, text=long_text, bounding_boxes=[], paragraph_index=1)]

    chunks = _chunk_pages(pages, document_id="doc-123", user_id="user-123")

    assert len(chunks) > 1
    assert all(chunk.metadata.document_id == "doc-123" for chunk in chunks)
    assert all(chunk.metadata.user_id == "user-123" for chunk in chunks)
    assert all(chunk.page_number == 1 for chunk in chunks)
    assert all(chunk.text.strip() for chunk in chunks)


def test_chunk_pages_skips_empty_pages() -> None:
    pages = [
        PageExtraction(page_number=1, text="", bounding_boxes=[], paragraph_index=1),
        PageExtraction(page_number=2, text="Meaningful content", bounding_boxes=[], paragraph_index=1),
    ]

    chunks = _chunk_pages(pages, document_id="doc-456", user_id="user-456")

    assert len(chunks) == 1
    assert chunks[0].page_number == 2
    assert chunks[0].metadata.document_id == "doc-456"
    assert chunks[0].metadata.user_id == "user-456"
