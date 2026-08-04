"""Tests for the Exa AI web search service."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.web_search import WebSearchService


# ---------------------------------------------------------------------------
# No API key — graceful degraded mode
# ---------------------------------------------------------------------------

async def test_search_returns_empty_when_no_api_key() -> None:
    svc = WebSearchService(api_key=None)
    result = await svc.search_external_legal_web("Nigeria employment law")
    assert result["results"] == []
    assert result["error"] == "EXA_API_KEY is not configured"


# ---------------------------------------------------------------------------
# Happy path — well-formed Exa response
# ---------------------------------------------------------------------------

@patch("app.services.web_search.Exa")
async def test_search_returns_formatted_results(mock_exa_class: MagicMock) -> None:
    mock_client = MagicMock()
    mock_exa_class.return_value = mock_client

    item = MagicMock()
    item.title = "Nigerian Contract Law 2025"
    item.url = "https://lawreview.ng/contract-2025"
    item.published_date = "2025-03-01"
    item.highlights = ["Termination requires 30 days notice", "Severance pay mandatory"]
    item.author = "Prof. Adeyemi"

    mock_client.search.return_value = MagicMock(results=[item])

    svc = WebSearchService(api_key="test-exa-key")
    result = await svc.search_external_legal_web("Nigerian contract termination", num_results=3)

    assert result["error"] is None
    assert len(result["results"]) == 1
    r = result["results"][0]
    assert r["title"] == "Nigerian Contract Law 2025"
    assert r["url"] == "https://lawreview.ng/contract-2025"
    assert "Termination requires 30 days notice" in r["highlights"]
    assert r["author"] == "Prof. Adeyemi"


@patch("app.services.web_search.Exa")
async def test_search_passes_num_results_to_exa(mock_exa_class: MagicMock) -> None:
    mock_client = MagicMock()
    mock_exa_class.return_value = mock_client
    mock_client.search.return_value = MagicMock(results=[])

    svc = WebSearchService(api_key="test-key")
    await svc.search_external_legal_web("query", num_results=7)

    _, kwargs = mock_client.search.call_args
    assert kwargs.get("num_results") == 7


@patch("app.services.web_search.Exa")
async def test_search_passes_search_type_to_exa(mock_exa_class: MagicMock) -> None:
    mock_client = MagicMock()
    mock_exa_class.return_value = mock_client
    mock_client.search.return_value = MagicMock(results=[])

    svc = WebSearchService(api_key="test-key")
    await svc.search_external_legal_web("query", search_type="neural")

    _, kwargs = mock_client.search.call_args
    assert kwargs.get("type") == "neural"


# ---------------------------------------------------------------------------
# Highlights edge cases
# ---------------------------------------------------------------------------

@patch("app.services.web_search.Exa")
async def test_search_joins_list_highlights(mock_exa_class: MagicMock) -> None:
    mock_client = MagicMock()
    mock_exa_class.return_value = mock_client

    item = MagicMock()
    item.title = "Title"
    item.url = "https://example.com"
    item.published_date = None
    item.highlights = ["Part A", "Part B", "Part C"]
    item.author = None
    mock_client.search.return_value = MagicMock(results=[item])

    svc = WebSearchService(api_key="test-key")
    result = await svc.search_external_legal_web("q")
    assert result["results"][0]["highlights"] == "Part A Part B Part C"


@patch("app.services.web_search.Exa")
async def test_search_handles_none_highlights(mock_exa_class: MagicMock) -> None:
    mock_client = MagicMock()
    mock_exa_class.return_value = mock_client

    item = MagicMock()
    item.title = "Title"
    item.url = "https://example.com"
    item.published_date = None
    item.highlights = None
    item.author = None
    mock_client.search.return_value = MagicMock(results=[item])

    svc = WebSearchService(api_key="test-key")
    result = await svc.search_external_legal_web("q")
    assert result["results"][0]["highlights"] == ""


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@patch("app.services.web_search.Exa")
async def test_search_handles_exa_api_error(mock_exa_class: MagicMock) -> None:
    mock_client = MagicMock()
    mock_exa_class.return_value = mock_client
    mock_client.search.side_effect = Exception("Exa rate limit 429")

    svc = WebSearchService(api_key="test-key")
    result = await svc.search_external_legal_web("legal query")

    assert result["results"] == []
    assert "Exa rate limit 429" in (result["error"] or "")


@patch("app.services.web_search.Exa")
async def test_search_always_returns_query_in_result(mock_exa_class: MagicMock) -> None:
    mock_client = MagicMock()
    mock_exa_class.return_value = mock_client
    mock_client.search.return_value = MagicMock(results=[])

    svc = WebSearchService(api_key="test-key")
    result = await svc.search_external_legal_web("my specific query")
    assert result["query"] == "my specific query"
