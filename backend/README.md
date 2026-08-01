# SIFT.AI Backend

FastAPI backend for ingestion, chunking, Ahnlich vector search, document
management, and audio transcription.

For a step-by-step human runbook, see [HUMAN_RUNBOOK.md](HUMAN_RUNBOOK.md).

## Structure

- `app/main.py`: FastAPI application instance, lifespan wiring, router registration
- `app/api/routes/health.py`: basic health and root routes
- `app/api/routes/documents.py`: upload, list, delete, and strict search endpoints
- `app/api/routes/audio.py`: Whisper-based audio transcription endpoint
- `app/services/vector_store.py`: Ahnlich AI proxy integration (with an in-memory fallback)
- `app/services/cache.py`: Redis-backed search result cache (no-op if `REDIS_URL` is unset)
- `app/db/`: Postgres-backed document registry (SQLAlchemy models + service), used for
  `GET /api/v1/documents` and `DELETE /api/v1/documents/{document_id}`. Ahnlich itself has
  no concept of "a document" - only chunks/vectors + metadata - so document-level listing
  and deletion is backed by Postgres (e.g. Neon) instead.
- `tests/`: pytest suite covering chunking, upload, search, document management, and the
  vector-store metadata encoding

## Endpoints

- `GET /` , `GET /health`
- `POST /api/v1/documents/upload`
- `GET /api/v1/documents?user_id=...`
- `DELETE /api/v1/documents/{document_id}`
- `POST /api/v1/search/strict`
- `POST /api/v1/audio/transcribe`

## Environment variables

See [.env.example](.env.example) for the full list (Ahnlich connection, `DATABASE_URL`,
`REDIS_URL`, Whisper model settings). Everything degrades gracefully when unset: no
`AHNLICH_HOST` reachable -> in-memory vector fallback; no `DATABASE_URL` -> in-memory
document registry; no `REDIS_URL` -> caching disabled.

## Run locally

1. Install dependencies with `python -m pip install --editable ".[dev]"`.
2. Start the app with `fastapi dev app/main.py`.
3. Open `http://127.0.0.1:8000`, `http://127.0.0.1:8000/docs`, or `http://127.0.0.1:8000/redoc`.

## Tests

```bash
python -m pytest
```

## Docker

1. Build the image with `docker build -t sift-ai-backend .`.
2. Run the container with `docker run --rm -p 8000:8000 sift-ai-backend`.
3. Or use `docker compose up --build` to also start Ahnlich and Redis (see
   [HUMAN_RUNBOOK.md](HUMAN_RUNBOOK.md)).
