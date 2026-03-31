import express from 'express';
import Ajv from 'ajv';
import Redis from 'ioredis';
import { Pool } from 'pg';
import crypto from 'crypto';
import { provenanceSchema } from './provenanceSchema';
import { computeTrustScore } from './trust';
import { requireAuth, requireRole } from './auth';
import { canTransition, WorkflowStatus } from './workflow';

const app = express();
app.use(express.json());
const ajv = new Ajv();
const validateProvenance = ajv.compile(provenanceSchema);
const REVIEWS_URL = process.env.REVIEWS_URL || 'http://reviews:4100';

app.use((req, res, next) => {
  const correlationId = String(req.headers['x-correlation-id'] || crypto.randomUUID());
  res.setHeader('x-correlation-id', correlationId);
  (req as any).correlationId = correlationId;
  next();
});

export const pool = new Pool({
  host: process.env.POSTGRES_HOST || 'localhost',
  port: Number(process.env.POSTGRES_PORT || 5432),
  user: process.env.POSTGRES_USER || 'postgres',
  password: process.env.POSTGRES_PASSWORD || 'postgres',
  database: process.env.POSTGRES_DB || 'ai_transparency'
});

export const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

function normalizeScore(value: unknown, fallback = 0): number {
  const num = Number(value);
  if (Number.isNaN(num)) return fallback;
  return Math.max(0, Math.min(1, num));
}

async function writeAuditLog(action: string, entityId: string, payload: unknown) {
  const payloadString = JSON.stringify(payload);
  const payloadHash = crypto.createHash('sha256').update(payloadString).digest('hex');
  const previous = await pool.query('SELECT payload_hash FROM audit_logs ORDER BY created_at DESC LIMIT 1');
  await pool.query(
    `INSERT INTO audit_logs(actor, action, entity_type, entity_id, payload, payload_hash)
      VALUES ($1,$2,$3,$4,$5,$6)`,
    ['system', action, 'model', entityId, { payload: payloadString, prev_hash: previous.rows[0]?.payload_hash || null }, payloadHash]
  );
}

async function getReviewSummary(modelId: string, correlationId?: string) {
  const response = await fetch(`${REVIEWS_URL}/models/${modelId}/reviews/summary`, {
    headers: { authorization: `Bearer ${process.env.AUTH_TOKEN || 'dev-token'}`, 'x-correlation-id': correlationId || '' }
  });
  if (!response.ok) return { avg_rating: 3, review_count: 0 };
  return response.json() as Promise<{ avg_rating: number; review_count: number }>;
}

async function recomputeTrust(modelId: string, correlationId?: string) {
  const m = await pool.query('SELECT * FROM models WHERE id = $1', [modelId]);
  if (!m.rows[0]) return null;
  const model = m.rows[0];

  const benches = await pool.query('SELECT metrics FROM benchmark_runs WHERE model_id = $1 ORDER BY created_at DESC LIMIT 20', [modelId]);
  const scoreValues = benches.rows.map((r) => normalizeScore(r.metrics?.score, NaN)).filter((n) => !Number.isNaN(n));
  const benchmarkScore = scoreValues.length ? scoreValues.reduce((a, b) => a + b, 0) / scoreValues.length : 0;

  const summary = await getReviewSummary(modelId, correlationId);
  const userSentiment = Math.max(-1, Math.min(1, (Number(summary.avg_rating) - 3) / 2));

  const trust = computeTrustScore({
    benchmarkScore,
    provenanceScore: normalizeScore(model.provenance_score),
    userSentiment,
    auditScore: 0.5
  });

  await pool.query('UPDATE models SET trust_score=$1 WHERE id=$2', [trust, modelId]);
  return trust;
}

app.get('/health', (_req, res) => res.json({ status: 'ok' }));

app.post('/models', requireAuth, requireRole(['publisher', 'admin']), async (req, res, next) => {
  try {
    if (!validateProvenance(req.body.training_data)) {
      return res.status(400).json({ error: 'Invalid training_data provenance schema', details: validateProvenance.errors });
    }
    const { name, version, architecture, training_data } = req.body;
    if (!name) return res.status(400).json({ error: 'name is required' });

    const provenance_score = normalizeScore(training_data.provenance_score);
    const result = await pool.query(
      `INSERT INTO models(name, version, architecture, training_data, provenance_score)
       VALUES ($1,$2,$3,$4,$5) RETURNING *`,
      [name, version, architecture, training_data, provenance_score]
    );

    const model = result.rows[0];
    await writeAuditLog('create_model', model.id, model);
    res.status(201).json(model);
  } catch (err) { next(err); }
});

