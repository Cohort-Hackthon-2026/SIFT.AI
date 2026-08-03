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
        data={"document_name": "sample.pdf", "source_type": "pdf"},
        files={"file": ("sample.pdf", _make_pdf_bytes("Alpha beta gamma"), "application/pdf")},
    )

    assert upload_response.status_code == 200
    document_id = upload_response.json()["document_id"]

    search_response = client.post(
        "/api/v1/search/strict",
        json={"query": "Alpha gamma", "document_id": document_id, "top_k": 3},
    )

    assert search_response.status_code == 200
    payload = search_response.json()
    assert payload["results"]
    assert payload["results"][0]["metadata"]["document_id"] == document_id
    assert payload["results"][0]["metadata"]["user_id"] == "test-user-1"
    # page_number must round-trip as an int, not a string
    assert isinstance(payload["results"][0]["metadata"]["page_number"], int)


def test_strict_search_predicate_excludes_other_documents(client) -> None:
    client.post(
        "/api/v1/documents/upload",
        data={"document_name": "doc-a.pdf"},
        files={"file": ("doc-a.pdf", _make_pdf_bytes("unique zebra content"), "application/pdf")},
    )
    upload_b = client.post(
        "/api/v1/documents/upload",
        data={"document_name": "doc-b.pdf"},
        files={"file": ("doc-b.pdf", _make_pdf_bytes("unique zebra content"), "application/pdf")},
    )
    document_b_id = upload_b.json()["document_id"]

    search_response = client.post(
        "/api/v1/search/strict",
        json={"query": "zebra", "document_id": document_b_id, "top_k": 5},
    )

    payload = search_response.json()
    assert payload["results"]
    assert all(result["metadata"]["document_id"] == document_b_id for result in payload["results"])


def test_strict_search_rejects_empty_query(client) -> None:
    response = client.post("/api/v1/search/strict", json={"query": "   "})
    assert response.status_code == 400


def test_strict_search_only_returns_the_authenticated_users_own_documents(client, as_user) -> None:
    as_user("user-A")
    client.post(
        "/api/v1/documents/upload",
        data={"document_name": "user-a-doc.pdf"},
        files={"file": ("a.pdf", _make_pdf_bytes("confidential merger agreement details"), "application/pdf")},
    )

    as_user("user-B")
    search_response = client.post(
        "/api/v1/search/strict",
        json={"query": "confidential merger agreement", "top_k": 5},
    )

    # user-B's query matches the text closely, but the chunk belongs to
    # user-A - it must never surface for a different authenticated user,
    # even without a document_id filter narrowing the search.
    assert search_response.json()["results"] == []
