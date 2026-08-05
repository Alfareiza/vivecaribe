# Project brief — ViveCaribe

## What this is

ViveCaribe is an API-first booking platform for guided experiences in the
Caribbean (e.g. Cartagena / Barranquilla stadium tours). Operators receive
booking confirmations from channels such as GetYourGuide, Viator, and Homefans;
the system normalizes those bookings into a shared `Reserva` model.

## Goals

1. Expose a durable business API (`User`, `Reserva`, future booking endpoints).
2. Automate email ingest so new bookings land in Postgres without manual copy.
3. Keep WhatsApp notification optional until Meta Business is approved.
4. Deploy as a serverless-friendly FastAPI app on Vercel + Supabase Postgres.

## Non-goals (current phase)

- Full frontend / customer portal.
- Real Meta WhatsApp Cloud API sends (NoOp stub only).
- Multi-tenant SaaS for other operators.

## Delivery sequence

Issues #1–#6 delivered scaffold, domain, persistence, auth, automation BC, and
the pipeline API. Issue #7 hardens tests/docs. Issue #8 covers deploy/cron.
