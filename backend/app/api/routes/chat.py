# app/api/routes/chat.py
import asyncio
import json
import logging
from typing import Any, List, Optional
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator
from sse_starlette.sse import EventSourceResponse


from app.rate_limit import rate_limited_user_id
from app.services.agent_router import AgentRouterService
from app.services.llm_synthesis import LLMSynthesisService
from app.services.web_search import WebSearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Maximum number of prior messages (user+assistant) to include as
# conversation context so the LLM has multi-turn memory.
MAX_HISTORY_MESSAGES = 10

# Maximum total characters of history text to include (prevents token blowout
# when conversations get very long).
MAX_HISTORY_CHARS = 4000

# Minimum user message length to consider for vectorisation.
# Short greetings / follow-ups ("yes", "what about section 5?") are not
# useful as searchable context.
MIN_VECTORISE_LENGTH = 50

# Maximum number of inline images per chat request.
MAX_INLINE_IMAGES = 3

# Maximum inline image size in bytes (5 MB).
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024


class ChatRequest(BaseModel):

    query: str
    chat_id: Optional[str] = None
    # None = not supplied by the client -> fall back to the stored chat mode.
    # STRICT is a real explicit choice here (NOT a sentinel), so an explicitly
    # selected "STRICT" overrides a stored "ENHANCED" session.
    mode: Optional[str] = None
    document_ids: Optional[List[str]] = None
    # Base64-encoded images for inline multimodal analysis (max 3, 5MB each).
    images: Optional[List[str]] = Field(default=None, max_length=MAX_INLINE_IMAGES)
    top_k: int = 5
    min_score_threshold: float = 0.5

    @model_validator(mode="before")
    @classmethod
    def parse_stringified_json(cls, data: Any) -> Any:
        if isinstance(data, str):
            try:
                return json.loads(data)
            except Exception:
                pass
        return data


def _parse_bounding_boxes(raw: Any) -> list[dict]:
    """Safely parse bounding_boxes from chunk metadata.

    The value is stored as a JSON string in the vector store (Ahnlich only
    supports raw_string metadata). Returns an empty list on any parse error.
    """
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _validate_inline_images(images: list[str] | None) -> list[str]:
    """Validate and cap inline image attachments."""
    if not images:
        return []
    validated = []
    for img_b64 in images[:MAX_INLINE_IMAGES]:
        # Rough size check: base64 is ~4/3 of raw bytes
        estimated_bytes = len(img_b64) * 3 // 4
        if estimated_bytes > MAX_IMAGE_SIZE_BYTES:
            logger.warning(
                f"Skipping inline image exceeding {MAX_IMAGE_SIZE_BYTES // (1024*1024)}MB limit "
                f"(estimated {estimated_bytes // (1024*1024)}MB)"
            )
            continue
        validated.append(img_b64)
    return validated


