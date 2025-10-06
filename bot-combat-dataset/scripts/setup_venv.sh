#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel
python -m pip install -r requirements.txt
python -m pip install -e .

echo "\n[OK] Virtualenv ready. Activate with: source .venv/bin/activate"
