from io import BytesIO

import fitz
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_upload_endpoint_extracts_text_and_metadata() -> None:
    pdf_bytes = BytesIO()
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Hello world")
    document.save(pdf_bytes, garbage=4, deflate=True)
    document.close()
    pdf_bytes.seek(0)

    response = client.post(
        "/api/v1/documents/upload",
        data={"source_type": "pdf"},
        files={"file": ("sample.pdf", pdf_bytes.getvalue(), "application/pdf")},
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