@router.post("/stream")
async def chat_stream(
    request: Request,
    payload: ChatRequest,
    current_user_id: str = Depends(rate_limited_user_id),
):
    """
    Main agentic chat endpoint streaming tokens and event updates via Server-Sent Events (SSE).
    Supports Strict Mode (vector store only) and Enhanced Mode (hybrid Exa web search + conflict checking).

    Now also supports:
    - Conversation history context (multi-turn memory)
    - Inline image analysis via Gemini Vision (base64 images in the `images` field)
    - User text vectorisation (substantive user text is indexed for future retrieval)

    If `chat_id` is supplied, session default `mode` and `document_ids` are resolved if omitted,
    and user query + assistant response + citation metadata are automatically saved in the DB.
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty.",
        )

    vector_store = getattr(request.app.state, "vector_store", None)
    document_registry = getattr(request.app.state, "document_registry", None)
    chat_registry = getattr(request.app.state, "chat_registry", None)

    # Validate inline images early (before any async work).
    validated_images = _validate_inline_images(payload.images)

    # 1. Resolve Chat Session defaults & verify ownership if chat_id is provided
    #
    # Mode precedence: the mode the client sends with THIS message always wins,
    # so switching STRICT<->ENHANCED mid-conversation takes effect immediately.
    # Only when the client omits mode entirely do we fall back to the mode the
    # chat was created with.
    chat_record = None
    explicit_mode = payload.mode.upper().strip() if payload.mode and payload.mode.strip() else None
    effective_mode = explicit_mode or "STRICT"
    effective_doc_ids = payload.document_ids or []
    old_mode = None  # Track for mode_change SSE event

    # Conversation history for multi-turn context.
    conversation_history: list[dict[str, str]] = []

    if payload.chat_id and chat_registry:
        chat_record = await chat_registry.get_chat(payload.chat_id, user_id=current_user_id)
        if not chat_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat '{payload.chat_id}' was not found.",
            )
        # Use stored chat defaults only when this message didn't override them.
        if not payload.document_ids and chat_record.get("document_ids"):
            effective_doc_ids = chat_record.get("document_ids", [])
        old_mode = chat_record.get("mode")
        if explicit_mode is None and old_mode:
            effective_mode = old_mode
        elif explicit_mode is not None and old_mode and old_mode != explicit_mode:
            # Mode changed mid-session — will emit mode_change SSE event.
            pass

        # Persist the resolved mode back onto the chat so the session default
        # tracks the user's most recent choice (and the sidebar reflects it).
        if explicit_mode is not None and chat_record.get("mode") != explicit_mode:
            try:
                await chat_registry.update_chat(
                    payload.chat_id, user_id=current_user_id, mode=explicit_mode
                )
            except Exception as exc:  # non-fatal: the stream still uses effective_mode
                logger.warning(f"Failed to persist mode change for chat {payload.chat_id}: {exc}")

        # Fetch conversation history for multi-turn context.
        try:
            all_messages = await chat_registry.list_messages(
                chat_id=payload.chat_id, user_id=current_user_id
            )
            # Take the most recent messages, capped by count and total chars.
            recent = all_messages[-MAX_HISTORY_MESSAGES:] if all_messages else []
            total_chars = 0
            for msg in recent:
                msg_content = msg.get("content", "")
                if total_chars + len(msg_content) > MAX_HISTORY_CHARS:
                    break
                conversation_history.append({
                    "role": msg.get("role", "user"),
                    "content": msg_content,
                })
                total_chars += len(msg_content)
        except Exception as exc:
            logger.warning(f"Failed to fetch conversation history: {exc}")

        # Persist User Message
        await chat_registry.add_message(
            chat_id=payload.chat_id,
            role="user",
            content=payload.query.strip(),
        )

        # P1-6: Vectorise substantive user text for future retrieval.
        if vector_store and len(payload.query.strip()) >= MIN_VECTORISE_LENGTH:
            try:
                chat_chunk_id = str(uuid4())
                await vector_store.upsert_chunks(
                    chunks=[payload.query.strip()],
                    metadata=[{
                        "chunk_id": chat_chunk_id,
                        "document_id": f"chat-text-{payload.chat_id}",
                        "page_number": 1,
                        "user_id": current_user_id,
                        "bounding_boxes": "[]",
                        "source": "chat_text",
                    }],
                )
            except Exception as exc:
                logger.warning(f"Failed to vectorise user message: {exc}")

    async def event_generator():
        # P2-2: Emit mode_change event when the user toggled mode mid-session.
        if old_mode and explicit_mode and old_mode != explicit_mode:
            yield {
                "event": "mode_change",
                "data": json.dumps({"from": old_mode, "to": effective_mode}),
            }

        # 1. Emit Initial Status
        yield {
            "event": "status",
            "data": json.dumps({"step": "Searching internal vector store...", "progress": 10}),
        }

        # 2. Multi-document in-process search & re-ranking
        all_chunks = []
        doc_ids = effective_doc_ids

        if vector_store:
            if doc_ids:
                for doc_id in doc_ids:
                    predicates = {"user_id": current_user_id, "document_id": doc_id}
                    try:
                        res = await vector_store.search(
                            query=payload.query, top_k=payload.top_k, predicates=predicates
                        )
                        if res and isinstance(res, list):
                            all_chunks.extend(res)
                    except Exception as e:
                        logger.error(f"Error searching doc {doc_id}: {e}")
            else:
                # Search across all documents owned by current_user_id
                predicates = {"user_id": current_user_id}
                try:
                    res = await vector_store.search(
                        query=payload.query, top_k=payload.top_k, predicates=predicates
                    )
                    if res and isinstance(res, list):
                        all_chunks.extend(res)
                except Exception as e:
                    logger.error(f"Error searching user documents: {e}")

        # Filter by similarity threshold & re-rank
        filtered_chunks = [
            chunk for chunk in all_chunks if chunk.get("score", 0.0) >= payload.min_score_threshold
        ]

        filtered_chunks.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        top_chunks = filtered_chunks[: payload.top_k]

        # 3. Document Name Resolution (using document registry)
        doc_name_cache = {}
        processed_chunks = []
        for chunk in top_chunks:
            meta = chunk.get("metadata", {})
            doc_id = meta.get("document_id")
            chunk_source = meta.get("source", "pdf")

            # Skip chat-text chunks from internal document citations.
            # Conversation memory is already handled via conversation_history.
            if chunk_source == "chat_text" or (doc_id and str(doc_id).startswith("chat-text-")):
                continue

            doc_name = "Document"
            if doc_id:
                if doc_id in doc_name_cache:
                    doc_name = doc_name_cache[doc_id]
                elif document_registry:
                    try:
                        doc_rec = await document_registry.get_document(doc_id)
                        if doc_rec and "document_name" in doc_rec:
                            doc_name = doc_rec["document_name"]
                            doc_name_cache[doc_id] = doc_name
                    except Exception:
                        pass

            processed_chunks.append({
                "text": chunk.get("text", ""),
                "score": chunk.get("score", 0.0),
                "document_id": doc_id,
                "document_name": doc_name,
                "page_number": meta.get("page_number", 1),
                "chunk_id": meta.get("chunk_id", ""),
                "bounding_boxes": _parse_bounding_boxes(meta.get("bounding_boxes")),
                "source": chunk_source,
            })

        # 4. Handle Execution Mode (STRICT vs ENHANCED)
        llm_service = LLMSynthesisService()
        agent_router = AgentRouterService()
        web_service = WebSearchService()

        external_snippets = []
        conflict_alert = None

        if effective_mode == "ENHANCED":
            yield {
                "event": "status",
                "data": json.dumps({"step": "Querying Exa AI for legal web precedents...", "progress": 40}),
            }
            # Reformulate query for Exa
            exa_query = await agent_router.reformulate_query(payload.query, processed_chunks)
            web_res = await web_service.search_external_legal_web(exa_query, num_results=4)
            external_snippets = web_res.get("results", [])
            
            if web_res.get("error"):
                # P2-2: Structured error event for web search failure.
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "code": "WEB_SEARCH_FAILED",
                        "message": str(web_res.get("error")),
                        "remediation": "Proceeding without web sources. Results will be based on uploaded documents only.",
                    }),
                }

            yield {
                "event": "status",
                "data": json.dumps({"step": "Checking for legal conflicts...", "progress": 70}),
            }
            # Conflict detection check
            conflict_alert = await agent_router.detect_legal_conflicts(processed_chunks, external_snippets)

        # 5. Emit Metadata Event (Citations & Conflicts)
        internal_citations = [
            {
                "document_id": c["document_id"],
                "document_name": c.get("document_name", "Document"),
                "page_number": c["page_number"],
                "chunk_id": c["chunk_id"],
                "bounding_boxes": c.get("bounding_boxes", []),
                "file_url": f"/api/v1/documents/{c['document_id']}/file"
                    if c.get("document_id") and c.get("source") != "chat_text"
                    else None,
                "source": c.get("source", "pdf"),
                "text": c.get("text", ""),
                "content": c.get("text", ""),
            }
            for c in processed_chunks
            if c.get("source") != "chat_text" and c.get("document_id") and not str(c.get("document_id", "")).startswith("chat-text-")
        ]
        external_citations = [
            {
                "title": s.get("title", "Web Source"),
                "url": s.get("url", ""),
                "domain": urlparse(s.get("url", "")).netloc or "Web",
                "text": s.get("text", s.get("highlight", "")),
                "content": s.get("text", s.get("highlight", "")),
            }
            for s in external_snippets
        ]

        metadata_payload = {
            "mode": effective_mode,
            "internal_citations": internal_citations,
            "external_citations": external_citations,
            "conflict_alert": conflict_alert,
        }

        yield {
            "event": "metadata",
            "data": json.dumps(metadata_payload),
        }

        # 6. Stream Synthesis Tokens & Accumulate for Persistence
        yield {
            "event": "status",
            "data": json.dumps({"step": "Synthesizing answer...", "progress": 90}),
        }

        full_assistant_response = []

        async def _persist_assistant() -> None:
            """Save whatever assistant text we accumulated.

            Called both on normal completion and from the finally-block when
            the client disconnects mid-stream (asyncio.CancelledError), so a
            partial answer is never silently lost from the chat history.
            """
            if not (payload.chat_id and chat_registry):
                return
            assistant_content = "".join(full_assistant_response).strip()
            if not assistant_content:
                return
            try:
                await chat_registry.add_message(
                    chat_id=payload.chat_id,
                    role="assistant",
                    content=assistant_content,
                    metadata=metadata_payload,
                )
            except Exception as persist_err:  # never let a save failure mask the stream
                logger.error(f"Failed to persist assistant response: {persist_err}")

        persisted = False
        try:
            try:
                if effective_mode == "STRICT":
                    async for token in llm_service.stream_strict_synthesis(
                        payload.query,
                        processed_chunks,
                        history=conversation_history,
                        images=validated_images,
                    ):
                        safe_token = llm_service.validate_strict_response(token)
                        if safe_token:
                            full_assistant_response.append(safe_token)
                            yield {"event": "message", "data": json.dumps({"delta": safe_token})}
                else:
                    async for token in llm_service.stream_enhanced_synthesis(
                        payload.query,
                        processed_chunks,
                        external_snippets,
                        history=conversation_history,
                        images=validated_images,
                    ):
                        if token:
                            full_assistant_response.append(token)
                            yield {"event": "message", "data": json.dumps({"delta": token})}
            except asyncio.CancelledError:
                # Client disconnected mid-stream: persist the partial answer,
                # then re-raise so the ASGI server can tear the request down.
                await _persist_assistant()
                persisted = True
                raise
            except Exception as err:
                logger.error(f"Error during LLM streaming: {err}")
                # P2-2: Structured error event for LLM failures.
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "code": "LLM_STREAM_FAILED",
                        "message": str(err),
                        "remediation": "Try again or switch to a different mode.",
                    }),
                }
                err_msg = f"\n[Streaming error: {err}]"
                full_assistant_response.append(err_msg)
                yield {"event": "message", "data": json.dumps({"delta": err_msg})}

            # Persist Assistant Response on normal completion
            await _persist_assistant()
            persisted = True
        finally:
            # Backstop: any other early exit (e.g. GeneratorExit) still saves.
            if not persisted:
                await _persist_assistant()

        yield {
            "event": "status",
            "data": json.dumps({"step": "Done", "progress": 100}),
        }

    return EventSourceResponse(event_generator())
