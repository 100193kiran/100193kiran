import express from 'express';
import Ajv from 'ajv';
import Redis from 'ioredis';
import { Pool } from 'pg';
import crypto from 'crypto';
import { provenanceSchema } from './provenanceSchema';
import { computeTrustScore } from './trust';

const app = express();
app.use(express.json());
const ajv = new Ajv();
const validate = ajv.compile(provenanceSchema);

export const pool = new Pool({
  host: process.env.POSTGRES_HOST || 'localhost',
  port: Number(process.env.POSTGRES_PORT || 5432),
  user: process.env.POSTGRES_USER || 'postgres',
  password: process.env.POSTGRES_PASSWORD || 'postgres',
  database: process.env.POSTGRES_DB || 'ai_transparency'
});

export const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

app.get('/health', (_req, res) => res.json({ status: 'ok' }));

app.post('/models', async (req, res) => {
  if (!validate(req.body.training_data)) {
    return res.status(400).json({ error: 'Invalid training_data provenance schema' });
  }
  const { name, version, architecture, training_data } = req.body;
  const provenance_score = training_data.provenance_score;
  const result = await pool.query(
    `INSERT INTO models(name, version, architecture, training_data, provenance_score)
     VALUES ($1,$2,$3,$4,$5) RETURNING *`,
    [name, version, architecture, training_data, provenance_score]
  );
  const model = result.rows[0];
  const payload = JSON.stringify(model);
  await pool.query(
    `INSERT INTO audit_logs(actor, action, entity_type, entity_id, payload, payload_hash)
      VALUES ($1,$2,$3,$4,$5,$6)`,
    ['system', 'create_model', 'model', model.id, payload, crypto.createHash('sha256').update(payload).digest('hex')]
  );
  res.status(201).json(model);
});

async function recomputeTrust(modelId: string) {
  const m = await pool.query('SELECT * FROM models WHERE id = $1', [modelId]);
  if (!m.rows[0]) return null;
  const model = m.rows[0];
  const benches = await pool.query('SELECT metrics FROM benchmark_runs WHERE model_id = $1 ORDER BY created_at DESC LIMIT 20', [modelId]);
  const nums = benches.rows.flatMap((r) => Object.values(r.metrics || {}).filter((v): v is number => typeof v === 'number'));
  const benchmarkScore = nums.length ? Math.max(0, Math.min(1, nums.reduce((a, b) => a + Number(b), 0) / nums.length)) : 0;

  const reviews = await pool.query('SELECT rating FROM reviews WHERE model_id = $1', [modelId]);
  const avgRating = reviews.rows.length ? reviews.rows.reduce((a, r) => a + Number(r.rating || 0), 0) / reviews.rows.length : 3;
  const userSentiment = Math.max(-1, Math.min(1, (avgRating - 3) / 2));

  const trust = computeTrustScore({
    benchmarkScore,
    provenanceScore: Number(model.provenance_score || 0),
    userSentiment,
    auditScore: 0.5
  });
  await pool.query('UPDATE models SET trust_score=$1 WHERE id=$2', [trust, modelId]);
  return trust;
}

app.get('/models/:id', async (req, res) => {
  const key = `model:${req.params.id}`;
  const cached = await redis.get(key);
  if (cached) return res.json(JSON.parse(cached));

  const modelRes = await pool.query('SELECT * FROM models WHERE id = $1', [req.params.id]);
  if (!modelRes.rows[0]) return res.status(404).json({ error: 'Not found' });

  const benchmarkRes = await pool.query(
    `SELECT benchmark_name, AVG((metrics->>'score')::numeric) as avg_score
      FROM benchmark_runs WHERE model_id = $1 GROUP BY benchmark_name`,
    [req.params.id]
  );
  const reviewRes = await pool.query('SELECT author, rating, text, tags, created_at FROM reviews WHERE model_id = $1 ORDER BY created_at DESC LIMIT 5', [req.params.id]);
  const payload = { model: modelRes.rows[0], benchmark_summary: benchmarkRes.rows, reviews_summary: reviewRes.rows };
  await redis.set(key, JSON.stringify(payload), 'EX', 60);
  res.json(payload);
});

app.post('/models/:id/benchmarks', async (req, res) => {
  const { benchmark_name, metrics, auditor_signature } = req.body;
  await pool.query(
    'INSERT INTO benchmark_runs(model_id, benchmark_name, metrics, auditor_signature) VALUES ($1,$2,$3,$4)',
    [req.params.id, benchmark_name, metrics, auditor_signature]
  );
  await recomputeTrust(req.params.id);
  await redis.del(`model:${req.params.id}`);
  const payload = JSON.stringify(req.body);
  await pool.query(
    `INSERT INTO audit_logs(actor, action, entity_type, entity_id, payload, payload_hash)
      VALUES ($1,$2,$3,$4,$5,$6)`,
    ['system', 'add_benchmark', 'model', req.params.id, payload, crypto.createHash('sha256').update(payload).digest('hex')]
  );
  res.status(201).json({ ok: true });
});

app.get('/models/:id/benchmarks', async (req, res) => {
  const data = await pool.query('SELECT * FROM benchmark_runs WHERE model_id = $1 ORDER BY created_at DESC', [req.params.id]);
  res.json(data.rows);
});

app.post('/models/:id/recompute_trust', async (req, res) => {
  const trust = await recomputeTrust(req.params.id);
  if (trust === null) return res.status(404).json({ error: 'Not found' });
  await redis.del(`model:${req.params.id}`);
  res.json({ trust_score: trust });
});

const port = Number(process.env.PORT || 4000);
if (process.env.NODE_ENV !== 'test') {
  app.listen(port, () => console.log(`profiles on ${port}`));
}

export default app;
