"""
Robot Wars scraper for bot-combat-dataset.

This module scrapes Robot Wars season/event pages (e.g., fandom wiki)
and writes out JSONL files: bots.jsonl, fights.jsonl, events.jsonl

Design goals:
- Robust to slight variations in page structure (table captions, heading-based sections)
- Respectful fetching (custom user-agent, retry/backoff, optional delays)
- Produces records compatible with the repo's schema:
  bots: bot_id, name, team_name, weight_class, country, primary_weapon,
        drive_type, active_years, aliases, wiki_url
  fights: fight_id, event_id, series, season, round_name, blue_bot_id,
          red_bot_id, blue_bot_name, red_bot_name, winner_bot_id, winner_bot_name,
          method, duration, referee_decision, notes, source_url
  events: event_id, name, series, season, location, date_start, date_end, source_url
"""

from __future__ import annotations
import requests
from bs4 import BeautifulSoup
import time
import random
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
import hashlib
import unicodedata

# Configure module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(ch)

# Constants
DEFAULT_USER_AGENT = "bot-combat-dataset-robotwars-scraper/1.0 (+https://github.com/yourname/bot-combat-dataset)"
DEFAULT_HEADERS = {"User-Agent": DEFAULT_USER_AGENT}
JSONL_FILENAMES = {
    "bots": "bots.jsonl",
    "fights": "fights.jsonl",
    "events": "events.jsonl",
}

# ---- Helpers ----

