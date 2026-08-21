# Active context — ViveCaribe

## Current focus

Gastos: partido-level expense tracking, split across linked reservas
by participant count (`#81`, PR open). Built on top of Reserva
financiero (`#78`/`#79`, PR #80 — merged to main), which built on
Vercel Ignored Build Step fix (`#74` — merged & wired live) and
Reservas partido linking + income auto-fill (`#72`, PR #73 — merged),
which built on the full Create/Edit/Delete UI (`#40`/`#41`/`#70`,
PR #71 — merged). Partidos `#61`→`#69` (CRUD + UI/UX passes, PR #69)
status as of its last update, below.

## Recent decisions

### Gastos: partido-level expenses split across reservas (#81, PR open)

- New `Gasto` entity: one row per `(partido_id, categoria)` — a fixed
  5-value `GastoCategoria` StrEnum (Comida y/o Snacks, Transporte,
  Boletas, Apoyos, Otros), `monto` in COP, DB-unique on the pair. The
  operator sets/clears one amount per category rather than managing a
  free-form list — a real product constraint ("categories are usually
  not repeated"), not an arbitrary simplification.
- New `gasto_reserva_splits` table: persisted per-reserva share,
  proportional to `participants` among the partido's non-deleted
  linked reservas. Recomputed (delete-then-reinsert, cheap at ≤5 gastos
  per partido) by a single shared `_recompute_gasto_splits(session,
  partido_id)` function called from **four** places:
  `SqlAlchemyGastoRepository.upsert`/`delete`, and
  `SqlAlchemyReservaRepository.save`/`soft_delete` (the latter two also
  cover a reserva joining/leaving a partido and participant-count
  edits) — a cross-aggregate recompute doesn't belong on either
  repository alone, so it lives as a module-level function both share.
- `Reserva.costos` is no longer client-writable (dropped from
  `ReservaCreate`/`ReservaUpdate`) — it's the sum of that reserva's
  gasto shares, `None` when its partido has zero gastos (distinct from
  a confirmed `0`), `None` again if the reserva has no partido at all.
  Migration resets every existing `costos` to `NULL` (one-time; it's
  switching from manually-entered to fully derived). `profit`/
  `percentage_profit` keep deriving from `costos` unchanged.
- **Real bug found via `SqlAlchemyReservaRepository.save`'s own recompute
  logic**: unlinking a reserva from its partido via `PATCH
  /reservas/{id}` (`partido_id: null`) left `costos` stale, because the
  post-unlink recompute only touches reservas *still* linked to the old
  partido — the just-unlinked row is invisible to that query. Fixed by
  explicitly zeroing `costos` whenever `save()` observes the row ending
  up with no `partido_id`, independent of the recompute calls. The
  existing bulk `unlink_partido()` (used on partido soft-delete) already
  did this per-row; the single-reserva PATCH path didn't.
- **Routing gotcha**: `categoria` travels as a **query parameter**, not
  a path segment, on `PUT`/`DELETE /partidos/{id}/gastos`. "Comida y/o
  Snacks" contains a literal `/`, which 404s even percent-encoded
  (`%2F`) — ASGI servers decode `%2F` before route matching, so a
  `{categoria}` path param can never match it. Query values have no
  such restriction. Found via a real failing curl the user pasted in,
  not by writing a test first.
- Frontend: both the Partido modal (editable) and Reserva modal
  (read-only) render Gastos as a collapsed-by-default dropdown —
  header shows the label + a `Total $X` `Badge` + a chevron, matching
  the pre-existing `CollapsibleMetadata` pattern in
  `ReservationDetailModal.tsx`. Collapsed content gets `inert={!open}`
  so it's out of tab order, not just visually hidden (an a11y gap the
  pre-existing `CollapsibleMetadata` also has, left alone there —
  out of scope this round). **Chevron direction, explicit user
  correction**: default (closed) `AngleDownIcon` points down; the
  natural "expand" rotation is `rotate-180` (→ up, matches
  `CollapsibleMetadata`) but this user wants a right-pointing triangle
  on expand instead — `-rotate-90`, not `rotate-180`. Don't assume the
  180°-flip convention generalizes to every new collapsible in this app.
- Partido modal's Gastos editor is a compact single-row-per-category
  list (icon chip + label + input), not a card grid — cards (icon+label
  row, input row, separate proportion-bar row, ×5 in a 2-col grid) ate
  enough vertical space to push the modal title off-screen on shorter
  viewports. Fixed by (a) collapsing by default, (b) wrapping the whole
  modal body in `max-h-[min(65vh,34rem)] overflow-y-auto` (title/footer
  stay pinned — same pattern `ReservationDetailModal` already used), and
  (c) the proportion bar moved onto the row's own bottom divider
  (`absolute inset-x-0 bottom-0 h-0.5`, width = share%) instead of a
  separate layout row, so it costs no extra height.
- Gasto amounts are **whole pesos, no decimals** — a dedicated
  `sanitizeIntegerInput`/`formatIntegerCO` pair (digits-only, no `.`
  accepted at all) instead of reusing `sanitizeDecimalInput`/
  `formatPlainNumberCO`. A smaller custom `<input>` (h-8) replaces the
  shared `Input` component in this one section only, since that
  component hardcodes `h-11` with no size prop — not worth widening its
  contract for one denser table.
- **Race found via `playwright-cli`, not a human typing**: each gasto
  field auto-saves independently on blur, but the original
  `useEffect` reseeding all 5 drafts from `detail.gastos` on every
  `detail` update meant one field's async save response could arrive
  *after* the operator had already started typing into a sibling field,
  silently reverting that sibling's still-unsaved draft back to its
  last-committed value. Fixed by keying the reseed effect on
  `detail?.id` (fires once per loaded partido, not on every save
  round-trip) and having `handleGastoBlur` patch only its own category's
  draft from the save response.
- **Coverage-measurement gotcha, project-wide fix**: adding the gasto
  repository code dropped backend coverage to 89.95% (gate is 90%)
  despite the new code being heavily exercised by new tests —
  `[tool.coverage.run]` had no `concurrency` setting, and SQLAlchemy's
  async engine bridges DBAPI calls through `greenlet`, which
  `coverage.py`'s default thread-only trace hook doesn't follow.
  `concurrency = ["greenlet", "thread"]` in `pyproject.toml` took
  measured coverage from 89.95% → 95.94% instantly, no test changes —
  this was under-reporting real coverage on **every** async DB code
  path in the project already, not something newly broken by this PR.
- New `tests/test_gastos_api.py`: upsert-is-create-or-update, the
  slash-categoria routing case explicitly, split proportional to
  participants (verified per-category, not just the total), recompute
  on a reserva joining an already-gasto'd partido, `costos` resets on
  unlink, `costos` stays `None` (not `0`) until the first gasto exists.
  `test_reservas_api.py`'s three tests that used to set `costos`
  directly in the create/patch payload were rewritten to go through a
  real partido+single-reserva link instead (that reserva gets 100% of
  the gasto, same assertions as before).

### Reserva financiero: trm_estimado/trm_final rates, income_final, UI redesign (#78/#79, PR #80 — merged)

- New rate pair, both driving a server-computed COP amount the operator
  never edits directly:
  - `trm_estimado` — auto-fetched client-side at reserva creation from
    the same third-party FX source as before (`lib/trm.ts`), stored
    silently (no visible create-mode input). Editable via `PATCH` only
    while still `null` (covers legacy/pipeline reservas missing it);
    once set, the backend router silently drops further attempts to
    change it rather than erroring — matches the disabled/locked
    frontend input so a stray client write can't desync from what the
    UI shows. Drives `income_estimado = income × trm_estimado`.
  - `trm_final` (renamed from `trm_del_dia` via `alter_column`, data
    preserved) — always editable, filled in once the operator actually
    receives payment; no lock. Drives `income_final = income ×
    trm_final` (`domain/reserva.py`'s `compute_income_final`; COP
    reservas get a direct passthrough, no conversion). `profit`/
    `percentage_profit` (`compute_profit`) now take `income_final` +
    `costos` directly instead of re-deriving the moneda/rate branching
    inline — `income_final` is the single source of truth for "the
    real COP amount," computed via a `model_validator` that runs
    before the profit one (validator order matters here: Pydantic v2
    runs `mode="after"` validators in class-body definition order).
- **Derived-field-with-override pattern, revised**: the old "focus =
  raw, blur = formatted" toggle (`incomeEstimadoFocused` et al.) is
  gone for `trm_estimado`/`trm_final`/`costos` — found via Playwright
  QA that it raced a bulk value-set (Playwright `.fill()`, but a real
  paste operation is the same risk): the field's *displayed* value
  flips identity on focus/blur via a separate `useState`, and an
  external tool setting `.value` while that state transition was still
  in flight got its write silently doubled and *persisted*
  (`4100` → saved as `41004100.00`). Fields now just show the raw
  sanitized string unconditionally — no focus-driven re-render, no
  race. `income_estimado`'s own focus/blur toggle (create-mode only,
  pre-existing from #72) was left as-is, out of scope, but carries the
  same theoretical risk if ever revisited.
- New `sanitizeDecimalInput()` in `ReservationDetailModal.tsx`: strips
  everything but digits and a single `.` on every keystroke (was a
  literal bug report — the rate fields accepted arbitrary text with no
  feedback). Applied to `trm_estimado`, `trm_final`, `costos`.
- Derived amounts (`income_estimado`, `income_final`) render as
  `disabled` `Input`s with a "(calculado)" label suffix in the edit
  form — they were always computed, but looked like ordinary editable
  fields before. `FormField`'s `label` prop widened `string` →
  `React.ReactNode` (local component, no other callers) to allow the
  muted suffix styling. `income_final` has no `FormState` field at all
  — it's derived inline at render time from `form.income`/
  `form.trm_final` (`editFormIncomeFinal` in the component body) since
  it's never submitted, just displayed live as the operator types.
- Edit form reorganized into two bordered "Estimado"/"Final" panels
  (rate above the amount it derives, each in its own
  `rounded-xl border ... bg-gray-50/40` box) instead of `trm_estimado`
  nested under `income_estimado`'s column while `trm_final` sat in an
  unrelated row with Costos — the two pairs read as parallel groups
  now. Consulted `/frontend-design` for this specific micro-layout
  question; its "bold aesthetic" framing doesn't fit a sober admin CRUD
  form, so the actual call (locked/derived fields get less visual
  weight than genuinely editable ones) was made directly.
- Resumen (view mode) redesigned from a single flat `dl` list into a
  `StatCard`-based hierarchy: hero row (`Ingreso final`, `Profit` —
  large/bold `text-title-sm`) + secondary row (`Ingreso`, `Ingreso
  estimado`, `Costos` — smaller/muted), responsive `grid-cols-1
  sm:grid-cols-2/3`. Ordering encodes importance per explicit ask:
  `Ingreso final` most prominent, `Ingreso` second (ahead of `Ingreso
  estimado`, which is only a creation-time guess). `% Profit` merged
  into the `Profit` card as a small colored `Badge` (reusing the
  existing `EcommerceMetrics.tsx` KPI-badge convention) instead of a
  separate progress-bar card — a bar implies "progress toward a goal,"
  which a margin percentage isn't; removed the now-dead `PercentageBar`
  component. Empty hero values render a plain "—" (not an oversized
  "Pendiente de pago" sentence at hero type size) with the explanation
  moved to the small caption line instead.
- QA note: this round's Playwright verification used a throwaway
  `qa-trm-test@example.com` user registered directly against the local
  dev backend (`POST /users`) — not a seeded fixture, fine to
  re-register if needed for future manual QA on this branch/DB.

### Vercel Ignored Build Step compares last-deployed SHA, not HEAD^ (#74)

- Root cause: dashboard "Ignored Build Step" for both projects ran
  `git diff HEAD^ HEAD --quiet -- .`. A rebase-merge landing a
  multi-commit PR (e.g. #73: feature commit + trailing `docs(memory-bank)`
  commit) can put the tip commit's diff against its own parent at zero
  even though the branch as a whole changed real files — silently
  skipping the build. Hit on #66 and again on #73 (frontend production
  served the pre-#73 build until a manual `vercel --prod` redeploy).
- Fix: `scripts/vercel-ignored-build-step.sh`, referenced from both
  projects' dashboard field as
  `bash "$(git rev-parse --show-toplevel)/scripts/vercel-ignored-build-step.sh"`.
  Diffs against `$VERCEL_GIT_PREVIOUS_SHA` (the commit Vercel actually
  last deployed for that project) instead of `HEAD^`, falling back to
  `HEAD^` only if that env var is unset or unreachable (e.g. first deploy
  on a new branch). See techContext.md for the manual-redeploy gotcha
  (`vercel --prod` path-doubling) hit while working around the stale
  frontend in the meantime.
- Ignored Build Step isn't settable via `vercel.json`/`vercel.ts` — it's
  dashboard-only *or* the REST API's `commandForIgnoringBuildStep` field
  (`PATCH /v9/projects/{idOrName}`, confirmed via the Vercel docs' project
  settings + API reference). Wired both projects (`vivecaribe`,
  `vivecaribe-frontend`) to the script via that API call instead of the
  dashboard UI — same effect, scriptable/repeatable. Exit-code contract
  double-checked against the docs: `0` cancels the build, `1` continues
  it, matching `git diff --quiet`'s native exit codes (no inversion
  needed in the script).

### Reservas partido linking on create + income auto-fill + form polish (#72, PR #73 — merged)

- New "Partido" section in the create form only (`createMode`) — "+
  Buscar partido" (disabled until Ciudad + Fecha del evento are set)
  looks up same-city/same-day partidos via the existing `fetchPartidos`;
  results render as a clickable list with a "Vincular" hover affordance
  (previous plain-list version tested as unclear UX — clicking a row to
  assign wasn't obvious). Single-select (`reservas.partido_id` is one
  FK, not many-to-many); resets if Ciudad/Fecha change afterward so a
  stale link can't silently survive an edit. Lookups are cached
  client-side for 60s (`partidoLookupCache` in
  `ReservationDetailModal.tsx`) so repeatedly clicking the button
  doesn't repeatedly hit the API.
- `dayWindow`/`partidoLabel` (previously private to `PartidoSelector.tsx`)
  moved to `reservationUtils.ts` as shared exports — now used by both
  the edit-mode `PartidoSelector` and the new create-mode picker.
- Ingreso auto-fills from Precio × a per-provider payout rate
  (`INCOME_RATE_BY_PROVIDER`: GetYourGuide 70%, Viator 76.34%, Homefans
  75%, everyone else incl. the new providers 100%) — create mode only,
  stops once the operator hand-edits Ingreso (a `incomeTouched` flag set
  only inside that field's own `onChange`, never by the auto-fill
  effect itself).
- Ingreso estimado auto-fills the same way: direct copy when Moneda is
  COP, otherwise a **live** TRM fetch (`apps/frontend/src/lib/trm.ts`,
  `fetchTrmToCop`, hits `cdn.jsdelivr.net`'s free currency-api, per-key
  in-memory cache) converts Ingreso to COP — replacing the old
  `TRM_COP_PLACEHOLDER = 4000` hardcoded guess. Debounced 500ms since
  Precio's keystroke-by-keystroke typing cascades into this field and
  would otherwise fire one HTTP request per keystroke. On fetch failure,
  shows the operator-facing message inline (`role="alert"`) and leaves
  the field untouched rather than clobbering it. Same "stops once
  touched" pattern as Ingreso.
- The read-only Resumen view (existing reservas) had a real bug: it
  *always* recomputed from the flat placeholder, ignoring any already-
  stored `income_estimado`. Now: stored value shown directly (no
  fetch) → COP passthrough → live TRM fetch, in that order, only for
  reservas missing a stored value. Fetch failure here is quiet ("—", no
  alert) since viewing a reserva is passive, not an active edit.
- Form polish: `PROVIDER_LABELS.propio` → "ViveCaribe" (was "Propio"),
  used everywhere the map is read (form dropdown + table filter). New
  generic `Input` `prefix` prop (`components/form/input/InputField.tsx`)
  renders a static left-edge label inside the bordered box — like a
  phone field's country-code chip — used for Ingreso estimado's "COP"
  tag instead of cramming "(COP)" into the label (which wrapped and
  misaligned the row). New `formatPlainNumberCO()` in
  `reservationUtils.ts` shows es-CO thousands/decimal formatting
  (`544.252.161,08`) while unfocused, raw digits while focused/editing —
  scoped to just this one field, not Precio/Ingreso (those vary by
  Moneda, this one's always COP).
- Cliente section reflow: row 1 is now Nombre / Personas (narrowed to
  `sm:w-28`, was stretching full-width) / Menores de edad / Notificado
  WhatsApp (moved up from row 2); row 2 becomes Teléfono / País, Punto
  de encuentro / Lugar de recogida, Tipo de tour alone.

### Reservas full Create/Edit/Delete UI + validation hardening (#40/#41/#70, PR #71 — merged)

- `ReservationDetailModal` now handles view, create, and edit in one
  component: `createMode` prop opens a blank form (skips the
  `GET /reservas/{id}` fetch); `isEditing` state toggles the read-only
  detail view into an edit form seeded from `detail`. `handleDelete`
  mirrors `PartidoModal`'s pattern: `window.confirm` then `DELETE`;
  `onSaved`/`onDeleted` callback props let the parent table refetch.
- New providers `vayara`, `otro`, `airbnb` on `BookingProvider` (plain
  `StrEnum` + `VARCHAR`, no migration needed). Vayara gets a same-day
  `paid_at` formula; Otro/Airbnb fall through the existing "no formula
  defined" `None` branch.
- `sender`, `subject`, `fecha_email_recibido` made nullable (migration
  `a8b9c0d1e2f3`) since a manually-created reserva has no source email;
  the automation pipeline always supplies real values regardless, so
  this doesn't change pipeline behavior.
- `reserva_reference` (create only) is generated client-side as
  `{provider prefix}-{ddmmyy}-{random 3-char suffix}`; `handleSave`
  retries up to 5x with a fresh suffix on an actual 409. Found via QA:
  without the suffix+retry, two same-day/same-provider manual creates
  collided forever with no way out, since the reference isn't
  shown/editable in the UI.
- Validation hardening found via manual Playwright QA: `ReservaCreate`/
  `ReservaUpdate` were missing `max_length` on most base string fields
  (`phone`, `customer_name`, `moneda`, `nombre_experiencia`,
  `ciudad_experiencia`, `pais_del_visitante`, `source`, `sender`,
  `subject`, `reserva_reference`) — overflow crashed with a raw 500
  instead of a 422 (only the #55 operator fields had `max_length`
  already). `price`/`income` are now `gt=0` (tightened from an initial
  `ge=0` per explicit business rule — no $0/negative bookings). `phone`
  must start with `+` (E.164-style) when non-empty — validated only on
  `ReservaCreate`/`ReservaUpdate`, deliberately not the domain model or
  read schemas, so existing non-`+` pipeline data still reads fine.
  Frontend mirrors all of this: `maxLength` on the affected inputs,
  `isValid` requires `price`/`income` > 0, `phone` auto-normalized
  (`+` prepended) on blur and again at submit.
- New shared `InfoHint` (`components/ui/tooltip/InfoHint.tsx`): generic
  "i" icon + tooltip, `align` prop (`"center"` default, `"right"` only
  for the one field actually at a container's right edge — defaulting
  every tooltip to right-align just moves the clipping risk left).
- País is a searchable free-text `<input list=...>` + `<datalist>`
  sourced from the `world-countries` npm package
  (`apps/frontend/src/lib/countries.ts`), not a closed `<Select>` —
  stores the typed string as-is, no alpha-2 conversion (that's
  pipeline-only, via `pycountry`).
- **Gotcha**: Tailwind v4 arbitrary values don't reliably support `fr`
  inside `calc()` for `grid-template-columns` in this project's browser
  target — confirmed the browser itself silently rejects
  `el.style.gridTemplateColumns = "calc(1fr - 5px) ..."` (not a
  Tailwind-compilation issue). Use `calc(100% - Npx)` on a plain block
  element, or a fixed pixel width on one flex item with `flex-1` on the
  rest, instead of `fr` + `calc` together.
- **Gotcha**: don't run `npm run build` (production) while
  `next dev --turbopack` is live against the same `.next` directory —
  it corrupts the dev server's Turbopack cache and it can silently serve
  stale HMR output for specific edits. If HMR stops reflecting a change,
  restart the dev server (clear `.next/cache`) rather than assuming the
  edit is wrong. Stick to `eslint` + browser reload while a dev server
  is running.

### Auto-match reservas on partido create + tiered badges (#68 / PR #69 — merged)

- `GET /reservas` gained `ciudad` (exact, case-insensitive) and
  `unassigned_only` filters. On partido create, checks same-ciudad +
  same-calendar-day unassigned reservas; if any exist, a confirmation
  modal (`PartidoMatchedReservasModal`) offers one-click bulk-assign
  instead of closing immediately. No matches ⇒ falls back to
  create-and-close. See systemPatterns.md for the `effectiveId` /
  `displayAsExisting` bridge that lets `PartidoModal` render as "existing"
  right after create, before the parent even knows the new id.
- Reserva-count badge on partido cards now tiers by volume: 0 gray,
  1-2 bronze, 3-4 silver, 5+ gold, shine-sweep on hover for non-zero tiers.
- Shared ticket icon: `public/images/icons/ticket.svg`, referenced via
  `next/image` (not SVGR) in the sidebar "Reservas" item and the badge —
  see systemPatterns.md's public-icon note for the currentColor tradeoff.

### Partidos list ordering (PR #67)

- Split into two sections instead of one fecha-desc list: upcoming
  (today + future) ascending, then a "Partidos pasados" divider, then past
  descending — so the past match *closest to today* shows first. No cap
  added on either side beyond what the backend already returns.

### Partidos reservas_count fix (PR #66)

- `GET /partidos` list items were always showing 0 reservas — the list
  endpoint's `PartidoShortItem` never carried a count. Fixed via a single
  `LEFT JOIN + COUNT` repository query (no N+1). Found and fixed a real
  bug along the way: the non-deleted-reservas filter must live in the
  JOIN's ON clause, not WHERE — see systemPatterns.md.

### Partidos UI/UX pass (PR #65)

- Card temporal states (past greyed / today orange pulse / future
  neutral), reserva-count badge, fecha-desc sort (later superseded by
  #67's split), ciudad/estadio auto-select from `equipo_local` (Junior →
  Barranquilla + Romelio Martínez, Cartagena → Cartagena + Jaime Morón),
  nested `ReservationDetailModal` reused (not duplicated) for viewing a
  linked reserva's full detail from inside `PartidoModal`.

### Partidos feature (#61 / PR #62)

- New `Partido` domain + `PartidoORM`, optional 1:many with `Reserva` via
  nullable `partido_id`. Full CRUD under `/partidos`; linking happens from
  the `Reserva` side (`PATCH /reservas/{id}`), not from `Partido`.

### Reserva operator fields + paid_at (#55 / PR #56)

- New nullable operator/finance columns on `reservas` / domain `Reserva`:
  `notas_cliente`, `tipo_tour`, `notas_personales`, `costos`,
  `meeting_point`, `lugar_de_recogida`, `income_estimado`, `profit`,
  `percentage`; `menores_de_edad` NOT NULL default false.
- Enums `TipoTour` / `MeetingPoint` use literal wire values
  (`"football tour"`, `"Door-to-Door"`, …).
- `paid_at` derived in domain (`model_validator` + revalidating
  `model_copy`) from `booking_provider` + `fecha_evento` (Bogota):
  GYG/Viator → 7th next month (9th if weekend); Propio → +1 day;
  Homefans → next Thursday (same-day Thu → following week). Null when
  no `fecha_evento`. Not client-writable.
- Create/Update schemas expose operator fields; list (`ReservaShortItem`)
  stays slim. Migration `d4e5f6a7b8c9`.

### GET /reservas filters + slim list + es_hoy (#46 / PR #54)

- Server filters: `estado`, `booking_provider`, `fecha_evento_from/to`
  (AND; Bogota calendar days in SQL; null fecha excluded when ranged).
- List DTO `ReservaShortItem` (slim + `income` + computed `es_hoy`).
- `ReservaResponse` inherits domain `Reserva`, excludes `deleted_at`,
  adds computed `es_hoy`. Create/Update stay separate models.
- UI: server pagination/filters; orange ping “Hoy” from `es_hoy`;
  estado filter kept, estado badge hidden; generic `StatusDot`.
- Modal refetches `GET /reservas/{id}` for full detail.

### Shared loading UI (#50)

- `PulseLoader` + `PageLoading` + `InlineLoading` under
  `apps/frontend/src/components/ui/loading/` (CSS module).
- Spanish `label` required and SR-only; wired on auth + reservas fetch.

### Operator auth (#44 / #45) + CORS session (#49)

- Browser → API direct; access JWT in memory; refresh HttpOnly cookie.
- `(admin)` gate: boot `/refresh` or redirect `/signin`.

### Reservas shell (#42) + detail share (#48)

- `/reservas` table + detail modal; Edit still disabled stub → #40.
- Share: WhatsApp / Google Calendar from modal (#48 closed).

### Dual Vercel + portable Docker (#38)

- API `vivecaribe` (container) + UI `vivecaribe-frontend` (Next native).
- Compose: `db` + `api` + `frontend`.

## Known gaps (intentional / deferred)

- #47 signup wire.
- Real WhatsApp Meta integration (NoOp until Meta approval).
- Zoho `mark_as_read`; per-user ownership / RBAC on reservas.
- `correlation_id` ContextVar — no middleware sets it yet.
- Hourly Colombia-window ingest still needs Pro (Hobby Cron is once/day).
  API-project Cron was removed; ingest is triggered by an external scheduler.
- Stored dates eventually all America/Bogota (noted during #46).
- No provider logo asset for `otro` yet — `ProviderLogo` 404s for it
  (`vayara`/`airbnb`/etc. have real SVGs under
  `public/images/providers/`, `otro` doesn't; cosmetic, non-blocking).
- Partido↔reserva matching only runs on partido *create* and only offers a
  one-time confirmation; no ongoing/periodic re-match for reservas created
  or edited afterward (noted as a future idea before #68/#69 built the
  create-time version).
- `public/images/icons/*.svg` referenced via `next/image` don't inherit
  `currentColor` (fixed color regardless of theme/hover/tier) — accepted
  tradeoff for having one source-of-truth icon file (#69).

## Next

- #47 signup (low priority) if needed.
