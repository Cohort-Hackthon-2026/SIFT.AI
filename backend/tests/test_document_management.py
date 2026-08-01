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


def test_list_documents_returns_uploaded_document(client) -> None:
    upload_response = client.post(
        "/api/v1/documents/upload",
        data={"user_id": "user-list", "document_name": "list-me.pdf"},
        files={"file": ("list-me.pdf", _make_pdf_bytes("some content"), "application/pdf")},
    )
    document_id = upload_response.json()["document_id"]

    list_response = client.get("/api/v1/documents", params={"user_id": "user-list"})

    assert list_response.status_code == 200
    documents = list_response.json()["documents"]
    assert any(doc["document_id"] == document_id for doc in documents)
    match = next(doc for doc in documents if doc["document_id"] == document_id)
    assert match["document_name"] == "list-me.pdf"
    assert match["page_count"] == 1
    assert match["chunk_count"] >= 1
    assert match["file_size_bytes"] > 0


def test_list_documents_filters_by_user(client) -> None:
    client.post(
        "/api/v1/documents/upload",
        data={"user_id": "user-one"},
        files={"file": ("a.pdf", _make_pdf_bytes("content a"), "application/pdf")},
    )
    client.post(
        "/api/v1/documents/upload",
        data={"user_id": "user-two"},
        files={"file": ("b.pdf", _make_pdf_bytes("content b"), "application/pdf")},
    )

    response = client.get("/api/v1/documents", params={"user_id": "user-one"})
    documents = response.json()["documents"]

    assert all(doc["user_id"] == "user-one" for doc in documents)


def test_delete_document_removes_it_from_listing_and_search(client) -> None:
    upload_response = client.post(
        "/api/v1/documents/upload",
        data={"user_id": "user-del", "document_name": "delete-me.pdf"},
        files={"file": ("delete-me.pdf", _make_pdf_bytes("removable content"), "application/pdf")},
    )
    document_id = upload_response.json()["document_id"]

    delete_response = client.delete(f"/api/v1/documents/{document_id}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"document_id": document_id, "deleted": True}

    list_response = client.get("/api/v1/documents", params={"user_id": "user-del"})
    assert all(doc["document_id"] != document_id for doc in list_response.json()["documents"])

    search_response = client.post(
        "/api/v1/search/strict",
        json={"query": "removable", "document_id": document_id, "top_k": 5},
    )
    assert search_response.json()["results"] == []


def test_delete_unknown_document_returns_404(client) -> None:
    response = client.delete("/api/v1/documents/does-not-exist")
    assert response.status_code == 404
