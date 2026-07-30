from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import urlparse


class VectorStoreProtocol(Protocol):
    async def initialize(self) -> None: ...

    async def upsert_chunks(self, chunks: list[str], metadata: list[dict[str, Any]]) -> None: ...

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]: ...

    async def delete_document(self, document_id: str) -> None: ...


@dataclass
class VectorStoreService:
    """A lightweight local vector-store shim for Step 3 development."""

    _entries: list[dict[str, Any]] = field(default_factory=list)

    async def initialize(self) -> None:
        self._entries = []

    async def upsert_chunks(self, chunks: list[str], metadata: list[dict[str, Any]]) -> None:
        if len(chunks) != len(metadata):
            raise ValueError("chunks and metadata must be the same length")

        for chunk, item_metadata in zip(chunks, metadata, strict=True):
            self._entries.append({"text": chunk, "metadata": item_metadata, "score": 0.0})

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        query_tokens = set(query.lower().split())
        if not query_tokens:
            return []

        scored_entries = []
        for entry in self._entries:
            entry_tokens = set(entry["text"].lower().split())
            overlap = len(query_tokens & entry_tokens)
            if overlap:
                scored_entries.append({
                    "text": entry["text"],
                    "metadata": entry["metadata"],
                    "score": float(overlap),
                })

        scored_entries.sort(key=lambda item: item["score"], reverse=True)
        return scored_entries[:top_k]

    async def delete_document(self, document_id: str) -> None:
        self._entries = [entry for entry in self._entries if entry["metadata"].get("document_id") != document_id]


def _extract_metadata_value(value: Any) -> Any:
    if value is None:
        return None

    if hasattr(value, "raw_string") and getattr(value, "raw_string") is not None:
        return value.raw_string
    if hasattr(value, "value"):
        inner = getattr(value, "value")
        if isinstance(inner, dict):
            return {k: _extract_metadata_value(v) for k, v in inner.items()}
        return _extract_metadata_value(inner)
    if hasattr(value, "key"):
        return _extract_metadata_value(value.key)
    if hasattr(value, "raw_bytes"):
        return value.raw_bytes
    return value


