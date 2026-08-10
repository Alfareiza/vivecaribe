# ViveCaribe Frontend

Admin UI for ViveCaribe booking operations. Next.js App Router app in the
monorepo.

Monorepo overview: [`README.md`](../../README.md) · API:
[`apps/backend/README.md`](../backend/README.md).

## Tech stack

- **Next.js** 16 (App Router)
- **React** 19
- **TypeScript**
- **Tailwind CSS** v4
- UI starter based on TailAdmin (layouts, charts, forms, tables)

## Local development

API + Postgres must be available (see [backend local
dev](../backend/README.md#local-development) or root Compose). The API must
allow this origin via `CORS_ORIGINS` (include `http://localhost:3000`).

```bash
cd apps/frontend
cp .env.example .env.local   # if needed
npm install
npm run dev
```

App: http://localhost:3000 · Sign-in: http://localhost:3000/signin ·
Reservas: http://localhost:3000/reservas

```bash
# .env.local (not committed) — see `.env.example`
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_LOGIN_REDIRECT_URL=/reservas
```

## Auth workflow (frontend ↔ API)

Cross-origin calls use `credentials: "include"` so the API can set/read the
HttpOnly **refresh** cookie. The **access** JWT is kept in JS memory only.

```text
1. /signin → POST {API}/login
     ← access_token (memory) + Set-Cookie refresh_token (API host)
2. Redirect to NEXT_PUBLIC_LOGIN_REDIRECT_URL (default /reservas)
   or ?callbackUrl=… (relative paths only)
3. (admin) layout boots → POST {API}/refresh if memory empty
     fail → /signin?callbackUrl=…
4. API calls → Authorization: Bearer <access>
     on 401 → refresh once → retry; still 401 → sign-in
5. Header “Cerrar sesión” → POST {API}/logout + clear memory → /signin
```

Details and curl examples: [backend Auth](../backend/README.md#auth).

`/signup` remains TailAdmin UI only (register API not wired from the admin —
see GitHub #47). Temporary text loading states (`Cargando…` /
`Verificando sesión…`) are tracked in #50.

## Reservas list

`/reservas` loads live data via authenticated `GET /reservas?skip=&limit=100`
(loops until `total` is covered), then filters/sorts client-side. Server-side
list filters: #46. Edit / share modal polish: #40 / #48.

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Dev server |
| `npm run build` | Production build |
| `npm start` | Serve production build |
| `npm run lint` | ESLint |

## Docker (portable)

```bash
# from repo root
docker compose up --build frontend
# or
docker build -t vivecaribe-frontend ./apps/frontend
```

Uses Next.js `output: 'standalone'` and listens on **3000**.

## Deploy

- **Vercel project:** `vivecaribe-frontend` · Root Directory `apps/frontend` ·
  Framework **Next.js** (native — not the container image)
- **Portable / AWS:** [`Dockerfile`](Dockerfile)
- **Ignored Build Step:** `git diff HEAD^ HEAD --quiet -- .`

| Variable | Notes |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | Public API origin, e.g. `https://vivecaribe.vercel.app` |
| `NEXT_PUBLIC_LOGIN_REDIRECT_URL` | Post-login path, default `/reservas` |

API project must set `CORS_ORIGINS` to include this UI origin (and
`http://localhost:3000` for local).

Production: https://vivecaribe-frontend.vercel.app
