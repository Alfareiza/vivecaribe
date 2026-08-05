# Active context — ViveCaribe

## Current focus

Issue **#7** — tests hardening, Memory Bank, `.env.example` / README polish,
and a 90% package coverage gate. Branch: `feat/7-tests-docs`.

## Recent decisions

- Document (do not implement) the missing domain `Result` type.
- Keep automation auth **JWT-only** for now; do not wire `CRON_SECRET` in #7.
- Enforce **whole-package** statement coverage ≥ 90% (including Gmail/Outlook).
- Ignore only `refresh_token*.txt` for local OAuth artifacts.
- Repository `save()` refreshes ORM rows after flush so `updated_at` is safe.

## Known gaps (intentional / deferred)

- Propio extractor is still a skeleton.
- `CRON_SECRET` auth for Vercel Cron → issue **#8**.
- Real WhatsApp Meta integration → later.
- `correlation_id` ContextVar exists but no middleware sets it yet.
- Domain ports / Result pattern from the early plan were never shipped.

## Next

After #7 merges: issue **#8** (Dockerfile.vercel, `vercel.json` cron calling
`POST /automation/emails/get-bookings`, production wiring).
