# Bot Combat Dataset

Dataset, scrapers, and a lightweight retrieval chat agent for bots-vs-bots combat data (e.g., BattleBots). This project helps you scrape public web pages, normalize the data into Pandas DataFrames, export to Excel/Parquet, and ask natural-language questions against the results using a small, local TF‑IDF retriever (no external LLMs required).

## What you get
- End-to-end pipeline: scrape ➜ normalize ➜ export (Excel, Parquet) ➜ chat
- Cleaned table set: `bots`, `fights`, `events`, `teams`
- CLI with subcommands: `scrape`, `build`, `chat`
- Minimal “SLM-like” chat agent using TF‑IDF retrieval over your tables

## Repository layout
```text
bot-combat-dataset/
  README.md                  # This documentation
  pyproject.toml             # Project metadata and CLI entrypoint
  requirements.txt           # Runtime dependencies
  setup.py                   # Packaging glue (editable installs)
  scripts/
    setup_venv.sh            # Create venv (or fallback to user site) and install deps
    quickstart.sh            # One-shot demo: install, build demo, run chat once
  bot_combat_dataset/
    __init__.py
    cli.py                   # CLI entrypoint and commands
    schemas.py               # Data classes for Bots, Fights, Events, Teams
    normalization.py         # Build DataFrames and export to Excel/Parquet
    io_utils.py              # JSONL IO + safe directory creation
    scrapers/
      __init__.py
      fandom.py              # MVP scraper: BattleBots Fandom season pages
      robotwars.py           # MVP scraper: Robot Wars Fandom pages
    chat/
      agent.py               # TF-IDF retrieval QA agent over the tables
  data/
    raw/                     # Raw JSONL scraped files land here
    processed/               # Parquet files land here
```

## Data model (Excel sheets / DataFrames)

### bots
| column          | description |
|-----------------|-------------|
| bot_id          | Stable slug for the bot name |
| name            | Display name |
| team_name       | Team name if known |
| weight_class    | e.g., Heavyweight |
| country         | Country/region if known |
| primary_weapon  | Primary offensive mechanism |
| drive_type      | Locomotion/drive description |
| active_years    | Free-text like "2016–2021" |
| aliases         | List of other known names |
| wiki_url        | Source page URL |

### fights
| column            | description |
|-------------------|-------------|
| fight_id          | Stable ID; season/table/row slug |
| event_id          | Links to `events.event_id` |
| series            | "BattleBots", etc. |
| season            | Season string, e.g., "2018" |
| round_name        | e.g., "Quarterfinals" |
| blue_bot_id       | Home corner bot ID |
| red_bot_id        | Away corner bot ID |
| blue_bot_name     | Display name at source |
| red_bot_name      | Display name at source |
| winner_bot_id     | Winning bot ID if determined |
| winner_bot_name   | Winning bot name if present |
| method            | KO, TKO, UD, JD, etc. |
| duration          | Elapsed time, free-text (e.g., "1:59") |
| referee_decision  | True if judges’ decision, else False/None |
| notes             | Free-text summary/remarks |
| source_url        | Page URL parsed |

### events
| column      | description |
|-------------|-------------|
| event_id    | Stable slug of series/season |
| name        | Human-friendly name |
| series      | Franchise (e.g., BattleBots) |
| season      | Season identifier if known |
| location    | Venue or region if known |
| date_start  | Start date (string) |
| date_end    | End date (string) |
| source_url  | Page URL parsed |

### teams
| column   | description |
|----------|-------------|
| team_id  | Stable slug |
| name     | Team name |
| country  | Country/region if known |
| members  | List of member names |

## Prerequisites
- Linux/macOS or WSL
- Recommended: Python 3.11 or 3.12
  - Note: Python 3.13 may require building some dependencies from source. If you encounter build errors, prefer Python 3.11/3.12.

## Setup
Option A (recommended): use the helper script.
```bash
cd bot-combat-dataset
./scripts/setup_venv.sh
# Then activate if a venv was created
source .venv/bin/activate  # if present
```
The script attempts a virtualenv install; if `venv/ensurepip` is unavailable, it falls back to a user‑site install and prints a reminder about PATH.

Option B (manual):
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel setuptools
pip install -r requirements.txt
pip install -e .
```

## Quickstart (demo, no scraping required)
This generates a tiny in-memory demo dataset and runs a single Q&A.
```bash
cd bot-combat-dataset
./scripts/quickstart.sh
```
If you prefer to run steps manually:
```bash
# Build demo dataset to Excel + Parquet
python -m bot_combat_dataset.cli build --demo \
  --excel data/bot_combat_dataset.xlsx \
  --parquet data/processed