app.get('/models/:id', async (req, res, next) => {
  try {
    const key = `model:${req.params.id}`;
    const cached = await redis.get(key);
    if (cached) return res.json(JSON.parse(cached));

    const modelRes = await pool.query('SELECT * FROM models WHERE id = $1', [req.params.id]);
    if (!modelRes.rows[0]) return res.status(404).json({ error: 'Not found' });

    const benchmarkRes = await pool.query(
      `SELECT benchmark_name, AVG((metrics->>'score')::numeric) as avg_score, COUNT(*)::int as runs
       FROM benchmark_runs WHERE model_id = $1 GROUP BY benchmark_name ORDER BY benchmark_name`,
      [req.params.id]
    );

    const reviewsResponse = await fetch(`${REVIEWS_URL}/models/${req.params.id}/reviews`, {
      headers: { authorization: `Bearer ${process.env.AUTH_TOKEN || 'dev-token'}` }
    });
    const reviews = reviewsResponse.ok ? await reviewsResponse.json() : [];
    const payload = { model: modelRes.rows[0], benchmark_summary: benchmarkRes.rows, reviews_summary: reviews.slice(0, 5) };

    await redis.set(key, JSON.stringify(payload), 'EX', 60);
    res.json(payload);
  } catch (err) { next(err); }
});

app.post('/models/:id/benchmarks', requireAuth, requireRole(['auditor', 'admin']), async (req, res, next) => {
  try {
    const { benchmark_name, metrics, auditor_signature } = req.body;
    if (!benchmark_name || typeof benchmark_name !== 'string') return res.status(400).json({ error: 'benchmark_name is required' });
    if (!metrics || typeof metrics !== 'object') return res.status(400).json({ error: 'metrics object is required' });

    await pool.query('INSERT INTO benchmark_runs(model_id, benchmark_name, metrics, auditor_signature) VALUES ($1,$2,$3,$4)', [req.params.id, benchmark_name, metrics, auditor_signature]);
    await recomputeTrust(req.params.id, (req as any).correlationId);
    await redis.del(`model:${req.params.id}`);
    await writeAuditLog('add_benchmark', req.params.id, req.body);
    res.status(201).json({ ok: true });
  } catch (err) { next(err); }
});

app.get('/models/:id/benchmarks', async (req, res, next) => {
  try {
    const data = await pool.query('SELECT * FROM benchmark_runs WHERE model_id = $1 ORDER BY created_at DESC', [req.params.id]);
    res.json(data.rows);
  } catch (err) { next(err); }
});

app.post('/models/:id/recompute_trust', requireAuth, requireRole(['auditor', 'admin']), async (req, res, next) => {
  try {
    const trust = await recomputeTrust(req.params.id, (req as any).correlationId);
    if (trust === null) return res.status(404).json({ error: 'Not found' });
    await redis.del(`model:${req.params.id}`);
    res.json({ trust_score: trust });
  } catch (err) { next(err); }
});

app.get('/models/:id/workflow', requireAuth, async (req, res, next) => {
  try {
    const model = await pool.query('SELECT id, workflow_status FROM models WHERE id = $1', [req.params.id]);
    if (!model.rows[0]) return res.status(404).json({ error: 'Not found' });
    const events = await pool.query('SELECT actor, from_status, to_status, note, created_at FROM model_workflow_events WHERE model_id=$1 ORDER BY created_at DESC', [req.params.id]);
    res.json({ model_id: req.params.id, workflow_status: model.rows[0].workflow_status, history: events.rows });
  } catch (err) { next(err); }
});

