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

Root no longer owns Docker/Vercel entrypoints. The API container does not
run Vercel Cron; ingest is triggered by HTTP callers with `CRON_SECRET`.

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
- Ingest: authenticated `GET`/`POST /automation/emails/get-bookings`.
  Production API Vercel Authentication is preview-only so external schedulers
  can reach FastAPI; the GET is still gated by `CRON_SECRET`.

### Frontend session gate

- Client `(admin)` layout: boot `/refresh` or redirect `/signin`.
- No Next middleware JWT check (refresh cookie is on API host, not UI host).

## Reservas list / detail API (#46)

- `GET /reservas` — filters: `estado`, `booking_provider`,
  `fecha_evento_from` / `fecha_evento_to` (AND; Bogota calendar days via SQL
  `timezone('America/Bogota', fecha_evento)::date`; null fecha excluded when
  ranged). Order: `fecha_evento` desc nulls last. Items: slim
  `ReservaShortItem` (+ computed `es_hoy`).
- `GET /reservas/{id}` — full `ReservaResponse` (inherits domain `Reserva`,
  excludes `deleted_at`, computed `es_hoy`).
- Indexes: `estado`, `booking_provider`, `fecha_evento` (plus existing).
- Frontend: server pagination/filters; “Hoy” badge from `es_hoy`; modal
  refetches by id. `StatusDot` kept for future badge kinds.

## Reserva derived fields (#55)

- Persistable fields that are pure functions of other attributes live on the
  domain model, not in routers: `@model_validator(mode="after")` syncs them;
  `model_copy` re-validates so PATCH stays consistent.
- `paid_at` ← `booking_provider` + `fecha_evento` (America/Bogota). Callers
  use `Reserva(**data)` / `model_copy(update=...)` without computing it.
- New enums: `TipoTour`, `MeetingPoint` (literal phrase values). Operator
  notes/finance columns nullable except `menores_de_edad` (default false).

## Partidos (`#61`–`#69`)

- Domain `Partido`: `equipo_local`/`equipo_visitante` (≤25 chars),
  `nombre_campeonato` (`Campeonato` enum), `estadio` (`Estadio` enum),
  `ciudad` (`Ciudad` enum — mirrors `apps/frontend/src/types/partido.ts`'s
  `CIUDAD_OPTIONS`, add new cities on both sides), `fecha`. Soft delete via
  `deleted_at`. One-to-many with `Reserva` via nullable `reservas.partido_id`
  FK (`ondelete="SET NULL"`) — the relationship is informational only,
  linking happens from the `Reserva` side (`PATCH /reservas/{id}`).
- `GET /partidos` (`PartidoShortItem`) — filters `ciudad` (substring,
  case-insensitive), `fecha_from`/`fecha_to`, `q` (equipo_local /
  equipo_visitante / ciudad). Returns `reservas_count` per item via a single
  `LEFT JOIN ReservaORM ... GROUP BY partido.id` query — **the non-deleted
  filter on reservas lives in the JOIN's ON clause, not WHERE**; putting it
  in WHERE was a real bug (#66) that dropped a partido from the list
  entirely if all its reservas were soft-deleted, instead of just zeroing
  its count. Repository returns plain dicts (partido fields + count) so the
  router stays a one-line `PartidoShortItem.model_validate(item)` — no
  bespoke `context=` needed.
- `GET /partidos/{id}` (`PartidoResponse`) — embeds full linked `reservas`
  (non-deleted, via `ReservaRepo.list_by_partido`).
- `GET /reservas` gained `ciudad` (exact, case-insensitive match on
  `ciudad_experiencia`) and `unassigned_only` (`partido_id IS NULL`)
  filters (#68/#69), used for the auto-match-on-create flow below —
  reused rather than adding a dedicated `/partidos/{id}/candidate-reservas`
  endpoint.

### Frontend patterns worth reusing

- **Date state**: `getDateState()` in `reservationUtils.ts` classifies an
  ISO string as `past`/`today`/`future` by comparing raw Y-M-D against
  today in America/Bogota — same "naive wall-clock" convention as
  `formatRawDateTime`/`toLocalDateKey`. Drives both partido card styling
  and the upcoming/past list split.
- **Uncontrolled `<Select>` + derived state**: this codebase's `Select`
  component only accepts `defaultValue` (no controlled `value`). When code
  needs to programmatically change a Select after mount (ciudad/estadio
  auto-select from `equipo_local`, or the create→existing-partido
  transition), the fix is a `key={...}` on the Select tied to the value
  that should force a resync — not switching to `value=`, which errors.
- **Bridging create→existing without parent involvement**: `PartidoModal`
  computes `effectiveId = partidoId ?? detail?.id ?? null` and
  `displayAsExisting = effectiveId !== null`. This lets the modal render
  as "existing partido" (title, delete button, linked reservas) right
  after a successful create — before the parent grid's `selectedId` prop
  ever changes — by setting `detail` locally from the create response.
  The original prop-driven `isCreate` is kept only for the effect that
  decides reset-vs-fetch on open, so it doesn't refire mid-flow.
- **Bulk-assign UX without a bulk endpoint**: `PartidoMatchedReservasModal`
  fires individual `PATCH /reservas/{id}` via `Promise.allSettled`. On
  partial failure it merges succeeded rows into the parent immediately,
  drops them from its own list, and keeps only failed rows + an inline
  `role="alert"` error for retry — no toast system in this app, so errors
  are always inline banners, never toasts.
- **Public SVG icons**: reusable icons live in `public/images/icons/*.svg`
  and are referenced via `next/image`, not inlined/SVGR-imported — this
  trades away `currentColor` theming (the icon renders at a fixed color,
  not tinted by sidebar active/hover state or badge tier) for a single
  source-of-truth file. `src/icons/*.svg` (SVGR, `currentColor`-themed) is
  the older pattern for icons that predate this decision.

## Persistence

| Table | Key |
|-------|-----|
| `users` | `email` unique |
| `refresh_tokens` | `token_hash` unique; `family_id` for rotation/reuse revoke |
| `email_messages` | `(source, mailbox_message_id)` |
| `reservas` | `(booking_provider, reserva_reference)`; soft delete via `deleted_at`; operator/finance + `paid_at` (#55); nullable `partido_id` FK `SET NULL` (#61) |
| `partidos` | soft delete via `deleted_at`; indexed on `fecha`, `ciudad` (#61) |

## Deviations from the original architecture plan

- No domain `Result` type — exceptions (`DomainError`).
- No `domain/ports.py` Protocols — concrete repos/adapters.
- Config file is `booking_providers.yaml` (not `accounts.yaml`).
- Dual Vercel projects (not single container serving UI + API).
