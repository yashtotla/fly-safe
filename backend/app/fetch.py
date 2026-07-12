"""Async fetchers — each returns the raw payload for its source's parser.

AeroDataBox costs ~6 units/call (~100 calls/month); the scheduler gates how often
`fetch_flight` runs. The free sources are unmetered.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.sources import easa, statedept

_ADB_HOST = "aerodatabox.p.rapidapi.com"
_ADB_BASE = f"https://{_ADB_HOST}"


async def fetch_flight(
    client: httpx.AsyncClient, number: str, date_from: str, date_to: str
) -> object:
    url = f"{_ADB_BASE}/flights/number/{number}/{date_from}/{date_to}"
    resp = await client.get(
        url,
        headers={"x-rapidapi-key": settings.aerodatabox_api_key, "x-rapidapi-host": _ADB_HOST},
        params={"withAircraftImage": "false", "withLocation": "false"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


async def fetch_advisories(client: httpx.AsyncClient) -> object:
    resp = await client.get(
        statedept.FEED_URL, headers={"accept": "application/json"}, timeout=30.0
    )
    resp.raise_for_status()
    return resp.json()


async def fetch_czibs(client: httpx.AsyncClient) -> str:
    resp = await client.get(easa.LISTING_URL, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    return resp.text
