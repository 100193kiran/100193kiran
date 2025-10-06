from __future__ import annotations

import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass
import re

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..schemas import Bot, Fight, Event

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


HEADERS = {
    "User-Agent": "bot-combat-dataset/0.1 (+https://example.com; research; contact@example.com)",
}


class ScraperError(Exception):
    pass


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True,
       retry=retry_if_exception_type((requests.RequestException, ScraperError)))
def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    if resp.status_code != 200:
        raise ScraperError(f"Non-200 status {resp.status_code} for {url}")
    return resp.text


def parse_battlebots_season_page(url: str) -> Tuple[List[Bot], List[Fight], List[Event]]:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html5lib")

    series = "BattleBots"
    season = None

    # Attempt to infer season from title or URL
    title = soup.find("title").get_text(strip=True) if soup.find("title") else ""
    season_match = re.search(r"(\d{4}) Season|Season (\d+)", title)
    if season_match:
        season = season_match.group(1) or season_match.group(2)

    events: List[Event] = []
    fights: List[Fight] = []
    bots: List[Bot] = []

    # Try to parse fights from wikitables
    tables = soup.select("table.wikitable")
    for t_index, table in enumerate(tables):
        headers = [th.get_text(strip=True) for th in table.select("thead th")]
        if not headers:
            headers = [th.get_text(strip=True) for th in table.select("tr th")]
        rows = table.select("tbody tr")
        if not rows:
            rows = table.select("tr")

        # Heuristic: table that contains columns mentioning bots and results
        header_line = "|".join(h.lower() for h in headers)
        if not any(k in header_line for k in ["bot", "blue", "red", "winner", "result"]):
            continue

        for r_index, row in enumerate(rows[1:]):  # skip header row
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) < 3:
                continue
            text_line = " | ".join(cells)

            # Very loose extraction; improved mappers can be added later
            blue_name = None
            red_name = None
            winner_name = None
            method = None

            # Guess columns by header keywords
            try:
                header_to_idx = {h.lower(): i for i, h in enumerate(headers)}
            except Exception:
                header_to_idx = {}

            def find_col(keyword: str) -> Optional[int]:
                for i, h in enumerate(headers):
                    if keyword in h.lower():
                        return i
                return None

            idx_blue = find_col("blue") or find_col("bot 1") or find_col("robot 1")
            idx_red = find_col("red") or find_col("bot 2") or find_col("robot 2")
            idx_winner = find_col("winner") or find_col("result")
            idx_method = find_col("method") or find_col("type") or find_col("result")

            if idx_blue is not None and idx_blue < len(cells):
                blue_name = cells[idx_blue]
            if idx_red is not None and idx_red < len(cells):
                red_name = cells[idx_red]
            if idx_winner is not None and idx_winner < len(cells):
                winner_name = cells[idx_winner]
            if idx_method is not None and idx_method < len(cells):
                method = cells[idx_method]

            if not blue_name and not red_name:
                # extremely noisy row; skip
                continue

            # Build ids by slugging names
            blue_id = slugify_name(blue_name) if blue_name else None
            red_id = slugify_name(red_name) if red_name else None
            winner_id = slugify_name(winner_name) if winner_name else None

            # Register bots
            if blue_name:
                bots.append(Bot(bot_id=blue_id or blue_name.lower(), name=blue_name))
            if red_name:
                bots.append(Bot(bot_id=red_id or red_name.lower(), name=red_name))

            fight_id = slugify_name(f"{season or 'unknown'}-{t_index}-{r_index}-{blue_id}-{red_id}")
            fights.append(
                Fight(
                    fight_id=fight_id,
                    event_id=None,
                    series=series,
                    season=season,
                    round_name=None,
                    blue_bot_id=blue_id,
                    red_bot_id=red_id,
                    blue_bot_name=blue_name,
                    red_bot_name=red_name,
                    winner_bot_id=winner_id,
                    winner_bot_name=winner_name,
                    method=method,
                    duration=None,
                    referee_decision=None,
                    notes=None,
                    source_url=url,
                )
            )

    # Deduplicate bots by bot_id
    unique_bots = {}
    for b in bots:
        if b.bot_id and b.bot_id not in unique_bots:
            unique_bots[b.bot_id] = b
    bots = list(unique_bots.values())

    if not fights:
        logger.warning("No fights parsed from %s; page structure may differ.", url)

    # Create a generic event if we recognized at least some content
    event_id = slugify_name(f"{series}-{season or 'unknown'}")
    events.append(
        Event(
            event_id=event_id,
            name=f"{series} {season or ''}".strip(),
            series=series,
            season=season,
            source_url=url,
        )
    )

    return bots, fights, events


def slugify_name(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-")
    return slug.lower()
