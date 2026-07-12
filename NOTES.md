# fly-safe — Research & Design Notes

_Feasibility spike. Last updated: 2026-07-13. Author: research pass with Claude._

A live, **informational** dashboard that shows a traveler the current + historical
situation affecting their India→US-via-Gulf journey, so they can decide for
themselves. First route: **Mumbai (BOM) → Doha (DOH) → Atlanta (ATL), Qatar Airways.**

---

## 1. Locked decisions

| Decision | Choice |
|---|---|
| First route | BOM → DOH → ATL, Qatar Airways (QR) |
| Audience | Indian students flying to US via Gulf hubs, fall 2026 cohort |
| Runtime | **Python backend** (FastAPI + pydantic) + light web frontend |
| Liveness | **Always-on API server**, polls sources on a schedule + caches |
| Flight data | Small paid tier acceptable (AeroDataBox / FlightAware) |
| LLM policy | **No generative inference on the live/safety path.** LLM only for (a) drafting historical cards that are human-reviewed once before deploy, then frozen, and (b) optional news triage into *leads* (never facts). |
| Hands-off | = **no routine chore the live system needs a human to perform to stay correct.** Runs unattended, **fails safe on its own.** Coming back to *improve* it as it grows / on feedback is expected. |

## 2. Non-negotiable principles (the product IS these)

1. **Purely informational, zero opinion.** We never compute our own risk verdict.
   We surface each authority's *own* classification, verbatim, with attribution.
2. **Every datum carries `source + source_url + fetched_at`.** Enforce in the
   pydantic schema so an un-sourced record cannot exist.
3. **Claim ↔ source-tier match.** "Is the airspace restricted?" answered only from
   official sources. "Is my flight operating?" from flight-status data. **News is
   context/leads only — it never becomes a status claim.**
4. **Freshness contract per field.** Each field has a max age. Past it, show
   "last confirmed Xh ago — unverified since" + link. **Never stale-as-fresh,
   never silence, never a guess.** A failed fetch degrades to last-known + a
   visible stale flag.
5. **Conflict = show both**, side by side, with timestamps.
6. **Always one-click to the primary source.** We are an organized signpost, not
   the final word. This is the honest posture given no aggregator can promise zero
   error — same stance OpsGroup/Safe Airspace themselves take.
7. **Hands-off ⇒ deterministic live path.** No human is watching in production, so
   the live pipeline uses structured APIs + verbatim-quoted official text only.
   ("Hands-off" = no routine chore needed to stay correct; *improving* it later is fine.)
