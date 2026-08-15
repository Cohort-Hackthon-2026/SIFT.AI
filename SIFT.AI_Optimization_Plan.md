## SIFT.AI Optimization Plan

This document outlines the key areas for improvement and the steps to enhance SIFT.AI's performance, user experience, reliability, security, and cost-effectiveness.

### Performance & Scalability

1. **PDF Processing Bottlenecks**: (REVIEWED) PDF extraction (`fitz`) and chunking are currently synchronous and block the event loop in `app/api/routes/documents.py`.
    - *Action*: Move PDF processing to `BackgroundTasks` or a task queue.
2. **Vector DB Scalability**: (REVIEWED) Ahnlich AI gRPC client is used for production; local fallback is a token-overlap search.
    - *Action*: Ensure `AhnlichVectorStoreService` implements batch upserts for large documents and consider horizontal scaling for the vector engine.
3. **FastAPI Latency**: (REVIEWED) Basic caching exists in `app/services/cache.py` but is not consistently applied across all endpoints.
    - *Action*: Apply Redis caching to search results and document lists. Implement async task offloading for I/O bound work.

### User Experience

1. **Citation Deep-Linking**: (IMPROVEMENT PLANNED) Current citation formatting needs more structure (document name, page number, and paragraph highlighting).
    - *Action*: Update `metadata` event in `chat.py` to include specific paragraph/coordinate data from `BoundingBox`.
2. **Conflict Alerts**: (INITIAL SYSTEM BUILT) A conflict detection system using LLM comparison is in place in `agent_router.py`.
    - *Action*: Implement "Confidence Score" filtering to reduce false positives in conflict alerts.
3. **Mode Transitions**: (IMPROVEMENT PLANNED) Mode transitions are handled via the `mode` field in `ChatRequest`.
    - *Action*: Add explicit `event: mode_change` in SSE stream to confirm operational boundaries to the frontend.

### Reliability & Fallbacks

1. **API Fallback**: (IMPLEMENTED) Added fallback model support in `LLMSynthesisService` and `AgentRouterService`. Added error status reporting for web search failures in `chat_stream`.
    - *Action*: Implement exponential backoff for API retries.
2. **Chat Session Persistence**: (RELIABILITY ISSUE IDENTIFIED) Partial responses are currently lost if the client disconnects mid-stream.
    - *Action*: Implement periodic "intermediate save" calls during the SSE stream or a `on_disconnect` hook to save the partial `full_assistant_response`.

### Security

1. **API Key Management**: (REVIEWED) API keys are loaded via environment variables in service constructors.
    - *Action*: Move to a dedicated `app/config.py` for centralized validation and secret rotation.
2. **Clerk Auth**: (REVIEWED) Middleware is in place.
    - *Action*: Add rate-limiting per user/API key to prevent abuse.

### Maintainability

1. **Codebase Modularity**: (REVIEWED) Services are separated into `app/services/`.
    - *Action*: Decouple `chat.py` logic from the route handler into a `ChatAgentService` to facilitate testing and reuse.
2. **Logging/Monitoring**: (IMPROVEMENT PLANNED) Basic logging is implemented.
    - *Action*: Integrate structured JSON logging and Sentry for error tracking.

### Cost Optimization

1. **Rate Limits/Caching**: (IMPROVEMENT PLANNED) No current rate limits or broad caching for LLM calls.
    - *Action*: Implement a "Query Normalizer" to avoid duplicate Exa/Tavily calls for semantically similar questions.
2. **Vector DB Optimization**: (IMPROVEMENT PLANNED) No specific storage optimization.
    - *Action*: Implement metadata pruning and TTL for temporary research documents.

## Completed Tasks

1. **Conduct Code Reviews & Fix Tests**:
    - Fixed `AgentRouterService` and `LLMSynthesisService` tests to properly handle mocked LLM calls and avoid actual API requests during unit testing.
    - Improved mock handling in `_stream_with_fallback` and `_invoke_with_fallback`.
    - Simplified `stream_strict_synthesis` to return a standard fallback message when no chunks are found.
2. **Develop Fallback Mechanisms**:
    - Integrated model fallback list in LLM services.
    - Added error event reporting in `chat.py` when web search fails, allowing the assistant to continue with internal knowledge instead of crashing.

## Next Steps

1. **Reliable Persistence**: Implement partial response saving in `chat.py` SSE stream to prevent data loss on disconnection.
2. **Background PDF Processing**: Refactor `documents.py` to process uploads asynchronously using FastAPI `BackgroundTasks`.
3. **Enhanced Citations**: Update the citation metadata to include PDF coordinates for the frontend viewer.
4. **Configuration Centralization**: Move all ENV-based settings to a validated `Settings` class using `pydantic-settings`.
