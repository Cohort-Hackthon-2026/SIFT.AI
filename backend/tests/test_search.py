from io import BytesIO

import fitz
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _make_pdf_bytes(text: str) -> bytes:
    pdf_bytes = BytesIO()
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(pdf_bytes, garbage=4, deflate=True)
    document.close()
    pdf_bytes.seek(0)
    return pdf_bytes.getvalue()


def test_strict_search_returns_matching_chunks_for_document() -> None:
    upload_response = client.post(
        "/api/v1/documents/upload",
        data={"user_id": "user-123", "document_name": "sample.pdf", "source_type": "pdf"},
        files={"file": ("sample.pdf", _make_pdf_bytes("Alpha beta gamma"), "application/pdf")},
    )

    assert upload_response.status_code == 200
    document_id = upload_response.json()["document_id"]

    search_response = client.post(
        "/api/v1/search/strict",
        json={"query": "Alpha gamma", "user_id": "user-123", "document_id": document_id, "top_k": 3},
    )

    assert search_response.status_code == 200
    payload = search_response.json()
    assert payload["results"]
    assert payload["results"][0]["metadata"]["document_id"] == document_id
    assert payload["results"][0]["metadata"]["user_id"] == "user-123"
