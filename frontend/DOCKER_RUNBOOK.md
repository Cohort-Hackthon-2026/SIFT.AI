# Frontend Docker Runbook

## Prerequisites

- Docker Desktop installed and running
- The repository cloned locally

## Run the frontend with Docker

From the frontend folder, run:

```bash
docker compose up --build -d
```

This will:

- build the frontend image
- start the container in the background
- expose the app at http://localhost:5173

## Stop the frontend

```bash
docker compose down
```

## View logs

```bash
docker compose logs -f
```

## Rebuild after code changes

```bash
docker compose up --build -d
```

## Notes

- The app is served on port 5173.
- If you change frontend dependencies, rebuild the container to ensure they are installed.
