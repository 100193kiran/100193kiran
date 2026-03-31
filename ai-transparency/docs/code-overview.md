# Code Overview

## apps/
- `web-frontend`: UI + API proxy for browser-friendly routing.
- `api-gateway`: edge auth/rate-limit and service routing.

## services/
- `profiles`: model source of truth, trust recompute, workflow governance.
- `reviews`: review persistence and summary API.
- `benchmarks`: ingest API + schema validation + publish/forward.
- `ingest-worker`: async pipeline consumer with enrichment and retries.
- `analytics`: hallucination risk prediction endpoint.

## infra/
- SQL bootstrap/migrations, Kubernetes deployments/services/ingress, Terraform starter.

## tests/
- Unit and contract tests + E2E scaffold.
