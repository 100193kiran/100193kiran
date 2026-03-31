CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS models (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name text NOT NULL,
  version text,
  architecture text,
  training_data jsonb,
  provenance_score numeric DEFAULT 0,
  trust_score numeric DEFAULT 0,
  created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS benchmark_runs (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  model_id uuid REFERENCES models(id) ON DELETE CASCADE,
  benchmark_name text NOT NULL,
  metrics jsonb NOT NULL,
  auditor_signature text,
  created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reviews (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  model_id uuid REFERENCES models(id) ON DELETE CASCADE,
  author text,
  rating int,
  text text,
  tags jsonb,
  created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  actor text,
  action text,
  entity_type text,
  entity_id uuid,
  payload jsonb,
  payload_hash text,
  created_at timestamptz DEFAULT now()
);
