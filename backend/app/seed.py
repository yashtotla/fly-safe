"""Dev seeding: populate the cache from the captured recon fixtures so the API
serves real-shaped data with ZERO external calls (protects the AeroDataBox budget).

Seeded rows use a fixed `fetched_at` = the recon capture date, so freshness ages
honestly (fresh near that date, stale later) rather than faking "just confirmed".
Only seeds a source when its table is empty.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import store
from app.config import settings
from app.models import AdvisoryRow, CzibRow, FlightStatusRow
from app.sources import aerodatabox, easa, statedept

FIX = pathlib.Path(__file__).resolve().parent.parent / "tests" / "fixtures"
# When the committed fixtures were captured (see NOTES §14).
CAPTURED_AT = dt.datetime(2026, 7, 13, tzinfo=dt.UTC)


async def _empty(session: AsyncSession, model) -> bool:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one() == 0


async def seed_if_empty(session: AsyncSession) -> None:
    if await _empty(session, FlightStatusRow):
        raw = json.loads((FIX / "aerodatabox" / "QR557_2026-07-12.json").read_text())
        for f in aerodatabox.parse(raw):
            await store.upsert_flight(
                session,
                flight_number=f.number.replace(" ", ""),
                flight_date="2026-07-12",
                payload=f.model_dump(mode="json"),
                status=f.status.value,
                source=aerodatabox.SOURCE,
                source_url="https://www.flightradar24.com/data/flights/qr557",
                source_tier=aerodatabox.SOURCE_TIER,
                max_age_seconds=settings.flight_max_age_seconds,
                fetched_at=CAPTURED_AT,
            )

    if await _empty(session, AdvisoryRow):
        raw = json.loads((FIX / "statedept" / "advisories_sample.json").read_text())
        for a in statedept.parse(raw, {"IN", "QA"}):
            await store.upsert_advisory(
                session,
                country_code=a.country_code,
                payload=a.model_dump(mode="json"),
                level=a.level,
                source=statedept.SOURCE,
                source_url=a.link,
                source_tier=statedept.SOURCE_TIER,
                max_age_seconds=settings.advisory_max_age_seconds,
                fetched_at=CAPTURED_AT,
            )

    if await _empty(session, CzibRow):
        html = (FIX / "easa" / "czibs_sample.html").read_text()
        for c in easa.parse(html):
            await store.upsert_czib(
                session,
                identifier=c.identifier,
                payload=c.model_dump(mode="json"),
                status=c.status,
                source=easa.SOURCE,
                source_url=c.url or easa.LISTING_URL,
                source_tier=easa.SOURCE_TIER,
                max_age_seconds=settings.czib_max_age_seconds,
                fetched_at=CAPTURED_AT,
            )

    await session.commit()
