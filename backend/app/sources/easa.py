"""EASA Conflict Zone Information Bulletins (CZIB) — parse (Phase 2) + fetch (Phase 3).

No API — the listing is a server-rendered table, scraped here. This is a
link-and-quote source: we extract identifier/title/status/validity/URL and surface
them with a link. Fail-safe: if parsing yields nothing, the panel just links to the
listing page rather than asserting anything.
"""

from __future__ import annotations

from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict

SOURCE = "easa_czib"
SOURCE_TIER = "T0"
LISTING_URL = "https://www.easa.europa.eu/en/domains/air-operations/czibs"
_BASE = "https://www.easa.europa.eu"


class Czib(BaseModel):
    model_config = ConfigDict(extra="ignore")
    identifier: str  # "CZIB-2026-04" or "2026-03-R14"
    title: str  # "Airspace of Iran"
    status: str  # "Active" / "Withdrawn"
    valid_until: str | None = None  # dd/mm/yyyy as published
    url: str | None = None

    @property
    def is_active(self) -> bool:
        return self.status.strip().lower() == "active"


def parse(html: str) -> list[Czib]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[Czib] = []
    for cell in soup.select("td.views-field-title"):
        num = cell.select_one(".czib_number")
        title = cell.select_one(".cz-title")
        status = cell.select_one(".cz-status")
        if not (num and title and status):
            continue
        row = cell.find_parent("tr")
        until = row.select_one("td.views-field-field-easa-conflict-zone-until") if row else None
        link = title.find("a") or cell.find("a")
        href = link.get("href") if link else None
        if href and href.startswith("/"):
            href = _BASE + href
        out.append(
            Czib(
                identifier=num.get_text(strip=True),
                title=title.get_text(strip=True),
                status=status.get_text(strip=True),
                valid_until=until.get_text(strip=True) if until else None,
                url=href,
            )
        )
    return out


def active(czibs: list[Czib]) -> list[Czib]:
    return [c for c in czibs if c.is_active]
