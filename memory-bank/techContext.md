# Tech context — ViveCaribe

## Stack

### Backend

- Python **3.13+**, packaged with **uv** (`apps/backend/pyproject.toml` /
  `uv.lock`)
- FastAPI + Uvicorn
- Pydantic v2 + pydantic-settings
- SQLAlchemy 2.x async (`asyncpg` / `psycopg`) + Alembic
- Argon2 (`argon2-cffi`) + PyJWT
- httpx, Tenacity, BeautifulSoup4, PyYAML, Rich, Sentry SDK
- Playwright (Zoho free-tier: login/cookies only — no IMAP/API)
- phonenumbers, pycountry
- Gmail (Google OAuth), Outlook (MSAL), Zoho (Playwright + HTTP mail)

### Frontend

- Next.js **16**, React **19**, TypeScript, Tailwind CSS **v4**
- TailAdmin starter (ApexCharts, FullCalendar, jvectormap, etc.)
- Package manager: npm (`package-lock.json`)
- `output: 'standalone'` for Docker

## Monorepo layout

- `apps/backend` — API package, tests, migrations, YAML, Dockerfiles, `vercel.json`
- `apps/frontend` — Next.js admin UI + portable Dockerfile
- Repo root — Compose, CI, README, Memory Bank (no root Docker/Vercel files)

## Runtime data dir (API)

- `APP_DATA_DIR` — writable root for Zoho session JSON (Docker/Vercel).
  Falls back to user home when unset.
- Images keep `/app` immutable for non-root; persist `/data` separately.

## Local tooling

```bash
docker compose up -d db          # Postgres 16 on host port 5433
cd apps/backend
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn vivecaribe.main:app --reload
uv run pytest                    # 90% coverage gate

cd apps/frontend
npm install
npm run dev                      # :3000
```

Full stack: `docker compose up --build` → `db` + `api` + `frontend`.

`booking_providers.yaml` is resolved relative to process CWD — run API
commands from `apps/backend` (Compose mounts the file into `/app`).

## Test database

Pytest forces `DATABASE_URL` to a `*_test` database
(`vivecaribe_test` by default). Override with `TEST_DATABASE_URL`.
Fixtures refuse to reset any database whose name does not end with `_test`.

## CI

`.github/workflows/test.yml` — Postgres 16 on 5433;
`defaults.run.working-directory: apps/backend`; `uv sync`,
`alembic upgrade head`, `uv run pytest` with coverage fail-under 90.
Frontend CI not required for #38 (Vercel preview builds the UI).

## Deploy targets

| App | Vercel project | Root Directory | Mechanism |
|-----|----------------|----------------|-----------|
| API | `vivecaribe` | `apps/backend` | `Dockerfile.vercel` → Fluid Compute; cron in `vercel.json` |
| UI | `vivecaribe-frontend` | `apps/frontend` | Next.js native |

Production DB for API: Supabase transaction pooler (`:6543`) with `NullPool`
+ disabled prepared statements when `ENVIRONMENT != local`.

Ignored Build Step (not Skip Unaffected Projects): polyglot monorepo without
JS workspaces. Command pattern:
`git diff HEAD^ HEAD --quiet -- .` (runs inside Root Directory).

Portable images (Compose / future AWS):

- `apps/backend/Dockerfile` → uvicorn `:8000`
- `apps/frontend/Dockerfile` → Next standalone `:3000`
