# Progress — ViveCaribe

## Done

| Issue / track | Status | Summary |
|---------------|--------|---------|
| #1 Scaffold | Closed | uv, Docker, Settings, logging, Sentry, health |
| #2 Domain core | Closed | Reserva, User, enums, DomainError hierarchy |
| #3 Persistence | Closed | SQLAlchemy models, Alembic, repositories |
| #4 Auth | Closed | `/users`, `/login`, Argon2, JWT |
| #5 Automation BC | Closed | Gmail/Outlook, extractors, pipeline, WhatsApp NoOp |
| #6 Pipeline API | Closed | `POST /automation/emails/get-bookings` |
| #7 Tests + docs | Closed | Coverage gate, CI, Memory Bank, README |
| #8 Deploy | Closed / verify | `Dockerfile.vercel`, GET+POST automation, no API-project Cron |
| Propio + Zoho | Merged | HTTP search/md, PropioExtractor, YAML |
| Zoho OTP + data dir | Merged | GYG Gmail OTP poller; `APP_DATA_DIR` sessions |
| Extractor income/country | Merged | Shared phone→alpha-2; provider income formulas |
| #25–#33 Reserva CRUD | Closed | POST/GET/PATCH/DELETE + paginated list |
| #36 Monorepo layout | Closed | `apps/backend` + frontend placeholder |
| #38 Dual Vercel / frontend app | Closed | Next in `apps/frontend`, Compose frontend |
| #42 Phase 0 list UI | Closed | `/reservas` mock table + frontend CI (PR #43) |
| #44 / #45 Refresh tokens | Closed | Opaque refresh + HttpOnly cookie; `/refresh` `/logout` |
| #41 Phases 1–2 | Merged (#49) | CORS, sign-in, live GET `/reservas` |
| #50 Shared loading UI | Closed | PulseLoader / PageLoading / InlineLoading |
| #48 Detail modal share | Closed (#53) | WhatsApp / Google Calendar + modal UX |
| #46 List filters + es_hoy | Merged (#54) | Server filters, ReservaShortItem, Hoy badge |
| #55 Operator fields + paid_at | Merged (#56) | Domain/ORM/API + Alembic; derived `paid_at` |
| #63 fecha_evento timezone | Merged (#64) | Fixed 5h-off display in frontend |
| #61 Partidos feature | Merged (#62) | `Partido` domain/ORM, CRUD API, frontend shell |
| Partidos UI/UX pass | Merged (#65) | Temporal states, badge, ciudad/estadio auto-select, nested reserva modal |
| Partidos reservas_count fix | Merged (#66) | LEFT JOIN + COUNT, no N+1; fixed soft-delete join bug |
| Partidos list split | Merged (#67) | Upcoming asc / "Partidos pasados" divider / past desc |
| Auto-match reservas + tiered badges | Merged (#69) | Ciudad+day match on create, bulk-assign confirm modal, bronze/silver/gold badges |
| Reservas Create/Edit/Delete UI + validation hardening | Merged (#71) | Closes #40/#41/#70; full CRUD via one modal; Vayara/Otro/Airbnb; max_length/gt=0/phone-`+` validation |
| Reservas partido linking + income auto-fill + form polish | Merged (#73) | Closes #72; partido picker on create (cached, single-select); Ingreso/Ingreso estimado auto-fill via provider rate + live TRM; ViveCaribe label, COP prefix + es-CO number formatting |
| Vercel Ignored Build Step fix | Merged (#74) | Diff against `$VERCEL_GIT_PREVIOUS_SHA` not `HEAD^`, so a multi-commit push whose tip doesn't touch a project's files no longer silently skips that project's build (hit on #66 and #73); both dashboards wired to the new script via API |
| Reserva financiero: trm_estimado/trm_final, income_final, UI redesign | Merged (#78/#79, PR #80) | `trm_estimado` (auto-fetched at creation, editable only while null) + `trm_final` (renamed from `trm_del_dia`, always editable) drive server-computed `income_estimado`/`income_final`; `profit`/`percentage_profit` now derive from `income_final`. Edit form redesigned into paired Estimado/Final panels with disabled "(calculado)" derived fields; Resumen redesigned into a hero (Ingreso final, Profit + % badge)/secondary (Ingreso, Ingreso estimado, Costos) hierarchy. Numeric-only sanitization on rate/cost inputs; fixed a focus-triggered reformat race that could silently double a saved rate |

## In progress / open children of #41

- #47 — Sign Up / `POST /users` from UI (low priority)

## Works today

- Register/login; access JWT + refresh cookie rotation.
- Reserva CRUD; soft-delete hidden from get/list.
- `GET /reservas` server filters (`estado`, `booking_provider`,
  `fecha_evento_from/to`, `ciudad`, `unassigned_only`) + slim list +
  `es_hoy`; detail by id.
- Operator/finance fields on create/update/detail; `paid_at` auto-derived.
- Reserva financiero: `trm_estimado` (auto-fetched from a third-party FX
  API at creation, locked once set) and `trm_final` (always editable,
  filled in once payment is received) drive server-computed
  `income_estimado`/`income_final`; `profit`/`percentage_profit` derive
  from `income_final`. Edit form and Resumen view both reflect the
  Estimado/Final pairing with derived fields rendered disabled.
- Admin UI: authenticated `/reservas` with server pagination/filters and
  Hoy badge; one modal (`ReservationDetailModal`) handles view, create,
  edit, and soft-delete, including all operator/finance fields.
- Reservas validation: `max_length` matches DB columns on every base
  field (was 500ing on overflow before); `price`/`income` > 0; `phone`
  must start with `+` when set (auto-normalized on the form).
- Reservas create form: pick a partido inline (cached lookup by
  ciudad+día); Ingreso/Ingreso estimado auto-fill from Precio (provider
  payout rate + live TRM to COP), editable and stops auto-filling once
  hand-edited.
- Partidos CRUD (`/partidos`); optional 1:many with reservas via
  `partido_id`. `/partidos` UI: upcoming/past split list, temporal card
  states, tiered reserva-count badge, auto-match unassigned reservas by
  ciudad+day on create with bulk-assign confirmation.
- Shared pulse loading for auth gate, reservas fetch, and sign-in submit.
- Automation POST accepts JWT **or** `CRON_SECRET`; GET same auth.
- Pipeline GYG / Viator / Homefans / Propio (Zoho); idempotent persistence.
- Isolated Postgres tests ≥ 90% coverage; frontend CI path-filtered build.
- Compose: Postgres + API + frontend.
- Migrate workflow on main applies Alembic when migrations change.
- `scripts/vercel-ignored-build-step.sh` computes each Vercel project's
  Ignored Build Step decision from `$VERCEL_GIT_PREVIOUS_SHA`. Both
  projects' `commandForIgnoringBuildStep` are wired to it (set via
  `PATCH /v9/projects/{id}` — Ignored Build Step isn't configurable
  through `vercel.json`/`vercel.ts`, dashboard or API only).

## Left to build

- Remaining #41 children (#47).
- Real WhatsApp Meta notifier after Meta authorization.
- Zoho mark-as-read (deferred).
- Optional: per-user ownership on reservas.
- Partido↔reserva matching is create-time only, one-shot; no periodic
  re-match for reservas added/edited afterward.

## Known issues / deliberate non-goals

- No domain `Result` type (exceptions by design).
- WhatsApp stays NoOp until Meta approves.
- Local OAuth helper scripts / refresh token files must stay untracked.
- Homefans `get_income` still has a rough error path — watch in production.
- Single-container UI+API on Vercel rejected (#38): dual projects.
