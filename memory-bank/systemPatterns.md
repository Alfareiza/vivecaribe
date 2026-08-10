# System patterns — ViveCaribe

## Architecture

### Backend

API-first Clean Architecture under `apps/backend/src/vivecaribe/`:

- `domain/` — durable business types (`Reserva`, `User`, `EmailMessage`, errors).
- `application/auth/` — register/login use cases.
- `application/automation/` — pipeline + HTML extractors (`providers/`).
- `infrastructure/db/` — SQLAlchemy models/repos/session.
- `infrastructure/integrations/` — Gmail, Outlook, Zoho, WhatsApp NoOp, Argon2/JWT.
- `api/` — thin FastAPI routers + `deps.py` composition root.
- Package-level `settings.py` and `logging.py`.

### Frontend

Next.js 16 App Router under `apps/frontend/src/`:

- `app/` — routes (admin dashboard, auth pages, UI element demos).
- `components/` — TailAdmin UI primitives (forms, tables, charts, etc.).
- `components/ui/loading/` — shared pulse loaders (#50): `PulseLoader`,
  `PageLoading` (full viewport / `className` hatch), `InlineLoading`.
  Spanish `label` is required and screen-reader-only; `color` + `darkColor`.
- `layout/` — sidebar / header shell.
- `context/` — theme + sidebar + auth session gate.
- `output: 'standalone'` in `next.config.ts` for the portable Docker image.

### Monorepo deploy topology

```text
GitHub monorepo
├── apps/frontend  → Dockerfile (portable) + Vercel project (Next native)
├── apps/backend   → Dockerfile + Dockerfile.vercel + Vercel project (container)
└── docker-compose → db (Postgres 16) + api + frontend
```

Root no longer owns Docker/Vercel entrypoints. Cron lives in
`apps/backend/vercel.json`.

## Pipeline (automation BC)

Stages live in `ProcessBookingEmailsUseCase.start`:

1. Fetch messages (Gmail / Outlook / Zoho adapters).
2. Extract via registry (`EXTRACTORS`).
3. Validate draft.
4. Persist `email_messages` + `reservas` (`get_or_create`).
5. Optional WhatsApp notify.
6. `mark_as_read` **only** when notify returns `True` **and** the mailbox
   client implements `mark_as_read` (Gmail/Outlook). Zoho skips for now.

## Mailbox contract

```python
async def fetch_messages(*, query: str, max_results: int = 30) -> list[EmailMessage]
```

| mailbox_name | Auth | Notes |
|--------------|------|-------|
| `gmail` | OAuth token + refresh | Shared `GMAIL_CLIENT_*`; also Zoho OTP poller |
| `outlook` | MSAL refresh | Shared `OUTLOOK_CLIENT_*` |
| `zoho` | username + password | Playwright login + HTTP search.do/md.do |

### Zoho OTP coupling

When Zoho shows an identity email challenge, `ZohoSession` uses the
**GetYourGuide** Gmail mailbox from `booking_providers.yaml` to poll
`from:zohoaccounts.com` OTP mail. Session JSON under `APP_DATA_DIR` (or `~`).

## Extractor patterns

- Shared: phone → E.164; `get_pais_del_visitante` alpha-2 unless overridden.
- Homefans overrides country via `pycountry`.
- `price` vs `income` are provider-specific.

## Auth pattern

- Access JWT in browser **memory**; refresh token in **HttpOnly cookie** on
  the API origin (`POST /login`, `/refresh`, `/logout`). See #44/#45.
- `/reservas` and other operator routes: Bearer access JWT.
- Automation GET/POST: JWT **or** `CRON_SECRET`.
- Browser calls need `CORS_ORIGINS` + `credentials: "include"` (#41 Phase 1).
- Hobby Vercel Cron: daily `GET /automation/emails/get-bookings` at 09:00 UTC.

### Frontend session gate

- Client `(admin)` layout: boot `/refresh` or redirect `/signin`.
- No Next middleware JWT check (refresh cookie is on API host, not UI host).

## Persistence

| Table | Key |
|-------|-----|
| `users` | `email` unique |
| `refresh_tokens` | `token_hash` unique; `family_id` for rotation/reuse revoke |
| `email_messages` | `(source, mailbox_message_id)` |
| `reservas` | `(booking_provider, reserva_reference)`; soft delete via `deleted_at` |

## Deviations from the original architecture plan

- No domain `Result` type — exceptions (`DomainError`).
- No `domain/ports.py` Protocols — concrete repos/adapters.
- Config file is `booking_providers.yaml` (not `accounts.yaml`).
- Dual Vercel projects (not single container serving UI + API).