@dataclass
class AhnlichVectorStoreService:
    """Ahnlich-backed vector store implementation."""

    _endpoint: str | None = None
    _host: str | None = None
    _port: int = 1370
    _api_key: str | None = None
    _store_name: str | None = None
    _fallback: VectorStoreService = field(default_factory=VectorStoreService)
    _last_error: str | None = None

    def __post_init__(self) -> None:
        self._endpoint = self._endpoint or os.getenv("AHNLICH_ENDPOINT")
        self._host = self._host or os.getenv("AHNLICH_HOST") or self._resolved_host_from_endpoint()
        self._port = int(os.getenv("AHNLICH_PORT", str(self._port)))
        self._api_key = self._api_key or os.getenv("AHNLICH_API_KEY")
        self._store_name = self._store_name or os.getenv("AHNLICH_STORE_NAME", "sift_ai_store")

    def _resolved_host_from_endpoint(self) -> str:
        if not self._endpoint:
            return "127.0.0.1"

        parsed = urlparse(self._endpoint)
        if parsed.hostname:
            return parsed.hostname
        return "127.0.0.1"

    def _connection_settings(self) -> tuple[str, int]:
        if self._endpoint:
            parsed = urlparse(self._endpoint)
            if parsed.hostname:
                return parsed.hostname, parsed.port or self._port

        return self._host or "127.0.0.1", self._port

    def _has_connection_target(self) -> bool:
        return bool(self._endpoint or self._host or os.getenv("AHNLICH_HOST"))

    def _set_last_error(self, error: Exception | None) -> None:
        if error is None:
            self._last_error = None
            return
        self._last_error = f"{type(error).__name__}: {error}"

    def _clear_last_error(self) -> None:
        self._last_error = None

    async def initialize(self) -> None:
        if not self._has_connection_target():
            await self._fallback.initialize()
            return

        self._clear_last_error()

        try:
            from grpclib.client import Channel
            from ahnlich_client_py.grpc.services.ai_service import AiServiceStub
            from ahnlich_client_py.grpc.ai import query as ai_query
            from ahnlich_client_py.grpc.ai.models import AiModel
        except ImportError:
            await self._fallback.initialize()
            return

        host, port = self._connection_settings()
        self._clear_last_error()
        try:
            async with Channel(host=host, port=port) as channel:
                client = AiServiceStub(channel)
                response = await client.list_stores(ai_query.ListStores())
                if self._store_name not in {store.name for store in response.stores}:
                    await client.create_store(
                        ai_query.CreateStore(
                            store=self._store_name,
                            index_model=AiModel.ALL_MINI_LM_L6_V2,
                            query_model=AiModel.ALL_MINI_LM_L6_V2,
                            predicates=["document_id", "user_id", "page_number"],
                            error_if_exists=False,
                            store_original=True,
                        )
                    )
        except Exception as exc:
            self._set_last_error(exc)
            await self._fallback.initialize()
            return

    async def upsert_chunks(self, chunks: list[str], metadata: list[dict[str, Any]]) -> None:
        if len(chunks) != len(metadata):
            raise ValueError("chunks and metadata must be the same length")

        if not self._has_connection_target():
            await self._fallback.upsert_chunks(chunks, metadata)
            return

        try:
            from grpclib.client import Channel
            from ahnlich_client_py.grpc.services.ai_service import AiServiceStub
            from ahnlich_client_py.grpc.ai import query as ai_query
            from ahnlich_client_py.grpc.ai.preprocess import PreprocessAction
            from ahnlich_client_py.grpc import keyval, metadata as metadata_module
        except ImportError:
            await self._fallback.upsert_chunks(chunks, metadata)
            return

        host, port = self._connection_settings()
        self._clear_last_error()
        try:
            async with Channel(host=host, port=port) as channel:
                client = AiServiceStub(channel)
                inputs = []
                for chunk_text, item_metadata in zip(chunks, metadata, strict=True):
                    metadata_value = {key: metadata_module.MetadataValue(raw_string=str(value)) for key, value in item_metadata.items()}
                    inputs.append(
                        keyval.AiStoreEntry(
                            key=keyval.StoreInput(raw_string=chunk_text),
                            value=keyval.StoreValue(value=metadata_value),
                        )
                    )
                await client.set(
                    ai_query.Set(
                        store=self._store_name,
                        inputs=inputs,
                        preprocess_action=PreprocessAction.NoPreprocessing,
                    )
                )
        except Exception as exc:
            self._set_last_error(exc)
            await self._fallback.upsert_chunks(chunks, metadata)
            return

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not self._has_connection_target():
            return await self._fallback.search(query=query, top_k=top_k)

        try:
            from grpclib.client import Channel
            from ahnlich_client_py.grpc.services.ai_service import AiServiceStub
            from ahnlich_client_py.grpc.ai import query as ai_query
            from ahnlich_client_py.grpc.ai.preprocess import PreprocessAction
            from ahnlich_client_py.grpc.algorithm.algorithms import Algorithm
            from ahnlich_client_py.grpc import keyval
        except ImportError:
            return await self._fallback.search(query=query, top_k=top_k)

        host, port = self._connection_settings()
        self._clear_last_error()
        try:
            async with Channel(host=host, port=port) as channel:
                client = AiServiceStub(channel)
                response = await client.get_sim_n(
                    ai_query.GetSimN(
                        store=self._store_name,
                        search_input=keyval.StoreInput(raw_string=query),
                        closest_n=top_k,
                        algorithm=Algorithm.CosineSimilarity,
                        preprocess_action=PreprocessAction.NoPreprocessing,
                    )
                )
        except Exception as exc:
            self._set_last_error(exc)
            return await self._fallback.search(query=query, top_k=top_k)

        results = []
        for entry in response.entries:
            metadata_value = _extract_metadata_value(entry.value)
            results.append({
                "text": entry.key.raw_string if hasattr(entry.key, "raw_string") else str(entry.key),
                "metadata": metadata_value if isinstance(metadata_value, dict) else {},
                "score": float(entry.score) if hasattr(entry, "score") else 0.0,
            })

        return results

    async def delete_document(self, document_id: str) -> None:
        if not self._has_connection_target():
            await self._fallback.delete_document(document_id)
            return

        try:
            from grpclib.client import Channel
            from ahnlich_client_py.grpc.services.ai_service import AiServiceStub
            from ahnlich_client_py.grpc.ai import query as ai_query
            from ahnlich_client_py.grpc import predicates, metadata as metadata_module
        except ImportError:
            await self._fallback.delete_document(document_id)
            return

        condition = predicates.PredicateCondition(
            value=predicates.Predicate(
                equals=predicates.Equals(
                    key="document_id",
                    value=metadata_module.MetadataValue(raw_string=document_id),
                )
            )
        )

        host, port = self._connection_settings()
        try:
            async with Channel(host=host, port=port) as channel:
                client = AiServiceStub(channel)
                response = await client.get_pred(
                    ai_query.GetPred(
                        store=self._store_name,
                        condition=condition,
                    )
                )
                for entry in response.entries:
                    await client.del_key(ai_query.DelKey(store=self._store_name, keys=[entry.key]))
        except Exception:
            await self._fallback.delete_document(document_id)
            return


def create_vector_store_service() -> VectorStoreProtocol:
    use_ahnlich = os.getenv("USE_AHNLICH", "true").lower() in {"1", "true", "yes", "on"}
    if use_ahnlich:
        return AhnlichVectorStoreService()
    return VectorStoreService()
