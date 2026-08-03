# SIFT.AI Backend Runbook

This file is the Docker-only guide for running the backend.

## 1. What you need first

- Docker Desktop running
- The repository cloned locally

## 2. Start the backend with Docker

From the backend folder, run:

```bash
cd backend
docker compose up --build
```

This starts both the API container and the Ahnlich container and exposes it at:

- http://localhost:8000
- http://localhost:8000/docs
- http://localhost:1370

> Note: On first startup, the Ahnlich service may download ONNX embedding models from the internet. If outbound network access is restricted, model startup may fail or take longer than expected.
>
> Allow extra time for the model download to complete before assuming the backend is unavailable.

If you want the backend to use an external Ahnlich service instead, set these environment variables before starting the stack:

```bash
export AHNLICH_HOST=your-host
export AHNLICH_PORT=1370
```

### Document registry (Postgres / Neon)

`GET /api/v1/documents` and `DELETE /api/v1/documents/{document_id}` are backed by Postgres
(Ahnlich has no concept of "a document," only chunks). Set `DATABASE_URL` to any standard
Postgres connection string (a Neon pooled URL works as-is) before starting the stack:

```bash
export DATABASE_URL="postgresql://<user>:<password>@<host>/<db>?sslmode=require&channel_binding=require"
```

If `DATABASE_URL` is unset, the registry falls back to an in-memory store (fine for a quick
local check, but document listings won't survive a restart).

### Search cache (Redis)

`docker-compose.yml` already starts a `redis` container and points `REDIS_URL` at it. If you
run the API outside Docker, set `REDIS_URL=redis://localhost:6379/0` (or leave it unset -
caching is skipped, not required).

### Auth (Clerk)

Every `/api/v1/documents*` and `/api/v1/audio/transcribe` request now requires a valid Clerk
session token. If you don't have a Clerk account/application yet:

```bash
export AUTH_ENABLED=false
```

This treats every request as a fixed `local-dev-user` - fine for smoke-testing the API alone,
**but the moment there's a real frontend involved, do this properly instead**:

1. Create a free Clerk account at clerk.com and create an application.
2. In the Clerk Dashboard, go to Configure -> API Keys -> Advanced and copy:
   - the **JWKS URL** -> `CLERK_JWKS_URL`
   - the same domain without the `/.well-known/jwks.json` suffix -> `CLERK_ISSUER`
3. Set `AUTH_ENABLED=true` (the default - you can omit it).

```bash
export CLERK_JWKS_URL="https://<your-instance>.clerk.accounts.dev/.well-known/jwks.json"
export CLERK_ISSUER="https://<your-instance>.clerk.accounts.dev"
```

With `AUTH_ENABLED=true` and no valid `CLERK_JWKS_URL`/`CLERK_ISSUER` set, every request will
correctly fail with `401` - that's the safe default (fail closed), not a bug.

To test manually without a frontend yet, mint a session token from the Clerk Dashboard
(Users -> pick a user -> "Impersonate user" gives you a working session in the browser you can
pull a token from via `window.Clerk.session.getToken()` in devtools), then:

```bash
curl http://localhost:8000/api/v1/documents -H "Authorization: Bearer <token>"
```

See `../frontend/FRONTEND_INTEGRATION.md` for how the frontend attaches this token to every
request once auth pages exist there.

### Copy `.env.example`

The simplest way to set all of the above is:

```bash
cp .env.example .env
# then fill in DATABASE_URL (and anything else you need)
```

Docker Compose and `fastapi dev` both pick up a local `.env` automatically.

## 3. Run it in the background

```bash
cd backend
docker compose up --build -d
```

## 4. Stop it

```bash
cd backend
docker compose down
```

## 5. View logs

```bash
cd backend
docker compose logs -f
```

## 6. Notes

- The app entrypoint is `app.main:app`.
- If port `8000` is already in use, stop the other process or change the port mapping in the Compose file.
