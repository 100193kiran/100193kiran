# Architectural Overview

## Context
The platform is an event-driven microservice architecture with an API edge layer and governance-centric data model.

## Core runtime planes
1. **Experience plane**: Next.js frontend + API gateway.
2. **Domain plane**: profiles, reviews, benchmarks, analytics, ingest-worker.
3. **Data plane**: Postgres, Redis, Kafka, optional Elasticsearch.
4. **Governance plane**: workflow states, model cards, compliance evidence, audit logs.

## High-level request flow
- User enters via web UI.
- UI calls gateway.
- Gateway enforces auth/rate limits and routes to downstream services.
- Profiles orchestrates trust score, model read model, and governance endpoints.

## Event flow
- Benchmarks ingest validates payload and schema version.
- Service publishes Kafka event.
- Ingest worker consumes, enriches with PII flag, posts to profiles.
