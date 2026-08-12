# Project brief — ViveCaribe

## What this is

ViveCaribe is an API-first booking platform for guided experiences in the
Caribbean (e.g. Cartagena / Barranquilla stadium tours). Operators receive
booking confirmations from channels such as GetYourGuide, Viator, Homefans,
and first-party Propio (Grupo Vive Caribe / WooCommerce via Zoho Mail);
the system normalizes those bookings into a shared `Reserva` model.

A Next.js admin UI (`apps/frontend`) provides the operator-facing dashboard
(TailAdmin-based starter). Backend and frontend deploy as **independent**
Vercel projects from the same GitHub monorepo.

## Goals

1. Expose a durable business API (`User`, `Reserva`, future booking endpoints).
2. Automate email ingest so new bookings land in Postgres without manual copy.
3. Keep WhatsApp notification optional until Meta Business is approved.
4. Deploy API as serverless-friendly FastAPI container on Vercel + Supabase
   Postgres; deploy UI as native Next.js on a separate Vercel project.
5. Keep portable Docker images per app for Compose and future AWS/ECS/K8s.

## Non-goals (current phase)

- Serving frontend and API from a single container / single `$PORT`.
- Real Meta WhatsApp Cloud API sends (NoOp stub only).
- Multi-tenant SaaS for other operators.

## Delivery sequence

Issues #1–#8 delivered scaffold through Vercel container deploy / cron auth.
Follow-on on main: Propio via Zoho Mail, Zoho OTP via GYG Gmail, extractor
income/country hardening, monorepo `#36`, frontend + dual Vercel `#38`,
reservas list + auth `#41` / `#49`, loading UI `#50`, detail share `#48`,
list filters + `es_hoy` `#46` / `#54`, operator fields + `paid_at`
`#55` / `#56`.
Open `#41` children: Edit `#40`, signup `#47`.
