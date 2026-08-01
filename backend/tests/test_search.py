from io import BytesIO

import fitz


def _make_pdf_bytes(text: str) -> bytes:
    pdf_bytes = BytesIO()
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(pdf_bytes, garbage=4, deflate=True)
    document.close()
    pdf_bytes.seek(0)
    return pdf_bytes.getvalue()


def test_strict_search_returns_matching_chunks_for_document(client) -> None:
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
    # page_number must round-trip as an int, not a string
    assert isinstance(payload["results"][0]["metadata"]["page_number"], int)


def test_strict_search_predicate_excludes_other_documents(client) -> None:
    client.post(
        "/api/v1/documents/upload",
        data={"user_id": "user-A", "document_name": "doc-a.pdf"},
        files={"file": ("doc-a.pdf", _make_pdf_bytes("unique zebra content"), "application/pdf")},
    )
    upload_b = client.post(
        "/api/v1/documents/upload",
        data={"user_id": "user-A", "document_name": "doc-b.pdf"},
        files={"file": ("doc-b.pdf", _make_pdf_bytes("unique zebra content"), "application/pdf")},
    )
    document_b_id = upload_b.json()["document_id"]

    search_response = client.post(
        "/api/v1/search/strict",
        json={"query": "zebra", "user_id": "user-A", "document_id": document_b_id, "top_k": 5},
    )

    payload = search_response.json()
    assert payload["results"]
    assert all(result["metadata"]["document_id"] == document_b_id for result in payload["results"])


def test_strict_search_rejects_empty_query(client) -> None:
    response = client.post("/api/v1/search/strict", json={"query": "   "})
    assert response.status_code == 400
