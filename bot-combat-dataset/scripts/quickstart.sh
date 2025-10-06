#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

./scripts/setup_venv.sh
source .venv/bin/activate

# Build demo dataset to ensure pipeline works without scraping
python -m bot_combat_dataset.cli build --demo --excel "data/bot_combat_dataset.xlsx" --parquet "data/"

# Start demo chat session once to verify agent
python -m bot_combat_dataset.cli chat --demo -q "Who defeated Tombstone in the demo data?"
