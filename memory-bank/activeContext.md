# Active context — ViveCaribe

## Current focus

Epic **#41** — frontend ↔ API reservas. Backend operator fields +
`paid_at` landed (#55 / PR #56). Next: **#40** Edit (PATCH from modal).

## Recent decisions

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

## Next

- #40 Edit reserva (PATCH from modal) — include new operator fields.
- Then #47 signup (low priority) if needed.
