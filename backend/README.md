# SIFT.AI Backend

FastAPI backend scaffold following the official first-steps pattern.

For a step-by-step human runbook, see [HUMAN_RUNBOOK.md](HUMAN_RUNBOOK.md).

## Structure

- `app/main.py`: FastAPI application instance and router wiring
- `app/api/routes/health.py`: basic health and root routes
- `tests/test_health.py`: smoke tests for the API

## Run locally

1. Install dependencies with `python -m pip install --editable .`.
2. Start the app with `fastapi dev app/main.py`.
3. Open `http://127.0.0.1:8000`, `http://127.0.0.1:8000/docs`, or `http://127.0.0.1:8000/redoc`.

## Docker

1. Build the image with `docker build -t sift-ai-backend .`.
2. Run the container with `docker run --rm -p 8000:8000 sift-ai-backend`.
