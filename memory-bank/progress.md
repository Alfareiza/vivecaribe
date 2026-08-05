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
| #7 Tests + docs | In progress | Coverage gate, CI, Memory Bank, README |

## Works today

- Register/login and JWT-protected automation endpoint.
- Pipeline with GYG / Viator / Homefans extractors; Propio skeleton.
- Idempotent `email_messages` + `reservas` persistence.
- Isolated Postgres test suite with ≥ 90% statement coverage.
- Local Docker Compose Postgres + optional full API container.

## Left to build

- Issue **#8**: Vercel cron schedule, Dockerfile.vercel polish, production
  cron auth (`CRON_SECRET` or equivalent).
- Real WhatsApp Meta notifier (replace NoOp).
- Propio HTML sample + extractor implementation.
- Optional future booking CRUD endpoints under `application/bookings/`.

## Known issues

- Automation accepts JWT only (cron cannot call without a user token yet).
- No domain `Result` type (exceptions used instead).
- Local OAuth helper scripts / refresh token files must stay untracked.
