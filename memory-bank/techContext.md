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
- Shared loading: `apps/frontend/src/components/ui/loading/` (#50)
- Reservas UI: `apps/frontend/src/components/reservations/` (#48 share + detail)
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

`.github/workflows/test.yml`:

- **Backend job:** Postgres 16 on 5433; `working-directory: apps/backend`;
  `uv sync`, `alembic upgrade head`, `uv run pytest` (coverage ≥ 90%).
- **Frontend job:** path-filtered (`apps/frontend/**`); `npm ci` +
  `npm run build` (Node 22).

`.github/workflows/migrate.yml` (prod schema):

- On push to `main` when `apps/backend/migrations/**` or `alembic.ini` change
  (also `workflow_dispatch`).
- Runs `uv run alembic upgrade head` against repository secret `DATABASE_URL`
  (prod Supabase). Not run in Vercel or Docker Compose entrypoints.

## Env vars (auth / CORS / UI)

| Variable | App | Notes |
|----------|-----|--------|
| `CORS_ORIGINS` | API | Comma-separated browser origins (credentials) |
| `JWT_SECRET` / `JWT_EXPIRE_MINUTES` | API | Access JWT |
| `JWT_REFRESH_EXPIRE_DAYS` | API | Refresh cookie TTL (default 7) |
| `NEXT_PUBLIC_API_URL` | Frontend | API origin, e.g. `https://vivecaribe.vercel.app` |
| `NEXT_PUBLIC_LOGIN_REDIRECT_URL` | Frontend | Default `/reservas` |

## Deploy targets

| App | Vercel project | Root Directory | Mechanism |
|-----|----------------|----------------|-----------|
| API | `vivecaribe` | `apps/backend` | `Dockerfile.vercel` → Fluid Compute; cron in `vercel.json` |
| UI | `vivecaribe-frontend` | `apps/frontend` | Next.js native · https://vivecaribe-frontend.vercel.app |

Production DB for API: Supabase transaction pooler (`:6543`) with `NullPool`
+ disabled prepared statements when `ENVIRONMENT != local`.

Ignored Build Step (not Skip Unaffected Projects): polyglot monorepo without
JS workspaces. Command pattern:
`git diff HEAD^ HEAD --quiet -- .` (runs inside Root Directory).

Portable images (Compose / future AWS):

- `apps/backend/Dockerfile` → uvicorn `:8000`
- `apps/frontend/Dockerfile` → Next standalone `:3000`
