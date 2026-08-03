# Backend Developer 2 Handoff - Agent Router, Web Search & Response Synthesis

This describes exactly what Backend Developer 1 built, how to call it from
your code, and what to watch out for. Read this before starting Step 1 of
your section in `Updated_AI_Build_Plan.md`.

## What already exists and works

A FastAPI app (`backend/app/`) with:

- **Every endpoint below now requires a valid Clerk session token**
  (`Authorization: Bearer <token>`) - see `app/auth.py` and
  `backend/HUMAN_RUNBOOK.md`'s Auth section. `/chat/stream` should follow
  the same pattern: `current_user_id: str = Depends(get_current_user_id)`
  from `app.auth`, not a client-supplied field. Current account model is
  individual users only (no firm/organization support yet - see
  `frontend/CLERK_AUTH_INTEGRATION.md` for the reasoning).
- `POST /api/v1/documents/upload` - PDF -> extracted pages -> chunked text ->
  embedded and stored in Ahnlich, with a Postgres-backed document registry
  entry (name, page count, size, upload time).
- `POST /api/v1/search/strict` - takes `{query, document_id?, top_k}` (no
  `user_id` field - it's derived from the caller's token, not accepted from
  the client), embeds the query via Ahnlich's AI proxy, filters server-side
  by metadata predicates (`user_id`, `document_id`), and returns scored
  chunk matches with full citation metadata (`document_id`, `page_number`,
  `chunk_id`, `user_id`).
- `GET /api/v1/documents`, `DELETE /api/v1/documents/{id}` - document
  management, not directly relevant to your work except that a document a
  user just deleted will simply stop appearing in strict-search results.
  Both are scoped to the authenticated user only - `DELETE` on someone
  else's document returns `404` (not `403`, deliberately - see `app/api/routes/documents.py`).
- `POST /api/v1/audio/transcribe` - Whisper transcription, used by the
  frontend's voice-input fallback; not something you call, just context for
  why `/chat/stream` requests may originate from transcribed audio text with
  slightly noisier phrasing than typed queries.
- Redis-backed search caching (identical `query + user_id + document_id +
  top_k` combos are cached ~5 min) - already applied inside
  `/search/strict`, so you get this for free by calling that endpoint;
  nothing extra needed on your end.

All 30 backend tests pass (`cd backend && python -m pytest`). You can run
the app locally with `docker compose up --build` (starts the API, Ahnlich,
and Redis together) - see `backend/HUMAN_RUNBOOK.md`.

## The one integration point that matters to you: `/api/v1/search/strict`

Per the build plan, your `POST /api/v1/chat/stream` endpoint should call this
directly (in-process function call, not an HTTP round-trip to yourself) when
`mode == "STRICT"`. Two ways to do that, in order of preference:

**Option A - import the logic directly (recommended).** Since your endpoint
will live in the same FastAPI app/process, add a thin internal function in
`app/services/vector_store.py` (or call `AhnlichVectorStoreService.search()`
directly via `request.app.state.vector_store`) rather than making an HTTP
call to your own server. This avoids self-referential network calls and lets
you reuse the exact predicate-filtering and caching logic already built. Your
chat route would do roughly:

```python
from app.auth import get_current_user_id

@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    payload: ChatRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    vector_store = request.app.state.vector_store
    predicates = {"user_id": current_user_id}
    if payload.document_id:
        predicates["document_id"] = payload.document_id

    results = await vector_store.search(payload.query, top_k=5, predicates=predicates)
    # results: list of {"text": str, "score": float, "metadata": {...}}
```

**Option B - call the HTTP endpoint.** Simpler to keep the two developers'
code fully decoupled, at the cost of an extra internal HTTP hop. Fine for an
MVP; Option A is the better long-term shape once both pieces are merged into
one app.

Either way, here's the exact response shape you're working with from
`/search/strict` (or the equivalent direct call):

```json
{
  "results": [
    {
      "text": "the actual chunk text",
      "score": 0.83,
      "metadata": {
        "chunk_id": "3f2a...-p4-c2",
        "document_id": "3f2a1c9e-...",
        "page_number": 4,
        "user_id": "lawyer-42"
      }
    }
  ],
  "provider": "ahnlich",
  "used_fallback": false,
  "cached": false,
  "last_error": null
}
```

Feed `results[].text` into your Strict Mode prompt as the context chunks,
and `results[].metadata` gives you everything the build plan's citation
format needs: `[Doc: {document_name}, Page: {page_number}]`. **Note:
`document_name` is not in this payload** - only `document_id`. You'll need to
resolve `document_id -> document_name` yourself for the citation label. The
document registry has it:

```python
document_registry = request.app.state.document_registry
doc = await document_registry.get_document(document_id)
document_name = doc["document_name"] if doc else document_id  # fallback
```

