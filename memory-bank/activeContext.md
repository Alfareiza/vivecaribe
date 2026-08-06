# Active context — ViveCaribe

## Current focus

**Zoho HTTP warm path** — branch `feat/propio-zoho-mailbox`. Refactored
`ZohoMailbox` so Playwright is login/cookies only; listing + reads use
`search.do` / `md.do` via `context.request`.

Propio WooCommerce bookings (`BookingProvider.PROPIO`) flow through
`ZohoMailbox` → `PropioExtractor` → existing automation pipeline.

## Recent decisions (Propio / Zoho)

- Public API unchanged: `ZohoMailbox.fetch_messages(*, query, max_results)`.
- Internals: `ZohoSession` (login / `storage_state` / headers) +
  `ZohoMailClient` (search / read / fetch) in the same `zoho.py`.
- Session file: `~/.zohomail_storage.json` (`storage_state` + meta csrf /
  client_session_id / static_version). Constant `accId` only.
- Query wrapped as `Subject = ( {query} )`, single `quote(..., safe="()")`.
- Time filter client-side on `LTIME`; no subject filter in `_summaries`.
- Parallel `md.do` reads (concurrency 5). Re-login once on 401/403 /
  `AUTHENTICATION_FAILED` only.
- Defaults: folder `NOTIFICATIONS`, `time_window="1m"`.
- YAML query: `"You've got a new order"`; creds `PROPIO_ZOHO_USERNAME` /
  `PROPIO_ZOHO_PASSWORD`.
- No `mark_as_read` on Zoho; use case calls it only when present.
- Root `zoho.py` prototype ignored (local/experiments only).

## Known gaps (intentional / deferred)

- Zoho `mark_as_read` (deferred).
- Long-lived browser / skip Chromium launch on warm path (deferred).
- Real WhatsApp Meta integration → after Meta authorization.
- `correlation_id` ContextVar exists but no middleware sets it yet.
- Hourly Colombia-window cron needs Pro (Hobby is once/day).

## Next

Live Zoho warm/cold timing smoke; then commit / PR for Propio+Zoho.
