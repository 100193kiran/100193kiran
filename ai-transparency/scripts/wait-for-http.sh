#!/usr/bin/env bash
set -euo pipefail

URL="${1:?url required}"
TIMEOUT="${2:-90}"
START="$(date +%s)"

until curl -fsS "$URL" >/dev/null 2>&1; do
  NOW="$(date +%s)"
  if (( NOW - START > TIMEOUT )); then
    echo "Timed out waiting for $URL"
    exit 1
  fi
  sleep 2
done

echo "Ready: $URL"
