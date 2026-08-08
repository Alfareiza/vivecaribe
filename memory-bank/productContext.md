# Product context — ViveCaribe

## Why it exists

Booking confirmations arrive as HTML emails across Gmail, Outlook, and Zoho
inboxes.
Manual parsing is slow and error-prone. ViveCaribe turns those emails into
structured reservations operators can trust, while remaining an API platform
(not a one-off script).

## How it should work

1. Operator (`POST` + JWT/body) or Vercel Cron (`GET` + `CRON_SECRET`)
   calls `/automation/emails/get-bookings`.
2. Pipeline fetches unread/matching messages per `booking_providers.yaml`.
3. Provider-specific extractors map HTML → `ReservaDraft` → `Reserva`
   (`pais_del_visitante` as ISO alpha-2; `price`/`income` per channel).
4. Idempotent persistence on `(booking_provider, reserva_reference)`.
5. WhatsApp notify is optional; with NoOp, emails stay unread for reprocessing.

## UX goals

### API consumers

- Predictable auth (`POST /users`, `POST /login` → Bearer JWT).
- Reserva CRUD under `/reservas` (JWT; soft delete; paginated list).
- Structured pipeline counters (`fetched`, `created`, `existing`, `notified`).
- Clear env docs (`.env.example`) and Memory Bank for future agents.
- Safe local tests that never touch the developer Postgres database.
- Clear monorepo layout (`apps/backend` vs `apps/frontend`).

### Frontend (operators)

- Admin dashboard for day-to-day booking operations (layouts, tables, charts
  from TailAdmin starter under `apps/frontend`).
- Talks to the API via `NEXT_PUBLIC_API_URL` (not embedded in the API image).
- Local: `npm run dev` or Compose `frontend` on `:3000`.
- Production: separate Vercel project from the API.
