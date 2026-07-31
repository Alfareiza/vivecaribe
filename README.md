# ViveCaribe

API-first booking platform for ViveCaribe. Scaffold + domain core + PostgreSQL
persistence (SQLAlchemy async / Alembic) are in place. Auth and automation
follow in later issues.

## Requirements

- Python **3.13+**
- [uv](https://docs.astral.sh/uv/)
- Docker (Postgres for local persistence)

Pick **one** local path (not both at once):

### Option A — API on your machine (recommended for development)

Runs only the Postgres container. The FastAPI app runs with `uv` on the host
(hot reload, easy debugging).

```bash
cp .env.example .env
# edit .env with local secrets

docker compose up -d db   # start Postgres only (background)
uv sync --group dev
uv run alembic upgrade head   # apply DB migrations (creates tables like users)
uv run uvicorn vivecaribe.main:app --reload --host 0.0.0.0 --port 8000
```

### Option B — API + Postgres both in Docker

Builds and starts every Compose service (`db` and `api`). Use this when you
want a fully containerized stack (no local `uvicorn`).

```bash
cp .env.example .env
# edit .env with local secrets

docker compose up --build   # start db + api (foreground; Ctrl+C to stop)
```

Health check (either option):

```bash
curl http://localhost:8000/health
```

Auth (public):

```bash
curl -X POST http://localhost:8000/users \
  -H 'Content-Type: application/json' \
  -d '{"email":"ops@vivecaribe.com","password":"secret123"}'

curl -X POST http://localhost:8000/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"ops@vivecaribe.com","password":"secret123"}'
```

Protected routes use `Authorization: Bearer <access_token>` (JWT only).

## Database

| Environment | `DATABASE_URL` |
|-------------|----------------|
| Local | `postgresql+asyncpg://postgres:postgres@localhost:5433/vivecaribe` (Compose `db` → host `5433`) |
| Vercel + Supabase | Transaction pooler URL (port **6543**). App uses `NullPool` + disables prepared-statement cache. |

Migrations:

```bash
uv run alembic upgrade head   # apply pending revisions (creates/updates tables)
uv run alembic revision --autogenerate -m "describe change"
```

If the API errors with `relation "users" does not exist` but `alembic current`
already shows `head`, the version table was stamped without the real schema.
Reset the stamp and re-apply:

```bash
uv run alembic stamp base
uv run alembic upgrade head
```

CI note (not wired yet): GitHub Actions can start the same `postgres:16` service
container and run `alembic upgrade head` + `pytest` against
`postgresql+asyncpg://postgres:postgres@localhost:5433/vivecaribe`.

## Project layout

```text
src/vivecaribe/
├── main.py            # FastAPI app factory + lifespan
├── settings.py        # pydantic-settings BaseSettings
├── logging.py         # shared ``logger`` + configure_logging
├── api/               # HTTP routers & schemas
├── domain/            # business core (Pydantic entities + ports)
├── application/       # use cases (later issues)
└── infrastructure/
    └── db/            # SQLAlchemy session, ORM, repositories
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

Unit tests always run. Persistence tests need Postgres (same as Option A —
only the `db` service):

```bash
docker compose up -d db   # Postgres only; skip if it is already running
uv run alembic upgrade head   # apply DB migrations (creates tables like users)
uv run pytest
```
