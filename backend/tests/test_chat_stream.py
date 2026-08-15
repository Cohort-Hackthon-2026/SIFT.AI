"""Tests for POST /api/v1/chat/stream (SSE chat endpoint)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Basic validation / auth
# ---------------------------------------------------------------------------

def test_chat_stream_rejects_empty_query(client) -> None:
    """400 Bad Request when query string is whitespace-only."""
    response = client.post(
        "/api/v1/chat/stream",
        json={"query": "   ", "mode": "STRICT"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Query string cannot be empty."


def test_chat_stream_rejects_missing_query(client) -> None:
    """400 Bad Request when query key is absent (Pydantic default is '')."""
    response = client.post(
        "/api/v1/chat/stream",
        json={"query": "", "mode": "STRICT"},
    )
    assert response.status_code == 400


def test_chat_stream_unauthorized_without_token(raw_client) -> None:
    """401 Unauthorized when no bearer token is sent and AUTH_ENABLED=true."""
    response = raw_client.post(
        "/api/v1/chat/stream",
        json={"query": "Test legal query", "mode": "STRICT"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# STRICT mode — SSE stream structure
# ---------------------------------------------------------------------------

def test_chat_stream_strict_returns_200_with_sse_content_type(client) -> None:
    """Valid STRICT request should respond 200 text/event-stream."""
    with patch("app.api.routes.chat.LLMSynthesisService") as mock_llm_class:
        async def _mock_stream(*args, **kwargs):
            yield "Legal answer token."

        mock_svc = MagicMock()
        mock_svc.stream_strict_synthesis = _mock_stream
        mock_svc.validate_strict_response = MagicMock(side_effect=lambda x: x)
        mock_llm_class.return_value = mock_svc

        response = client.post(
            "/api/v1/chat/stream",
            json={"query": "What are the termination terms?", "mode": "STRICT"},
        )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


def test_chat_stream_strict_contains_status_events(client) -> None:
    """Response body must include SSE status events."""
    with patch("app.api.routes.chat.LLMSynthesisService") as mock_llm_class:
        async def _mock_stream(*args, **kwargs):
            yield "answer"

        mock_svc = MagicMock()
        mock_svc.stream_strict_synthesis = _mock_stream
        mock_svc.validate_strict_response = MagicMock(side_effect=lambda x: x)
        mock_llm_class.return_value = mock_svc

        response = client.post(
            "/api/v1/chat/stream",
            json={"query": "contract terms?", "mode": "STRICT"},
        )
    assert "event: status" in response.text


def test_chat_stream_strict_contains_metadata_event(client) -> None:
    """Response body must include a metadata event with citations."""
    with patch("app.api.routes.chat.LLMSynthesisService") as mock_llm_class:
        async def _mock_stream(*args, **kwargs):
            yield "answer"

        mock_svc = MagicMock()
        mock_svc.stream_strict_synthesis = _mock_stream
        mock_svc.validate_strict_response = MagicMock(side_effect=lambda x: x)
        mock_llm_class.return_value = mock_svc

        response = client.post(
            "/api/v1/chat/stream",
            json={"query": "contract terms?", "mode": "STRICT"},
        )
    assert "event: metadata" in response.text


def test_chat_stream_strict_empty_context_yields_fallback(client) -> None:
    """When vector store has no matching chunks, the fallback string must appear in the stream."""
    with patch("app.api.routes.chat.LLMSynthesisService") as mock_llm_class:
        async def _mock_stream(query, context_chunks, history=None, images=None):
            if not context_chunks:
                yield "Information not found in the uploaded documents."
            else:
                yield "Found content."

        mock_svc = MagicMock()
        mock_svc.stream_strict_synthesis = _mock_stream
        mock_svc.validate_strict_response = MagicMock(side_effect=lambda x: x)
        mock_llm_class.return_value = mock_svc

        response = client.post(
            "/api/v1/chat/stream",
            json={"query": "query with zero matches", "mode": "STRICT"},
        )
    assert "Information not found in the uploaded documents." in response.text


def test_chat_stream_strict_message_tokens_in_response(client) -> None:
    """Token deltas must appear as SSE message events."""
    with patch("app.api.routes.chat.LLMSynthesisService") as mock_llm_class:
        async def _mock_stream(*args, **kwargs):
            yield "Section 4 applies here."

        mock_svc = MagicMock()
        mock_svc.stream_strict_synthesis = _mock_stream
        mock_svc.validate_strict_response = MagicMock(side_effect=lambda x: x)
        mock_llm_class.return_value = mock_svc

        response = client.post(
            "/api/v1/chat/stream",
            json={"query": "What is section 4?", "mode": "STRICT"},
        )
    assert "event: message" in response.text
    assert "Section 4 applies here." in response.text


def test_chat_stream_strict_done_event_in_response(client) -> None:
    """The SSE stream must end with a status event reporting 'Done'."""
    with patch("app.api.routes.chat.LLMSynthesisService") as mock_llm_class:
        async def _mock_stream(*args, **kwargs):
            yield "answer"

        mock_svc = MagicMock()
        mock_svc.stream_strict_synthesis = _mock_stream
        mock_svc.validate_strict_response = MagicMock(side_effect=lambda x: x)
        mock_llm_class.return_value = mock_svc

        response = client.post(
            "/api/v1/chat/stream",
            json={"query": "any query", "mode": "STRICT"},
        )
    assert "Done" in response.text


# ---------------------------------------------------------------------------
# ENHANCED mode — web search is invoked
# ---------------------------------------------------------------------------

def test_chat_stream_enhanced_calls_web_search_service(client) -> None:
    """ENHANCED mode must invoke WebSearchService.search_external_legal_web."""
    with (
        patch("app.api.routes.chat.LLMSynthesisService") as mock_llm_class,
        patch("app.api.routes.chat.WebSearchService") as mock_web_class,
        patch("app.api.routes.chat.AgentRouterService") as mock_router_class,
    ):
        async def _mock_enhanced(*args, **kwargs):
            yield "Enhanced legal answer."

        mock_llm = MagicMock()
        mock_llm.stream_enhanced_synthesis = _mock_enhanced
        mock_llm_class.return_value = mock_llm

        mock_web = MagicMock()
        mock_web.search_external_legal_web = AsyncMock(return_value={"results": []})
        mock_web_class.return_value = mock_web

        mock_router = MagicMock()
        mock_router.reformulate_query = AsyncMock(return_value="reformulated query")
        mock_router.detect_legal_conflicts = AsyncMock(return_value=None)
        mock_router_class.return_value = mock_router

        response = client.post(
            "/api/v1/chat/stream",
            json={"query": "What does recent case law say?", "mode": "ENHANCED"},
        )

    assert response.status_code == 200
    mock_web.search_external_legal_web.assert_called_once()
    mock_router.reformulate_query.assert_called_once()


def test_chat_stream_enhanced_with_conflict_alert_in_metadata(client) -> None:
    """Conflict alerts detected by AgentRouterService must appear in the metadata event."""
    conflict = {
        "has_conflict": True,
        "severity": "HIGH",
        "contract_clause": "30-day notice",
        "legal_precedent": "60-day rule",
        "explanation": "Conflict",
    }

    with (
        patch("app.api.routes.chat.LLMSynthesisService") as mock_llm_class,
        patch("app.api.routes.chat.WebSearchService") as mock_web_class,
        patch("app.api.routes.chat.AgentRouterService") as mock_router_class,
    ):
        async def _mock_enhanced(*args, **kwargs):
            yield "answer"

        mock_llm = MagicMock()
        mock_llm.stream_enhanced_synthesis = _mock_enhanced
        mock_llm_class.return_value = mock_llm

        mock_web = MagicMock()
        mock_web.search_external_legal_web = AsyncMock(return_value={"results": []})
        mock_web_class.return_value = mock_web

        mock_router = MagicMock()
        mock_router.reformulate_query = AsyncMock(return_value="query")
        mock_router.detect_legal_conflicts = AsyncMock(return_value=conflict)
        mock_router_class.return_value = mock_router

        response = client.post(
            "/api/v1/chat/stream",
            json={"query": "contract compliance?", "mode": "ENHANCED"},
        )

    assert "conflict_alert" in response.text
    assert "HIGH" in response.text


# ---------------------------------------------------------------------------
# STRICT mode — validate_strict_response guardrail is applied
# ---------------------------------------------------------------------------

def test_chat_stream_strict_guardrail_applied_to_every_token(client) -> None:
    """validate_strict_response must be called for each token in STRICT mode."""
    with patch("app.api.routes.chat.LLMSynthesisService") as mock_llm_class:
        async def _mock_stream(*args, **kwargs):
            yield "token one"
            yield "token two"

        mock_svc = MagicMock()
        mock_svc.stream_strict_synthesis = _mock_stream
        validate_mock = MagicMock(side_effect=lambda x: x)
        mock_svc.validate_strict_response = validate_mock
        mock_llm_class.return_value = mock_svc

        client.post(
            "/api/v1/chat/stream",
            json={"query": "query", "mode": "STRICT"},
        )
    assert validate_mock.call_count == 2


# ---------------------------------------------------------------------------
# CHAT SESSION auto-persistence tests
# ---------------------------------------------------------------------------

def test_chat_stream_with_chat_id_persists_user_and_assistant_messages(client) -> None:
    """When chat_id is passed, user prompt and streamed assistant answer are saved in history."""
    # 1. Create a chat session
    chat_resp = client.post("/api/v1/chats", json={"title": "Persisted Chat", "mode": "STRICT"})
    chat_id = chat_resp.json()["chat_id"]

    # 2. Stream a response with chat_id
    with patch("app.api.routes.chat.LLMSynthesisService") as mock_llm_class:
        async def _mock_stream(*args, **kwargs):
            yield "The termination clause requires "
            yield "30 days notice."

        mock_svc = MagicMock()
        mock_svc.stream_strict_synthesis = _mock_stream
        mock_svc.validate_strict_response = MagicMock(side_effect=lambda x: x)
        mock_llm_class.return_value = mock_svc

        response = client.post(
            "/api/v1/chat/stream",
            json={"query": "What is the termination clause?", "chat_id": chat_id},
        )

    assert response.status_code == 200

    # 3. Check message history for the chat
    msg_resp = client.get(f"/api/v1/chats/{chat_id}/messages")
    assert msg_resp.status_code == 200
    messages = msg_resp.json()["messages"]

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "What is the termination clause?"

    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "The termination clause requires 30 days notice."
    assert "mode" in messages[1]["metadata"]


def test_chat_stream_returns_404_for_unknown_chat_id(client) -> None:
    """Stream request with non-existent chat_id returns 404 Not Found."""
    response = client.post(
        "/api/v1/chat/stream",
        json={"query": "Hello", "chat_id": "non-existent-uuid"},
    )
    assert response.status_code == 404

