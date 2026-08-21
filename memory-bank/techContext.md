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
- Reservas UI: server-filtered list + `es_hoy` badge (`StatusDot`) (#46)
- Package manager: npm (`package-lock.json`)
- `output: 'standalone'` for Docker

## Monorepo layout

- `apps/backend` — API package, tests, migrations, YAML, Dockerfiles
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

**Coverage gotcha (#81)**: `[tool.coverage.run]` needs
`concurrency = ["greenlet", "thread"]` — SQLAlchemy's async engine
bridges DBAPI calls through `greenlet`, and coverage.py's default
thread-only trace hook doesn't follow it, silently under-reporting
every async DB code path project-wide (measured 89.95% → 95.94% after
adding this, zero test changes). If backend coverage ever looks
implausibly low relative to how thoroughly a path is actually tested,
check this setting first before writing more tests to compensate.

`.github/workflows/migrate.yml` (prod schema):

- On push to `main` when `apps/backend/migrations/**` or `alembic.ini` change
  (also `workflow_dispatch`).
- Runs `uv run alembic upgrade head` against repository secret `DATABASE_URL`
  (prod Supabase). Not run in Vercel or Docker Compose entrypoints.
- Latest schema add: `gastos` + `gasto_reserva_splits` tables, plus a
  one-time reset of `reservas.costos` to `NULL` (#81, migration
  `958c6f8b6a56`) — `costos` becomes fully derived from gastos.
  Previous: `trm_estimado`/`trm_final` (renamed from `trm_del_dia`) +
  `income_final` on `reservas` (#78/#79, PR #80).

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
| API | `vivecaribe` | `apps/backend` | `Dockerfile.vercel` → Fluid Compute |
| UI | `vivecaribe-frontend` | `apps/frontend` | Next.js native · https://vivecaribe-frontend.vercel.app |

Production DB for API: Supabase transaction pooler (`:6543`) with `NullPool`
+ disabled prepared statements when `ENVIRONMENT != local`.

Ignored Build Step (not Skip Unaffected Projects): polyglot monorepo without
JS workspaces. Both projects' dashboard "Ignored Build Step" field runs
`bash "$(git rev-parse --show-toplevel)/scripts/vercel-ignored-build-step.sh"`
(runs inside each project's Root Directory; fixed in #74).

**Known gotcha (fixed #74)**: the original inline command was
`git diff HEAD^ HEAD --quiet -- .`. `HEAD^` is the immediate git parent of
the new commit, *not* the last commit actually deployed for that project.
A single `git push` only triggers one build for the branch tip — if that
push carries multiple commits (e.g. GitHub "Rebase and merge" landing a
multi-commit PR) and the relevant change lives in an earlier commit than
the tip, the tip-only `HEAD^` diff can come up empty and the whole build
gets silently skipped, even though real changes exist relative to what's
live in production. Hit twice: PR #66 (backend-only tip commit, frontend
change one commit back) and PR #73 (docs-only tip commit, feature commit
one back) — both times production frontend served stale code until a
manual `vercel --prod` redeploy. `scripts/vercel-ignored-build-step.sh`
now diffs against `$VERCEL_GIT_PREVIOUS_SHA` (the last commit Vercel
actually deployed for that project), falling back to `HEAD^` only if that
env var is unset or points at a commit no longer reachable.

**Manual prod redeploy gotcha**: `vercel --prod` run from inside
`apps/frontend` (where its own `.vercel/project.json` lives) double-applies
that project's "Root Directory: apps/frontend" setting, producing a
"path .../apps/frontend/apps/frontend does not exist" error. Run it from
the repo root instead, with `VERCEL_ORG_ID`/`VERCEL_PROJECT_ID` env vars
set to the frontend project's ids (repo root's own `.vercel/project.json`
links to the *backend* project, `vivecaribe`, not the frontend one).

Portable images (Compose / future AWS):

- `apps/backend/Dockerfile` → uvicorn `:8000`
- `apps/frontend/Dockerfile` → Next standalone `:3000`
