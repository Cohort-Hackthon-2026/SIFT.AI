# SIFT.AI — Development & Debugging Session Summary

## 📅 Session Overview
This document summarizes all the major work, architectural adjustments, bug fixes, performance analyses, and prompt enhancements completed during this development session.

---

## 1. Provider & LLM Routing Architecture

### Attempted AgentRouter Setup & Fallback to Gemini
- **Initial Request**: Configured an OpenAI-compatible proxy (**AgentRouter**) using a tiered fallback cascade:
  - **Tier 1**: `gpt-5.6-sol` (Fast, conversational queries)
  - **Tier 2**: `claude-opus-4-8` (Main document analysis)
  - **Tier 3**: `claude-opus-5` (Escalation fallback)
- **Issue Encountered**: Requests sent to `https://agentrouter.org/v1` failed with HTTP `401 Unauthorized` (`"unauthorized client detected"`).
- **Resolution**: Reverted active provider back to **Google Gemini** using a verified Google AI Studio API key (`GEMINI_API_KEY`).
- **Files Modified**:
  - [`pyproject.toml`](file:///Users/user/Documents/Projects/SIFT.AI/backend/pyproject.toml)
  - [`.env`](file:///Users/user/Documents/Projects/SIFT.AI/backend/.env)
  - [`app/services/agent_router.py`](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/services/agent_router.py)
  - [`app/services/llm_synthesis.py`](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/services/llm_synthesis.py)

---

## 2. Vector Store Latency & Performance Diagnostics

### Root Cause Analysis for Slow Vector Store Loading & Timeouts
- **Symptom**: `AhnlichVectorStore Error: TimeoutError` during vector search.
- **Root Cause Identified**:
  - The `ghcr.io/deven96/ahnlich-ai` Docker container runs an **x86_64 (`linux/amd64`)** image under **QEMU / Rosetta emulation** on Apple Silicon (`arm64`).
  - Loading ONNX models (`all-MiniLM-L6-v2`) inside emulated CPU environments causes massive latency (>10s), triggering gRPC timeouts.
- **Options Provided**:
  - *Option A*: Fallback to lightweight local in-memory vector store for instant local development.
  - *Option B*: Implement non-blocking background initialization and connection caching for Ahnlich.

---

## 3. Critical Bug Fixes

### Fix 1: `KeyError: 'document_name'` in Chat SSE Route
- **Symptom**: `Error during LLM streaming: 'document_name'` thrown in `app/api/routes/chat.py`.
- **Root Cause**: Accessing `c["document_name"]` directly on processed chunks where the key was missing.
- **Fix**: Replaced direct dict access with `c.get("document_name", "Document")` safe default in [`chat.py`](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/api/routes/chat.py#L192).

### Fix 2: Prompt String Template Format Error (`KeyError: 'document_name'`)
- **Symptom**: Streaming error output `[Streaming error: 'document_name']` shown in UI.
- **Root Cause**: `STRICT_MODE_SYSTEM_PROMPT` and `ENHANCED_MODE_SYSTEM_PROMPT` in `llm_synthesis.py` contained literal citation instructions like `[Doc: {document_name}, Page: {page_number}]`. Calling `.format(context_chunks=...)` made Python attempt to format `{document_name}` as a template key.
- **Fix**: Escaped all literal citation brackets to `{{document_name}}` and `{{page_number}}` in [`llm_synthesis.py`](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/services/llm_synthesis.py#L22).

---

## 4. Structured Legal Output System Prompts

### Response Formatting & Arrangement Enhancement
- **User Requirement**: Prevent disorganized or haphazard LLM responses by enforcing a clean, standardized Markdown legal memo format.
- **Implementation**: Updated system prompts in `llm_synthesis.py` to mandate the following response structure:
  - **📌 Executive Summary**: High-level 1-2 sentence overview.
  - **📝 Detailed Analysis**: Thorough legal examination with bolded key terms, subheadings, and inline citations.
  - **⚖️ Legal Conflicts & Risks**: (Enhanced Mode) Contradiction analysis between document clauses and live web law.
  - **💡 Key Takeaways / Next Steps**: 1-3 actionable conclusions.

---

## 5. Docker Container Lifecycle & Rebuilds
- Rebuilt Docker backend services using `docker compose up --build -d`.
- Verified hot-reloading via `WatchFiles` for FastAPI python changes.
