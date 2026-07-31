# ViveCaribe

API-first booking platform for ViveCaribe. This repository currently ships the
project scaffold (settings, logging, health endpoint, Docker). Domain,
persistence, auth, and automation land in follow-up issues.

## Requirements

- Python **3.13+**
- [uv](https://docs.astral.sh/uv/)
- Docker (optional, for containerized local runs)

## Local setup (uv)

```bash
cp .env.example .env
# edit .env with local secrets

uv sync --group dev
uv run uvicorn vivecaribe.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## Local setup (Docker)

```bash
cp .env.example .env
# edit .env with local secrets

docker compose up --build
curl http://localhost:8000/health
```

## Project layout

```text
src/vivecaribe/
├── main.py            # FastAPI app factory + lifespan
├── settings.py        # pydantic-settings BaseSettings
├── logging.py         # get_logger / configure_logging
├── api/               # HTTP routers & schemas
├── domain/            # business core (later issues)
├── application/       # use cases (later issues)
└── infrastructure/    # adapters (later issues)
```

## Config

| Source | Purpose |
|--------|---------|
| `.env` | Secrets and runtime settings (`DATABASE_URL`, `JWT_SECRET`, …) |
| `accounts.yaml` | Non-secret mailbox names and search queries |

## Deploy (Vercel)

Production: https://vivecaribe.vercel.app

```bash
vercel deploy --prod
```

Entrypoint: `src/main.py` (re-exports `vivecaribe.main:app`).

## Tests

```bash
uv run pytest
```
