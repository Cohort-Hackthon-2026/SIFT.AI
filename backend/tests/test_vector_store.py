import pytest

from app.services.vector_store import AhnlichVectorStoreService, VectorStoreService


@pytest.mark.asyncio
async def test_vector_store_search_returns_relevant_chunks() -> None:
    store = VectorStoreService()
    await store.initialize()

    await store.upsert_chunks(
        chunks=["alpha beta gamma", "delta epsilon zeta"],
        metadata=[
            {"document_id": "doc-1", "page_number": 1, "user_id": "user-1"},
            {"document_id": "doc-2", "page_number": 2, "user_id": "user-1"},
        ],
    )

    results = await store.search("alpha gamma", top_k=3)

    assert results
    assert results[0]["metadata"]["document_id"] == "doc-1"
    assert results[0]["score"] >= 0.0


@pytest.mark.asyncio
async def test_vector_store_delete_document_removes_matching_entries() -> None:
    store = VectorStoreService()
    await store.initialize()

    await store.upsert_chunks(
        chunks=["hello world", "goodbye moon"],
        metadata=[
            {"document_id": "doc-3", "page_number": 1, "user_id": "user-2"},
            {"document_id": "doc-4", "page_number": 1, "user_id": "user-2"},
        ],
    )

    await store.delete_document("doc-3")
    results = await store.search("hello", top_k=5)

    assert all(item["metadata"]["document_id"] != "doc-3" for item in results)


def test_ahnlich_service_reads_host_and_port_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AHNLICH_HOST", "ahnlich")
    monkeypatch.setenv("AHNLICH_PORT", "1370")

    service = AhnlichVectorStoreService()

    assert service._host == "ahnlich"
    assert service._port == 1370
