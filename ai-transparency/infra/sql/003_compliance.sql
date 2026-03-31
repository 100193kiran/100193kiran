CREATE TABLE IF NOT EXISTS model_cards (
  model_id uuid PRIMARY KEY REFERENCES models(id) ON DELETE CASCADE,
  summary text,
  intended_use text,
  limitations text,
  evaluation_data jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS compliance_evidence (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  model_id uuid REFERENCES models(id) ON DELETE CASCADE,
  evidence_type text NOT NULL,
  uri text NOT NULL,
  digest text,
  metadata jsonb,
  created_at timestamptz DEFAULT now()
);
