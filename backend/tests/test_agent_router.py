"""Tests for the AgentRouterService (query reformulator + conflict detector)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.services.agent_router import AgentRouterService


# ---------------------------------------------------------------------------
# reformulate_query
# ---------------------------------------------------------------------------

async def test_reformulate_returns_original_when_no_llm() -> None:
    svc = AgentRouterService(api_key=None)
    result = await svc.reformulate_query("Nigeria employment law termination", [])
    assert result == "Nigeria employment law termination"


async def test_reformulate_returns_llm_output() -> None:
    mock_response = MagicMock()
    mock_response.content = "Nigerian Labour Act 2004 employment termination 2024 ruling"

    svc = AgentRouterService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.ainvoke = AsyncMock(return_value=mock_response)

    result = await svc.reformulate_query(
        "What does the contract say about termination?",
        [{"text": "Section 4.2: 30 days notice required."}],
    )
    assert result == "Nigerian Labour Act 2004 employment termination 2024 ruling"


async def test_reformulate_strips_whitespace_from_llm_output() -> None:
    mock_response = MagicMock()
    mock_response.content = "  labour act termination  \n"

    svc = AgentRouterService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.ainvoke = AsyncMock(return_value=mock_response)

    result = await svc.reformulate_query("query", [])
    assert result == "labour act termination"


async def test_reformulate_falls_back_to_original_on_llm_error() -> None:
    svc = AgentRouterService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.ainvoke = AsyncMock(side_effect=Exception("LLM timeout"))

    result = await svc.reformulate_query("What is the penalty clause?", [])
    assert result == "What is the penalty clause?"


async def test_reformulate_uses_first_three_chunks_as_context() -> None:
    """Only the first 3 internal chunks should be passed as context."""
    captured_messages = []
    mock_response = MagicMock()
    mock_response.content = "reformulated"

    async def _capture(messages):
        captured_messages.extend(messages)
        return mock_response

    svc = AgentRouterService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.ainvoke = _capture

    chunks = [{"text": f"chunk {i}"} for i in range(6)]
    await svc.reformulate_query("query", chunks)

    human_content = captured_messages[1].content  # HumanMessage
    # Only first 200 chars of chunks 0-2 should appear in context
    assert "chunk 0" in human_content
    assert "chunk 1" in human_content
    assert "chunk 2" in human_content
    # chunk 3-5 should NOT be in the context summary
    assert "chunk 3" not in human_content


# ---------------------------------------------------------------------------
# detect_legal_conflicts
# ---------------------------------------------------------------------------

async def test_detect_returns_none_when_no_llm() -> None:
    svc = AgentRouterService(api_key=None)
    result = await svc.detect_legal_conflicts(
        [{"text": "30-day notice clause"}],
        [{"highlights": "New law requires 60 days"}],
    )
    assert result is None


async def test_detect_returns_none_when_no_internal_chunks() -> None:
    svc = AgentRouterService(api_key="test-key")
    result = await svc.detect_legal_conflicts([], [{"highlights": "Some ruling"}])
    assert result is None


async def test_detect_returns_none_when_no_web_snippets() -> None:
    svc = AgentRouterService(api_key="test-key")
    result = await svc.detect_legal_conflicts([{"text": "Clause"}], [])
    assert result is None


async def test_detect_returns_conflict_dict_on_conflict() -> None:
    conflict_json = """{
        "has_conflict": true,
        "severity": "HIGH",
        "contract_clause": "30-day notice without severance",
        "legal_precedent": "2025 Labour Amendment mandates 60-day severance",
        "explanation": "Contract clause directly contradicts 2025 Amendment"
    }"""
    mock_response = MagicMock()
    mock_response.content = conflict_json

    svc = AgentRouterService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.ainvoke = AsyncMock(return_value=mock_response)

    result = await svc.detect_legal_conflicts(
        [{"text": "Section 4: 30-day notice without severance"}],
        [{"highlights": "2025 Labour Act Amendment: 60-day mandatory severance"}],
    )

    assert result is not None
    assert result["has_conflict"] is True
    assert result["severity"] == "HIGH"
    assert "contract_clause" in result
    assert "legal_precedent" in result
    assert "explanation" in result


async def test_detect_returns_none_when_no_conflict() -> None:
    mock_response = MagicMock()
    mock_response.content = '{"has_conflict": false}'

    svc = AgentRouterService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.ainvoke = AsyncMock(return_value=mock_response)

    result = await svc.detect_legal_conflicts(
        [{"text": "Standard clause"}],
        [{"highlights": "Consistent ruling"}],
    )
    assert result is None


async def test_detect_returns_none_on_json_parse_error() -> None:
    mock_response = MagicMock()
    mock_response.content = "NOT VALID JSON {{{broken}}}"

    svc = AgentRouterService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.ainvoke = AsyncMock(return_value=mock_response)

    result = await svc.detect_legal_conflicts(
        [{"text": "clause"}], [{"highlights": "ruling"}]
    )
    assert result is None


async def test_detect_handles_code_block_wrapped_json() -> None:
    """LLMs often wrap JSON in ```json ... ``` - the parser must handle this."""
    wrapped = """```json
{
    "has_conflict": true,
    "severity": "MEDIUM",
    "contract_clause": "Clause A",
    "legal_precedent": "Precedent B",
    "explanation": "They conflict"
}
```"""
    mock_response = MagicMock()
    mock_response.content = wrapped

    svc = AgentRouterService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.ainvoke = AsyncMock(return_value=mock_response)

    result = await svc.detect_legal_conflicts(
        [{"text": "Clause A text"}],
        [{"highlights": "Precedent B text"}],
    )
    assert result is not None
    assert result["severity"] == "MEDIUM"


async def test_detect_returns_none_on_llm_exception() -> None:
    svc = AgentRouterService(api_key="test-key")
    svc.llm = MagicMock()
    svc.llm.ainvoke = AsyncMock(side_effect=Exception("LLM connection error"))

    result = await svc.detect_legal_conflicts(
        [{"text": "clause"}], [{"highlights": "ruling"}]
    )
    assert result is None
