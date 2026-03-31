#!/usr/bin/env bash
set -euo pipefail

MODEL_FILE="${1:-.seed-model-id}"
ROOT_URL="${ROOT_URL:-http://localhost}"
PROFILES_URL="${PROFILES_URL:-$ROOT_URL:4000}"
AUTH_TOKEN="${AUTH_TOKEN:-dev-token}"

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
req = urllib.request.Request(f"{profiles_url}/models/{model_id}")
req.add_header('authorization', f'Bearer {__import__("os").environ.get("AUTH_TOKEN","dev-token")}')
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode())

model = data.get("model", {})
bench = data.get("benchmark_summary", [])
trust = model.get("trust_score")

assert model.get("id") == model_id, "model id mismatch"
assert isinstance(bench, list), "benchmark_summary not list"
assert trust is not None, "missing trust_score"
wf_req = urllib.request.Request(f"{profiles_url}/models/{model_id}/workflow")
wf_req.add_header('authorization', f'Bearer {__import__("os").environ.get("AUTH_TOKEN","dev-token")}')
with urllib.request.urlopen(wf_req) as wr:
    workflow = json.loads(wr.read().decode())
assert workflow.get('workflow_status') in {'submitted','approved','rejected','draft'}
print(json.dumps({"model_id": model_id, "trust_score": trust, "workflow": workflow.get('workflow_status'), "benchmarks": bench}, indent=2))
PY

echo "Smoke check passed for model $MODEL_ID"
