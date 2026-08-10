# Active context — ViveCaribe

## Current focus

Epic **#41** — frontend ↔ API reservas wiring. **Phases 0–2 + #50
landed** (list shell, refresh tokens, auth + live list, shared loading UI).
Remaining children: Edit (#40), server list filters (#46), signup (#47),
modal share/UX (#48).

## Recent decisions

### Shared loading UI (#50)

- `PulseLoader` + `PageLoading` + `InlineLoading` under
  `apps/frontend/src/components/ui/loading/` (CSS module).
- Props: `size` / `speed` / `color` / `darkColor`; wrappers always pass
  size/speed; `label` required and SR-only (no visible Spanish copy).
- `PageLoading` default `min-h-screen`; layout via `className` (e.g.
  `flex-1` in auth shell).
- Sign-in busy: call-site spinner-only + `aria-label="Entrando…"` (no
  `Button` API change).
- Wired: auth boot, `SignInGate`, sign-in Suspense, reservas fetch,
  submit button.

### Operator auth (Q1 + #44 / #45)

- Browser → API **direct** (`NEXT_PUBLIC_API_URL`); not a Next BFF.
- **Access JWT** in JS memory only (never localStorage / sessionStorage /
  cookie).
- **Refresh token** opaque, hashed in `refresh_tokens`; HttpOnly cookie on
  the API host; rotate on `/refresh`; reuse → revoke family.
- Endpoints: `POST /login`, `POST /refresh`, `POST /logout`.
- TTLs: access `JWT_EXPIRE_MINUTES` (default 60); refresh
  `JWT_REFRESH_EXPIRE_DAYS` (default 7).
- Cookie: HttpOnly; local `SameSite=Lax` + insecure OK; staging/prod
  `SameSite=None` + `Secure`.

### CORS + frontend session (#41 Phase 1–2 / PR #49)

- API `CORS_ORIGINS` comma-separated allowlist + `allow_credentials=True`.
  Typical: `http://localhost:3000,https://vivecaribe-frontend.vercel.app`.
- Admin `(admin)` layout client gate: boot `/refresh` or redirect `/signin`.
- Sign-in Spanish; social buttons visible but disabled; logout from header.
- `NEXT_PUBLIC_LOGIN_REDIRECT_URL` (default `/reservas`); safe `callbackUrl`.
- `/reservas` fetches all pages (`limit=100` loop) then client filter/sort.
  Server filters deferred to #46.

### Reservas list shell (#42 / PR #43)

- Route `/reservas`, sidebar **Reservas**, Spanish UI, badge mapping,
  detail modal, Edit disabled stub (#40).

### Dual Vercel + portable Docker (#38)

- **Two** Vercel projects, same GitHub repo:
  - `vivecaribe` → Root Directory `apps/backend` → Container + cron.
  - `vivecaribe-frontend` → Root Directory `apps/frontend` → Next native.
- Compose: `db` + `api` + `frontend` (`NEXT_PUBLIC_API_URL`).

## Known gaps (intentional / deferred)

- #40 Edit (PATCH) · #46 GET `/reservas` filters · #47 signup wire ·
  #48 modal share (WhatsApp / Google Calendar) + UX.
- Real WhatsApp Meta integration (NoOp until Meta approval).
- Zoho `mark_as_read`; per-user ownership / RBAC on reservas.
- `correlation_id` ContextVar — no middleware sets it yet.
- Hourly Colombia-window cron needs Pro (Hobby is once/day).

## Next

- Pick next #41 child (#40 Edit or #46 filters).
