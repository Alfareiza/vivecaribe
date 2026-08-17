# Active context — ViveCaribe

## Current focus

Partidos (football matches) feature, `#61`→`#69`: CRUD + frontend shell
(#61/#62), then a run of UI/UX passes (#65-#69, PR #69 still open — see
below). Once #69 merges, next up is the still-open **#41** child: **#40**
Edit reserva (PATCH from modal).

## Recent decisions

### Auto-match reservas on partido create + tiered badges (#68 / PR #69, open)

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

- #40 Edit (PATCH) · #47 signup wire.
- Real WhatsApp Meta integration (NoOp until Meta approval).
- Zoho `mark_as_read`; per-user ownership / RBAC on reservas.
- `correlation_id` ContextVar — no middleware sets it yet.
- Hourly Colombia-window ingest still needs Pro (Hobby Cron is once/day).
  API-project Cron was removed; ingest is triggered by an external scheduler.
- Stored dates eventually all America/Bogota (noted during #46).
- Frontend does not yet show/edit the new operator fields (#40).
- Vercel Ignored Build Step compares `HEAD^` not last-deployed SHA — can
  silently skip a project's build on a multi-commit push (see
  techContext.md). Not yet fixed on either Vercel project.
- Partido↔reserva matching only runs on partido *create* and only offers a
  one-time confirmation; no ongoing/periodic re-match for reservas created
  or edited afterward (noted as a future idea before #68/#69 built the
  create-time version).
- `public/images/icons/*.svg` referenced via `next/image` don't inherit
  `currentColor` (fixed color regardless of theme/hover/tier) — accepted
  tradeoff for having one source-of-truth icon file (#69).

## Next

- Merge PR #69 (auto-match reservas + tiered badges).
- #40 Edit reserva (PATCH from modal) — include new operator fields.
- Then #47 signup (low priority) if needed.
