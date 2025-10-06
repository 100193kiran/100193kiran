#!/usr/bin/env bash
set -euo pipefail

PY=${PYTHON:-python3}

if "$PY" -m ensurepip --version >/dev/null 2>&1; then
  echo "[INFO] ensurepip available; creating virtualenv"
  "$PY" -m venv .venv
  source .venv/bin/activate
  python -m pip install -U pip wheel setuptools
  python -m pip install -r requirements.txt
  python -m pip install -e .
  echo "[OK] Virtualenv ready. Activate with: source .venv/bin/activate"
else
  echo "[WARN] ensurepip/venv not available; installing to user site"
  "$PY" -m pip install -U --user pip wheel setuptools
  "$PY" -m pip install --user -r requirements.txt
  "$PY" -m pip install --user -e .
  echo "[OK] User-site install complete. Ensure your PATH includes user-site bin."
fi
