from __future__ import annotations

import json
import os
import sys
import logging
from typing import Optional, List, Dict

import click
import pandas as pd

from .schemas import Bot, Fight, Event
from .normalization import build_dataframes, export_to_excel, export_to_parquet
from .io_utils import write_jsonl, read_jsonl, ensure_parent_dir
from .scrapers.fandom import parse_battlebots_season_page
from .chat.agent import RetrievalQABot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
def main() -> None:
    """Bot Combat Dataset CLI"""


@main.command()
@click.option("--source", type=click.Choice(["fandom-battlebots"]), default="fandom-battlebots")
@click.option("--url", multiple=True, help="Season or event page URLs to scrape")
@click.option("--outdir", default="data/raw", help="Output directory for JSONL files")
def scrape(source: str, url: List[str], outdir: str) -> None:
    """Scrape raw data from online sources into JSONL files."""
    ensure_parent_dir(os.path.join(outdir, "placeholder"))

    all_bots: List[Bot] = []
    all_fights: List[Fight] = []
    all_events: List[Event] = []

    if source == "fandom-battlebots":
        if not url:
            logger.error("Please provide at least one --url for fandom-battlebots")
            sys.exit(2)
        for u in url:
            logger.info("Scraping BattleBots season page: %s", u)
            bots, fights, events = parse_battlebots_season_page(u)
            all_bots.extend(bots)
            all_fights.extend(fights)
            all_events.extend(events)

    # Deduplicate by IDs
    bot_map = {b.bot_id: b for b in all_bots if b.bot_id}
    event_map = {e.event_id: e for e in all_events if e.event_id}

    bot_count = write_jsonl((b.to_record() for b in bot_map.values()), os.path.join(outdir, "bots.jsonl"))
    fight_count = write_jsonl((f.to_record() for f in all_fights), os.path.join(outdir, "fights.jsonl"))
    event_count = write_jsonl((e.to_record() for e in event_map.values()), os.path.join(outdir, "events.jsonl"))

    click.echo(f"Wrote {bot_count} bots, {fight_count} fights, {event_count} events to {outdir}")


@main.command()
@click.option("--rawdir", default="data/raw", help="Directory with JSONL raw files")
@click.option("--excel", default="data/bot_combat_dataset.xlsx", help="Path to Excel workbook to write")
@click.option("--parquet", "parquet_dir", default="data/processed", help="Directory to write Parquet files")
@click.option("--demo", is_flag=True, help="Build from demo in-memory sample instead of raw files")
def build(rawdir: str, excel: str, parquet_dir: str, demo: bool) -> None:
    """Build normalized DataFrames and export to Excel and Parquet."""
    if demo:
        bots, fights, events = _demo_records()
    else:
        bots_json = read_jsonl(os.path.join(rawdir, "bots.jsonl")) if os.path.exists(os.path.join(rawdir, "bots.jsonl")) else []
        fights_json = read_jsonl(os.path.join(rawdir, "fights.jsonl")) if os.path.exists(os.path.join(rawdir, "fights.jsonl")) else []
        events_json = read_jsonl(os.path.join(rawdir, "events.jsonl")) if os.path.exists(os.path.join(rawdir, "events.jsonl")) else []

        bots = [Bot(**rec) for rec in bots_json]
        fights = [Fight(**rec) for rec in fights_json]
        events = [Event(**rec) for rec in events_json]

    dfs = build_dataframes(bots=bots, fights=fights, events=events)
    ensure_parent_dir(excel)
    export_to_excel(dfs, excel)
    os.makedirs(parquet_dir, exist_ok=True)
    parquet_paths = export_to_parquet(dfs, parquet_dir)

    click.echo(f"Excel written to {excel}\nParquet files: {', '.join(parquet_paths)}")


@main.command()
@click.option("--data", "data_path", default="data/bot_combat_dataset.xlsx", help="Path to Excel workbook produced by build")
@click.option("--demo", is_flag=True, help="Use demo dataset in-memory")
@click.option("-q", "question", default=None, help="Ask a single question and exit")
def chat(data_path: str, demo: bool, question: Optional[str]) -> None:
    """Interactive or one-shot Q&A over the dataset using retrieval."""
    if demo:
        bots, fights, events = _demo_records()
        tables = build_dataframes(bots=bots, fights=fights, events=events)
    else:
        if not os.path.exists(data_path):
            raise SystemExit(f"Data not found: {data_path}. Run build first.")
        tables = {
            name: pd.read_excel(data_path, sheet_name=name)
            for name in ["bots", "fights", "events", "teams"]
        }
    agent = RetrievalQABot(tables)

    if question:
        result = agent.answer(question)
        click.echo(json.dumps(result, indent=2))
        return

    click.echo("Interactive chat. Type 'exit' to quit.")
    while True:
        q = input("You: ").strip()
        if q.lower() in {"exit", "quit"}:
            break
        result = agent.answer(q)
        click.echo(result["answer"])  # brief
        # Show top-2 contexts for transparency
        for ctx in result["contexts"][:2]:
            click.echo(f"  ctx: {ctx['score']:.3f} - {ctx['text'][:120]}")


def _demo_records():
    # Minimal high-signal demo enabling quickstart
    bots = [
        Bot(bot_id="tombstone", name="Tombstone", primary_weapon="Spinning bar"),
        Bot(bot_id="bite-force", name="Bite Force", primary_weapon="Vertical spinner"),
        Bot(bot_id="whiplash", name="Whiplash", primary_weapon="Lifter/Spinner"),
    ]

    events = [
        Event(event_id="battlebots-2018", name="BattleBots 2018", series="BattleBots", season="2018"),
    ]

    fights = [
        Fight(
            fight_id="2018-finals-tombstone-biteforce",
            event_id="battlebots-2018",
            series="BattleBots",
            season="2018",
            round_name="Finals",
            blue_bot_id="tombstone",
            red_bot_id="bite-force",
            blue_bot_name="Tombstone",
            red_bot_name="Bite Force",
            winner_bot_id="bite-force",
            winner_bot_name="Bite Force",
            method="KO",
            duration="1:59",
            referee_decision=False,
            notes="Bite Force outdrives Tombstone and lands decisive hits.",
            source_url=None,
        ),
        Fight(
            fight_id="2018-quarterfinals-biteforce-whiplash",
            event_id="battlebots-2018",
            series="BattleBots",
            season="2018",
            round_name="Quarterfinals",
            blue_bot_id="bite-force",
            red_bot_id="whiplash",
            blue_bot_name="Bite Force",
            red_bot_name="Whiplash",
            winner_bot_id="bite-force",
            winner_bot_name="Bite Force",
            method="UD",
            duration="3:00",
            referee_decision=True,
            notes="Judges' unanimous decision.",
            source_url=None,
        ),
    ]

    return bots, fights, events
