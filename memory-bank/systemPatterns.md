# System patterns — ViveCaribe

## Architecture

API-first Clean Architecture with a compact layout:

- `domain/` — durable business types (`Reserva`, `User`, `EmailMessage`, errors).
- `application/auth/` — register/login use cases.
- `application/automation/` — pipeline + HTML extractors (`providers/`).
- `infrastructure/db/` — SQLAlchemy models/repos/session.
- `infrastructure/integrations/` — Gmail, Outlook, Zoho, WhatsApp NoOp, Argon2/JWT.
- `api/` — thin FastAPI routers + `deps.py` composition root.
- Package-level `settings.py` and `logging.py`.

## Pipeline (automation BC)

Stages live in `ProcessBookingEmailsUseCase.start` (not a separate
`pipeline.py`):

1. Fetch messages (Gmail / Outlook / Zoho adapters).
2. Extract via registry (`EXTRACTORS`).
3. Validate draft.
4. Persist `email_messages` + `reservas` (`get_or_create`).
5. Optional WhatsApp notify.
6. `mark_as_read` **only** when notify returns `True` **and** the mailbox
   client implements `mark_as_read` (Gmail/Outlook). Zoho skips for now.

## Mailbox contract

All mailbox clients expose:

```python
async def fetch_messages(*, query: str, max_results: int = 30) -> list[EmailMessage]
```

Zoho-specific knobs (`folder_name`, `time_window`) are **class defaults**, not
YAML fields — YAML only supplies the subject query string.

| mailbox_name | Auth | Notes |
|--------------|------|-------|
| `gmail` | OAuth token + refresh | Shared `GMAIL_CLIENT_*` |
| `outlook` | MSAL refresh | Shared `OUTLOOK_CLIENT_*` |
| `zoho` | username + password | Playwright login + HTTP search.do/md.do |

## Persistence

| Table | Key |
|-------|-----|
| `users` | `email` unique |
| `email_messages` | `(source, mailbox_message_id)` |
| `reservas` | `(booking_provider, reserva_reference)` |

`body_html` is stored on `email_messages` (no separate HTML table).

## Auth pattern

- Public register/login.
- Most protected routes use Bearer JWT (`get_current_user`).
- Automation GET/POST accept Bearer JWT **or** Bearer `CRON_SECRET`
  (`require_jwt_or_cron`, constant-time compare). Cron returns no `User`.
- `GET` runs defaults (all providers, `notify=false`); `POST` accepts body.
- Hobby Vercel Cron: daily `GET /automation/emails/get-bookings` at 09:00 UTC.

## Deviations from the original architecture plan

- No domain `Result` type — deliberately dropped; exceptions (`DomainError`).
- No `domain/ports.py` / automation ports Protocols — concrete repos/adapters.
- Config file is `booking_providers.yaml` (not `accounts.yaml`).
- Entity/table naming uses `EmailMessage` / `email_messages`.
- Extractors live under `application/automation/providers/`.
- Vercel Cron uses GET + `CRON_SECRET`; POST remains for operators with body.
