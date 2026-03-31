# AI Transparency Platform — 2026 Modernization Mega PR Spec

This document is a direct implementation blueprint for evolving this repo from scaffold to platform.

## Outcomes
1. Cohesive product: catalog, governance workflows, evidence bundles, search, dashboards.
2. Reliability: idempotent ingestion, retries, DLQ, backpressure.
3. Developer experience: typed clients, OpenAPI, deterministic tests.
4. Observability: OTel traces, structured logs, Prometheus metrics.
5. Security: JWT/OIDC-ready authn/z, rate limits, secret hygiene, supply-chain checks.
6. Modern UX: App Router, Tailwind/shadcn, charts, dark mode.
7. Credible ML: offline training, artifact metadata, explainability.

## Target architecture
- API Gateway as single public entrypoint.
- Domain services: profiles, benchmarks, ingest-worker, reviews, analytics.
- Platform dependencies: Postgres, Redis, Kafka, OpenSearch, MinIO.
- Versioned events with envelope fields: `event_id`, `schema_version`, `occurred_at`, `producer`, `payload`.

## Major workstreams

### A) Platform foundation
- Fastify gateway with auth/rate limiting/request ID.
- OTel collector + Tempo + Prometheus + Grafana in compose.
- Health/readiness endpoint standardization.

### B) Backend modernization
- Node services: Fastify + Zod + Prisma + RFC7807 errors.
- Idempotent ingestion and DLQ (`benchmarks.v1`, `benchmarks.dlq.v1`).
- Expanded domain tables: model_versions, evidence_bundles, benchmark_definitions, review_moderation, ingest_dead_letters, model_artifacts.

### C) Frontend + analytics modernization
- Next.js App Router + Tailwind + shadcn/ui + react-query.
- UI tabs: Overview/Provenance/Benchmarks/Reviews/Audit.
- Analytics endpoints: `/predict/risk`, `/explain` with artifact metadata persistence.

## Delivery strategy (3 PRs)
1. **PR A — Platform foundation**: gateway/auth/observability/compose.
2. **PR B — Backend modernization**: Fastify+Prisma, schema contracts, idempotent Kafka + DLQ.
3. **PR C — Frontend + analytics**: App Router UI polish + charts + ML artifact registry.

## Codex execution prompt
Use this exact instruction in Codex:

> “Modernize `ai-transparency` into a 2026-grade AI governance platform in 3 PRs (A/B/C), preserving end-to-end runability with `make up`, `make seed`, `make test`, and adding observability/security/integration rigor. Enforce API routing through gateway, versioned event contracts, idempotency and DLQ semantics, Fastify+Zod+Prisma backend modernization, and App Router + Tailwind + shadcn UI modernization.”