app.post('/models/:id/workflow/submit', requireAuth, requireRole(['publisher', 'admin']), async (req, res, next) => {
  try {
    const actor = (req.headers['x-user-id'] as string | undefined) || 'publisher';
    const row = await pool.query('SELECT workflow_status FROM models WHERE id = $1', [req.params.id]);
    if (!row.rows[0]) return res.status(404).json({ error: 'Not found' });
    const fromStatus = row.rows[0].workflow_status as WorkflowStatus;
    const toStatus: WorkflowStatus = 'submitted';
    if (!canTransition(fromStatus, toStatus)) return res.status(409).json({ error: 'invalid_transition', fromStatus, toStatus });

    await pool.query('UPDATE models SET workflow_status = $1 WHERE id = $2', [toStatus, req.params.id]);
    await pool.query('INSERT INTO model_workflow_events(model_id, actor, from_status, to_status, note) VALUES ($1,$2,$3,$4,$5)', [req.params.id, actor, fromStatus, toStatus, req.body?.note || null]);
    await redis.del(`model:${req.params.id}`);
    res.json({ model_id: req.params.id, workflow_status: toStatus });
  } catch (err) { next(err); }
});

app.post('/models/:id/workflow/approve', requireAuth, requireRole(['auditor', 'admin']), async (req, res, next) => {
  try {
    const actor = (req.headers['x-user-id'] as string | undefined) || 'auditor';
    const target: WorkflowStatus = req.body?.decision === 'reject' ? 'rejected' : 'approved';
    const row = await pool.query('SELECT workflow_status FROM models WHERE id = $1', [req.params.id]);
    if (!row.rows[0]) return res.status(404).json({ error: 'Not found' });
    const fromStatus = row.rows[0].workflow_status as WorkflowStatus;
    if (!canTransition(fromStatus, target)) return res.status(409).json({ error: 'invalid_transition', fromStatus, toStatus: target });

    await pool.query('UPDATE models SET workflow_status = $1 WHERE id = $2', [target, req.params.id]);
    await pool.query('INSERT INTO model_workflow_events(model_id, actor, from_status, to_status, note) VALUES ($1,$2,$3,$4,$5)', [req.params.id, actor, fromStatus, target, req.body?.note || null]);
    await redis.del(`model:${req.params.id}`);
    res.json({ model_id: req.params.id, workflow_status: target });
  } catch (err) { next(err); }
});

app.post('/models/:id/model-card', requireAuth, requireRole(['publisher', 'admin']), async (req, res, next) => {
  try {
    const { summary, intended_use, limitations, evaluation_data } = req.body;
    await pool.query(
      `INSERT INTO model_cards(model_id, summary, intended_use, limitations, evaluation_data)
       VALUES ($1,$2,$3,$4,$5)
       ON CONFLICT (model_id) DO UPDATE SET summary = EXCLUDED.summary, intended_use = EXCLUDED.intended_use,
       limitations = EXCLUDED.limitations, evaluation_data = EXCLUDED.evaluation_data`,
      [req.params.id, summary, intended_use, limitations, evaluation_data || {}]
    );
    await writeAuditLog('upsert_model_card', req.params.id, req.body);
    res.status(201).json({ ok: true });
  } catch (err) { next(err); }
});

app.get('/models/:id/model-card', async (req, res, next) => {
  try {
    const result = await pool.query('SELECT * FROM model_cards WHERE model_id=$1', [req.params.id]);
    if (!result.rows[0]) return res.status(404).json({ error: 'Not found' });
    res.json(result.rows[0]);
  } catch (err) { next(err); }
});

app.post('/models/:id/compliance/evidence', requireAuth, requireRole(['auditor', 'admin']), async (req, res, next) => {
  try {
    const { evidence_type, uri, digest, metadata } = req.body;
    await pool.query(
      'INSERT INTO compliance_evidence(model_id, evidence_type, uri, digest, metadata) VALUES ($1,$2,$3,$4,$5)',
      [req.params.id, evidence_type, uri, digest, metadata || {}]
    );
    await writeAuditLog('add_compliance_evidence', req.params.id, req.body);
    res.status(201).json({ ok: true });
  } catch (err) { next(err); }
});

app.get('/models/:id/compliance/evidence', requireAuth, async (req, res, next) => {
  try {
    const result = await pool.query('SELECT * FROM compliance_evidence WHERE model_id=$1 ORDER BY created_at DESC', [req.params.id]);
    res.json(result.rows);
  } catch (err) { next(err); }
});

app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error(err);
  res.status(500).json({ error: 'internal_server_error' });
});

const port = Number(process.env.PORT || 4000);
if (process.env.NODE_ENV !== 'test') {
  app.listen(port, () => console.log(`profiles on ${port}`));
}

export default app;
