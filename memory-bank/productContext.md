# Product context — ViveCaribe

## Why it exists

Booking confirmations arrive as HTML emails across Gmail, Outlook, and Zoho
inboxes.
Manual parsing is slow and error-prone. ViveCaribe turns those emails into
structured reservations operators can trust, while remaining an API platform
(not a one-off script).

## How it should work

1. Operator (`POST` + JWT/body) or an external scheduler (`GET` +
   `CRON_SECRET`) calls `/automation/emails/get-bookings`.
2. Pipeline fetches unread/matching messages per `booking_providers.yaml`.
3. Provider-specific extractors map HTML → `ReservaDraft` → `Reserva`
   (`pais_del_visitante` as ISO alpha-2; `price`/`income` per channel).
4. Idempotent persistence on `(booking_provider, reserva_reference)`.
5. WhatsApp notify is optional; with NoOp, emails stay unread for reprocessing.

## UX goals

### API consumers

- Predictable auth (`POST /users`, `POST /login` → Bearer JWT).
- Reserva CRUD under `/reservas` (JWT; soft delete; filtered/paginated list
  with slim items + `es_hoy`; full detail by id including operator/finance
  fields and domain-derived `paid_at`).
- Structured pipeline counters (`fetched`, `created`, `existing`, `notified`).
- Clear env docs (`.env.example`) and Memory Bank for future agents.
- Safe local tests that never touch the developer Postgres database.
- Clear monorepo layout (`apps/backend` vs `apps/frontend`).

### Frontend (operators)

- Admin dashboard for day-to-day booking operations (TailAdmin under
  `apps/frontend`).
- Auth: email/password sign-in; access token in memory; refresh via HttpOnly
  cookie on the API; live `/reservas` list with server filters + `es_hoy`
  (epic #41 through #46 / #54).
- Loading UX: shared pulse spinner (page / inline / button); Spanish labels
  for assistive tech only.
- Talks to the API via `NEXT_PUBLIC_API_URL` with credentialed CORS
  (`CORS_ORIGINS` on the API).
- Local: `npm run dev` or Compose `frontend` on `:3000`.
- Production: https://vivecaribe-frontend.vercel.app (separate Vercel project).
