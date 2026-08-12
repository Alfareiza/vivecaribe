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
| #41 Phases 1–2 | Merged (#49) | CORS, sign-in, live GET `/reservas` |
| #50 Shared loading UI | Closed | PulseLoader / PageLoading / InlineLoading |
| #48 Detail modal share | Closed (#53) | WhatsApp / Google Calendar + modal UX |
| #46 List filters + es_hoy | Merged (#54) | Server filters, ReservaShortItem, Hoy badge |
| #55 Operator fields + paid_at | Merged (#56) | Domain/ORM/API + Alembic; derived `paid_at` |

## In progress / open children of #41

- #40 — Edit reserva (PATCH) from modal
- #47 — Sign Up / `POST /users` from UI (low priority)

## Works today

- Register/login; access JWT + refresh cookie rotation.
- Reserva CRUD; soft-delete hidden from get/list.
- `GET /reservas` server filters + slim list + `es_hoy`; detail by id.
- Operator/finance fields on create/update/detail; `paid_at` auto-derived.
- Admin UI: authenticated `/reservas` with server pagination/filters and
  Hoy badge; modal refetches full detail (UI edit of new fields still #40).
- Shared pulse loading for auth gate, reservas fetch, and sign-in submit.
- Automation POST accepts JWT **or** `CRON_SECRET`; GET (cron) same auth.
- Pipeline GYG / Viator / Homefans / Propio (Zoho); idempotent persistence.
- Isolated Postgres tests ≥ 90% coverage; frontend CI path-filtered build.
- Compose: Postgres + API + frontend.
- Migrate workflow on main applies Alembic when migrations change.

## Left to build

- Remaining #41 children (#40, #47).
- Real WhatsApp Meta notifier after Meta authorization.
- Zoho mark-as-read (deferred).
- Optional: per-user ownership on reservas.

## Known issues / deliberate non-goals

- No domain `Result` type (exceptions by design).
- WhatsApp stays NoOp until Meta approves.
- Local OAuth helper scripts / refresh token files must stay untracked.
- Homefans `get_income` still has a rough error path — watch in production.
- Single-container UI+API on Vercel rejected (#38): dual projects.