def slugify(text: str) -> str:
    """Create a stable slug: lowercase ascii, dash-separated, remove punctuation."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text or "unknown"

def stable_id_from_text(prefix: str, text: str) -> str:
    """Create a short stable ID using slug + hash suffix to avoid collisions."""
    base = slugify(text)[:64]
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}-{base}-{h}"

def safe_mkdir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def write_jsonl(outpath: Path, records: List[Dict]):
    """Append or create a JSONL file from a list of dict records."""
    mode = "a" if outpath.exists() else "w"
    with outpath.open(mode, encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    logger.info("Wrote %d records to %s", len(records), outpath)

def fetch_url(url: str, headers: dict = DEFAULT_HEADERS, max_attempts: int = 3, backoff: float = 1.0) -> str:
    """Fetch url with retries and exponential backoff. Returns HTML text."""
    attempt = 0
    while attempt < max_attempts:
        try:
            logger.debug("Fetching %s (attempt %d)", url, attempt + 1)
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            attempt += 1
            sleep_time = backoff * (2 ** (attempt - 1)) + random.random() * 0.5
            logger.warning("Fetch attempt %d failed for %s: %s. Sleeping %.2fs", attempt, url, e, sleep_time)
            time.sleep(sleep_time)
    raise RuntimeError(f"Failed to fetch {url} after {max_attempts} attempts")

# ---- Parsers / heuristics ----

def extract_event_metadata(soup: BeautifulSoup, source_url: str) -> Dict:
    """
    Try to pull event-level metadata: event name, series, season, location, dates.
    This is heuristic: looks for infoboxes or top headings.
    """
    metadata = {
        "event_id": None,
        "name": None,
        "series": "Robot Wars",
        "season": None,
        "location": None,
        "date_start": None,
        "date_end": None,
        "source_url": source_url,
    }

    # 1) Infobox (common on fandom wikis)
    infobox = soup.find(class_=re.compile(r"infobox", re.I))
    if infobox:
        # Try title in infobox or page title
        title_tag = infobox.find(["th", "caption"])
        if title_tag and title_tag.get_text(strip=True):
            metadata["name"] = title_tag.get_text(strip=True)
        # Try key-value rows
        for row in infobox.find_all("tr"):
            header = row.find("th")
            value = row.find("td")
            if not header or not value:
                continue
            key = header.get_text(strip=True).lower()
            val = value.get_text(" ", strip=True)
            if "location" in key or "venue" in key:
                metadata["location"] = val
            if "date" in key:
                # try to parse start/end loosely
                parts = re.split(r"\s*–\s*|\s*-\s*|to", val)
                if parts:
                    metadata["date_start"] = parts[0].strip()
                    if len(parts) > 1:
                        metadata["date_end"] = parts[-1].strip()

    # 2) Page title / h1 / first heading if name not found
    if not metadata["name"]:
        h1 = soup.find(["h1", "h2"])
        if h1:
            metadata["name"] = h1.get_text(strip=True)

    # 3) Season detection via title (e.g., "Series 7", "2016 Season")
    if metadata["name"]:
        m = re.search(r"(series|season)\s*(\d+|\d{4})", metadata["name"].lower())
        if m:
            metadata["season"] = m.group(0)

    # fallback event_id
    if metadata["name"]:
        metadata["event_id"] = stable_id_from_text("event", metadata["name"])
    else:
        # Use url slug if nothing else
        metadata["event_id"] = stable_id_from_text("event", source_url)

    return metadata

def parse_bots_section(soup: BeautifulSoup, source_url: str) -> List[Dict]:
    """
    Parse bot lists. Many fandom pages have a "Competitors" or "Robots" table/list.
    Returns list of bot records following the bots schema.
    """
    bots = []

    # look for sections with headings like "Competitors", "Robots", "Participants"
    candidate_headings = soup.find_all(re.compile("^h[2-4]$"))
    for h in candidate_headings:
        txt = h.get_text(" ", strip=True).lower()
        if any(keyword in txt for keyword in ("competitor", "robots", "participants", "bots", "entries")):
            # look for next sibling which is a table or list
            sibling = h.find_next_sibling()
            # allow small climbing until we find a table or ul
            steps = 0
            while sibling and steps < 6:
                if sibling.name in ("table", "ul", "div"):
                    # parse a table or list into bot entries
                    if sibling.name == "table":
                        # table rows
                        for tr in sibling.select("tr"):
                            # skip header
                            cols = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                            if not cols or len(cols) < 1:
                                continue
                            # heuristics: first col = name, other cols = team/weight/weapon
                            name = cols[0]
                            team = cols[1] if len(cols) > 1 else None
                            notes = "; ".join(cols[2:]) if len(cols) > 2 else None
                            bot = {
                                "bot_id": stable_id_from_text("bot", name),
                                "name": name,
                                "team_name": team or None,
                                "weight_class": None,
                                "country": None,
                                "primary_weapon": None,
                                "drive_type": None,
                                "active_years": None,
                                "aliases": [],
                                "wiki_url": source_url,
                                "notes": notes,
                            }
                            bots.append(bot)
                        break
                    elif sibling.name == "ul":
                        for li in sibling.find_all("li", recursive=False):
                            name = li.get_text(" ", strip=True)
                            if not name:
                                continue
                            bot = {
                                "bot_id": stable_id_from_text("bot", name),
                                "name": name,
                                "team_name": None,
                                "weight_class": None,
                                "country": None,
                                "primary_weapon": None,
                                "drive_type": None,
                                "active_years": None,
                                "aliases": [],
                                "wiki_url": source_url,
                                "notes": None,
                            }
                            bots.append(bot)
                        break
                sibling = sibling.find_next_sibling()
                steps += 1

    # fallback: look for "infobox" style lists of competitors or any table with "Robot" header
    if not bots:
        for table in soup.find_all("table"):
            headers = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
            if any("robot" in h or "name" in h or "competitor" in h for h in headers):
                for tr in table.select("tr"):
                    tds = tr.find_all("td")
                    if not tds:
                        continue
                    # name in first td
                    name = tds[0].get_text(" ", strip=True)
                    team = tds[1].get_text(" ", strip=True) if len(tds) > 1 else None
                    bot = {
                        "bot_id": stable_id_from_text("bot", name),
                        "name": name,
                        "team_name": team or None,
                        "weight_class": None,
                        "country": None,
                        "primary_weapon": None,
                        "drive_type": None,
                        "active_years": None,
                        "aliases": [],
                        "wiki_url": source_url,
                        "notes": None,
                    }
                    bots.append(bot)
                if bots:
                    break

    # dedupe by bot_id
    seen = set()
    unique = []
    for b in bots:
        if b["bot_id"] not in seen:
            unique.append(b)
            seen.add(b["bot_id"])
    logger.info("Parsed %d bots", len(unique))
    return unique

def parse_fights_section(soup: BeautifulSoup, event_meta: Dict, source_url: str) -> List[Dict]:
    """
    Parse fight tables. Heuristics:
    - Look for tables where headers include "Red", "Blue", "Winner", "Method", "Time", "Round"
    - Look for sections titled "Bracket", "Tournament", "Matches", "Results"
    """
    fights = []

    # find candidate tables
    tables = []
    for table in soup.find_all("table"):
        headers = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
        if any(h in headers for h in ("red", "blue", "winner", "result", "method", "time", "round")):
            tables.append(table)

    # fallback: search for headings like Results / Matches / Bracket
    if not tables:
        for h in soup.find_all(re.compile("^h[2-4]$")):
            txt = h.get_text(" ", strip=True).lower()
            if any(k in txt for k in ("result", "matches", "bracket", "fights", "heat")):
                # gather first few tables after heading
                sib = h.find_next_sibling()
                steps = 0
                while sib and steps < 8:
                    if sib.name == "table":
                        tables.append(sib)
                    sib = sib.find_next_sibling()
                    steps += 1

    for table in tables:
        # attempt to map columns
        headers = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
        rows = table.find_all("tr")
        for tr in rows:
            tds = tr.find_all("td")
            if not tds:
                continue
            # Heuristic mapping: find text in tds for blue/red/winner/method/time
            row_texts = [td.get_text(" ", strip=True) for td in tds]
            combined = " | ".join(row_texts)
            # Simple heuristics to find two bot names: detect "vs" or split common layout
            # Case 1: "Blue vs Red" in a single cell
            blue = None
            red = None
            winner = None
            method = None
            duration = None
            round_name = None
            notes = combined

            # Try explicit cells
            if len(tds) >= 2:
                # if header labels present, try to map by header name
                mapped = {}
                for idx, h in enumerate(headers):
                    if not h:
                        continue
                    if "blue" in h or "home" in h:
                        mapped["blue"] = tds[idx].get_text(" ", strip=True)
                    if "red" in h or "away" in h:
                        mapped["red"] = tds[idx].get_text(" ", strip=True)
                    if "winner" in h or "result" in h:
                        mapped["winner"] = tds[idx].get_text(" ", strip=True)
                    if "method" in h or "decision" in h:
                        mapped["method"] = tds[idx].get_text(" ", strip=True)
                    if "time" in h or "duration" in h:
                        mapped["duration"] = tds[idx].get_text(" ", strip=True)
                    if "round" in h or "heat" in h:
                        mapped["round"] = tds[idx].get_text(" ", strip=True)
                blue = mapped.get("blue")
                red = mapped.get("red")
                winner = mapped.get("winner")
                method = mapped.get("method")
                duration = mapped.get("duration")
                round_name = mapped.get("round")

            # If not explicit, try to parse single-cell "Blue vs Red" or "Bot A vs Bot B"
            if not blue or not red:
                # look for " vs " pattern
                for txt in row_texts:
                    m = re.search(r"(.+?)\s+v(?:s|ersus)\.?\s+(.+)", txt, re.I)
                    if m:
                        blue = (blue or m.group(1).strip())
                        red = (red or m.group(2).strip())
                        break
                # other pattern: "Bot A — Bot B" or "Bot A  |  Bot B"
                if not blue or not red:
                    # try splitting first tds text if it contains separators
                    primary = row_texts[0]
                    for sep in ["—", "–", "-", " vs ", " v ", " vs. ", "|"]:
                        if sep in primary and len(primary.split(sep)) >= 2:
                            parts = [p.strip() for p in primary.split(sep) if p.strip()]
                            if len(parts) >= 2:
                                blue = (blue or parts[0])
                                red = (red or parts[1])
                                break

            # derive winner/winner_bot_name
            if winner:
                # winner might be a name; sometimes it's "Blue" or "Red"
                w = winner.strip()
                if w.lower() in ("blue", "red"):
                    winner_bot_name = blue if w.lower() == "blue" else red
                else:
                    winner_bot_name = w
            else:
                # try to detect winner from "defeated" textual patterns in notes
                m = re.search(r"(.+?)\s+(defeat|defeated|beat|beats|won against)\s+(.+)", combined, re.I)
                if m:
                    winner_bot_name = m.group(1).strip()
                else:
                    winner_bot_name = None

            # Create fight record if we have at least two bot names
            if blue and red:
                # Normalize bot ids
                blue_id = stable_id_from_text("bot", blue)
                red_id = stable_id_from_text("bot", red)
                fight_desc = f"{blue} vs {red} | {event_meta.get('name') or event_meta.get('event_id')}"
                fight_id = stable_id_from_text("fight", fight_desc)
                fight = {
                    "fight_id": fight_id,
                    "event_id": event_meta.get("event_id"),
                    "series": event_meta.get("series"),
                    "season": event_meta.get("season"),
                    "round_name": round_name,
                    "blue_bot_id": blue_id,
                    "red_bot_id": red_id,
                    "blue_bot_name": blue,
                    "red_bot_name": red,
                    "winner_bot_id": stable_id_from_text("bot", winner_bot_name) if winner_bot_name else None,
                    "winner_bot_name": winner_bot_name,
                    "method": method,
                    "duration": duration,
                    "referee_decision": True if method and "judge" in method.lower() else None,
                    "notes": notes,
                    "source_url": source_url,
                }
                fights.append(fight)
            else:
                logger.debug("Skipping row without two bot names: %s", combined)

    # dedupe by fight_id
    unique = {}
    for f in fights:
        unique[f["fight_id"]] = f
    fights_list = list(unique.values())
    logger.info("Parsed %d fights", len(fights_list))
    return fights_list

# ---- Top-level orchestration ----

def scrape_robotwars_page(url: str, outdir: str | Path, delay: float = 0.5, max_retries: int = 3) -> Dict[str, int]:
    """
    Scrape a Robot Wars season/event page and append records to JSONL files.

    Returns a small summary dict with counts.
    """
    outdir = Path(outdir)
    safe_mkdir(outdir)

    html = fetch_url(url, max_attempts=max_retries)
    soup = BeautifulSoup(html, "html.parser")

    # event metadata
    event_meta = extract_event_metadata(soup, url)
    # parse bots and fights
    bots = parse_bots_section(soup, url)
    fights = parse_fights_section(soup, event_meta, url)

    # single event record
    events = [event_meta]

    # write to JSONL files (append)
    write_jsonl(outdir / JSONL_FILENAMES["bots"], bots)
    write_jsonl(outdir / JSONL_FILENAMES["fights"], fights)
    write_jsonl(outdir / JSONL_FILENAMES["events"], events)

    # polite delay
    time.sleep(delay + random.random() * 0.5)

    summary = {"bots": len(bots), "fights": len(fights), "events": len(events)}
    logger.info("Scrape summary for %s: %s", url, summary)
    return summary

# ---- CLI-friendly helper if you want to run as script ----
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scrape Robot Wars season/event page")
    parser.add_argument("url", help="Event or season page URL to scrape")
    parser.add_argument("--outdir", "-o", default="data/raw", help="Directory to write JSONL files")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests")
    args = parser.parse_args()
    scrape_robotwars_page(args.url, args.outdir, delay=args.delay)
