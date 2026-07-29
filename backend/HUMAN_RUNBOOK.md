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

If you want the backend to use an external Ahnlich service instead, set these environment variables before starting the stack:

```bash
export AHNLICH_HOST=your-host
export AHNLICH_PORT=1370
```

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
