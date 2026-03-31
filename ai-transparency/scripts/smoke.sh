#!/usr/bin/env bash
set -euo pipefail

MODEL_FILE="${1:-.seed-model-id}"
ROOT_URL="${ROOT_URL:-http://localhost}"
PROFILES_URL="${PROFILES_URL:-$ROOT_URL:4000}"

if [[ ! -f "$MODEL_FILE" ]]; then
  echo "Model id file not found: $MODEL_FILE"
  echo "Run: make seed"
  exit 1
fi

MODEL_ID="$(cat "$MODEL_FILE")"

python - <<'PY' "$PROFILES_URL" "$MODEL_ID"
import json
import sys
import urllib.request

profiles_url, model_id = sys.argv[1], sys.argv[2]
with urllib.request.urlopen(f"{profiles_url}/models/{model_id}") as r:
    data = json.loads(r.read().decode())

model = data.get("model", {})
bench = data.get("benchmark_summary", [])
trust = model.get("trust_score")

assert model.get("id") == model_id, "model id mismatch"
assert isinstance(bench, list), "benchmark_summary not list"
assert trust is not None, "missing trust_score"
print(json.dumps({"model_id": model_id, "trust_score": trust, "benchmarks": bench}, indent=2))
PY

echo "Smoke check passed for model $MODEL_ID"