# Ask a one-shot question over the demo
python -m bot_combat_dataset.cli chat --demo -q "Who defeated Tombstone in the demo data?"
```

## Scrape real data
MVP support is for BattleBots and Robot Wars Fandom pages. Page slugs may change over time—verify the exact URL. Examples to try:
- `https://battlebots.fandom.com/wiki/BattleBots_2018_Season`
- `https://battlebots.fandom.com/wiki/BattleBots_2019_Season`
- `https://robotwars.fandom.com/wiki/Robot_Wars_(series)` (use a concrete season/subpage)

Run the scraper (one or more `--url`):
```bash
python -m bot_combat_dataset.cli scrape \
  --source fandom-battlebots \
  --url "https://battlebots.fandom.com/wiki/BattleBots_2018_Season" \
  --url "https://battlebots.fandom.com/wiki/BattleBots_2019_Season" \
  --outdir data/raw

# Robot Wars example
python -m bot_combat_dataset.cli scrape \
  --source fandom-robotwars \
  --url "https://robotwars.fandom.com/wiki/Series_7" \
  --outdir data/raw
```
This writes JSONL files to `data/raw/`:
- `bots.jsonl`
- `fights.jsonl`
- `events.jsonl`

Then build normalized outputs:
```bash
python -m bot_combat_dataset.cli build \
  --rawdir data/raw \
  --excel data/bot_combat_dataset.xlsx \
  --parquet data/processed
```
Artifacts:
- Excel: `data/bot_combat_dataset.xlsx` with sheets `bots`, `fights`, `events`, `teams`
- Parquet: `data/processed/{bots,fights,events,teams}.parquet`

## Chat over your dataset
Interactive mode reads from the Excel workbook produced by `build`.
```bash
python -m bot_combat_dataset.cli chat --data data/bot_combat_dataset.xlsx
```
One-shot question:
```bash
python -m bot_combat_dataset.cli chat --data data/bot_combat_dataset.xlsx -q "Show finals winners for the 2018 season"
```
How it works (SLM-style):
- Default retriever is TF‑IDF; you can switch to BM25 for better sparse matching.
- Answer synthesis is template-based by default; optionally enable a tiny `t5-small` generator if you have internet and want slightly more fluent answers.

To use BM25 and/or T5 generation in code:
```python
from bot_combat_dataset.chat.agent import RetrievalQABot, RetrievalQAConfig
# tables = build_dataframes(...)
cfg = RetrievalQAConfig(retriever="bm25", generator="template")
agent = RetrievalQABot(tables, cfg)
print(agent.answer("Who defeated Tombstone? ")['answer'])
```

If you want T5 generation:
```python
from bot_combat_dataset.chat.agent import RetrievalQABot, RetrievalQAConfig
cfg = RetrievalQAConfig(retriever="bm25", generator="t5", t5_model_name="t5-small")
agent = RetrievalQABot(tables, cfg)
print(agent.answer("Summarize the finals result.")["answer"])
```

## Notes on scraping ethically
- Check and respect each site’s Terms of Use and robots.txt
- Identify your agent with a descriptive User‑Agent
- Add delays/backoff for politeness; this project already retries with exponential backoff
- Cache raw HTML or JSONL where possible to avoid re‑hitting sources

## Troubleshooting
- Python 3.13 builds: If `pandas` or other packages attempt to build from source and fail, use Python 3.11/3.12.
- PATH warnings after user‑site install: add `~/.local/bin` to your PATH.
- Fandom page not found (404): season page slugs can change; search the wiki and update the URL accordingly.

## Testing
Install test deps (already in `requirements.txt`) and run:
```bash
cd bot-combat-dataset
./scripts/setup_venv.sh
source .venv/bin/activate  # if created
pytest
```

Run a single file or test for quick feedback:
```bash
pytest tests/test_robotwars_scraper.py::test_parse_fights_section_mixed_headers -q
pytest tests/test_chat_agent.py -q
pytest tests/test_chat_agent_bm25.py -q
```

Smoke-test the CLI end-to-end (demo):
```bash
python -m bot_combat_dataset.cli build --demo --excel data/bot_combat_dataset.xlsx --parquet data/processed
python -m bot_combat_dataset.cli chat --data data/bot_combat_dataset.xlsx -q "Who won the finals?"
```

## Publishing as a standalone GitHub repo (optional)
If this project lives within a monorepo and you want to publish just `bot-combat-dataset/` as its own repository, you can use a subtree split:
```bash
# From the monorepo root
# 1) Create a split branch containing only the dataset folder history
git subtree split --prefix bot-combat-dataset -b bot-combat-dataset-publish

# 2) Create an empty repo on GitHub named `bot-combat-dataset`
# 3) Add it as a remote and push the split branch
git remote add dataset https://github.com/<your-username>/bot-combat-dataset.git
git push -u dataset bot-combat-dataset-publish:main
```

## Roadmap
- Improve Fandom parsing robustness and coverage
- Add Robot Wars and other sources
- Enrich schema (judges’ scorecards, damage/control/aggression breakdowns)
- Add lightweight reranking and richer answer synthesis

