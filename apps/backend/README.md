# ViveCaribe API

FastAPI backend: business API (`User`, `Reserva`) and the automation pipeline
that ingests booking emails (Gmail / Outlook / Zoho), persists reservations,
and optionally notifies WhatsApp (NoOp until Meta is approved).

Monorepo overview: [`README.md`](../../README.md) · UI:
[`apps/frontend/README.md`](../frontend/README.md).

## Stack

- Python **3.13+**, [uv](https://docs.astral.sh/uv/)
- FastAPI · Uvicorn · SQLAlchemy async · Alembic · Pydantic v2
- Playwright (Zoho free-tier mail) · Postgres 16

## Local development

From the **repo root**, copy env once: `cp .env.example .env`.

### Recommended — API on the host, Postgres in Docker

```bash
docker compose up -d db
cd apps/backend
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn vivecaribe.main:app --reload --host 0.0.0.0 --port 8000
```

Health: `curl http://localhost:8000/health`

### Fully containerized API

```bash
# from repo root
docker compose up --build api
```

Build context is this directory (`Dockerfile`). Image listens on **8000**.

## Auth

Browser admin auth (frontend + API) uses a **split token** model:

| Credential | Where it lives | Purpose |
|------------|----------------|---------|
| Access JWT | Frontend **JS memory only** (never `localStorage` / `sessionStorage` / cookie) | `Authorization: Bearer …` on API calls |
| Refresh token | **HttpOnly cookie** on the API origin (`refresh_token`) | `POST /refresh` only — mint a new access JWT |

```text
POST /login  → JSON { access_token } + Set-Cookie refresh_token
POST /refresh → cookie in, new access_token + rotated cookie
POST /logout  → revoke refresh family + Clear-Cookie
```

Protected business routes (`/reservas`, …) require the access JWT.
`GET`/`POST /automation/emails/get-bookings` also accept
`Authorization: Bearer $CRON_SECRET`.

### Local curl

```bash
curl -X POST http://localhost:8000/users \
  -H 'Content-Type: application/json' \
  -d '{"email":"ops@vivecaribe.com","password":"secret123"}'

# -c/-b keep the HttpOnly refresh cookie for /refresh and /logout
curl -c /tmp/vc-cookies -b /tmp/vc-cookies \
  -X POST http://localhost:8000/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"ops@vivecaribe.com","password":"secret123"}'

curl -c /tmp/vc-cookies -b /tmp/vc-cookies -X POST http://localhost:8000/refresh
curl -c /tmp/vc-cookies -b /tmp/vc-cookies -X POST http://localhost:8000/logout
```

### CORS (browser → API)

The Next.js admin calls the API **cross-origin** with `credentials: "include"`.
Set a comma-separated allowlist:

```bash
CORS_ORIGINS=http://localhost:3000,https://vivecaribe-frontend.vercel.app
```

| Method | Body | Behavior |
|--------|------|----------|
| `GET` | none | All providers, `notify=false` (Vercel Cron) |
| `POST` | optional JSON | Optional `booking_provider` / `notify` |

## Run automation locally

1. Fill mailbox OAuth vars in root `.env` (see `.env.example` and
   `booking_providers.yaml`).
2. Start the API (host or Compose).
3. Call with JWT **or** `CRON_SECRET`:

```bash
TOKEN='<access_token from /login>'
# or: TOKEN="$CRON_SECRET"

curl -X POST http://localhost:8000/automation/emails/get-bookings \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"booking_provider":"getyourguide","notify":false}'

curl -X GET http://localhost:8000/automation/emails/get-bookings \
  -H "Authorization: Bearer $CRON_SECRET"
```

Omit `booking_provider` on POST to process every account in
`booking_providers.yaml`. With WhatsApp NoOp, `notify=true` will **not**
mark emails as read.

CLI (no HTTP), from `apps/backend`:

```bash
uv run python -m vivecaribe.application.automation.use_cases
```

## Database

| Environment | `ENVIRONMENT` | `DATABASE_URL` |
|-------------|---------------|----------------|
| Local | `local` | `postgresql+asyncpg://postgres:postgres@localhost:5433/vivecaribe` |
| Vercel + Supabase | `prod` | Pooler port **6543**, scheme `postgresql+asyncpg://` or `postgresql+psycopg://` |

Outside `local`, the app uses `NullPool` and disables prepared statements for
the pooler. Supabase dashboard URIs use plain `postgresql://` — **change the
scheme** before pasting into Vercel. URL-encode special characters in the
password.

| Table | Idempotency key | Notes |
|-------|-----------------|-------|
| `users` | `email` UK | Argon2 password hash |
| `refresh_tokens` | `token_hash` UK | Opaque refresh; rotated; family revoke on reuse |
| `email_messages` | `(source, mailbox_message_id)` | Includes `body_html` |
| `reservas` | `(booking_provider, reserva_reference)` | Soft delete via `deleted_at` |

```bash
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "describe change"
```

If the API errors with `relation "users" does not exist` but `alembic current`
shows `head`, reset and re-apply:

```bash
uv run alembic stamp base
uv run alembic upgrade head
```

## Layout

```text
apps/backend/
├── pyproject.toml / uv.lock
├── alembic.ini
├── booking_providers.yaml
├── Dockerfile / Dockerfile.vercel
├── migrations/
├── tests/
└── src/vivecaribe/
    ├── main.py
    ├── settings.py
    ├── logging.py
    ├── api/                 # routers, schemas, deps
    ├── domain/              # Reserva, User, EmailMessage, errors
    ├── application/
    │   ├── auth/
    │   └── automation/      # pipeline + extractors
    └── infrastructure/
        ├── db/
        └── integrations/    # Gmail, Outlook, Zoho, WhatsApp NoOp
```

## Config

| Source | Purpose |
|--------|---------|
| Repo root `.env` | Secrets (`DATABASE_URL`, `JWT_SECRET`, OAuth, …) |
| `booking_providers.yaml` | Non-secret mailbox queries / credential var names |

## Tests

```bash
docker compose up -d db
cd apps/backend
uv sync --group dev
uv run alembic upgrade head
uv run pytest
```

Pytest uses an isolated `vivecaribe_test` DB (see `tests/conftest.py`).
Override with `TEST_DATABASE_URL` if needed. Coverage gate: **90%** on
`src/vivecaribe`.

CI: [`.github/workflows/test.yml`](../../.github/workflows/test.yml) runs from
`apps/backend`.

## Deploy

- **Vercel project:** `vivecaribe` · Root Directory `apps/backend` · Container
  ([`Dockerfile.vercel`](Dockerfile.vercel))
- **Portable / AWS:** [`Dockerfile`](Dockerfile) (uvicorn `:8000`)
- **Production:** https://vivecaribe.vercel.app
- **Ignored Build Step:** `git diff HEAD^ HEAD --quiet -- .` (skip when this
  folder unchanged)

### Cron

This API project does **not** schedule ingest. Callers (operators or an
external scheduler) `GET`/`POST` the endpoint with JWT or
`Authorization: Bearer $CRON_SECRET`.

```bash
curl -X GET https://vivecaribe-alfareizas-projects.vercel.app/automation/emails/get-bookings \
  -H "Authorization: Bearer $CRON_SECRET"
```

### Production env vars (API project)

| Variable | Notes |
|----------|--------|
| `ENVIRONMENT` | `prod` — **not** `production` |
| `DATABASE_URL` | Async driver + Supabase pooler `:6543` |
| `JWT_SECRET` | Long random string |
| `CRON_SECRET` | Bearer for automation / cron |
| `CORS_ORIGINS` | Comma-separated browser origins (e.g. `http://localhost:3000,https://vivecaribe-frontend.vercel.app`) |
| `LOG_LEVEL` / `SENTRY_DSN` | Optional |
| `GMAIL_CLIENT_*` / `OUTLOOK_CLIENT_*` | Shared OAuth apps |
| Per-mailbox tokens | Names in `booking_providers.yaml` |

### Database migrations (prod)

On merge to `main`, [`.github/workflows/migrate.yml`](../../.github/workflows/migrate.yml)
runs `alembic upgrade head` when `apps/backend/migrations/**` (or `alembic.ini`)
changes. Set the repository secret **`DATABASE_URL`** to the same async Supabase
URL used on Vercel. You can also run the workflow manually via **Actions →
Migrate → Run workflow**.

Manual fallback from this directory:

```bash
DATABASE_URL='postgresql+asyncpg://postgres.<ref>:<password>@aws-<region>.pooler.supabase.com:6543/postgres' \
  uv run alembic upgrade head
```

```bash
curl https://vivecaribe.vercel.app/health
```