Consider caching this resolution per request (a chat turn typically cites
2-5 chunks from 1-2 documents, not worth a registry hit per chunk).

## Edge cases to handle in your synthesis/routing layer

1. **Empty results.** `results: []` is a normal, expected response - it
   means no chunks matched (low similarity, wrong `document_id` filter, or
   the document has zero extractable text - see the "no extractable text"
   warning case below). Your Strict Mode prompt needs to produce the
   fallback statement the build plan specifies ("Information not found in
   uploaded documents") rather than hallucinating an answer - this is a
   correctness/safety issue for a legal product, not just UX polish.

2. **`used_fallback: true`.** This means Ahnlich itself was unreachable and
   results came from a local in-memory dev fallback instead (only happens
   in local/dev environments without Ahnlich running, or during an Ahnlich
   outage). Consider surfacing this as a status event in your SSE stream
   (e.g. `event: status, data: "Vector search running in degraded mode"`) so
   it's visible rather than silently returning suspiciously-thin results in
   production.

3. **Zero-chunk documents.** A document can exist in `GET /api/v1/documents`
   (`chunk_count: 0`) but never appear in any search results - this happens
   for scanned/image-only PDFs with no extractable text layer (no OCR yet).
   If a user references such a document by name in `document_ids` and gets
   zero results, that's expected, not a bug on your end - nothing to do
   differently, just don't be surprised by it while testing.

4. **Similarity score thresholds.** The build plan calls for returning
   results "with similarity score thresholds" - `/search/strict` currently
   returns whatever Ahnlich's `top_k` gives it without a minimum-score
   cutoff (that's intentionally left to you, since what counts as "too
   irrelevant to cite" is a synthesis-layer/prompt-quality decision, not a
   retrieval-layer one). Apply your own threshold on `results[].score`
   before feeding chunks into the LLM prompt.

5. **Zero-Leak Validation (Step 5 of your plan).** Since Strict Mode
   context comes *only* from `/search/strict` chunks (never web results),
   your output-assertion check just needs to confirm no `[Web: ...]` tags
   or bare URLs appear in a Strict Mode response - there's no scenario on
   the retrieval side where web content could leak in, since Backend
   Developer 1's endpoints never touch the web. The guardrail is entirely
   about the LLM not fabricating one.

6. **`document_ids` scoping across multiple documents.** Your `/chat/stream`
   payload includes `document_ids` (plural, per the build plan), but
   `/search/strict` only accepts a single `document_id`. If a user has
   multiple documents selected, call `/search/strict` once per
   `document_id` and merge/re-rank the results yourself (by `score`) before
   building the prompt - don't assume you can pass a list through.

7. **Auth is already implemented - use it, don't re-derive it.** `app.auth`
   has the full Clerk JWT verification (JWKS fetch/cache, issuer check,
   optional `azp` check). Use `Depends(get_current_user_id)` on
   `/chat/stream` exactly as shown above rather than writing your own
   verification - there's no reason for two independent JWT-checking code
   paths in the same app, and Backend Developer 1's version is already
   tested (`tests/test_auth.py`, including cross-user isolation) against a
   self-signed test JWT that mirrors Clerk's real claim shape. This matters
   more for your endpoint than it did for Backend Developer 1's, since
   yours assembles the final answer a lawyer will act on - a user_id mixup
   here means a wrong answer sourced from someone else's case file, not
   just a wrong document listing.

8. **Legal-domain framing for your prompts.** This is a research tool for
   lawyers, not a general chatbot - a few things worth building into your
   Step 1 system prompts specifically:
   - Never present a synthesized answer as legal advice; frame outputs as
     research assistance ("the uploaded documents state X on page Y") not
     conclusions ("you should do X").
   - Strict Mode's "answer only from provided chunks" requirement is doing
     real work here - case law and contract language where the model fills
     gaps with plausible-sounding but wrong text is a much worse failure
     than the same behavior in a general-purpose assistant. Bias your
     prompt toward under-answering (returning the fallback statement) over
     over-answering when chunk coverage is thin.
   - In Enhanced Mode, keep internal (`[Doc: ...]`) and external
     (`[Web: ...]`) claims clearly separable per the build plan's citation
     format - a lawyer needs to know at a glance whether a given sentence
     came from their own case file or from a general web result, since only
     one of those is something they can verify against the record.

## What to build (per your Step 1-5, unaffected by anything above)

Nothing about your actual scope changes - LLM provider wiring, the
`/chat/stream` router, Tavily/Exa web search integration, hybrid synthesis,
and SSE streaming with `sse-starlette` are all yours to build fresh. The
above is only about the one seam between your work and Backend Developer 1's
work: what `/search/strict` gives you, in what shape, and what to watch for
at that boundary.
