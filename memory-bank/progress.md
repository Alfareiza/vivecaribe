# Progress — ViveCaribe

## Done

| Issue | Status | Summary |
|-------|--------|---------|
| #1 Scaffold | Closed | uv, Docker, Settings, logging, Sentry, health |
| #2 Domain core | Closed | Reserva, User, enums, DomainError hierarchy |
| #3 Persistence | Closed | SQLAlchemy models, Alembic, repositories |
| #4 Auth | Closed | `/users`, `/login`, Argon2, JWT |
| #5 Automation BC | Closed | Gmail/Outlook, extractors, pipeline, WhatsApp NoOp |
| #6 Pipeline API | Closed | `POST /automation/emails/get-bookings` |
| #7 Tests + docs | Closed | Coverage gate, CI, Memory Bank, README |

## In progress

| Issue | Status | Summary |
|-------|--------|---------|
| #8 Deploy | In progress | `Dockerfile.vercel`, GET+POST automation, Hobby daily cron |

## Works today

- Register/login and JWT-protected routes.
- Automation POST accepts JWT **or** `CRON_SECRET`; GET (cron) same auth, no body.
- Pipeline with GYG / Viator / Homefans extractors; Propio skeleton.
- Idempotent `email_messages` + `reservas` persistence.
- Isolated Postgres test suite with ≥ 90% statement coverage.
- Local Docker Compose Postgres + optional full API container.

## Left to build

- Finish issue **#8**: container deploy verification, runbook, PR smoke.
- Later: upgrade cron frequency (needs Pro) or refine schedule.
- Real WhatsApp Meta notifier after Meta authorization (replace NoOp).
- Propio HTML sample + extractor implementation.
- Optional future booking CRUD (explicitly out of #8).

## Known issues / deliberate non-goals

- No domain `Result` type (exceptions by design).
- WhatsApp stays NoOp until Meta approves.
- Local OAuth helper scripts / refresh token files must stay untracked.
