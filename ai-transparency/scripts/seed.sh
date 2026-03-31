#!/usr/bin/env bash
set -euo pipefail

MODEL_FILE="${1:-.seed-model-id}"
ROOT_URL="${ROOT_URL:-http://localhost}"
PROFILES_URL="${PROFILES_URL:-$ROOT_URL:4000}"
BENCHMARKS_URL="${BENCHMARKS_URL:-$ROOT_URL:5000}"
REVIEWS_URL="${REVIEWS_URL:-$ROOT_URL:4100}"
AUTH_TOKEN="${AUTH_TOKEN:-dev-token}"

bash scripts/wait-for-http.sh "$PROFILES_URL/health" 120
bash scripts/wait-for-http.sh "$BENCHMARKS_URL/health" 120
bash scripts/wait-for-http.sh "$REVIEWS_URL/health" 120

MODEL_JSON=$(curl -fsS -X POST "$PROFILES_URL/models" \
  -H 'content-type: application/json' \
  -H "authorization: Bearer $AUTH_TOKEN" \
  -H 'x-user-role: publisher' \
  -d '{
    "name":"TransparencyGPT",
    "version":"1.0.0",
    "architecture":"transformer",
    "training_data":{
      "sources":["internal-corpus","public-qa"],
      "collection_method":"curated_and_filtered",
      "licenses":["cc-by-4.0","odc-by-1.0"],
      "provenance_score":0.84
    }
  }')

MODEL_ID=$(python -c "import json,sys; print(json.load(sys.stdin)['id'])" <<< "$MODEL_JSON")
echo "$MODEL_ID" > "$MODEL_FILE"

echo "Seed model: $MODEL_ID"

curl -fsS -X POST "$BENCHMARKS_URL/ingest" \
  -H 'content-type: application/json' \
  -H "authorization: Bearer $AUTH_TOKEN" \
  -d "{\"model_id\":\"$MODEL_ID\",\"benchmark_name\":\"truthfulqa\",\"metrics\":{\"score\":0.78},\"auditor_signature\":\"sig-1\"}" >/dev/null

curl -fsS -X POST "$REVIEWS_URL/models/$MODEL_ID/reviews" \
  -H 'content-type: application/json' \
  -H "authorization: Bearer $AUTH_TOKEN" \
  -d '{"author":"auditor-1","rating":4,"text":"solid provenance","tags":["audit"]}' >/dev/null

echo "Benchmark and review submitted for model: $MODEL_ID"

# submit workflow
curl -fsS -X POST "$PROFILES_URL/models/$MODEL_ID/workflow/submit" \
  -H 'content-type: application/json' \
  -H "authorization: Bearer $AUTH_TOKEN" \
  -H 'x-user-role: publisher' \
  -d '{"note":"submit from seed script"}' >/dev/null

