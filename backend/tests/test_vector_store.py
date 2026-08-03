import pytest

from app.services.vector_store import (
    AhnlichVectorStoreService,
    VectorStoreService,
    _to_ahnlich_metadata_value,
)


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
async def test_vector_store_search_applies_predicate_filter() -> None:
    store = VectorStoreService()
    await store.initialize()

    await store.upsert_chunks(
        chunks=["shared keyword one", "shared keyword two"],
        metadata=[
            {"document_id": "doc-1", "page_number": 1, "user_id": "user-1"},
            {"document_id": "doc-2", "page_number": 1, "user_id": "user-1"},
        ],
    )

    results = await store.search("shared keyword", top_k=5, predicates={"document_id": "doc-2"})

    assert results
    assert all(item["metadata"]["document_id"] == "doc-2" for item in results)


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


def test_to_ahnlich_metadata_value_handles_non_string_types_without_raising() -> None:
    """Regression test.

    ahnlich_client_py's MetadataValue protobuf message only defines
    raw_string/image/audio fields - passing raw_integer=... (as the old
    implementation did for page_number) raises TypeError, which the
    surrounding try/except silently swallowed and caused every upload to
    fall back to the in-memory store instead of reaching Ahnlich.
    """
    from ahnlich_client_py.grpc import metadata as metadata_module

    int_value = _to_ahnlich_metadata_value(3, metadata_module)
    assert int_value.raw_string == "3"

    bool_value = _to_ahnlich_metadata_value(True, metadata_module)
    assert bool_value.raw_string == "true"

    float_value = _to_ahnlich_metadata_value(1.5, metadata_module)
    assert float_value.raw_string == "1.5"

    str_value = _to_ahnlich_metadata_value("already-a-string", metadata_module)
    assert str_value.raw_string == "already-a-string"
