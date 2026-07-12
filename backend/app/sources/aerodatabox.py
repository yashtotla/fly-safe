"""AeroDataBox flight status — parse (Phase 2) + fetch (Phase 3).

Validate-on-ingest: the raw response is parsed through these pydantic models; a
shape or enum mismatch raises, and the ingest layer treats that as a fetch failure
(keep last-known, alert) — questionable data is never stored. The status enum is
deliberately closed: an unknown value guard-fails rather than passing through.
"""

from __future__ import annotations

import datetime as dt
import enum

from pydantic import BaseModel, ConfigDict

SOURCE = "aerodatabox"
SOURCE_TIER = "T1"


class FlightState(str, enum.Enum):
    Unknown = "Unknown"
    Expected = "Expected"
    EnRoute = "EnRoute"
    CheckIn = "CheckIn"
    Boarding = "Boarding"
    GateClosed = "GateClosed"
    Departed = "Departed"
    Delayed = "Delayed"
    Approaching = "Approaching"
    Arrived = "Arrived"
    Diverted = "Diverted"
    Canceled = "Canceled"
    CanceledUncertain = "CanceledUncertain"


# Statuses that mean "not operating normally" (for the panel's plain-language read).
DISRUPTED = {FlightState.Diverted, FlightState.Canceled, FlightState.CanceledUncertain}


class _Airport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    iata: str | None = None
    icao: str | None = None
    name: str | None = None
    timeZone: str | None = None


class _TimePair(BaseModel):
    model_config = ConfigDict(extra="ignore")
    utc: str | None = None
    local: str | None = None


class FlightEndpoint(BaseModel):
    model_config = ConfigDict(extra="ignore")
    airport: _Airport
    scheduledTime: _TimePair | None = None
    revisedTime: _TimePair | None = None
    runwayTime: _TimePair | None = None
    terminal: str | None = None
    gate: str | None = None


class FlightStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")
    number: str
    status: FlightState
    codeshareStatus: str | None = None
    isCargo: bool | None = None
    departure: FlightEndpoint
    arrival: FlightEndpoint
    aircraft: dict | None = None
    airline: dict | None = None
    lastUpdatedUtc: str | None = None


def parse(raw: object) -> list[FlightStatus]:
    """Validate the flight-by-number response (a list of flight objects)."""
    if not isinstance(raw, list):
        raise ValueError(f"expected a list of flights, got {type(raw).__name__}")
    return [FlightStatus.model_validate(item) for item in raw]


def parse_time(s: str | None) -> dt.datetime | None:
    """Parse AeroDataBox time strings into tz-aware datetimes.

    Format is non-ISO: space separator, trailing 'Z', and no seconds
    (e.g. '2026-07-11 22:40Z', '2026-07-12 04:10+05:30').
    """
    if not s:
        return None
    t = s.strip().replace(" ", "T")
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    return dt.datetime.fromisoformat(t)
