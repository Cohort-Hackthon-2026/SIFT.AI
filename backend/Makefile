PROJECT_DIR := $(CURDIR)
IMAGE_NAME := sift-ai-backend
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help venv install dev test run docker-build docker-run docker-compose-up docker-compose-down clean

help:
	@printf "Available targets:\n"
	@printf "  make install          Install runtime and dev dependencies\n"
	@printf "  make venv             Create a local virtual environment\n"
	@printf "  make dev              Run the FastAPI dev server\n"
	@printf "  make test             Run the test suite\n"
	@printf "  make run              Run the app with uvicorn\n"
	@printf "  make docker-build     Build the Docker image\n"
	@printf "  make docker-run       Run the Docker image locally\n"
	@printf "  make docker-compose-up Start the Docker Compose stack\n"
	@printf "  make docker-compose-down Stop the Docker Compose stack\n"
	@printf "  make clean            Remove Python and test caches\n"

venv:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

install:
	$(PIP) install -e ".[dev]"

dev:
	$(VENV)/bin/fastapi dev app/main.py

test:
	$(PYTHON) -m pytest

run:
	$(VENV)/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

docker-build:
	docker build -t $(IMAGE_NAME) .

docker-run:
	docker run --rm -p 8000:8000 $(IMAGE_NAME)

docker-compose-up:
	docker compose up --build

docker-compose-down:
	docker compose down

clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info