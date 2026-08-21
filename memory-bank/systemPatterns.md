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

### Reserva financiero: trm_estimado/trm_final, income_final (#78/#79, PR #80)

- Same `model_validator(mode="after")` pattern as `paid_at`, chained:
  `_sync_income_final` (moneda/income/`trm_final` → `income_final`) is
  defined *before* `_sync_profit` (`income_final`/`costos` → `profit`,
  `percentage_profit`) in the class body — Pydantic v2 runs `mode="after"`
  validators in definition order, so `_sync_profit` sees the freshly
  computed `income_final` on the same pass. `compute_profit()` takes
  `income_final` + `costos` directly now, not moneda/income/rate — the
  currency branching lives in exactly one place (`compute_income_final`).
- `trm_estimado` is "settable once": writable via `ReservaUpdate` only to
  fill a still-`null` value; the router (`update_reserva`) pops it from
  the update dict when `existing.trm_estimado is not None` before
  building the patch, rather than raising — a silent no-op mirrors what
  the disabled frontend input already communicates, instead of adding a
  second source of truth (a 409/422) for the same rule.
- Renaming a live DB column: `op.alter_column(table, old, new_column_name=new)`
  in its own migration, not a drop+add — preserves data. Don't touch the
  historical migration that originally created the column under its old
  name; it stays accurate to what actually happened at that point in
  history.
- **Numeric-input sanitization**: `sanitizeDecimalInput()` in
  `ReservationDetailModal.tsx` strips everything but digits and a single
  `.` on every `onChange` (collapses extra `.`s instead of rejecting the
  keystroke) — applied to any field that's a plain rate/cost, not a
  Precio/Ingreso-style value with its own existing conventions.
