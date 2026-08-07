# Active context — ViveCaribe

## Current focus

On **`main`**. Reserva CRUD API is merged (#25–#33 / PRs #26–#34).

## Recent decisions

### Reserva CRUD API

- Thin routers call `SqlAlchemyReservaRepository` directly (no use-case
  layer; persistence + idempotency only).
- JWT required on all `/reservas` routes; no per-user ownership scoping
  (`user_id` remains optional / unused by the pipeline).
- Soft delete via nullable `deleted_at`; `get_by_id` / `list` exclude
  soft-deleted rows. Migration: `a1b2c3d4e5f6`.
- List pagination: `skip`/`limit` + `{total, items}`; order `created_at`
  desc; default limit 20, max 100.
- PATCH allows business fields only; identity/audit fields immutable.

### Zoho mailbox (prior)

- Public API: `ZohoMailbox.fetch_messages(*, query, max_results)`.
- Internals: `ZohoSession` + `ZohoMailClient` in `integrations/zoho.py`.
- Session file: `APP_DATA_DIR/.zohomail_storage.json` (fallback `~`).
- Sporadic Zoho email-OTP: poll GYG Gmail via
  `GmailMailbox.wait_for_zoho_otp`; raises `EmailNotFound` when missing.
- No `mark_as_read` on Zoho; use case calls it only when present.

### Extractors (prior)

- `BaseExtractor.get_pais_del_visitante()` — ISO alpha-2 from phone.
- Income formulas: GYG `* 0.7`, Homefans `* 0.75`, Viator net/1.31,
  Propio `income == price`.

## Known gaps (intentional / deferred)

- Zoho `mark_as_read`.
- Long-lived browser / skip Chromium on warm path.
- Real WhatsApp Meta integration (NoOp until Meta approval).
- `correlation_id` ContextVar — no middleware sets it yet.
- Hourly Colombia-window cron needs Pro (Hobby is once/day).
- Per-user ownership / role scoping on reservas (not introduced).

## Next

- Ops: run `alembic upgrade head` where the new `deleted_at` migration
  is not yet applied (Supabase / local).
- Ops smoke: Zoho warm/cold + OTP path in Docker/Vercel.
- Real WhatsApp Meta notifier after Meta authorization.
