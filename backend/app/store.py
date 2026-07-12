"""Persistence for polled snapshots.

Upserts each source's row (provenance + JSON payload), appends a change-log entry
when a key field changes, and tracks per-source health (success/failure) for the
/health endpoint and failure alerts.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AdvisoryRow,
    ChangeLogRow,
    CzibRow,
    FlightStatusRow,
    SourceHealthRow,
)


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


async def _log_change(
    session: AsyncSession, source: str, entity_key: str, field: str, old: object, new: object
) -> None:
    if old != new:
        session.add(
            ChangeLogRow(
                source=source,
                entity_key=entity_key,
                field=field,
                old_value=None if old is None else str(old),
                new_value=None if new is None else str(new),
                changed_at=utcnow(),
            )
        )


async def upsert_flight(
    session: AsyncSession,
    *,
    flight_number: str,
    flight_date: str,
    payload: dict,
    status: str,
    source: str,
    source_url: str,
    source_tier: str,
    max_age_seconds: int,
    fetched_at: dt.datetime,
) -> None:
    row = (
        await session.execute(
            select(FlightStatusRow).where(
                FlightStatusRow.flight_number == flight_number,
                FlightStatusRow.flight_date == flight_date,
            )
        )
    ).scalar_one_or_none()
    old_status = row.payload.get("status") if row else None
    if row is None:
        row = FlightStatusRow(flight_number=flight_number, flight_date=flight_date)
        session.add(row)
    row.payload = payload
    row.source, row.source_url, row.source_tier = source, source_url, source_tier
    row.max_age_seconds, row.fetched_at = max_age_seconds, fetched_at
    await _log_change(
        session, source, f"{flight_number}/{flight_date}", "status", old_status, status
    )


async def upsert_advisory(
    session: AsyncSession,
    *,
    country_code: str,
    payload: dict,
    level: int,
    source: str,
    source_url: str,
    source_tier: str,
    max_age_seconds: int,
    fetched_at: dt.datetime,
) -> None:
    row = (
        await session.execute(select(AdvisoryRow).where(AdvisoryRow.country_code == country_code))
    ).scalar_one_or_none()
    old_level = row.payload.get("level") if row else None
    if row is None:
        row = AdvisoryRow(country_code=country_code)
        session.add(row)
    row.payload = payload
    row.source, row.source_url, row.source_tier = source, source_url, source_tier
    row.max_age_seconds, row.fetched_at = max_age_seconds, fetched_at
    await _log_change(session, source, country_code, "level", old_level, level)


async def upsert_czib(
    session: AsyncSession,
    *,
    identifier: str,
    payload: dict,
    status: str,
    source: str,
    source_url: str,
    source_tier: str,
    max_age_seconds: int,
    fetched_at: dt.datetime,
) -> None:
    row = (
        await session.execute(select(CzibRow).where(CzibRow.identifier == identifier))
    ).scalar_one_or_none()
    old_status = row.payload.get("status") if row else None
    if row is None:
        row = CzibRow(identifier=identifier)
        session.add(row)
    row.payload = payload
    row.source, row.source_url, row.source_tier = source, source_url, source_tier
    row.max_age_seconds, row.fetched_at = max_age_seconds, fetched_at
    await _log_change(session, source, identifier, "status", old_status, status)


async def _get_health(session: AsyncSession, source: str) -> SourceHealthRow:
    row = (
        await session.execute(select(SourceHealthRow).where(SourceHealthRow.source == source))
    ).scalar_one_or_none()
    if row is None:
        row = SourceHealthRow(source=source, consecutive_failures=0)
        session.add(row)
    return row


async def record_success(session: AsyncSession, source: str) -> None:
    row = await _get_health(session, source)
    now = utcnow()
    row.last_attempt_at = now
    row.last_success_at = now
    row.consecutive_failures = 0
    row.last_error = None


async def record_failure(session: AsyncSession, source: str, error: str) -> int:
    """Record a failed attempt; return the new consecutive-failure count."""
    row = await _get_health(session, source)
    row.last_attempt_at = utcnow()
    row.consecutive_failures = (row.consecutive_failures or 0) + 1
    row.last_error = error[:500]
    return row.consecutive_failures
