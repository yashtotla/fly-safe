"""In-process poll scheduler.

Gated by settings.poll_enabled (OFF in dev, so uvicorn --reload never spends
AeroDataBox units — the API serves fixture-seeded data instead). Each source polls
on its own cadence; due-ness is based on last_success (persisted), so restarts
don't re-poll fresh data. A failed poll keeps last-known data, records the failure,
and (past the threshold) files a GitHub issue.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import fetch, store
from app.alerts import open_issue_if_needed
from app.catalog import ROUTES
from app.config import settings
from app.db import async_session
from app.models import SourceHealthRow
from app.sources import aerodatabox, easa, statedept

log = logging.getLogger("flysafe.scheduler")
CHECK_INTERVAL = 300  # seconds between due-ness checks


async def _due(session: AsyncSession, source: str, cadence: int) -> bool:
    row = (
        await session.execute(select(SourceHealthRow).where(SourceHealthRow.source == source))
    ).scalar_one_or_none()
    if row is None or row.last_success_at is None:
        return True
    last = row.last_success_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=dt.UTC)
    return (dt.datetime.now(dt.UTC) - last).total_seconds() >= cadence


async def poll_advisories(session: AsyncSession, client: httpx.AsyncClient) -> None:
    raw = await fetch.fetch_advisories(client)
    codes = {c for r in ROUTES.values() for c in r.advisory_countries} - {"US"}
    for a in statedept.parse(raw, codes):
        await store.upsert_advisory(
            session,
            country_code=a.country_code,
            payload=a.model_dump(mode="json"),
            level=a.level,
            source=statedept.SOURCE,
            source_url=a.link,
            source_tier=statedept.SOURCE_TIER,
            max_age_seconds=settings.advisory_max_age_seconds,
            fetched_at=store.utcnow(),
        )


async def poll_czibs(session: AsyncSession, client: httpx.AsyncClient) -> None:
    html = await fetch.fetch_czibs(client)
    for c in easa.active(easa.parse(html)):
        await store.upsert_czib(
            session,
            identifier=c.identifier,
            payload=c.model_dump(mode="json"),
            status=c.status,
            source=easa.SOURCE,
            source_url=c.url or easa.LISTING_URL,
            source_tier=easa.SOURCE_TIER,
            max_age_seconds=settings.czib_max_age_seconds,
            fetched_at=store.utcnow(),
        )


async def poll_flights(session: AsyncSession, client: httpx.AsyncClient) -> None:
    yday = (store.utcnow() - dt.timedelta(days=1)).strftime("%Y-%m-%d")
    seen: set[str] = set()
    for route in ROUTES.values():
        for leg in route.legs:
            if leg.flight_number in seen:
                continue
            seen.add(leg.flight_number)
            raw = await fetch.fetch_flight(client, leg.flight_number, yday, yday)
            for f in aerodatabox.parse(raw):
                await store.upsert_flight(
                    session,
                    flight_number=leg.flight_number,
                    flight_date=yday,
                    payload=f.model_dump(mode="json"),
                    status=f.status.value,
                    source=aerodatabox.SOURCE,
                    source_url=f"https://www.flightradar24.com/data/flights/{leg.flight_number.lower()}",
                    source_tier=aerodatabox.SOURCE_TIER,
                    max_age_seconds=settings.flight_max_age_seconds,
                    fetched_at=store.utcnow(),
                )


async def _guarded(session, client, source, coro) -> None:
    try:
        await coro
        await store.record_success(session, source)
    except Exception as e:  # noqa: BLE001 — any failure is a source failure: fail safe
        n = await store.record_failure(session, source, repr(e))
        log.warning("poll failed for %s (failure #%d): %r", source, n, e)
        try:
            await open_issue_if_needed(client, source, n, repr(e))
        except Exception:  # noqa: BLE001 — alerting must never crash the poller
            log.exception("alert failed for %s", source)
    await session.commit()


_PLAN = (
    (statedept.SOURCE, "advisory_poll_seconds", poll_advisories),
    (easa.SOURCE, "czib_poll_seconds", poll_czibs),
    (aerodatabox.SOURCE, "flight_poll_seconds", poll_flights),
)


async def run_scheduler() -> None:
    log.info("scheduler started")
    async with httpx.AsyncClient() as client:
        while True:
            try:
                async with async_session() as session:
                    for source, cadence_attr, fn in _PLAN:
                        if await _due(session, source, getattr(settings, cadence_attr)):
                            log.info("polling %s", source)
                            await _guarded(session, client, source, fn(session, client))
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                log.exception("scheduler tick failed")
            await asyncio.sleep(CHECK_INTERVAL)
