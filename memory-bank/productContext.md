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
3. Provider-specific extractors map HTML → `ReservaDraft` → `Reserva`.
4. Idempotent persistence on `(booking_provider, reserva_reference)`.
5. WhatsApp notify is optional; with NoOp, emails stay unread for reprocessing.

## UX goals for API consumers

- Predictable auth (`POST /users`, `POST /login` → Bearer JWT).
- Structured pipeline counters (`fetched`, `created`, `existing`, `notified`).
- Clear env docs (`.env.example`) and Memory Bank for future agents.
- Safe local tests that never touch the developer Postgres database.
