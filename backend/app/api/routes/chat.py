# app/api/routes/chat.py
import json
import logging
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, model_validator
from sse_starlette.sse import EventSourceResponse


from app.auth import get_current_user_id
from app.services.agent_router import AgentRouterService
from app.services.llm_synthesis import LLMSynthesisService
from app.services.web_search import WebSearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatRequest(BaseModel):

    query: str
    chat_id: Optional[str] = None
    mode: str = "STRICT"  # "STRICT" or "ENHANCED"
    document_ids: Optional[List[str]] = None
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


@router.post("/stream")
async def chat_stream(
    request: Request,
    payload: ChatRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Main agentic chat endpoint streaming tokens and event updates via Server-Sent Events (SSE).
    Supports Strict Mode (vector store only) and Enhanced Mode (hybrid Exa web search + conflict checking).

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

    # 1. Resolve Chat Session defaults & verify ownership if chat_id is provided
    chat_record = None
    effective_mode = payload.mode.upper() if payload.mode else "STRICT"
    effective_doc_ids = payload.document_ids or []

    if payload.chat_id and chat_registry:
        chat_record = await chat_registry.get_chat(payload.chat_id, user_id=current_user_id)
        if not chat_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat '{payload.chat_id}' was not found.",
            )
        # Use stored chat defaults if not explicitly overridden in payload
        if not payload.document_ids and chat_record.get("document_ids"):
            effective_doc_ids = chat_record.get("document_ids", [])
        if payload.mode == "STRICT" and chat_record.get("mode"):
            effective_mode = chat_record.get("mode", "STRICT")

        # Persist User Message
        await chat_registry.add_message(
            chat_id=payload.chat_id,
            role="user",
            content=payload.query.strip(),
        )

    async def event_generator():
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
                "document_name": c["document_name"],
                "page_number": c["page_number"],
                "chunk_id": c["chunk_id"],
            }
            for c in processed_chunks
        ]
        external_citations = [
            {"title": s["title"], "url": s["url"], "domain": s.get("title", "Web")}
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

        if effective_mode == "STRICT":
            async for token in llm_service.stream_strict_synthesis(payload.query, processed_chunks):
                safe_token = llm_service.validate_strict_response(token)
                if safe_token:
                    full_assistant_response.append(safe_token)
                    yield {"event": "message", "data": json.dumps({"delta": safe_token})}
        else:
            async for token in llm_service.stream_enhanced_synthesis(
                payload.query, processed_chunks, external_snippets
            ):
                if token:
                    full_assistant_response.append(token)
                    yield {"event": "message", "data": json.dumps({"delta": token})}

        # Persist Assistant Response if chat_id is present
        if payload.chat_id and chat_registry:
            assistant_content = "".join(full_assistant_response).strip()
            if assistant_content:
                await chat_registry.add_message(
                    chat_id=payload.chat_id,
                    role="assistant",
                    content=assistant_content,
                    metadata=metadata_payload,
                )

        yield {
            "event": "status",
            "data": json.dumps({"step": "Done", "progress": 100}),
        }

    return EventSourceResponse(event_generator())