- **Race found via Playwright, not by a human typing**: a field whose
  *displayed* value flips between raw (focused) and formatted (blurred)
  via `useState` is unsafe against any bulk value-set — paste, browser
  autofill, or a test tool's `.fill()` — because the external write can
  land mid-transition and get silently doubled by React reconciling
  against a stale DOM value. Fixed by dropping the focus-toggle
  reformatting entirely for `trm_estimado`/`trm_final`/`costos` (always
  show the raw sanitized string). `income_estimado`'s pre-existing
  create-mode toggle (#72) was left alone — out of scope, but carries
  the same theoretical risk.
- **Signaling "derived, not editable"**: a `disabled` `Input` +
  `React.ReactNode` label with a muted "(calculado)" suffix (`FormField`
  widened from `label: string` in this file only — it's a local
  component, no other callers) reads far more honestly than a plain
  enabled-looking input the operator technically shouldn't type into.
  `income_final` specifically has no `FormState` field at all — it's
  computed inline at render time from `form.income`/`form.trm_final`
  since it's display-only and never part of the PATCH payload.
- **Resumen (view mode) hierarchy**: `StatCard` component (label / big
  or small value / optional caption) replaces a flat `dl` list — a hero
  row (`Ingreso final`, `Profit`) at `text-title-sm font-bold` plus a
  secondary row (`Ingreso`, `Ingreso estimado`, `Costos`) at smaller/
  muted weight, `grid-cols-1 sm:grid-cols-2/3` for mobile-to-desktop.
  A percentage read as a `Badge` (green/red, reusing the
  `EcommerceMetrics.tsx` KPI convention) merged into the amount card it
  qualifies reads better than a separate progress-bar card — a bar
  implies "progress toward a goal," a margin percentage isn't one.
  Empty/pending values render a bare "—" at whatever size the slot is;
  a full sentence ("Pendiente de pago") at hero type size reads as a
  layout bug, not a status — push the explanation into the small
  caption line instead.

## Reservas Create/Edit/Delete (`#40`/`#41`/`#70`, PR #71)

- `ReservationDetailModal` is the single component for view, create, and
  edit — `createMode` prop opens a blank form (skips the
  `GET /reservas/{id}` fetch); `isEditing` state toggles the read-only
  detail view into an edit form seeded from `detail`. `handleDelete`
  mirrors `PartidoModal.handleDelete`: `window.confirm` then `DELETE`;
  `onSaved`/`onDeleted` callback props let the parent table refetch.
- `reserva_reference` (create only) is generated client-side as
  `{provider[:2].upper()}-{ddmmyy}-{3-char random suffix}`; `handleSave`
  retries up to 5x with a fresh suffix on an actual 409, so a same-day/
  same-provider collision resolves transparently instead of dead-ending
  (the field isn't shown/editable in the UI, so a bare 409 with no retry
  left the operator stuck).
- Validation now matches the DB columns exactly: `max_length` on every
  base string field in `ReservaCreate`/`ReservaUpdate` (previously only
  the #55 operator fields had it — overflow on `phone`/`customer_name`/
  `moneda`/etc. used to 500, not 422). `price`/`income` are `gt=0`.
  `phone` must start with `+` when non-empty — validated only on the
  Create/Update schemas, not the domain model or
  `ReservaResponse`/`ReservaShortItem`, so reading existing non-`+`
  records (automation pipeline data, pre-migration rows) is unaffected.
- New providers `vayara`/`otro`/`airbnb` on `BookingProvider` — plain
  `StrEnum` + `VARCHAR`, so adding one is a one-line change (same pattern
  as `Ciudad`). Vayara has a `paid_at` formula (same day as
  `fecha_evento`); Otro/Airbnb fall through the existing
  "no formula defined" `None` branch.
- `sender`/`subject`/`fecha_email_recibido` are nullable (migration
  `a8b9c0d1e2f3`) so a manually-created reserva can honestly have no
  source-email metadata; the automation pipeline always supplies real
  values regardless, so this doesn't change pipeline behavior.
- País: free-text `<input list=...>` + `<datalist>` sourced from the
  `world-countries` npm package (`apps/frontend/src/lib/countries.ts`),
  not a `<Select>` — lets the operator search/type any country without a
  closed-option list, stores the typed string as-is (no alpha-2
  conversion; that's pipeline-only, via `pycountry`).
- Generic `InfoHint` (`components/ui/tooltip/InfoHint.tsx`): "i" icon +
  hover/focus tooltip, `align: "center" | "right"` (default center).
  Only right-align a field whose icon actually sits at the container's
  right edge — defaulting every tooltip to right-align just moves the
  clipping risk to fields further left in the same row.

### Partido linking + income auto-fill on create (`#72`, PR #73)

- Create-mode-only "Partido" section: "+ Buscar partido" (disabled
  until Ciudad + Fecha del evento are set) calls the same
  `fetchPartidos` as the edit-mode `PartidoSelector`, via a 60s
  module-level cache (`partidoLookupCache` in
  `ReservationDetailModal.tsx`, keyed by `ciudad|from|to`) so mashing
  the button doesn't repeat the request. Results are a clickable list
  (hover shows a "Vincular" affordance — a plain list read as unclear
  in QA); single-select since `reservas.partido_id` is one FK, not
  many-to-many. Selection lives in local `selectedPartido` state (not
  `FormState`, since it holds a full `PartidoListItem` for display) and
  is sent as `partido_id` only in the create payload — no PATCH, unlike
  `PartidoSelector` which needs an existing reserva id.
  `dayWindow`/`partidoLabel` moved from `PartidoSelector.tsx` (private)
  to `reservationUtils.ts` (shared) since both pickers need them now.
- **Derived-field-with-override pattern**: Ingreso derives from Precio ×
  `INCOME_RATE_BY_PROVIDER[booking_provider]`; Ingreso estimado derives
  from Ingreso (direct copy if Moneda=COP, else a live TRM fetch). Both
  use a per-field boolean "touched" flag set *only* inside that field's
  own `onChange` (never by the auto-fill `useEffect` itself), so the
  effect's own `update()` calls don't self-trip the flag. Once touched,
  the effect no-ops on further upstream changes — lets an operator
  correct a value without the form fighting them. Create-mode only;
  editing an existing reserva never re-derives these.
- `apps/frontend/src/lib/trm.ts` (`fetchTrmToCop`): free
  `cdn.jsdelivr.net` currency API, per-currency in-memory
  `Map<string, Promise<number>>` cache (dedupes concurrent/repeated
  calls; evicts on failure so a transient error doesn't poison the
  cache for the rest of the session). Used by both the create form and
  the view-mode Resumen fallback (below). The TRM-driven auto-fill
  effect is debounced 500ms — Precio is typed keystroke-by-keystroke,
  which cascades into Ingreso and then this effect, so without the
  debounce it fires one HTTP request per keystroke.
- Fixed a real bug in the read-only Resumen "Ingreso est." row: it
  unconditionally recomputed from the old `TRM_COP_PLACEHOLDER = 4000`
  constant, ignoring any already-stored `income_estimado`. Now: stored
  value (no fetch) → COP passthrough → live fetch, in that order, and
  only reservas with a `null` `income_estimado` (pre-#73 or pipeline
  records) trigger the fetch. `TRM_COP_PLACEHOLDER`/`estimateIncomeCOP`/
  `formatNumberCO` removed as dead code once this landed.
- Reusable `Input` `prefix` prop (`components/form/input/InputField.tsx`):
  static left-edge label inside the input's own border (`pl-14` +
  absolutely-positioned span with a right border) — same visual idea as
  a phone field's country-code chip. Used for Ingreso estimado's "COP"
  tag; putting the currency in the *label* instead (`"Ingreso estimado
  (COP)"`) wrapped the label text and threw off row alignment.
- `formatPlainNumberCO()` in `reservationUtils.ts`: es-CO thousands/decimal
  formatting (`544.252.161,08`) for a plain editable amount field —
  shown while the input is unfocused, swapped for the raw digit string
  on focus (via a local `incomeEstimadoFocused` state) so the operator
  edits a normal parseable number, not a formatted string. Scoped to
  Ingreso estimado only (always COP); Precio/Ingreso vary by Moneda so
  they stay unformatted.

### Gotchas found this round

- **Tailwind v4 arbitrary values don't reliably support `fr` inside
  `calc()`** for `grid-template-columns` in this project's browser
  target — confirmed the browser itself rejects
  `el.style.gridTemplateColumns = "calc(1fr - 5px) ..."` outright (not a
  Tailwind-compilation issue; plain `calc(100% - Npx) 100px` works fine
  via the same API). For asymmetric grid/flex sizing, use a fixed
  `calc(100% - Npx)` on a plain block element, or a fixed pixel width on
  one flex item with `flex-1` on the rest — not `fr` + `calc` together.
- A native `datetime-local` input needs real fixed width (e.g.
  `sm:w-[220px]`) to avoid the browser's calendar icon covering the
  minutes; equal-thirds grid columns weren't wide enough.
- Don't run `npm run build` (production) while `next dev --turbopack` is
  running against the same `.next` directory — it corrupts Turbopack's
  shared cache and the dev server can silently serve stale HMR output
  for specific edits (confirmed: the compiled bundle had the new code,
  but the live DOM didn't reflect it, in a fresh browser tab, even after
  reload). If HMR seems to stop reflecting a change, restart the dev
  server (and clear `.next/cache`) rather than assuming the edit is
  wrong. Stick to `eslint` + browser reload for verification while a dev
  server is running.

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

## Gastos: partido-level expenses split across reservas (#81)

- `Gasto` (`domain/gasto.py`): `partido_id` + `categoria`
  (`GastoCategoria` StrEnum: Comida y/o Snacks, Transporte, Boletas,
  Apoyos, Otros) + `monto`, DB-unique on `(partido_id, categoria)` — at
  most one amount per category per partido, not a repeatable line-item
  list. `gasto_reserva_splits` persists each linked reserva's share
  (`gasto_id`, `reserva_id`, `monto`), FK `ondelete="CASCADE"` on both.
- **Recompute is centralized, not per-repository**: a single
  module-level `_recompute_gasto_splits(session, partido_id)` in
  `infrastructure/db/repositories.py` — deletes and reinserts every
  split row for the partido's gastos (cheap at ≤5 gastos), shares each
  proportional to `participants` among non-deleted linked reservas,
  and sets each reserva's `costos` = sum of its shares (or `None` when
  the partido has zero gastos, not `0` — those are different facts).
  Called from `SqlAlchemyGastoRepository.upsert`/`delete` **and**
  `SqlAlchemyReservaRepository.save`/`soft_delete` — a cross-aggregate
  concern doesn't belong owned by either repository alone.
