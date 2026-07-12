# fly-safe

A live, **informational-only** dashboard for travelers on India → US routes via a Gulf
hub. Given a route + date, it shows — with a source and timestamp on every value —
whether the flights are operating, the official travel-advisory levels, the current
airspace/conflict-zone bulletin, and how the airline has handled past escalations.

It states **no opinion and gives no advice**. It surfaces sourced facts and links so
travelers can decide for themselves, and it **fails safe** — showing stale/unavailable
rather than ever presenting unverified data as current.

**v1 route:** Mumbai (BOM) → Doha (DOH) → Atlanta (ATL), Qatar Airways.

## Structure

- `backend/` — async FastAPI service: polls sources on a schedule, caches, serves a JSON API.
- `frontend/` — React SPA (Vite + shadcn/Radix) rendering the cached data.
- `NOTES.md` — research, design decisions, and the build plan.

> ⚠️ Work in progress.
