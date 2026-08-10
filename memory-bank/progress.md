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
| Propio + Zoho | Merged | HTTP search/md, PropioExtractor, YAML |
| Zoho OTP + data dir | Merged | GYG Gmail OTP poller; `APP_DATA_DIR` sessions |
| Extractor income/country | Merged | Shared phone→alpha-2; provider income formulas |
| #25–#33 Reserva CRUD | Closed | POST/GET/PATCH/DELETE + paginated list |
| #36 Monorepo layout | Closed | `apps/backend` + frontend placeholder |
| #38 Dual Vercel / frontend app | Closed | Next in `apps/frontend`, Compose frontend |
| #42 Phase 0 list UI | Closed | `/reservas` mock table + frontend CI (PR #43) |
| #44 / #45 Refresh tokens | Closed | Opaque refresh + HttpOnly cookie; `/refresh` `/logout` |
| #41 Phases 1–2 | PR #49 | CORS, sign-in, live GET `/reservas` |

## In progress / open children of #41

- #40 — Edit reserva (PATCH) from modal
- #46 — Server-side filters on `GET /reservas`
- #47 — Sign Up / `POST /users` from UI (low priority)
- #48 — Detail modal UX + share (WhatsApp / Google Calendar)
- #50 — Shared loading UI (replace temporary text states)

## Works today

- Register/login; access JWT + refresh cookie rotation.
- Reserva CRUD + paginated list; soft-delete hidden from get/list.
- Admin UI: authenticated `/reservas` against live API (after #49 merge).
- Automation POST accepts JWT **or** `CRON_SECRET`; GET (cron) same auth.
- Pipeline GYG / Viator / Homefans / Propio (Zoho); idempotent persistence.
- Isolated Postgres tests ≥ 90% coverage; frontend CI path-filtered build.
- Compose: Postgres + API + frontend.

## Left to build

- Remaining #41 children (#40, #46–#48, #50).
- Real WhatsApp Meta notifier after Meta authorization.
- Zoho mark-as-read (deferred).
- Optional: per-user ownership on reservas.

## Known issues / deliberate non-goals

- No domain `Result` type (exceptions by design).
- WhatsApp stays NoOp until Meta approves.
- Local OAuth helper scripts / refresh token files must stay untracked.
- Homefans `get_income` still has a rough error path — watch in production.
- Single-container UI+API on Vercel rejected (#38): dual projects.
