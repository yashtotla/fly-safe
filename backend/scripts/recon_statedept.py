"""Recon: capture the US State Dept travel-advisory feed shape. FREE source.

Saves the raw response as a fixture so we model + test against real data.

Run:  uv run python scripts/recon_statedept.py
"""

import json
import pathlib

import httpx

FIX = pathlib.Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "statedept"
URL = "https://cadataapi.state.gov/api/TravelAdvisories"


def main() -> None:
    resp = httpx.get(URL, timeout=30.0, headers={"accept": "application/json"})
    print("HTTP", resp.status_code, "| content-type:", resp.headers.get("content-type"))
    resp.raise_for_status()

    FIX.mkdir(parents=True, exist_ok=True)
    try:
        data = resp.json()
    except Exception:
        (FIX / "advisories_raw.txt").write_text(resp.text)
        print("non-JSON; saved text. first 800 chars:\n", resp.text[:800])
        return

    (FIX / "advisories_raw.json").write_text(json.dumps(data, indent=2))
    print("saved raw ->", FIX / "advisories_raw.json")

    items = data if isinstance(data, list) else data.get("data") or data.get("items") or []
    print("top-level type:", type(data).__name__, "| item count:", len(items) if isinstance(items, list) else "n/a")
    if isinstance(items, list) and items:
        print("item keys:", sorted(items[0].keys()))
        # Surface the three countries we care about (India / Qatar / United States).
        wanted = ("qatar", "india", "united states")
        for it in items:
            blob = json.dumps(it).lower()
            if any(w in blob for w in wanted):
                title = it.get("Title") or it.get("title") or it.get("name")
                print("  match:", title)


if __name__ == "__main__":
    main()