8. **No static "current" facts.** Any time-sensitive value (e.g. "Kuwait closed
   until Aug 4") is fetched live or not asserted — never hard-coded, or it silently
   rots and becomes a manual-refresh chore. Historical cards are exempt (the past
   doesn't go stale).

## 3. Data source inventory

Tiers: **T0** = official/regulatory (may assert legal airspace status) ·
**T1** = operational facts (actual flights) · **T2** = expert aggregator (report
with attribution) · **T3** = news (context/leads only).

| Source | Tier | Gives us | Access / auth | Cost | Machine-readable? | Role & notes |
|---|---|---|---|---|---|---|
| **US State Dept Travel Advisories** | T0 | Advisory level (1–4) + threats per country (Qatar, India, transit) | Official API `cadataapi.state.gov/api/TravelAdvisories`; also RSS; MIT community JSON feeds (`josh/us-state-travel-advisories-feeds`) | Free | ✅ JSON | Primary "plan/prepare" signal. Report level verbatim + link. |
| **FAA NOTAM / NMS API** | T0 | NOTAMs, conflict-zone prohibitions (GeoJSON/AIXM) | Email `NOTAMS@faa.gov` for OAuth client_credentials | Free | ✅ GeoJSON/AIXM (but raw NOTAM text is cryptic) | Use to **flag + link** relevant NOTAMs. ⚠️ Do NOT auto-derive "airspace closed" from raw geometry — top misparse hazard. |
| **EASA CZIB** (Conflict Zone Info Bulletins) | T0 | Authoritative ME/Gulf risk bulletin + validity dates. Current: `2026-03-R13` (extended) | Web page + email subscription | Free | ❌ **No API/data format found** — HTML/PDF prose | Show bulletin existence + validity window + **verbatim summary + link**. Do not re-interpret. See §7 open item. |
| **AeroDataBox** | T1 | Live flight status by number, routing, delays, cancellations | RapidAPI / API.Market key | **Free 600 units/mo; PRO $5/mo = 6,000 units** | ✅ JSON | **Spine of the live view.** See §5 for unit math. Cheapest good fit. |
| **FlightAware AeroAPI** | T1 | Flight status/tracks; history back to 2011 | API key | Free allowance modest (v4 ~$5/mo credit *or* Starter 500 req/mo — **verify at signup**); Bronze $25/mo | ✅ JSON | Optional. Richer history/tracks; pricier. Reserve for v2 if OpenSky insufficient. |
| **OpenSky Network** | T1/T2 | Live positions; **historical trajectories** | Public REST (no auth); **full historical set free for university-affiliated researchers** (apply w/ GT email) | Free | ✅ JSON + Python/R/Trino | Live map + v2 diversion/reroute reconstruction. GT email unlocks bulk history. |
| **Qatar Airways** alerts | T1 | Airline's own travel alerts, operational updates, flight-status | `qatarairways.com/en/travel-alerts.html` (prose), trade-portal Operational Update, `fs.qatarairways.com` | Free | ⚠️ Mostly prose HTML | Link + quote. Prefer AeroDataBox for the operational *facts*. |
| **Safe Airspace** (OpsGroup) | T2 | Conflict-zone risk level per country, NOTAM digests, event history | Public website | Free | ❌ No API; scraping ToS unclear | Excellent, well-regarded. **Get reuse permission** (`report@safeairspace.net`) or deep-link + attribute only. See §7. |
| **News** (Reuters/AP/Al Jazeera/etc.) | T3 | Context; escalation *signal* | RSS / news APIs | Free–low | ✅ RSS | Leads only. Optional LLM triage. Never a status claim. |
| **India MEA / DGCA advisory** | T0 | India-side advisory for Qatar/transit | Web (format TBD) | Free | ❓ TBD | Secondary — verify availability (§7). |

## 4. Feasibility verdict

**An accurate live pipeline is feasible.** All safety-critical *live* facts come
from structured APIs:

- **Is the flight operating / rerouted / delayed?** → AeroDataBox (JSON). This is
  the strongest, hardest-to-get-wrong, most reassuring signal.
- **What advisory level applies?** → State Dept API (JSON), reported verbatim.
- **Where is the aircraft now?** → OpenSky (JSON).

The prose-only sources (EASA CZIB, QR alerts, Safe Airspace) are handled by
**link + verbatim quote**, with no risky interpretation — which satisfies both the
zero-wrong-info and hands-off constraints. Raw NOTAMs are used only to flag/link,
never to auto-conclude closures.

## 5. Cost analysis

**Hosting — effectively free for year one via GT student email:**
- **Azure for Students**: $100 credit/yr, **renewable annually**, **no credit card**,
  includes App Service — can host FastAPI free. (Verify GT `.edu`/`gatech.edu`
  eligibility.)
- **GitHub Student Developer Pack**: DigitalOcean **$200 credit**, Azure **$100**,
  plus **free domain** (.me via Namecheap / .tech for 1 yr).
- **Fly.io** as the no-strings fallback after credits lapse: ~$3–6/mo for a small
  always-on machine. DB free at this scale (SQLite on a volume, or Neon/Supabase
  free Postgres).

**Flight API — the only real recurring cost, and it's tiny:**
- AeroDataBox flight-status endpoint is Tier 2–3 (2–6 units/call).
- Naive 24/7 polling of 2 flight numbers every 3h ≈ 480 calls/mo → 960–2,880 units.
  Free tier (600) is borderline; **PRO ($5/mo, 6,000 units) is safe headroom.**
- **Smart polling** (only from ~3h before departure to arrival) likely fits the
  **free 600 units/mo** even for the single route.

**Bottom line: year-one run cost ≈ $0–5/mo.** The $20 budget is not a constraint.

## 6. LLM policy (confirmed)

- ❌ Never on the live/airspace/flight-status path.
- ✅ Draft the **historical track-record cards** (e.g. QR's 23 Jun 2025 Doha
  recovery). Human-reviewed once before deploy → frozen → compatible with hands-off.
- 🟡 Optional: triage news RSS into **leads** (flag "possible escalation"), never
  promoted to a status without an authoritative structured source confirming.
- If any prose extraction is ever automated, guard = temp 0 + display the extracted
  value next to the **verbatim source sentence + link** so errors are visible, not
  laundered.

## 7. Open questions / action items

1. **EASA CZIB — DECIDED: keep it simple.** No API; changes ~monthly. v1 = a
   **self-updating pointer**: fetch the current bulletin title + validity dates on
   schedule, show them + a direct link, no stored summary to hand-maintain, no
   geometry parsing. If the fetch breaks → degrade to "check official source →".
   Enrich later (richer extraction) once we have user feedback.
2. **Safe Airspace reuse.** Email `report@safeairspace.net` for permission
   (non-commercial student project, will attribute), or deep-link + cite only.
3. **FAA NMS API access.** Email `NOTAMS@faa.gov` to get OAuth client creds; lead
   time unknown — start early.
4. **FlightAware v4 pricing.** Confirm current free allowance at signup (v3 page is
   EOL). Likely moot if AeroDataBox suffices.
5. **AeroDataBox exact tier** for "flight status by number" — confirm 2 vs 6 units.
6. **India MEA/DGCA advisory** — confirm a usable, machine-readable source exists.
7. **Azure for Students eligibility** with the specific GT email domain.

## 8. Architecture sketch (pre-build, not final)

```
sources ─▶ fetchers (1/source, isolated) ─▶ normalizer ─▶ Signal records
                                                            (pydantic: value +
                                                             source + url +
                                                             fetched_at +
                                                             effective range +
                                                             max_age)
                                                                │
scheduler (APScheduler, per-source cadence) ── drives fetchers ─┘
                                                                │
                                                        SQLite/Postgres
                                                        (current + change-log)
                                                                │
                                            FastAPI  ── GET /route/{itinerary}
                                                                │
                                        thin web frontend (info-dense, timestamps,
                                        freshness badges, one-click source links)
```

- **Per-source cadence** matched to real update rate: flight status every few hours
  (or windowed around departures); advisories/CZIB daily (rarely move); news often.
- **Change-log** table gives a free "what changed since yesterday" view + audit trail.
- Frontend renders the snapshot only — no logic, no verdicts.

## 9. Current situation snapshot (2026-07-13, reference only)

_Validates the product; not the live data model._
- **Region:** heightened tension, not active war. Ceasefire/MOU regime with
  sporadic strikes (a US–Iran flare-up ~7–8 Jul 2026 produced **no new airspace
  closures**).
- **Qatar/Doha:** airspace reopened, "almost back to normal"; QR operating ~140
  daily Doha departures (growing from 16 Jun 2026) but with **reduced frequencies,
  a few routes still suspended, A380s grounded, all Doha traffic via
  QCAA-authorized corridors.**
- **Kuwait:** overflights prohibited (per research, through ~4 Aug 2026).
- **Iran:** west closed; east reopened above FL285. **UAE/Saudi:** open (GPS
  jamming + ATC congestion on southern bypass are the live irritants).
- **QR track record (hero card):** 23 Jun 2025 Al Udeid strike closed Qatari
  airspace with ~100 QR aircraft inbound → 90+ diversions, 20,000+ pax, all cleared
  <24h, scheduled ops resumed ~18h, **zero safety incidents.**

## 10. Sources

- Qatar Airways CEO open letter (Jun 2025): https://www.qatarairways.com/press-releases/en-WW/251548-to-our-passengers-an-open-letter-from-qatar-airways-group-chief-executive-officer/
- Qatar Airways travel alerts: https://www.qatarairways.com/en/travel-alerts.html
- QR flight status 2026 summary (Wego): https://blog.wego.com/qatar-airways-flight-status-2026/
- OpsGroup — Middle East current operational picture: https://ops.group/blog/middle-east-airspace-current-operational-picture/
- Safe Airspace database: https://safeairspace.net/summary/ · About: https://safeairspace.net/about/
- EASA CZIBs: https://www.easa.europa.eu/en/domains/air-operations/czibs · current ME bulletin: https://www.easa.europa.eu/en/domains/air-operations/czibs/2026-03-r13
- FAA NMS/NOTAM API: https://nms.aim.faa.gov/ · portal: https://api.faa.gov/
- US State Dept advisories API: https://cadataapi.state.gov/api/TravelAdvisories · RSS: https://travel.state.gov/content/travel/en/rss.html · JSON feeds: https://github.com/josh/us-state-travel-advisories-feeds
- AeroDataBox pricing: https://aerodatabox.com/pricing/
- FlightAware AeroAPI: https://www.flightaware.com/commercial/aeroapi/
- OpenSky Network data access: https://opensky-network.org/data · Trino historical: https://openskynetwork.github.io/opensky-api/trino.html
- GitHub Student Pack: https://education.github.com/pack · Azure for Students: https://azure.microsoft.com/en-us/free/students

## 11. Design decisions — interview log (2026-07-13)

_Reached one-by-one; not yet enacted. Awaiting final shared-understanding confirmation._

**Product / scope**
- **Route picker gated by a supported-routes catalog** — the picker lists only routes we have verified data for (start: BOM–DOH–ATL / QR); the option list grows as the backend can serve more. Never renders thin/dishonest data.
- **v1 panels = "core reassurance set":** (1) flight-operating status, (2) official travel-advisory levels, (3) airspace/CZIB pointer, (4) historical track-record cards. Deferred to v2: live map, news leads.
- **Input granularity = route + travel date.** Flight panel = your-date *scheduled* flights (no fabricated live status for a future date) + the route's recent operating health as the honest present-tense signal.
- **Flight lookup = curate flight numbers per route leg** (recorded in the catalog when a route is added); show *all* of a day's flights (short list — never guess which is the user's).
- **Advisories shown only for countries you're physically in** (India / Qatar / US), not overflown countries. _(content default)_

**Architecture**
- **Topology:** React SPA (Vite + shadcn/Radix, static build) + FastAPI JSON API. Provenance crosses the API boundary → every value in the JSON carries `source + url + fetched_at + freshness`; frontend must render it and never silently transform a fact.
- **Refresh:** scheduled poll + cache; API serves *only* from cache. Reads never wait on / fail with sources; cost = f(poll frequency), not traffic.
- **Runtime:** async FastAPI. Async chosen for the multi-source fetch fan-out (`asyncio.gather` over async `httpx`), not raw necessity at v1 scale.
- **Scheduler:** in-process background task, started on app startup. Fits an always-on single instance.
- **Storage / ORM:** SQLite (`aiosqlite` → `asyncpg` later) via SQLAlchemy 2.0 + Pydantic v2. `create_all()`. **No Alembic, no SQLModel.** Move to Supabase later = connection-URL swap; disposable snapshot repopulates, only the change-log migrates.
- **Data model:** **decoupled per-source models** (each in its natural shape; a new source is a new model, never a reshaping) + a shared **provenance mixin** (mandatory metadata columns; zero constraint on payload) + one generic **change-log** table + an **assembly layer** that composes the per-route bundle at cache-build time. Uniform only on the definitional invariant (provenance); decoupled on payload shapes.
- **Freshness:** 3-state per value — **fresh / stale / unavailable** — derived from a per-source `max_age`. User-facing = value + state + last-successful-check timestamp. Failed-attempt / `last_checked_at` data is **internal-only, never in the public API**. `max_age` tuned to volatility (short for fast/critical sources so staleness surfaces fast). _(thresholds = content default)_
- **Failure handling:** N consecutive failures for a source → auto-open a **deduped GitHub issue** + expose an internal **`/health` endpoint** listing each source's last success/failure/state.

**Deployment & delivery**
- **Repo:** monorepo (`/backend` FastAPI + `/frontend` Vite React + `NOTES`/docs). Atomic cross-cutting PRs; failure-alert issues land in the same tracker.
- **Backend host:** Fly.io — always-on container + persistent volume (SQLite on disk), low ops, ~$3–6/mo.
- **Frontend host:** Vercel, used as a **dumb static host only** (all logic stays on FastAPI/Fly; avoid Vercel-specific features). Needs CORS on the API. Hobby tier = non-commercial (fine). Easy exit if we monetize: upgrade to Vercel Pro (zero migration) or move to Cloudflare Pages (~1h).
- **Secrets:** Fly secrets (runtime) + GitHub Actions secrets (CI). Never in-repo.
- **CI/CD:** GitHub Actions — lint + tests on PR, deploy on merge to `main`.
- **Domain:** start on `*.fly.dev` / Vercel default; point a free student `.tech`/`.me` later. Name TBD.

**Historical cards**
- Frozen, human-reviewed editorial content as **version-controlled JSON/MDX in the repo** (PR diff = the approval gate; git = history; no live pipeline). Backend loads + serves them via the **same API** → one data path, one provenance-rendering path on the frontend.

**Quality gates**
- **Primary defense = runtime validate-on-ingest:** every fetched response parsed through a strict Pydantic schema; a validation failure is treated as a fetch failure → keep last-known, fire the alert, never store questionable data. Parsers also **reject unknown enum values** (catches renamed status codes).
- **Tests are evidence-driven, not guessed:** defer writing unit tests until Phase 1 reveals the real data shapes + edge cases, then write targeted parser tests for what actually exists. No frontend/E2E/coverage targets for v1.

**Build strategy**
- Build the MVP until it works **properly (locally first)**; **deployment is its own later phase** — solve CORS/hosting/CI when it's time to deploy, not up front.
- Within the build: source **reconnaissance first** (can't model decoupled schemas or write real tests until we've seen the payloads).

## 12. Build plan (v1) — awaiting confirmation, not enacted

1. **Reconnaissance.** Sign up AeroDataBox key. Pull *real* responses for BOM–DOH–ATL/QR and document actual shapes + edge cases: AeroDataBox flight-by-number+date (on-time/delayed/cancelled/diverted/missing/timezone), State Dept advisory API (IN/QA/US), EASA CZIB page structure (for the self-updating pointer), historical sources (for cards). Save fixtures. → outputs the real schemas.
2. **Data layer.** Decoupled per-source SQLAlchemy 2.0 models + shared provenance mixin; parsers with validate-on-ingest + reject-unknown-enum, built against Phase-1 fixtures; generic change-log; SQLite via aiosqlite, `create_all()`. Targeted unit tests for the *observed* edge cases.
3. **Poller + assembly + API.** In-process async scheduler (per-source cadence, cached); assembly layer composes the per-route bundle; FastAPI JSON API (`/route/{itinerary}?date=`); 3-state freshness derivation; failure → deduped GitHub issue + `/health`; historical cards loaded from repo content and served.
4. **Frontend.** Vite + React + shadcn/Radix. Route picker gated by the supported-routes catalog (v1 = [BOM–DOH–ATL/QR]); the four panels rendering value + provenance + freshness uniformly; disclaimer; shareable URL (`?from&hub&to&airline&date`). Info-dense, UI-light. Iterate until it works locally.
5. **Deployment.** Fly.io (backend + volume + secrets), Vercel (SPA), CORS, GitHub Actions CI. Handle deploy issues here.

**Definition of done (v1):** a shareable URL for BOM–DOH–ATL + a date renders the four panels with accurate, sourced, timestamped data; live data refreshes on schedule; every value shows its source + freshness; stale/unavailable states render correctly; a broken source fails safe (last-known + auto GitHub issue) and never shows wrong data; historical cards reviewed + frozen; disclaimer present; deployed and reachable.

## 13. Content defaults (I'll set these; veto any)

- **Advisory scope:** only countries you're physically in — IN / QA / US — not overflown countries.
- **Route-health signal:** last ~7-day operated/cancelled summary + your-date scheduled flights (confirm feasibility vs the API's date-range in Phase 1).
- **`max_age` + poll cadence (rough; tune per source):** flight status **polled ~1×/day** (budget-bound — see §14), max_age ~24–30h · advisories ~24h · CZIB pointer ~24h.
- **Historical events (curate + human-review each):** Apr 2024 (Iran→Israel #1) · Oct 2024 (Iran→Israel #2) · 13–24 Jun 2025 (12-day war) · **23 Jun 2025 (Doha airspace closure — hero card)** · Feb 2026.
- **Conflict display:** two sources of the same kind → show both, side by side, with attribution + timestamps.
- **API surface:** public, read-only, no auth for v1.
- **Disclaimer (draft):** "Informational only. This dashboard aggregates public sources with timestamps and links; it is not advice and not a safety guarantee. Verify with official sources before making travel decisions."

## 14. Reconnaissance findings

**AeroDataBox — flight status by number** (fixture: `backend/tests/fixtures/aerodatabox/QR557_2026-07-12.json`)
- Endpoint: `GET /flights/number/{number}/{dateFrom}/{dateTo}` on host `aerodatabox.p.rapidapi.com`; headers `x-rapidapi-key` + `x-rapidapi-host`. Key is a RapidAPI key.
- **Returns a LIST** of flight objects (one per operating day in the range).
- Per flight: `departure`/`arrival` = `{airport{icao,iata,name,shortName,municipalityName,location{lat,lon},countryCode,timeZone}, scheduledTime{utc,local}, revisedTime{utc,local}?, runwayTime{utc,local}? (arrival actual), terminal?, gate?, baggageBelt?, quality[]}`; plus `number` ("QR 557", spaced), `status` (enum, e.g. "Arrived"), `codeshareStatus` ("IsOperator"), `isCargo`, `aircraft{model?}`, `airline{name,iata,icao}`, `greatCircleDistance{…}`, `lastUpdatedUtc`.
- **Modeling / edge cases:** times are **non-ISO** strings (`"2026-07-11 22:40Z"`, space not `T`) → parse to tz-aware datetimes carefully (this is the timezone test). `revisedTime`/`runwayTime`/`terminal`/`gate`/`baggageBelt`/`aircraft.model` are OPTIONAL. `status` is an enum → map known values, guard-fail on unknown. Delay = `revisedTime` vs `scheduledTime`. Cancelled/Diverted are the concerning statuses.
- **⚠ BUDGET:** costs **6 API units/call** (quota header dropped 600→594 on one call) → **~100 flight-status calls/month.** Drives the ~1×/day cadence. TODO: check whether a multi-day range costs the same 6 units (would let one call cover N days of route health).
- **Route catalog (BOM–DOH–ATL / QR):** BOM→DOH = **QR557**, DOH→ATL = **QR755** (both daily, A350-1000; QR556/QR756 are the returns).

**US State Dept advisories** (`GET https://cadataapi.state.gov/api/TravelAdvisories` — free JSON; fixture `backend/tests/fixtures/statedept/advisories_sample.json`)
- List of ~213 items; keys `Title, Link, Category, Summary, Published, Updated, id`.
- **`Category` is a list of ISO codes** (`["QA"]`) → match country by code. **Level lives only in `Title`** ("Qatar - Level 3: Reconsider Travel") → parse level+label by regex; guard-fail if "Level N" absent. `Summary` is HTML; `Link`/`id` = official advisory URL (provenance); times ISO w/ offset.
- **Current (route-relevant):** Qatar **Level 3** (armed-conflict risk; ordered departure Mar 2 2026), India **Level 2**, **US = no advisory** (State Dept doesn't advise on the US) → render US leg as "no advisory issued". Sample edge cases: Iran L4, "Mexico Travel Advisory -" (multi-word title), Liberia.

**EASA CZIB** (listing `https://www.easa.europa.eu/en/domains/air-operations/czibs` — free, **server-rendered HTML**, scrapeable; raw fixture gitignored)
- No API. Parse the listing: identifier, title, status (Active/Withdrawn), validity range, detail URL. Needs an HTML parser (bs4); fail-safe = link to the listing page.
- **Current:** the blanket **"Middle East and Persian Gulf" bulletin (2026-03-R14) is WITHDRAWN** (was 28/02–08/07/2026). Active country CZIBs: **Iran CZIB-2026-04, Iraq CZIB-2026-05, Lebanon CZIB-2026-06** (expire 31/08/2026).
- **Panel framing:** show active regional CZIBs as *overflight context* (Iran/Iraq for this corridor) with validity + link — NOT a claim the flight overflies them. Complements advisories (in-country) vs airspace (overflown).
