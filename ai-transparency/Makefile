SHELL := /bin/bash

COMPOSE ?= docker compose
PROJECT ?= ai-transparency
MODEL_FILE ?= .seed-model-id

.PHONY: up down logs ps seed smoke test clean

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down --remove-orphans

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

seed:
	bash scripts/seed.sh $(MODEL_FILE)

smoke:
	bash scripts/smoke.sh $(MODEL_FILE)

test:
	cd services/profiles && npm test
	cd services/reviews && npm test
	pytest services/benchmarks/test_main.py services/analytics/test_analytics_main.py tests/contract/test_benchmark_schema.py

clean:
	rm -f $(MODEL_FILE)
