"""Historical track-record cards — frozen, human-reviewed editorial content loaded
from version-controlled JSON in backend/content/history. No live pipeline; the
review gate is the PR diff. Served through the same API as everything else.
"""

from __future__ import annotations

import functools
import pathlib

from pydantic import BaseModel

CONTENT = pathlib.Path(__file__).resolve().parents[1] / "content" / "history"


class HistorySource(BaseModel):
    label: str
    url: str


class HistoricalCard(BaseModel):
    airline: str  # IATA, e.g. "QR"
    date: str
    title: str
    summary: str
    airline_response: str
    sources: list[HistorySource]


@functools.lru_cache
def _all() -> tuple[HistoricalCard, ...]:
    if not CONTENT.exists():
        return ()
    # Newest first (filenames are date-prefixed).
    return tuple(
        HistoricalCard.model_validate_json(p.read_text())
        for p in sorted(CONTENT.glob("*.json"), reverse=True)
    )


def load_cards(airline: str) -> list[HistoricalCard]:
    return [c for c in _all() if c.airline == airline]
