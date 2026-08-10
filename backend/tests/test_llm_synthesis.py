"""Tests for the LLM synthesis service."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.services.llm_synthesis import LLMSynthesisService


# ---------------------------------------------------------------------------
# validate_strict_response — zero-leak guardrail (sync, no LLM needed)
# ---------------------------------------------------------------------------

def test_guardrail_strips_web_citation_tags() -> None:
    svc = LLMSynthesisService(api_key="test-key")
    dirty = "Per [Web: example.com](https://example.com/ruling), the statute applies."
    cleaned = svc.validate_strict_response(dirty)
    assert "[Web:" not in cleaned
    assert "https://example.com" not in cleaned


def test_guardrail_strips_bare_urls() -> None:
    svc = LLMSynthesisService(api_key="test-key")
    dirty = "See https://supreme-court.gov.ng/2025/ruling for details."
    cleaned = svc.validate_strict_response(dirty)
    assert "https://" not in cleaned


def test_guardrail_preserves_internal_doc_citations() -> None:
    svc = LLMSynthesisService(api_key="test-key")
    text = "Section 4 is enforceable. [Doc: contract.pdf, Page: 7]"
    assert svc.validate_strict_response(text) == text


def test_guardrail_strips_http_and_https_urls() -> None:
    svc = LLMSynthesisService(api_key="test-key")
    text = "See http://example.com/a and https://example.com/b"
    cleaned = svc.validate_strict_response(text)
    assert "http://" not in cleaned
    assert "https://" not in cleaned


def test_guardrail_returns_empty_string_for_url_only_input() -> None:
    svc = LLMSynthesisService(api_key="test-key")
    cleaned = svc.validate_strict_response("https://example.com")
    assert cleaned == ""


# ---------------------------------------------------------------------------
# stream_strict_synthesis
# ---------------------------------------------------------------------------

async def test_strict_empty_chunks_non_greeting_yields_fallback() -> None:
    """A real document question with no matching chunks must return the honest
    'not found' message, never an answer from the model's own knowledge."""
    svc = LLMSynthesisService(api_key="test-key")
    tokens = [t async for t in svc.stream_strict_synthesis("What does clause 4 say?", [])]
    assert tokens == ["Information not found in the uploaded documents."]


async def test_strict_empty_chunks_greeting_is_conversational() -> None:
    """Greetings/capability questions with no chunks are answered
    conversationally rather than getting a cold 'not found'."""
    async def _mock_astream(messages):
        chunk = MagicMock()
        chunk.content = "Hello! I'm SIFT.AI, your legal research assistant."
        yield chunk

    svc = LLMSynthesisService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.astream = _mock_astream

    tokens = [t async for t in svc.stream_strict_synthesis("Hi there", [])]
    assert "".join(tokens) == "Hello! I'm SIFT.AI, your legal research assistant."


async def test_strict_no_api_key_yields_unavailable_message() -> None:
    svc = LLMSynthesisService(api_key=None)
    chunks = [{"document_name": "contract.pdf", "page_number": 1, "text": "content"}]
    tokens = [t async for t in svc.stream_strict_synthesis("test query", chunks)]
    full = "".join(tokens)
    assert "unavailable" in full.lower() or "GEMINI_API_KEY" in full


async def test_strict_streams_llm_tokens() -> None:
    async def _mock_astream(messages):
        for text in ["Section ", "4 requires ", "30 days notice."]:
            chunk = MagicMock()
            chunk.content = text
            yield chunk

    svc = LLMSynthesisService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.astream = _mock_astream

    chunks = [{"document_name": "lease.pdf", "page_number": 4, "text": "Section 4: 30-day notice."}]
    tokens = [t async for t in svc.stream_strict_synthesis("termination clause?", chunks)]
    assert "".join(tokens) == "Section 4 requires 30 days notice."


async def test_strict_skips_empty_llm_content() -> None:
    async def _mock_astream(messages):
        for text in ["Valid token", "", "Another valid token"]:
            chunk = MagicMock()
            chunk.content = text
            yield chunk

    svc = LLMSynthesisService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.astream = _mock_astream

    chunks = [{"document_name": "doc.pdf", "page_number": 1, "text": "content"}]
    tokens = [t async for t in svc.stream_strict_synthesis("q", chunks)]
    # Empty string content must be skipped
    assert "" not in tokens
    assert tokens == ["Valid token", "Another valid token"]


async def test_strict_formats_context_with_doc_name_and_page() -> None:
    """The system prompt must embed document_name and page_number in context."""
    captured_messages = []

    async def _mock_astream(messages):
        captured_messages.extend(messages)
        chunk = MagicMock()
        chunk.content = "answer"
        yield chunk

    svc = LLMSynthesisService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.astream = _mock_astream

    chunks = [{"document_name": "MyContract.pdf", "page_number": 12, "text": "Clause 5 content."}]
    _ = [t async for t in svc.stream_strict_synthesis("What is clause 5?", chunks)]

    system_content = captured_messages[0].content
    assert "MyContract.pdf" in system_content
    assert "12" in system_content


# ---------------------------------------------------------------------------
# stream_enhanced_synthesis
# ---------------------------------------------------------------------------

async def test_enhanced_no_api_key_yields_unavailable_message() -> None:
    svc = LLMSynthesisService(api_key=None)
    tokens = [t async for t in svc.stream_enhanced_synthesis("q", [], [])]
    full = "".join(tokens)
    assert "unavailable" in full.lower() or "GEMINI_API_KEY" in full


async def test_enhanced_streams_llm_tokens() -> None:
    async def _mock_astream(messages):
        for text in ["Based on internal docs ", "and web sources..."]:
            chunk = MagicMock()
            chunk.content = text
            yield chunk

    svc = LLMSynthesisService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.astream = _mock_astream

    internal = [{"document_name": "case.pdf", "page_number": 2, "text": "Ruling text."}]
    external = [{"title": "EFCC 2025", "url": "https://efcc.gov.ng", "highlights": "Key ruling"}]
    tokens = [t async for t in svc.stream_enhanced_synthesis("EFCC case?", internal, external)]
    assert "".join(tokens) == "Based on internal docs and web sources..."


async def test_enhanced_includes_external_source_in_prompt() -> None:
    """External web snippet URL must appear in the system prompt."""
    captured_messages = []

    async def _mock_astream(messages):
        captured_messages.extend(messages)
        chunk = MagicMock()
        chunk.content = "answer"
        yield chunk

    svc = LLMSynthesisService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.astream = _mock_astream

    external = [{"title": "Court Ruling", "url": "https://court.gov.ng/ruling", "highlights": "Case text"}]
    _ = [t async for t in svc.stream_enhanced_synthesis("query", [], external)]

    system_content = captured_messages[0].content
    assert "https://court.gov.ng/ruling" in system_content
