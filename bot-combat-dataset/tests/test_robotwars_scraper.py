import json
from pathlib import Path

from bot_combat_dataset.scrapers.robotwars import (
    extract_event_metadata,
    parse_bots_section,
    parse_fights_section,
)
from bs4 import BeautifulSoup


def soup_from_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def test_extract_event_metadata_from_infobox():
    html = """
    <html><body>
    <table class="infobox">
      <tr><th>Robot Wars: Series 7</th></tr>
      <tr><th>Venue</th><td>Sheffield, UK</td></tr>
      <tr><th>Dates</th><td>2003–2004</td></tr>
    </table>
    </body></html>
    """
    soup = soup_from_html(html)
    meta = extract_event_metadata(soup, "http://example.com")
    assert meta["series"] == "Robot Wars"
    assert meta["name"].startswith("Robot Wars")
    assert meta["location"] == "Sheffield, UK"
    assert meta["date_start"] == "2003"
    assert meta["date_end"] == "2004"
    assert meta["event_id"]


def test_parse_bots_section_from_table():
    html = """
    <html><body>
      <h2>Competitors</h2>
      <table>
        <tr><th>Name</th><th>Team</th><th>Notes</th></tr>
        <tr><td>Razer</td><td>Team Razer</td><td>Former champion</td></tr>
        <tr><td>Hypno-Disc</td><td>Team Hypno</td><td>Spinner</td></tr>
      </table>
    </body></html>
    """
    soup = soup_from_html(html)
    bots = parse_bots_section(soup, "http://example.com")
    assert len(bots) == 2
    names = {b["name"] for b in bots}
    assert {"Razer", "Hypno-Disc"}.issubset(names)


def test_parse_fights_section_mixed_headers():
    html = """
    <html><body>
      <h2>Results</h2>
      <table>
        <tr><th>Round</th><th>Blue</th><th>Red</th><th>Winner</th><th>Method</th><th>Time</th></tr>
        <tr><td>Heat A</td><td>Razer</td><td>Hypno-Disc</td><td>Razer</td><td>KO</td><td>1:10</td></tr>
        <tr><td>Semi</td><td>Razer</td><td>Chaos 2</td><td>Chaos 2</td><td>UD</td><td>3:00</td></tr>
      </table>
    </body></html>
    """
    soup = soup_from_html(html)
    event_meta = {
        "event_id": "event-rw-7",
        "name": "Robot Wars Series 7",
        "series": "Robot Wars",
        "season": "Series 7",
    }
    fights = parse_fights_section(soup, event_meta, "http://example.com")
    assert len(fights) == 2
    winners = {f["winner_bot_name"] for f in fights}
    assert {"Razer", "Chaos 2"}.issubset(winners)
