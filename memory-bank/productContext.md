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

### Partidos (football matches, `#61`–`#69`)

- Operators track matches (`equipo_local` vs `equipo_visitante`, campeonato,
  estadio, ciudad, fecha) independently of reservas; a reserva may optionally
  attach to one via `partido_id`.
- `/partidos` list groups upcoming (soonest first) above a "Partidos
  pasados" divider (most-recent-first); cards show temporal state (past
  greyed, today pulses orange) and a tiered reserva-count badge
  (gray → bronze → silver → gold at 0 / 1-2 / 3-4 / 5+).
- Creating a partido auto-checks for existing unassigned reservas matching
  its ciudad + calendar day and offers a one-click bulk-assign confirmation
  instead of linking reservas one by one.

### Gastos (partido-level expenses, `#81`)

- Operators register a partido's shared expenses by category (Comida
  y/o Snacks, Transporte, Boletas, Apoyos, Otros) once, from the
  Partido modal's collapsed-by-default "Gastos" section — no more
  manually computing and typing each reserva's individual `costos`.
- Each linked reserva's share is computed automatically, proportional
  to how many people are on that booking, and stays live as gastos,
  reserva links, or participant counts change afterward. A reserva's
  own modal shows its computed share (read-only — gastos are only
  edited from the partido side) so the operator can see exactly how
  much of the shared spend landed on that specific booking, and how it
  feeds that reserva's profit.
