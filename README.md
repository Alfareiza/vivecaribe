# ViveCaribe

API-first booking platform for ViveCaribe experiences. The business core
(`Reserva`, `User`) is separate from the automation bounded context that
ingests booking emails (Gmail / Outlook), extracts fields, persists
reservations, and optionally notifies WhatsApp.

## Requirements

- Python **3.13+**
- [uv](https://docs.astral.sh/uv/)
- Docker (Postgres for local persistence and tests)

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

## Auth

Public endpoints:

```bash
curl -X POST http://localhost:8000/users \
  -H 'Content-Type: application/json' \
  -d '{"email":"ops@vivecaribe.com","password":"secret123"}'

curl -X POST http://localhost:8000/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"ops@vivecaribe.com","password":"secret123"}'
```

Protected routes use `Authorization: Bearer <access_token>` (JWT).

`GET` and `POST /automation/emails/get-bookings` also accept
`Authorization: Bearer $CRON_SECRET`.

| Method | Body | Behavior |
|--------|------|----------|
| `GET` | none | All providers, `notify=false` (Vercel Cron path) |
| `POST` | optional JSON | Optional `booking_provider` / `notify` filters |

## Run automation locally

1. Fill mailbox OAuth vars in `.env` (see `.env.example` and
   `booking_providers.yaml`).
2. Start the API (Option A above).
3. Authenticate with a JWT **or** `CRON_SECRET`.
4. Call the pipeline:

```bash
TOKEN='<access_token from /login>'
# or: TOKEN="$CRON_SECRET"

# Operator POST with filters
curl -X POST http://localhost:8000/automation/emails/get-bookings \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"booking_provider":"getyourguide","notify":false}'

# Cron-style GET (no body)
curl -X GET http://localhost:8000/automation/emails/get-bookings \
  -H "Authorization: Bearer $CRON_SECRET"
```

Omit `booking_provider` on POST to process every account in
`booking_providers.yaml`. With WhatsApp still NoOp, `notify=true` will
**not** mark emails as read.

CLI alternative (no HTTP):

```bash
uv run python -m vivecaribe.application.automation.use_cases
```

## Database

| Environment | `ENVIRONMENT` | `DATABASE_URL` |
|-------------|---------------|----------------|
| Local | `local` | `postgresql+asyncpg://postgres:postgres@localhost:5433/vivecaribe` (Compose `db` → host `5433`) |
| Vercel + Supabase | `prod` | Transaction pooler (port **6543**), **`postgresql+asyncpg://`** or **`postgresql+psycopg://`**. App uses `NullPool` + driver-specific prepared-statement disable. |

Supabase dashboard URIs use plain `postgresql://` — **change the scheme** before pasting
into Vercel. If the password contains `@`, `#`, `/`, or other reserved characters,
[URL-encode](https://developer.mozilla.org/en-US/docs/Glossary/Percent-encoding) it first.

### Tables (current)

| Table | Idempotency key | Notes |
|-------|-----------------|-------|
| `users` | `email` UK | Argon2 password hash |
| `email_messages` | `(source, mailbox_message_id)` | Includes `body_html` (no separate HTML table) |
| `reservas` | `(booking_provider, reserva_reference)` | FK `email_message_id → email_messages.id` |

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

## Project layout

```text
src/vivecaribe/
├── main.py                 # FastAPI app factory + lifespan
├── settings.py             # pydantic-settings BaseSettings + YAML load
├── logging.py              # shared logger (Rich local / JSON elsewhere)
├── api/                    # thin HTTP routers, schemas, deps
├── domain/                 # Reserva, User, EmailMessage, errors
├── application/
│   ├── auth/               # register / login use cases
│   └── automation/         # pipeline + HTML extractors (providers/)
└── infrastructure/
    ├── db/                 # SQLAlchemy session, ORM, repositories
    └── integrations/       # Gmail, Outlook, WhatsApp NoOp, security
booking_providers.yaml      # non-secret mailbox queries / credential var names
memory-bank/                # agent/project context
tests/                      # pytest suite (90% package coverage gate)
```

## Config

| Source | Purpose |
|--------|---------|
| `.env` | Secrets and runtime settings (`DATABASE_URL`, `JWT_SECRET`, OAuth tokens, …) |
| `booking_providers.yaml` | Non-secret booking-provider mailboxes and search queries |

## Tests

Unit tests always run. Persistence / auth API tests need Postgres (Compose `db`
on port **5433**). Pytest forces an isolated `vivecaribe_test` database
(see `tests/conftest.py`); override host/port with `TEST_DATABASE_URL` if needed.

```bash
docker compose up -d db
uv sync --group dev
uv run alembic upgrade head
uv run pytest
```

Coverage is enforced at **90%** statement coverage for `src/vivecaribe`
(`pytest-cov` via `pyproject.toml` addopts).

CI: GitHub Actions workflow [`.github/workflows/test.yml`](.github/workflows/test.yml)
starts Postgres 16, applies migrations, and runs the same `uv run pytest` gate.

## Deploy (Vercel)

Production: https://vivecaribe.vercel.app

- Production uses root [`Dockerfile.vercel`](Dockerfile.vercel) (Vercel
  detects that filename). `uv sync` installs the `vivecaribe` package;
  Uvicorn serves on `$PORT` (default `80`). `vercel.json` sets
  `"framework": null` so native FastAPI does not override the container.
- Local Compose continues to use [`Dockerfile`](Dockerfile) on port `8000`.
- `src/main.py` remains only as a fallback if the native FastAPI runtime
  is used without a container.

### Vercel Cron

Production cron (Hobby: once daily) hits
`GET /automation/emails/get-bookings` at **09:00 UTC** (= **04:00 Colombia**).
Hobby may fire anytime in that UTC hour (04:00–04:59 Colombia).

Vercel injects `Authorization: Bearer $CRON_SECRET` when `CRON_SECRET` is
set in the project env.

Manual check (same as cron):

```bash
curl -X GET https://vivecaribe.vercel.app/automation/emails/get-bookings \
  -H "Authorization: Bearer $CRON_SECRET"
```

Rotate `CRON_SECRET` / `JWT_SECRET` in the Vercel project env, then redeploy.

### Vercel env vars (Production)

Set these under **Production** only (not required for local `.env` + Docker):

| Variable | Example / notes |
|----------|-----------------|
| `ENVIRONMENT` | `prod` — **not** `production` (pydantic rejects it) |
| `DATABASE_URL` | See [Database](#database) — async driver + Supabase pooler `:6543` |
| `JWT_SECRET` | Long random string (≥ 32 bytes recommended) |
| `CRON_SECRET` | Long random string (Bearer for automation POST) |
| `LOG_LEVEL` | Optional, e.g. `INFO` |
| `SENTRY_DSN` | Optional |
| `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` | Shared Google OAuth app |
| `OUTLOOK_CLIENT_ID` / `OUTLOOK_CLIENT_SECRET` | Shared Microsoft app |
| Per-mailbox tokens | Names listed in `booking_providers.yaml` (`credentials_vars`) |

Example `DATABASE_URL` (replace `<ref>`, `<password>`, `<region>`):

```text
postgresql+asyncpg://postgres.<ref>:<password>@aws-<region>.pooler.supabase.com:6543/postgres
```

Apply migrations to Supabase **once** from your machine (same URL):

```bash
DATABASE_URL='postgresql+asyncpg://postgres.<ref>:<password>@aws-<region>.pooler.supabase.com:6543/postgres' \
  uv run alembic upgrade head
```

Verify after deploy:

```bash
curl https://vivecaribe.vercel.app/health
```
