# ViveCaribe Frontend

Admin UI for ViveCaribe (booking operations). Next.js App Router app under
`apps/frontend` in the monorepo.

## Tech stack

- **Next.js** 16 (App Router)
- **React** 19
- **TypeScript**
- **Tailwind CSS** v4
- UI starter based on TailAdmin (layouts, charts, forms, tables)

## Local development

```bash
cd apps/frontend
npm install
npm run dev
```

App: http://localhost:3000

Point the UI at the API with:

```bash
# .env.local (not committed)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run the API + Postgres from the repo root (`docker compose up -d db` and
uvicorn, or full Compose — see root README).

## Docker (portable)

```bash
# from repo root
docker compose up --build frontend
# or
docker build -t vivecaribe-frontend ./apps/frontend
```

Image uses Next.js `output: 'standalone'` and listens on port **3000**.

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Dev server |
| `npm run build` | Production build |
| `npm start` | Serve production build |
| `npm run lint` | ESLint |

## Deploy

- **Vercel:** project `vivecaribe-frontend`, Root Directory `apps/frontend`,
  Framework Next.js (native — not the container image).
- **AWS / other:** reuse `apps/frontend/Dockerfile`.

API project remains separate (`vivecaribe` → `apps/backend`).
