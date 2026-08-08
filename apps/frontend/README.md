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
dev](../backend/README.md#local-development) or root Compose).

```bash
cd apps/frontend
npm install
npm run dev
```

App: http://localhost:3000

```bash
# .env.local (not committed)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

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

Production promotion for this project is intentional (preview-first). See the
root README deploy table and PR / release process.