- `Reserva.costos` dropped from `ReservaCreate`/`ReservaUpdate` — it's
  derived, matching the `paid_at`/`income_final` "computed, not
  client-writable" convention from #55/#78, but computed by a
  repository-level recompute instead of a domain `model_validator`
  (it depends on sibling reservas across the partido, which a single
  entity's own validator can't see).
- `SqlAlchemyReservaRepository.save()` must explicitly null `costos`
  whenever a reserva ends up with `partido_id is None` — the
  post-unlink recompute call only updates reservas *still* linked to
  the old partido, so the just-unlinked row needs its own direct reset
  or it goes stale (real bug, found via manual PATCH testing, not
  caught by the original test suite before #81's tests were added).
- **`categoria` is a query param, not a path segment** on
  `PUT`/`DELETE /partidos/{id}/gastos` — "Comida y/o Snacks" contains a
  literal `/`, which breaks path-segment routing even percent-encoded
  (`%2F`): ASGI servers decode it before route matching. Any future
  closed-value field whose display text might contain `/` should default
  to a query param if it needs to appear in a URL at all.
- Frontend: collapsed-by-default dropdown (header = label + `Total $X`
  `Badge` + `AngleDownIcon`), reusing `ReservationDetailModal`'s
  pre-existing `CollapsibleMetadata` visual language for both the
  Partido (editable) and Reserva (read-only) instances. `inert={!open}`
  on the collapsed panel keeps it out of tab order — `CollapsibleMetadata`
  itself doesn't do this yet (pre-existing gap, left alone). Chevron
  rotation is **not** always `rotate-180`: this feature uses `-rotate-90`
  (down → right) per explicit user preference, so don't assume every
  new collapsible in this app wants the up-flip.
- Editable Gastos rows (Partido modal) are a compact single-row list
  (icon chip + label + input), each auto-saving independently on blur;
  a whole-number `sanitizeIntegerInput`/`formatIntegerCO` pair (no `.`
  accepted) instead of the decimal-aware helpers used elsewhere, backed
  by a small dedicated `<input>` (not the shared `Input` component,
  which hardcodes `h-11`). The proportion-of-total indicator is a thin
  bar drawn on the row's own bottom divider (`absolute inset-x-0
  bottom-0 h-0.5`, width = share%) — adds no extra layout height, unlike
  an earlier card-grid version that gave each category its own
  label-row + input-row + bar-row and pushed the modal title off-screen
  on shorter viewports.
- **Per-field auto-save reseed race**: don't reseed *every* field's
  local draft from a fresh server response on every save — a
  `useEffect` keyed on the whole `detail` object re-ran on each
  individual field's save round-trip and could silently overwrite a
  sibling field's still-unsaved in-progress draft with its last-
  committed value. Key the reseed on a stable id (`detail?.id`, fires
  once per loaded entity) and have the save handler patch only its own
  field from its own response.
- **Coverage tool gotcha (project-wide, not gasto-specific)**:
  `[tool.coverage.run]` needs `concurrency = ["greenlet", "thread"]`
  when SQLAlchemy's async engine is in play — its greenlet-based DBAPI
  bridge isn't followed by coverage.py's default thread-only trace hook,
  which was silently under-reporting every async DB code path's real
  coverage project-wide (89.95% measured → 95.94% after the one-line
  config fix, no test changes).

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
| `reservas` | `(booking_provider, reserva_reference)`; soft delete via `deleted_at`; operator/finance + `paid_at` (#55); nullable `partido_id` FK `SET NULL` (#61); `sender`/`subject`/`fecha_email_recibido` nullable (#70); `costos` fully derived, no longer client-writable (#81) |
| `partidos` | soft delete via `deleted_at`; indexed on `fecha`, `ciudad` (#61) |
| `gastos` | unique `(partido_id, categoria)`; FK `partido_id` `CASCADE` (#81) |
| `gasto_reserva_splits` | unique `(gasto_id, reserva_id)`; FKs `gasto_id`/`reserva_id` `CASCADE`; fully recomputed (delete+reinsert) on every relevant change, not incrementally patched (#81) |

## Deviations from the original architecture plan

- No domain `Result` type — exceptions (`DomainError`).
- No `domain/ports.py` Protocols — concrete repos/adapters.
- Config file is `booking_providers.yaml` (not `accounts.yaml`).
- Dual Vercel projects (not single container serving UI + API).
