# System patterns — ViveCaribe

## Architecture

API-first Clean Architecture with a compact layout:

- `domain/` — durable business types (`Reserva`, `User`, `EmailMessage`, errors).
- `application/auth/` — register/login use cases.
- `application/automation/` — pipeline + HTML extractors (`providers/`).
- `infrastructure/db/` — SQLAlchemy models/repos/session.
- `infrastructure/integrations/` — Gmail, Outlook, WhatsApp NoOp, Argon2/JWT.
- `api/` — thin FastAPI routers + `deps.py` composition root.
- Package-level `settings.py` and `logging.py`.

## Pipeline (automation BC)

Stages live in `ProcessBookingEmailsUseCase.start` (not a separate
`pipeline.py`):

1. Fetch messages (Gmail/Outlook adapters).
2. Extract via registry (`EXTRACTORS`).
3. Validate draft.
4. Persist `email_messages` + `reservas` (`get_or_create`).
5. Optional WhatsApp notify.
6. `mark_as_read` **only** when notify returns `True`.

## Persistence

| Table | Key |
|-------|-----|
| `users` | `email` unique |
| `email_messages` | `(source, mailbox_message_id)` |
| `reservas` | `(booking_provider, reserva_reference)` |

`body_html` is stored on `email_messages` (no separate HTML table).

## Auth pattern

- Public register/login.
- Protected routes use Bearer JWT (`get_current_user`).
- `CRON_SECRET` exists in Settings but is **not wired** into automation auth
  yet (JWT-only).

## Deviations from the original architecture plan

- No domain `Result` type — control flow uses exceptions (`DomainError`, etc.).
- No `domain/ports.py` / automation ports Protocols — concrete repos/adapters.
- Config file is `booking_providers.yaml` (not `accounts.yaml`).
- Entity/table naming uses `EmailMessage` / `email_messages`.
- Extractors live under `application/automation/providers/`.
