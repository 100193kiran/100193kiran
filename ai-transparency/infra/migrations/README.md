# Migration Management

- SQL bootstrap scripts in `infra/sql` are for first-run container initialization.
- Ongoing schema evolution should be managed with migration tools:
  - Python services: Alembic (`infra/migrations/alembic`)
  - Node services: TypeORM migrations (`services/profiles/migrations`)

This repository includes starter scaffolding so migration history can be versioned and reviewed in PRs.
