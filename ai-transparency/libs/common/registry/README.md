# Schema Registry Strategy

This directory documents schema-versioning conventions for events.

- Topic: `benchmarks`
- Current schema: `benchmark-ingest.v1.json`
- Version field: `schema_version` (semver)
- Compatibility rule: additive changes only for minor versions; major versions require new schema file and consumer rollout plan.

In production, this should be backed by Confluent Schema Registry or Glue Schema Registry.
