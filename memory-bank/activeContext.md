# Active context — ViveCaribe

## Current focus

Issue **#8** — Vercel container deploy (`Dockerfile.vercel`), dual auth
(JWT / `CRON_SECRET`) on `GET`+`POST /automation/emails/get-bookings`,
Hobby daily cron. Branch: `feat/8-deploy`.

## Recent decisions

- Domain `Result` type deliberately dropped — exceptions only.
- Booking CRUD is out of scope for #8.
- Real WhatsApp Meta integration blocked on Meta Business approval (NoOp).
- Automation: `GET` (no body, defaults) + `POST` (optional JSON filters).
- Auth on both methods: JWT **or** `CRON_SECRET` (`hmac.compare_digest`).
- Preserve unread-email behavior until WhatsApp is real (`notify=False`).
- Hobby cron: `0 9 * * *` UTC (= 04:00 Colombia), once daily.

## Known gaps (intentional / deferred)

- Propio extractor is still a skeleton.
- Real WhatsApp Meta integration → after Meta authorization.
- `correlation_id` ContextVar exists but no middleware sets it yet.
- Hourly Colombia-window cron needs Pro (Hobby is once/day).

## Next

Finish #8: PR, production smoke (`/health`, GET cron auth, POST JWT).
