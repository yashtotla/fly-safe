"""Provenance + freshness — the one invariant that stays uniform across all sources.

Every stored fact carries where it came from and when it was last confirmed. The
user-facing freshness is derived from `fetched_at` (last successful confirmation)
against a per-source `max_age`. Failed *attempts* are NOT modeled here — they live
in SourceHealth and never reach the public API (a failing source simply shows as
aging data, which is the honest, user-relevant signal).
"""

from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy.orm import Mapped, mapped_column


class FreshnessState(str, enum.Enum):
    FRESH = "fresh"  # confirmed within max_age
    STALE = "stale"  # have a last-known value, but older than max_age
    UNAVAILABLE = "unavailable"  # nothing trustworthy to show


def derive_freshness(
    fetched_at: dt.datetime | None,
    max_age_seconds: int,
    now: dt.datetime | None = None,
) -> FreshnessState:
    if fetched_at is None:
        return FreshnessState.UNAVAILABLE
    now = now or dt.datetime.now(dt.UTC)
    if fetched_at.tzinfo is None:  # stored naive == UTC
        fetched_at = fetched_at.replace(tzinfo=dt.UTC)
    age = (now - fetched_at).total_seconds()
    return FreshnessState.FRESH if age <= max_age_seconds else FreshnessState.STALE


class ProvenanceMixin:
    """Mandatory metadata columns mixed into every source's storage row.

    Constrains nothing about the payload — only guarantees attribution + freshness
    exist on every fact (the definitional invariant of this product).
    """

    source: Mapped[str] = mapped_column()  # e.g. "aerodatabox"
    source_url: Mapped[str] = mapped_column()  # official link for this fact
    source_tier: Mapped[str] = mapped_column()  # "T0".."T3"
    fetched_at: Mapped[dt.datetime] = mapped_column()  # last successful confirmation (UTC)
    max_age_seconds: Mapped[int] = mapped_column()  # freshness threshold for this source
