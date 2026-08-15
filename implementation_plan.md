# BE1 — AI & Legal Grounding Implementation Plan

Implement all BE1 tasks from the [SIFTAI_3_Dev_Delivery_Plan.md](file:///Users/user/Documents/Projects/SIFT.AI/SIFTAI_3_Dev_Delivery_Plan.md) (§5, lines 197–233), **plus three new input modalities**: conversation history as context, user text vectorisation, and image support.

## Current State Assessment

| Area | Status | Details |
|---|---|---|
| PDF bounding boxes | ✅ **Already extracted** | [`_extract_pdf_pages`](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/api/routes/documents.py#L115-L138) uses `fitz.get_text("blocks")` and produces `BoundingBox` objects per page |
| Bounding boxes in chunks | ❌ **Not propagated** | [`ChunkMetadata`](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/api/routes/documents.py#L49-L54) only has `chunk_id, document_id, page_number, user_id` |
| Citation SSE payload | ⚠️ **Partial** | [`chat.py` L220-228](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/api/routes/chat.py#L220-L228) emits `internal_citations` with `document_id, document_name, page_number, chunk_id, file_url` but **no `bounding_boxes`** |
| Nigerian citation prompts | ❌ **Not present** | System prompts use generic `[Doc: …, Page: …]` — no court codes, no NWLR format |
| Conflict `confidence_score` | ❌ **Not present** | `detect_legal_conflicts` returns `severity` but no numeric confidence |
| SSE lifecycle events | ❌ **Not present** | No `event: mode_change` or structured `event: error` |
| Conversation history context | ❌ **Not present** | `chat.py` doesn't fetch prior messages — each query is answered in isolation |
| Image upload & analysis | ❌ **Not present** | Only PDF files accepted; Gemini Vision multimodal capability unused |
| User text vectorisation | ❌ **Not present** | Only PDF chunks are indexed; user-sent text in chats is not searchable |

---

## Proposed Changes

### Phase 1 — Pitch-Ready

---

#### Task P1-1: Bounding-box propagation to chunk metadata & SSE citations

##### [MODIFY] [documents.py](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/api/routes/documents.py)

1. **Add `bounding_boxes` to `ChunkMetadata`** (L49-54): Add an optional field — a JSON-serialised string of `[{x0, y0, x1, y1}, ...]` (Ahnlich only supports `raw_string` metadata values).

2. **Propagate page-level bounding boxes into each chunk** in `_chunk_pages` (L141-174): Each chunk inherits the full page's bounding boxes (the FE highlight viewer overlays them all on that page).

##### [MODIFY] [chat.py](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/api/routes/chat.py)

3. **Include `bounding_boxes` in SSE `internal_citations`** (L220-228): Parse the JSON string from chunk metadata back into a list of dicts.

---

#### Task P1-2: Nigerian citation prompts

##### [MODIFY] [llm_synthesis.py](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/services/llm_synthesis.py)

1. **Teach Nigerian court codes**: `[SC]`, `[CA]`, `[FHC]`, `[NIC]`, `[SHCL]` etc.
2. **Teach NWLR citation format**: `[YYYY] Vol NWLR (Pt. XXX) Page`
3. **Set Nigeria as default jurisdiction context**
4. **Preserve existing memo structure** (Executive Summary / Detailed Analysis / Gaps / Key Takeaways)
5. **Keep literal citation braces escaped** (`{{document_name}}`, `{{page_number}}`)

---

#### Task P1-3: Conversation history as LLM context

> [!IMPORTANT]
> Currently each query is answered in isolation — the LLM has no memory of prior conversation turns. This makes multi-turn legal research (e.g. "what about section 5?" after asking about section 3) impossible.

##### [MODIFY] [chat.py](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/api/routes/chat.py)

1. **Fetch recent messages** from `chat_registry.list_messages()` when `chat_id` is provided (after L81, where we already fetch the chat record).

2. **Build a conversation history list** from the last **10 messages** (5 user + 5 assistant turns, configurable via `MAX_HISTORY_MESSAGES = 10`). Convert each message into a `HumanMessage` or `AIMessage` LangChain object.

3. **Pass the conversation history to the LLM** by inserting the history messages between the `SystemMessage` and the current `HumanMessage` in both `stream_strict_synthesis` and `stream_enhanced_synthesis`.

##### [MODIFY] [llm_synthesis.py](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/services/llm_synthesis.py)

4. **Accept `history` parameter** in both `stream_strict_synthesis` and `stream_enhanced_synthesis`. Insert history messages (as `HumanMessage`/`AIMessage` objects) between the system prompt and the current user query.

5. **Truncate history to stay within token budget**: Cap total history text at ~4000 characters to leave room for document chunks and the system prompt.

---

#### Task P1-4: Image upload support (persistent document-like storage)

> [!IMPORTANT]
> Design decision: images uploaded as documents are processed through Gemini Vision to extract text descriptions, which are then chunked and vectorised just like PDF text. This makes image content searchable via the same vector store pipeline.

##### [MODIFY] [documents.py](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/api/routes/documents.py)

1. **Expand accepted file types**: Accept `image/png`, `image/jpeg`, `image/webp`, `image/tiff` alongside `application/pdf`. Update the validation logic (L189-190).

2. **Add `_extract_image_text()`**: New function that uses Gemini Vision to extract text/description from an image:
   - Encode image bytes as base64
   - Send to Gemini via `ChatGoogleGenerativeAI` with a multimodal `HumanMessage` containing the image and a prompt: *"Extract all visible text from this image. If it's a legal document, preserve the document structure, headings, and formatting. If it's a diagram or chart, describe its contents in detail."*
   - Return the extracted text as a single `PageExtraction` (page_number=1, no bounding boxes for images)

3. **Route processing by file type** in `upload_document`: If the file is a PDF, use existing `_extract_pdf_pages`; if it's an image, use the new `_extract_image_text`. The rest of the pipeline (chunking, vectorising, registry storage) stays identical.

4. **Store images in R2**: Use the same `storage.upload_pdf()` path (rename to `storage.upload_file()` or just store with the correct extension in the key).

##### [NEW] [services/image_extraction.py](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/services/image_extraction.py)

5. **Isolated image extraction service**: Create a small service class `ImageExtractionService` that wraps Gemini Vision calls for text extraction from images. Keeps the documents route clean and makes the extraction testable independently.

---

#### Task P1-5: Inline image analysis in chat

> [!IMPORTANT]
> Design decision: images sent inline with chat messages go directly to Gemini Vision as multimodal content — they are not vectorised or persisted as documents. This is for quick one-off analysis (e.g. "what does this clause say?" with a photo of a contract page).

##### [MODIFY] [chat.py](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/api/routes/chat.py)

1. **Accept optional image attachments in `ChatRequest`**: Add an `images` field — a list of base64-encoded image strings (max 3 images per request to control token usage).

   ```python
   class ChatRequest(BaseModel):
       query: str
       chat_id: Optional[str] = None
       mode: Optional[str] = None
       document_ids: Optional[List[str]] = None
       images: Optional[List[str]] = None  # base64-encoded images
       top_k: int = 5
       min_score_threshold: float = 0.5
   ```

2. **Pass images to the LLM**: When `images` are present, build the `HumanMessage` as a multimodal content list:
   ```python
   content = [{"type": "text", "text": query}]
   for img_b64 in images:
       content.append({"type": "image_url", "image_url": f"data:image/jpeg;base64,{img_b64}"})
   human_msg = HumanMessage(content=content)
   ```

##### [MODIFY] [llm_synthesis.py](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/services/llm_synthesis.py)

3. **Accept optional `images` parameter** in both synthesis methods. When images are present, construct a multimodal `HumanMessage` instead of a text-only one. The existing `_stream_with_fallback` method already handles arbitrary LangChain messages, so no changes needed there.

4. **Update system prompts** to acknowledge image context: Add a line like *"The user may attach images of legal documents, clauses, or evidence. Analyse them alongside the document chunks to provide a comprehensive answer."*

---

#### Task P1-6: User text vectorisation

> [!IMPORTANT]
> When a user sends substantive text in chat (not just "hi" or "what about section 5?"), that text becomes searchable context for future queries in the same session.

##### [MODIFY] [chat.py](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/api/routes/chat.py)

1. **Vectorise user messages**: After persisting the user message (L104-108), if the message text is substantive (>50 characters, not a conversational greeting), upsert it into the vector store as a single chunk with metadata:
   ```python
   metadata = {
       "chunk_id": str(uuid4()),
       "document_id": f"chat-text-{chat_id}",  # virtual document ID
       "page_number": 1,
       "user_id": current_user_id,
       "source": "chat_text",  # distinguishes from PDF chunks
   }
   ```

2. **Include `source` field in processed chunks** so the SSE metadata can distinguish document citations from chat-text citations (the FE can render them differently — no PDF viewer link for chat-text sources).

---

### Phase 2 — Chambers & Matters

---

#### Task P2-1: Conflict detection with confidence scoring

##### [MODIFY] [agent_router.py](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/services/agent_router.py)

1. **Update the conflict detection prompt** (L126-141): Instruct the model to return `confidence_score` (float 0.0–1.0) alongside existing fields.
2. **Suppress low-confidence results**: If `confidence_score < 0.75`, return `None`.

---

#### Task P2-2: SSE lifecycle events

##### [MODIFY] [chat.py](file:///Users/user/Documents/Projects/SIFT.AI/backend/app/api/routes/chat.py)

1. **Emit `event: mode_change`** when the resolved mode differs from the stored chat mode:
   ```python
   yield {"event": "mode_change", "data": json.dumps({"from": old_mode, "to": effective_mode})}
   ```

2. **Emit structured `event: error`** payloads instead of embedding error text in `message` events:
   ```jsonc
   { "code": "WEB_SEARCH_FAILED", "message": "...", "remediation": "..." }
   ```

---

#### Task P1-3 (docs): Update FRONTEND_INTEGRATION_GUIDE.md

##### [MODIFY] [FRONTEND_INTEGRATION_GUIDE.md](file:///Users/user/Documents/Projects/SIFT.AI/FRONTEND_INTEGRATION_GUIDE.md)

- Add `bounding_boxes` and `file_url` to `InternalCitation`
- Add `confidence_score` to `LegalConflictAlert`
- Add `images` to `ChatStreamRequest`
- Document `mode_change` and structured `error` SSE events

---

### Phase 3–4 (scoped, deferred)

- **P3-1**: Audio brief generation for matters
- **P3-2**: Audit-event emission at query time
- **P3-3**: "No training on your data" enforcement
- **P4-1**: Deeper NWLR/court-rule tooling

---

## Open Questions

> [!IMPORTANT]
> **Image size limits**: Should inline images be capped at a certain size (e.g. 5MB per image, max 3 images per message)? I'm planning to default to 5MB/image, 3 images/message.

> [!NOTE]
> **Chat text vectorisation cleanup**: Should chat-text vectors be deleted when a chat session is deleted? I'll default to yes — the privacy/delete-my-data path should also purge these.

---

## Verification Plan

### Automated Tests

```bash
cd /Users/user/Documents/Projects/SIFT.AI/backend && python -m pytest tests/ -v
```

| Test file | What it covers |
|---|---|
| `test_processing.py` | `ChunkMetadata` includes `bounding_boxes`; `_chunk_pages` propagates page bounding boxes |
| `test_chat_stream.py` | SSE `metadata` includes `bounding_boxes` and `file_url`; conversation history is passed to LLM; inline images build multimodal messages; `event: mode_change` emitted on toggle; structured `event: error` payloads |
| `test_llm_synthesis.py` | Nigerian citation instructions in prompts; `{{` escaping intact; `history` parameter accepted; `images` parameter builds multimodal content |
| `test_agent_router.py` | `confidence_score` in conflict alert; low-confidence (<0.75) suppressed |
| `test_document_management.py` | Image uploads accepted; image text extraction produces chunks; PDF uploads still work identically |

### Manual Verification
- Full test suite green: `python -m pytest tests/ -v`
- No regressions across all 23 existing test files
