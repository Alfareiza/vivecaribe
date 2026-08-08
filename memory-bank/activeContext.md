# Active context — ViveCaribe

## Current focus

Issue **#38** — Next.js under `apps/frontend`, dual Vercel projects, per-app
Dockerfiles, Compose `db` + `api` + `frontend`. Branch
`feat/frontend-monorepo-deploy`.

## Recent decisions

### Dual Vercel + portable Docker (#38)

- **Two** Vercel projects, same GitHub repo:
  - `vivecaribe` → Root Directory `apps/backend` → Container
    (`Dockerfile.vercel`) + cron.
  - `vivecaribe-frontend` → Root Directory `apps/frontend` → Next.js native.
- Frontend on Vercel is **not** containerized; portable
  `apps/frontend/Dockerfile` is for Compose / AWS.
- Backend keeps container (Playwright/Chromium).
- Per-app Dockerfiles under `apps/{backend,frontend}/`; root Dockerfiles removed.
- Compose: `db` unchanged; `api` builds from `./apps/backend`; `frontend`
  on `:3000` with `NEXT_PUBLIC_API_URL`.
- Skip Unaffected Projects **not** used (no JS workspaces). Use **Ignored
  Build Step** / “changes in folder” per project.
- CI remains backend-only for this PR; frontend validated on Vercel preview.
- Frontend production deploy deferred until explicitly requested (preview OK).

### Monorepo (#36)

- Backend under `apps/backend/`; frontend was empty placeholder, now TailAdmin.
- Local OAuth/scratch scripts: leave alone (do not move).

### Reserva CRUD API (prior)

- Thin routers → `SqlAlchemyReservaRepository`; JWT on all `/reservas`.
- Soft delete via `deleted_at`; list `skip`/`limit`; PATCH business fields only.

### Zoho / extractors (prior)

- Zoho Playwright + search.do/md.do; OTP via GYG Gmail.
- Income formulas: GYG `* 0.7`, Homefans `* 0.75`, Viator net/1.31, Propio `= price`.

## Known gaps (intentional / deferred)

- Wire TailAdmin UI to live auth / reservas APIs.
- CORS allowlist for frontend origin on the API (when wiring starts).
- Real WhatsApp Meta integration (NoOp until Meta approval).
- Zoho `mark_as_read`; long-lived browser / skip Chromium on warm path.
- `correlation_id` ContextVar — no middleware sets it yet.
- Hourly Colombia-window cron needs Pro (Hobby is once/day).
- Per-user ownership / role scoping on reservas.

## Next

- Land #38 (CI green, Vercel Root Directories + Ignored Build Step).
- Ops: confirm API health + cron after Root Directory move.
- Later: connect UI to API; optional frontend CI job.
