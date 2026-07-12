import json
import pathlib

import pytest

from app.sources.statedept import parse, parse_item

SAMPLE = pathlib.Path(__file__).parent / "fixtures" / "statedept" / "advisories_sample.json"


def test_parse_route_countries():
    advs = parse(json.loads(SAMPLE.read_text()), {"QA", "IN"})
    by_code = {a.country_code: a for a in advs}
    assert by_code["QA"].level == 3
    assert "Reconsider" in by_code["QA"].label
    assert by_code["QA"].link.startswith("https://travel.state.gov")
    assert by_code["IN"].level == 2


def test_multiword_title_edge_case():
    # "Mexico Travel Advisory - Level 2: Exercise Increased Caution"
    advs = parse(json.loads(SAMPLE.read_text()), {"MX"})
    assert advs and advs[0].level == 2


def test_level_four_edge_case():
    advs = parse(json.loads(SAMPLE.read_text()), {"IR"})
    assert advs[0].level == 4


def test_bad_title_guard_fails():
    with pytest.raises(ValueError):
        parse_item({"Title": "Neverland travel info", "Category": ["NL"], "Link": "x"})
