"""Assembly: compose a route's bundle from the decoupled per-source rows, deriving
freshness + attaching provenance to every value. This is the read/API-facing view;
it asserts no opinion — just sourced, timestamped facts and links.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import history
from app.catalog import Route
from app.models import AdvisoryRow, CzibRow, FlightStatusRow
from app.provenance import FreshnessState, derive_freshness
from app.sources import aerodatabox, easa, statedept

DISCLAIMER = (
    "Informational only. This dashboard aggregates public sources with timestamps and "
    "links; it is not advice and not a safety guarantee. Verify with official sources "
    "before making travel decisions."
)

COUNTRY_NAMES = {"IN": "India", "QA": "Qatar", "US": "United States"}

_STATUS_LABELS = {
    "Arrived": "Arrived",
    "Departed": "In the air",
    "EnRoute": "In the air",
    "Approaching": "In the air",
    "Boarding": "Boarding",
    "GateClosed": "Gate closed",
    "CheckIn": "Check-in open",
    "Expected": "Scheduled",
    "Unknown": "Scheduled",
    "Delayed": "Delayed",
    "Diverted": "Diverted",
    "Canceled": "Cancelled",
    "CanceledUncertain": "Possibly cancelled",
}


class Provenance(BaseModel):
    source: str
    source_url: str
    tier: str
    fetched_at: dt.datetime
    freshness: FreshnessState


class FlightPanelItem(BaseModel):
    leg: str
    flight_number: str
    available: bool
    latest_date: str | None = None
    status: str | None = None
    status_label: str | None = None
    is_disrupted: bool = False
    dep_scheduled_local: str | None = None
    dep_revised_local: str | None = None
    arr_scheduled_local: str | None = None
    delay_minutes: int | None = None
    aircraft: str | None = None
    note: str | None = None
    provenance: Provenance | None = None


class AdvisoryPanelItem(BaseModel):
    country_code: str
    country_name: str
    available: bool
    level: int | None = None
    label: str | None = None
    link: str | None = None
    published: str | None = None
    note: str | None = None
    provenance: Provenance | None = None


class AirspacePanelItem(BaseModel):
    identifier: str
    title: str
    status: str
    valid_until: str | None = None
    url: str | None = None
    provenance: Provenance | None = None


class RouteBundle(BaseModel):
    route_id: str
    label: str
    airline: str
    airline_name: str
    origin: str
    hub: str
    destination: str
    travel_date: str | None
    flights: list[FlightPanelItem]
    advisories: list[AdvisoryPanelItem]
    airspace: list[AirspacePanelItem]
    airspace_note: str
    history: list[history.HistoricalCard]
    disclaimer: str
    generated_at: dt.datetime


def _prov(row, now: dt.datetime) -> Provenance:
    # SQLite stores naive datetimes; stamp them UTC so the client parses them as UTC
    # (not local) — otherwise "confirmed X ago" is off by the browser's tz offset.
    fetched = row.fetched_at if row.fetched_at.tzinfo else row.fetched_at.replace(tzinfo=dt.UTC)
    return Provenance(
        source=row.source,
        source_url=row.source_url,
        tier=row.source_tier,
        fetched_at=fetched,
        freshness=derive_freshness(fetched, row.max_age_seconds, now),
    )


def _delay_minutes(ep: aerodatabox.FlightEndpoint) -> int | None:
    if not (ep.scheduledTime and ep.revisedTime):
        return None
    sched = aerodatabox.parse_time(ep.scheduledTime.utc)
    rev = aerodatabox.parse_time(ep.revisedTime.utc)
    if not (sched and rev):
        return None
    return round((rev - sched).total_seconds() / 60)


async def _flights(session: AsyncSession, route: Route, now: dt.datetime) -> list[FlightPanelItem]:
    items: list[FlightPanelItem] = []
    for leg in route.legs:
        label = f"{leg.origin} → {leg.destination}"
        row = (
            await session.execute(
                select(FlightStatusRow)
                .where(FlightStatusRow.flight_number == leg.flight_number)
                .order_by(FlightStatusRow.flight_date.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if row is None:
            items.append(
                FlightPanelItem(
                    leg=label,
                    flight_number=leg.flight_number,
                    available=False,
                    note="No tracked operation yet for this flight.",
                )
            )
            continue
        f = aerodatabox.FlightStatus.model_validate(row.payload)
        items.append(
            FlightPanelItem(
                leg=label,
                flight_number=leg.flight_number,
                available=True,
                latest_date=row.flight_date,
                status=f.status.value,
                status_label=_STATUS_LABELS.get(f.status.value, f.status.value),
                is_disrupted=f.status in aerodatabox.DISRUPTED,
                dep_scheduled_local=f.departure.scheduledTime.local
                if f.departure.scheduledTime
                else None,
                dep_revised_local=f.departure.revisedTime.local
                if f.departure.revisedTime
                else None,
                arr_scheduled_local=f.arrival.scheduledTime.local
                if f.arrival.scheduledTime
                else None,
                delay_minutes=_delay_minutes(f.departure),
                aircraft=(f.aircraft or {}).get("model"),
                provenance=_prov(row, now),
            )
        )
    return items


async def _advisories(
    session: AsyncSession, route: Route, now: dt.datetime
) -> list[AdvisoryPanelItem]:
    items: list[AdvisoryPanelItem] = []
    for code in route.advisory_countries:
        name = COUNTRY_NAMES.get(code, code)
        row = (
            await session.execute(select(AdvisoryRow).where(AdvisoryRow.country_code == code))
        ).scalar_one_or_none()
        if row is None:
            note = (
                "The U.S. State Dept does not issue a travel advisory for the United States."
                if code == "US"
                else "Advisory not yet loaded."
            )
            items.append(
                AdvisoryPanelItem(country_code=code, country_name=name, available=False, note=note)
            )
            continue
        a = statedept.Advisory.model_validate(row.payload)
        items.append(
            AdvisoryPanelItem(
                country_code=code,
                country_name=name,
                available=True,
                level=a.level,
                label=a.label,
                link=a.link,
                published=a.published,
                provenance=_prov(row, now),
            )
        )
    return items


async def _airspace(
    session: AsyncSession, route: Route, now: dt.datetime
) -> list[AirspacePanelItem]:
    wanted = tuple(c.lower() for c in route.airspace_countries)
    rows = (await session.execute(select(CzibRow))).scalars().all()
    items: list[AirspacePanelItem] = []
    for row in rows:
        c = easa.Czib.model_validate(row.payload)
        if c.is_active and any(w in c.title.lower() for w in wanted):
            items.append(
                AirspacePanelItem(
                    identifier=c.identifier,
                    title=c.title,
                    status=c.status,
                    valid_until=c.valid_until,
                    url=c.url,
                    provenance=_prov(row, now),
                )
            )
    return items


async def build_bundle(
    session: AsyncSession, route: Route, travel_date: str | None, now: dt.datetime | None = None
) -> RouteBundle:
    now = now or dt.datetime.now(dt.UTC)
    return RouteBundle(
        route_id=route.id,
        label=route.label,
        airline=route.airline,
        airline_name=route.airline_name,
        origin=route.origin,
        hub=route.hub,
        destination=route.destination,
        travel_date=travel_date,
        flights=await _flights(session, route, now),
        advisories=await _advisories(session, route, now),
        airspace=await _airspace(session, route, now),
        airspace_note=(
            "Active EASA conflict-zone bulletins for airspace along this corridor "
            "(overflight context — not a claim about this flight's exact path)."
        ),
        history=history.load_cards(route.airline),
        disclaimer=DISCLAIMER,
        generated_at=now,
    )
