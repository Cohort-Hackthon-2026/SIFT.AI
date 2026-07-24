# SIFT.AI Backend Runbook

This file is the human-friendly guide for starting, building, running, and checking the backend.

## 1. What you need first

- Python 3.9 or newer if you want to run locally without Docker.
- Docker and Docker Compose if you want the containerized workflow.
- `make` if you want the short commands from the Makefile.

## 2. Install dependencies

If you want to work locally:

```bash
cd backend
make venv
make install
```

If you prefer Docker, you can skip local Python installation and use the container commands below instead.

## 3. Start the app locally

Use the FastAPI development server:

```bash
cd backend
make dev
```

Then open:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## 4. Run the app locally in a more direct way

If you want the app itself, not the FastAPI dev wrapper:

```bash
cd backend
make run
```

## 5. Build and run with Make

From the `backend` folder:

```bash
make install
make dev
make test
make run
```

Useful Docker-related targets:

```bash
make docker-build
make docker-run
make docker-compose-up
make docker-compose-down
```

## 6. Build and run with Docker directly

Build the image:

```bash
cd backend
docker build -t sift-ai-backend .
```

Run the container:

```bash
cd backend
docker run --rm -p 8000:8000 sift-ai-backend
```

Run the Compose stack:

```bash
cd backend
docker compose up --build
```

Stop the Compose stack:

```bash
cd backend
docker compose down
```

## 7. Run tests

```bash
cd backend
make test
```

If you want to check only that the Python files still parse:

```bash
cd backend
python3 -m compileall app tests
```

## 8. Small but useful things

- The root route is `GET /` and returns `{"message": "Hello World"}`.
- The health route is `GET /health` and returns `{"status": "ok"}`.
- FastAPI's auto docs are already available at `/docs` and `/redoc`.
- The app entrypoint is `app.main:app`.
- If you edit dependencies, update `pyproject.toml` and rerun `make install`.

## 9. Common gotchas

- If `fastapi` is not found, rerun `make venv` and `make install`.
- If port `8000` is already in use, stop the other process or change the port in the command.
- If Docker fails to build, check that Docker Desktop is running.