# SIFT.AI — Backend Finalization Roadmap (100% Completion Plan)

**Target:** Complete all remaining backend services, LLM synthesis pipelines, agent routers, web search integrations, SSE streaming controllers, and test coverage to reach **100% production readiness**.

> **Note**: This roadmap explicitly incorporates all architectural requirements, auth patterns, multi-doc merging, and edge-case handling outlined in [`backend/BACKEND_DEV2_HANDOFF.md`](file:///Users/user/Documents/Projects/SIFT.AI/backend/BACKEND_DEV2_HANDOFF.md).

---

## 1. Executive Summary & Integration Architecture

While the foundational backend (PDF chunking, Ahnlich Vector Store gRPC client, Postgres/Neon document registry, Redis caching, Auth middleware, and Whisper Audio transcription) built by Backend Dev 1 is **100% complete and tested**, the **Agentic Chat Engine & LLM Synthesis Core** is the final component.

```
                              [ Incoming POST /api/v1/chat/stream ]
                                               │
                                               ▼
                              [ Clerk Auth: get_current_user_id ]
                                               │
                         ┌─────────────────────┴─────────────────────┐
                         │                                           │
                         ▼                                           ▼
                 [ STRICT MODE ]                             [ ENHANCED MODE ]
                 • In-Process vector_store.search            • In-Process vector_store.search
                 • Multi-Doc Search Merging                  • Multi-Doc Search Merging
                 • Document Registry Name Resolution         • Document Registry Name Resolution
                 • Similarity Threshold Filter               • Tavily Web Search Client
                 • Degraded Mode Check (used_fallback)       • LLM Query Reformulator
                 • LLM Strict Synthesizer                    • Hybrid Aggregator Prompt
                 • Zero-Leak Assertion Guard                 • Legal Conflict Detector
                         │                                           │
                         └─────────────────────┬─────────────────────┘
                                               │
                                               ▼
                                   [ SSE Streaming Generator ]
                                (sse-starlette Token & Event Stream)
```

---

## 2. Comprehensive Handoff-Aligned Task Breakdown

### TASK 1: Environment & Dependency Configuration
- [ ] **Dependencies**: Update `backend/pyproject.toml` to include:
  - `openai` (or `anthropic` / `langchain-core`)
  - `httpx` (for Tavily API web search client)
  - `sse-starlette` (for async Server-Sent Events streaming)
- [ ] **Config Validation (`app/core/config.py`)**:
  - Add `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`
  - Add `TAVILY_API_KEY`
  - Add `DEFAULT_LLM_MODEL` (e.g. `gpt-4o` or `claude-3-5-sonnet`)
  - Add `MIN_SIMILARITY_THRESHOLD` (default: e.g. `0.65`)

---

### TASK 2: Vector Search Integration & Handoff Seam Handling
Per `BACKEND_DEV2_HANDOFF.md`, do **NOT** make an HTTP self-call. Use direct in-process calls:
- [ ] **In-Process Vector Store Ingestion**:
  - Retrieve vector store instance directly from `request.app.state.vector_store`.
  - Pass authenticated `user_id` extracted via `Depends(get_current_user_id)`.
- [ ] **Multi-Document Search Merging**:
  - Handle `document_ids` list: execute search per `document_id` with `user_id` predicate filtering, merge outputs, and re-rank by cosine `score`.
- [ ] **Document Name Resolution**:
  - Map `document_id` to human-readable `document_name` using `request.app.state.document_registry.get_document(doc_id)` with request-level caching.
- [ ] **Similarity Score Filtering**:
  - Filter out chunks below `MIN_SIMILARITY_THRESHOLD`.
- [ ] **Degraded Vector Mode Check**:
  - Monitor `used_fallback: true` from Ahnlich; if active, surface a degraded status event (`event: status, data: "Vector search running in degraded mode"`).

---

### TASK 3: Web Search Client Integration (`app/services/web_search.py`)
- [ ] **Tavily Legal Web Client**: Build an async HTTP client `WebSearchService` interacting with Tavily API.
- [ ] **Functionality**:
  - `async search_external_legal_web(query: str, max_results: int = 5) -> List[Dict]`
  - Cleans web snippets, extracts page title, publisher domain, and direct URL.
  - Formats snippets as `[EXTERNAL_SOURCE]` context objects.
- [ ] **Fallback Handling**: If `TAVILY_API_KEY` is missing or Tavily errors out, return empty results gracefully with a status event warning instead of crashing.

---

### TASK 4: LLM Synthesis Engine & Grounding Prompts (`app/services/llm_synthesis.py`)
- [ ] **LLM Client Wrapper**: Async wrapper for OpenAI/Anthropic API supporting streaming tokens and JSON mode.
- [ ] **Strict Mode System Prompt**:
  - Requires answers to be built **strictly** from provided PDF chunks.
  - Formats citations as `[Doc: {document_name}, Page: {page_number}]`.
  - Empty Context / Low Similarity Fallback: Outputs exact string: *"Information not found in the uploaded documents."*
- [ ] **Enhanced Mode System Prompt**:
  - Synthesizes `[INTERNAL_SOURCE]` and `[EXTERNAL_SOURCE]`.
  - Formats internal claims as `[Doc: {document_name}, Page: {page}]` and external claims as `[Web: {domain_name}]({url})`.
- [ ] **Zero-Leak Validation Guardrail**:
  - Function `validate_strict_response(response_text: str) -> str`.
  - Ensures no `[Web: ...]` tags or raw URLs appear in `STRICT` mode responses.

---

### TASK 5: Agent Router & Legal Conflict Detection (`app/services/agent_router.py`)
- [ ] **Query Reformulator Engine**:
  - `async reformulate_query(user_query: str, internal_chunks: List[Dict]) -> List[str]`.
  - Formulates 1–2 web search queries focused on statutory amendments or appellate precedents.
- [ ] **Legal Conflict Detector**:
  - `async detect_legal_conflicts(internal_chunks: List[Dict], web_snippets: List[Dict]) -> List[Dict]`.
  - Detects contradictions between contract terms and live legal rulings.
  - Outputs structured alert objects:
    ```json
    {
      "has_conflict": true,
      "conflict_details": {
        "contract_clause": "Section 4.2 states 30-day notice without severance...",
        "legal_precedent": "2025 Labor Act Amendment requires mandatory 60-day severance...",
        "severity": "HIGH"
      }
    }
    ```

---

### TASK 6: Streaming Chat Endpoint (`app/api/routes/chat.py`)
- [ ] **Endpoint Signature**: `POST /api/v1/chat/stream`
- [ ] **Security**: Requires Clerk authentication via `current_user_id: str = Depends(get_current_user_id)`.
- [ ] **Request Payload Schema (`ChatRequest`)**:
  ```json
  {
    "query": "What is the penalty for early termination?",
    "mode": "STRICT", // "STRICT" or "ENHANCED"
    "document_ids": ["doc_uuid_1", "doc_uuid_2"],
    "stream": true
  }
  ```
- [ ] **SSE Async Generator Workflow**:
  1. Authenticates request via Clerk JWT.
  2. Emits status event: `event: status, data: {"step": "Searching internal vector database..."}`.
  3. Executes multi-document vector search & registry document name resolution.
  4. Handles empty chunks / zero-chunk PDFs: emits prompt with fallback instruction.
  5. If `mode == "ENHANCED"`:
     - Emits status event: `event: status, data: {"step": "Querying live legal web precedents..."}`.
     - Runs `reformulate_query` -> `search_external_legal_web` -> `detect_legal_conflicts`.
  6. Emits metadata event with parsed citations and conflict alerts (`event: metadata`).
  7. Streams response tokens in real-time (`event: message, data: {"delta": "According to..."}`).
- [ ] **Main App Integration**: Mount `chat.py` router inside `app/main.py`.

---

### TASK 7: Automated Test Suite & Backend Verification
- [ ] **`tests/test_web_search.py`**: Test Tavily API response parsing & mock web search outputs.
- [ ] **`tests/test_llm_synthesis.py`**: Test strict mode grounding prompts and zero-leak citation assertions.
- [ ] **`tests/test_agent_router.py`**: Test query reformulation and conflict detection algorithms.
- [ ] **`tests/test_chat_stream.py`**: Integration tests for `POST /api/v1/chat/stream` with Clerk authentication, testing empty chunk fallbacks, multi-doc merging, and SSE event streaming.

---

## 3. Definition of Done (100% Ready Checklist)

- [ ] All 7 core tasks implemented adhering strictly to `BACKEND_DEV2_HANDOFF.md`.
- [ ] `POST /api/v1/chat/stream` authenticated with `get_current_user_id` and streams tokens over SSE.
- [ ] Multi-document vector search queries merged correctly with `document_name` resolution.
- [ ] Empty chunk / zero-chunk PDF queries return standard fallback: *"Information not found in the uploaded documents."*
- [ ] Enhanced mode executes live legal web queries and outputs conflict warning banners when applicable.
- [ ] All pytest unit and integration tests pass cleanly.
