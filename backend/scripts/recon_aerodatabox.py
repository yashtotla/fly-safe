"""One-shot reconnaissance: capture ONE real AeroDataBox flight-by-number response.

Frugal by design — makes exactly ONE request (AeroDataBox free tier = 600/month).
The saved fixture becomes the source of truth for modeling + tests; never re-hit the
API to re-derive the shape. The key is read from env (never hardcoded or printed).

Run:  uv run python scripts/recon_aerodatabox.py
"""

import json
import pathlib
import sys

import httpx

# Make the backend package (`app`) importable when run as a standalone script.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app.config import settings  # noqa: E402

FLIGHT = "QR557"          # BOM -> DOH (confirmed)
DATE = "2026-07-12"       # yesterday: a completed flight -> full "operated" shape
BASE = "https://aerodatabox.p.rapidapi.com"

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "aerodatabox"


def main() -> None:
    if not settings.aerodatabox_api_key:
        raise SystemExit("AERODATABOX_API_KEY not set in backend/.env")

    url = f"{BASE}/flights/number/{FLIGHT}/{DATE}/{DATE}"
    headers = {
        "x-rapidapi-key": settings.aerodatabox_api_key,
        "x-rapidapi-host": "aerodatabox.p.rapidapi.com",
    }
    # Trim the payload/units: no aircraft image, no live geo.
    params = {"withAircraftImage": "false", "withLocation": "false"}

    print(f"GET {url}")
    resp = httpx.get(url, headers=headers, params=params, timeout=30.0)
    print("HTTP", resp.status_code)

    quota = {k: v for k, v in resp.headers.items() if "ratelimit" in k.lower() or "quota" in k.lower()}
    print("quota headers:", quota)

    if resp.status_code != 200:
        print("body:", resp.text[:500])
        raise SystemExit("Non-200 — not saving. Adjust and retry deliberately (budget!).")

    data = resp.json()
    FIXTURES.mkdir(parents=True, exist_ok=True)
    out = FIXTURES / f"{FLIGHT}_{DATE}.json"
    out.write_text(json.dumps(data, indent=2))
    print("saved:", out)

    # Small shape summary only (keep stdout tiny).
    if isinstance(data, list):
        print("-> list of", len(data), "flight(s)")
        if data:
            print("-> top-level keys:", sorted(data[0].keys()))
    elif isinstance(data, dict):
        print("-> dict keys:", sorted(data.keys()))


if __name__ == "__main__":
    main()
