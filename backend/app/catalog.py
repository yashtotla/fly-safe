"""Supported routes. The picker only offers what's here; a new route is a new
entry (data verified first), nothing else changes.

Country/airspace context is expressed by stable names/codes, never by rotting
identifiers (e.g. we match active CZIBs by country name, not by CZIB number).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Leg:
    origin: str  # IATA
    destination: str  # IATA
    flight_number: str  # e.g. "QR557"


@dataclass(frozen=True)
class Route:
    id: str
    origin: str
    hub: str
    destination: str
    airline: str  # IATA, e.g. "QR"
    airline_name: str
    label: str
    legs: tuple[Leg, ...]
    advisory_countries: tuple[str, ...]  # ISO codes — in-country advisories (origin/hub/dest)
    airspace_countries: tuple[str, ...]  # overflight corridor — match active CZIBs by title


ROUTES: dict[str, Route] = {
    "bom-doh-atl-qr": Route(
        id="bom-doh-atl-qr",
        origin="BOM",
        hub="DOH",
        destination="ATL",
        airline="QR",
        airline_name="Qatar Airways",
        label="Mumbai → Doha → Atlanta · Qatar Airways",
        legs=(Leg("BOM", "DOH", "QR557"), Leg("DOH", "ATL", "QR755")),
        advisory_countries=("IN", "QA", "US"),
        airspace_countries=("Iran", "Iraq"),
    ),
}


def get_route(route_id: str) -> Route | None:
    return ROUTES.get(route_id)
