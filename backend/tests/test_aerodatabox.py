import json
import pathlib

import pytest
from pydantic import ValidationError

from app.sources.aerodatabox import FlightState, parse, parse_time

FIX = pathlib.Path(__file__).parent / "fixtures" / "aerodatabox" / "QR557_2026-07-12.json"


def test_parse_real_fixture():
    flights = parse(json.loads(FIX.read_text()))
    assert len(flights) == 1
    f = flights[0]
    assert f.number == "QR 557"
    assert f.status is FlightState.Arrived
    assert f.departure.airport.iata == "BOM"
    assert f.arrival.airport.iata == "DOH"
    assert f.departure.scheduledTime.utc == "2026-07-11 22:40Z"


def test_parse_time_is_tz_aware():
    utc = parse_time("2026-07-11 22:40Z")
    assert utc is not None and utc.utcoffset().total_seconds() == 0
    local = parse_time("2026-07-12 04:10+05:30")
    assert local.utcoffset().total_seconds() == 5.5 * 3600
    assert parse_time(None) is None


def test_unknown_status_guard_fails():
    bad = [
        {
            "number": "QR 1",
            "status": "TeleportedIn",  # not a known AeroDataBox status
            "departure": {"airport": {"iata": "BOM"}},
            "arrival": {"airport": {"iata": "DOH"}},
        }
    ]
    with pytest.raises(ValidationError):
        parse(bad)


def test_non_list_rejected():
    with pytest.raises(ValueError):
        parse({"not": "a list"})
