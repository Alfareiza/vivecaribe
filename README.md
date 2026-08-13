# ViveCaribe

Monorepo for **ViveCaribe** — booking automation and an admin UI for guided
experiences in the Caribbean.

Operators receive confirmations from GetYourGuide, Viator, Homefans, and
Propio; the API normalizes them into a shared `Reserva` model. The frontend
is the operator dashboard.

| App | Docs | Stack |
|-----|------|-------|
| API | [`apps/backend/README.md`](apps/backend/README.md) | FastAPI · Postgres · Docker |
| Admin UI | [`apps/frontend/README.md`](apps/frontend/README.md) | Next.js · React · Tailwind |

## Repository layout

```text
vivecaribe/
├── apps/
│   ├── backend/          # FastAPI API + automation pipeline
│   └── frontend/         # Next.js admin UI
├── docker-compose.yml    # db + api + frontend
├── .github/workflows/    # CI (backend tests)
└── memory-bank/          # agent / project context
```

Each app owns its portable `Dockerfile`. Deploy uses **two** Vercel projects
on this same GitHub repo (different Root Directories).

## Quick start

```bash
cp .env.example .env   # fill secrets at repo root
```

**Full stack (Docker):**

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/health |
| Postgres | `localhost:5433` |

**Day-to-day development** (hot reload): start Postgres only, then run each
app on the host — see [backend](apps/backend/README.md#local-development) and
[frontend](apps/frontend/README.md#local-development).

## Deploy

| Vercel project | Root Directory | Runtime | Production |
|----------------|----------------|---------|------------|
| `vivecaribe` | `apps/backend` | Container | https://vivecaribe-alfareizas-projects.vercel.app |
| `vivecaribe-frontend` | `apps/frontend` | Next.js | (promote when ready) |

Ignored Build Step on each project skips builds when that app’s folder did
not change. Details: [backend deploy](apps/backend/README.md#deploy) ·
[frontend deploy](apps/frontend/README.md#deploy).

## Requirements

- Docker (Compose)
- Python **3.13+** + [uv](https://docs.astral.sh/uv/) — backend host runs
- Node.js **20+** — frontend host runs
