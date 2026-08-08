# Progress — ViveCaribe

## Done

| Issue / track | Status | Summary |
|---------------|--------|---------|
| #1 Scaffold | Closed | uv, Docker, Settings, logging, Sentry, health |
| #2 Domain core | Closed | Reserva, User, enums, DomainError hierarchy |
| #3 Persistence | Closed | SQLAlchemy models, Alembic, repositories |
| #4 Auth | Closed | `/users`, `/login`, Argon2, JWT |
| #5 Automation BC | Closed | Gmail/Outlook, extractors, pipeline, WhatsApp NoOp |
| #6 Pipeline API | Closed | `POST /automation/emails/get-bookings` |
| #7 Tests + docs | Closed | Coverage gate, CI, Memory Bank, README |
| #8 Deploy | Closed / verify | `Dockerfile.vercel`, GET+POST automation, Hobby daily cron |
| Propio + Zoho | Merged on main | HTTP search/md, PropioExtractor, YAML |
| Zoho OTP + data dir | Merged | GYG Gmail OTP poller; `APP_DATA_DIR` sessions; Docker harden |
| Extractor income/country | Merged | Shared phone→alpha-2; GYG/Homefans/Viator formulas |
| #25 POST /reservas | Closed (PR #26) | Create + schemas/deps/router scaffolding |
| #27 GET /reservas/{id} | Closed (PR #28) | Fetch one reservation |
| #29 GET /reservas | Closed (PR #30) | Paginated list (`skip`/`limit`) |
| #31 PATCH /reservas/{id} | Closed (PR #32) | Partial update of business fields |
| #33 DELETE /reservas/{id} | Closed (PR #34) | Soft delete via `deleted_at` |
| #36 Monorepo layout | In progress | `apps/backend` + empty `apps/frontend`; root Docker/Vercel |

## In progress

- #36 — move API under `apps/backend`, empty frontend placeholder, CI/docs.

## Works today

- Register/login and JWT-protected routes.
- Reserva CRUD: `POST/GET/PATCH/DELETE /reservas` (+ paginated list).
- Soft-deleted reservas are hidden from get/list.
- Automation POST accepts JWT **or** `CRON_SECRET`; GET (cron) same auth, no body.
- Pipeline with GYG / Viator / Homefans / Propio (Zoho) extractors.
- Zoho free-tier: Playwright login + search.do/md.do; OTP via GYG Gmail when challenged.
- Idempotent `email_messages` + `reservas` persistence.
- Isolated Postgres test suite with ≥ 90% statement coverage.
- Local Docker Compose Postgres + optional full API container.

## Left to build

- Next.js scaffold in `apps/frontend` (+ decide static-export vs other
  single-container approach later).
- Real WhatsApp Meta notifier after Meta authorization (replace NoOp).
- Zoho mark-as-read (deferred).
- Optional: skip Chromium launch on warm Zoho path.
- Optional: per-user ownership / filters on reservas.

## Known issues / deliberate non-goals

- No domain `Result` type (exceptions by design).
- WhatsApp stays NoOp until Meta approves.
- Local OAuth helper scripts / refresh token files must stay untracked.
- Zoho free accounts have no IMAP/API — Playwright login only; mail via
  search.do / md.do (`context.request`).
- Homefans `get_income` still has a rough error path (logs + empty return) —
  watch in production.
