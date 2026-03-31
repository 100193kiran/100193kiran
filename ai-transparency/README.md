# ai-transparency

AI Transparency Platform monorepo scaffold.

## One-command developer UX

```bash
make up
```

Useful commands:

```bash
make up      # build and start full stack in background
make down    # stop and remove containers
make logs    # stream logs
make ps      # show service status
make seed    # create demo model + benchmark + review
make smoke   # verify model read path and trust score
```

## Runbook (local)

1. Start services:

```bash
make up
```

2. Wait for service health:

```bash
curl http://localhost:4000/health
curl http://localhost:5000/health
curl http://localhost:4100/health
curl http://localhost:6000/health
```

3. Seed example data:

```bash
make seed
```

4. Validate end-to-end behavior:

```bash
make smoke
```

## Manual API examples

```bash
curl -X POST http://localhost:4000/models -H 'content-type: application/json' -d '{
  "name":"DemoModel",
  "version":"1.0",
  "architecture":"transformer",
  "training_data":{
    "sources":["dataset-a"],
    "collection_method":"curated",
    "licenses":["cc-by-4.0"],
    "provenance_score":0.82
  }
}'

curl -X POST http://localhost:5000/ingest -H 'content-type: application/json' -d '{
  "model_id":"<MODEL_ID>",
  "benchmark_name":"truthfulqa",
  "metrics":{"score":0.74},
  "auditor_signature":"sig"
}'

curl -X POST http://localhost:4100/models/<MODEL_ID>/reviews -H 'content-type: application/json' -d '{
  "author":"auditor-1",
  "rating":4,
  "text":"good transparency",
  "tags":["governance"]
}'
```

## Troubleshooting

- Kafka may take 20-40 seconds to elect a controller and accept producers.
- Postgres init SQL runs only on first volume init; remove volumes if schema changes.
- If `make seed` fails due startup order, retry after `make logs` confirms kafka/profiles are healthy.
