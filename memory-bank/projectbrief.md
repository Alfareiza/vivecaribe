# Project brief — ViveCaribe

## What this is

ViveCaribe is an API-first booking platform for guided experiences in the
Caribbean (e.g. Cartagena / Barranquilla stadium tours). Operators receive
booking confirmations from channels such as GetYourGuide, Viator, Homefans,
and first-party Propio (Grupo Vive Caribe / WooCommerce via Zoho Mail);
the system normalizes those bookings into a shared `Reserva` model.

## Goals

1. Expose a durable business API (`User`, `Reserva`, future booking endpoints).
2. Automate email ingest so new bookings land in Postgres without manual copy.
3. Keep WhatsApp notification optional until Meta Business is approved.
4. Deploy as a serverless-friendly FastAPI app on Vercel + Supabase Postgres.

## Non-goals (current phase)

- Scaffolded Next.js admin UI (folder `apps/frontend` exists empty only).
- Serving the frontend from the Vercel API container.
- Real Meta WhatsApp Cloud API sends (NoOp stub only).
- Multi-tenant SaaS for other operators.

## Delivery sequence

Issues #1–#8 delivered scaffold through Vercel container deploy / cron auth.
Follow-on on main: Propio via Zoho Mail, Zoho OTP via GYG Gmail, extractor
income/country hardening.
