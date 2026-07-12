"""US State Dept travel advisories — parse (Phase 2) + fetch (Phase 3).

Country is matched by ISO code (`Category`); the level lives only in `Title`
("Qatar - Level 3: Reconsider Travel") and is extracted by regex — a title that
doesn't match the pattern guard-fails (treated as source drift).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

SOURCE = "state_dept"
SOURCE_TIER = "T0"
FEED_URL = "https://cadataapi.state.gov/api/TravelAdvisories"

_TITLE_RE = re.compile(r"^(?P<country>.+?)\s*-\s*Level\s+(?P<level>[1-4])\s*:\s*(?P<label>.+?)\s*$")


class Advisory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    country_code: str
    country_name: str
    level: int
    label: str
    title: str
    link: str
    published: str | None = None
    updated: str | None = None
    summary_html: str | None = None


def parse_item(item: dict) -> Advisory:
    title = item.get("Title") or ""
    m = _TITLE_RE.match(title)
    if not m:
        raise ValueError(f"advisory title not in 'Country - Level N: Label' form: {title!r}")
    cats = item.get("Category") or []
    if not cats:
        raise ValueError(f"advisory missing Category code: {title!r}")
    return Advisory(
        country_code=cats[0],
        country_name=m.group("country").strip(),
        level=int(m.group("level")),
        label=m.group("label").strip(),
        title=title,
        link=item.get("Link") or item.get("id") or "",
        published=item.get("Published"),
        updated=item.get("Updated"),
        summary_html=item.get("Summary"),
    )


def parse(raw: object, country_codes: set[str]) -> list[Advisory]:
    """Return advisories whose ISO code is in `country_codes`."""
    if not isinstance(raw, list):
        raise ValueError(f"expected a list of advisories, got {type(raw).__name__}")
    wanted = {c.upper() for c in country_codes}
    out = []
    for item in raw:
        cats = {c.upper() for c in (item.get("Category") or [])}
        if cats & wanted:
            out.append(parse_item(item))
    return out
