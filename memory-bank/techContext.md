# Tech context — ViveCaribe

## Stack

- Python **3.13+**, packaged with **uv** (`pyproject.toml` / `uv.lock`)
- FastAPI + Uvicorn
- Pydantic v2 + pydantic-settings
- SQLAlchemy 2.x async (`asyncpg` / `psycopg`) + Alembic
- Argon2 (`argon2-cffi`) + PyJWT
- httpx, Tenacity, BeautifulSoup4, PyYAML, Rich, Sentry SDK
- Gmail via Google OAuth refresh tokens; Outlook via MSAL consumers authority

## Local tooling

```bash
docker compose up -d db          # Postgres 16 on host port 5433
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn vivecaribe.main:app --reload
uv run pytest                    # 90% coverage gate
```

## Test database

Pytest forces `DATABASE_URL` to a `*_test` database
(`vivecaribe_test` by default). Override with `TEST_DATABASE_URL`.
Fixtures refuse to reset any database whose name does not end with `_test`.

## CI

`.github/workflows/test.yml` — Postgres 16 service on 5433, `uv sync`,
`alembic upgrade head`, `uv run pytest` with coverage fail-under 90.

## Deploy target

Vercel Fluid Compute entrypoint: `src/main.py`. Production DB: Supabase
transaction pooler (`:6543`) with `NullPool` + disabled prepared statements
when `ENVIRONMENT != local`. Full cron / Dockerfile.vercel work is issue #8.
