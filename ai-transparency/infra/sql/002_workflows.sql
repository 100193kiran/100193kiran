ALTER TABLE models
  ADD COLUMN IF NOT EXISTS workflow_status text NOT NULL DEFAULT 'draft';

CREATE TABLE IF NOT EXISTS model_workflow_events (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  model_id uuid REFERENCES models(id) ON DELETE CASCADE,
  actor text NOT NULL,
  from_status text,
  to_status text NOT NULL,
  note text,
  created_at timestamptz DEFAULT now()
);
