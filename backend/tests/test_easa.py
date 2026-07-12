import pathlib

from app.sources.easa import active, parse

SAMPLE = pathlib.Path(__file__).parent / "fixtures" / "easa" / "czibs_sample.html"


def test_parse_sample():
    czibs = parse(SAMPLE.read_text())
    by_id = {c.identifier: c for c in czibs}

    iran = by_id["CZIB-2026-04"]
    assert iran.title == "Airspace of Iran"
    assert iran.is_active
    assert iran.valid_until == "31/08/2026"

    withdrawn = by_id["2026-03-R14"]
    assert not withdrawn.is_active

    assert active(czibs) == [iran]


def test_failsafe_no_table():
    assert parse("<html><body>nothing here</body></html>") == []
