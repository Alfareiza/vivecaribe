# Active context — ViveCaribe

## Current focus

On **`main`**. Propio + Zoho Mail is merged. Latest follow-ups:

1. Zoho identity OTP completed via GetYourGuide Gmail poller; warm sessions
   under `APP_DATA_DIR` (Docker `/app` stays immutable for non-root).
2. Extractor hardening (`90e77c7`): shared phone→country, income formulas,
   Homefans `pycountry`, Viator E.164 phones.

## Recent decisions

### Zoho mailbox

- Public API: `ZohoMailbox.fetch_messages(*, query, max_results)`.
- Internals: `ZohoSession` (login / `storage_state` / headers) +
  `ZohoMailClient` (search / read / fetch) in `integrations/zoho.py`.
- Session file: `APP_DATA_DIR/.zohomail_storage.json` (fallback `~`).
- Sporadic Zoho email-OTP challenge: poll GYG Gmail
  (`from:zohoaccounts.com` OTP) via `GmailMailbox.wait_for_zoho_otp`;
  raises `EmailNotFound` when missing.
- Defaults: folder `NOTIFICATIONS`, `time_window="2m"` (also `1h`/`24h`/
  `2d`/`1m`/`3m`).
- No `mark_as_read` on Zoho; use case calls it only when present.
- Root `zoho.py` prototype is local/experiments only (untracked).

### Extractors

- `BaseExtractor.get_pais_del_visitante()` — ISO alpha-2 from phone via
  `phonenumbers` (GYG / Propio / Viator default).
- `normalize_phone` always returns E.164 (`+…`); strips leading zeros.
- Homefans country: `pycountry` name → alpha-2, else phone fallback.
- Income (operator):
  - GYG: `price * 0.7`
  - Homefans: first WooCommerce amount `* 0.75`
  - Viator: `Tarifa neta` = income; `price = income * 1.31`
  - Propio: `income == price`

## Known gaps (intentional / deferred)

- Zoho `mark_as_read`.
- Long-lived browser / skip Chromium on warm path.
- Real WhatsApp Meta integration (NoOp until Meta approval).
- `correlation_id` ContextVar — no middleware sets it yet.
- Hourly Colombia-window cron needs Pro (Hobby is once/day).

## Next

Ops smoke: Zoho warm/cold + OTP path in Docker/Vercel; watch Homefans
`prices()` / income edge cases.
