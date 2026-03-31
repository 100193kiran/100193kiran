import express from 'express';
import { Pool } from 'pg';
import fetch from 'node-fetch';

const app = express();
app.use(express.json());
const AUTH_TOKEN = process.env.AUTH_TOKEN || 'dev-token';

const pool = new Pool({
  host: process.env.POSTGRES_HOST || 'localhost',
  port: Number(process.env.POSTGRES_PORT || 5432),
  user: process.env.POSTGRES_USER || 'postgres',
  password: process.env.POSTGRES_PASSWORD || 'postgres',
  database: process.env.POSTGRES_DB || 'ai_transparency'
});

app.get('/health', (_req, res) => res.json({ status: 'ok' }));

app.post('/models/:id/reviews', async (req, res, next) => {
  try {
    if (req.headers.authorization !== `Bearer ${AUTH_TOKEN}`) {
      return res.status(401).json({ error: 'unauthorized' });
    }

    const { author, rating, text, tags } = req.body;
    if (!Number.isInteger(rating) || rating < 1 || rating > 5) {
      return res.status(400).json({ error: 'rating must be an integer between 1 and 5' });
    }

    const created = await pool.query(
      'INSERT INTO reviews(model_id, author, rating, text, tags) VALUES ($1,$2,$3,$4,$5) RETURNING *',
      [req.params.id, author || 'anonymous', rating, text || '', tags || []]
    );

    await fetch(`${process.env.PROFILES_URL || 'http://profiles:4000'}/models/${req.params.id}/recompute_trust`, { method: 'POST', headers: { authorization: `Bearer ${AUTH_TOKEN}`, 'x-user-role': 'auditor' } });

    res.status(201).json(created.rows[0]);
  } catch (err) {
    next(err);
  }
});

app.get('/models/:id/reviews', async (req, res, next) => {
  try {
    const rows = await pool.query('SELECT * FROM reviews WHERE model_id=$1 ORDER BY created_at DESC', [req.params.id]);
    res.json(rows.rows);
  } catch (err) {
    next(err);
  }
});

app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error(err);
  res.status(500).json({ error: 'internal_server_error' });
});

if (process.env.NODE_ENV !== 'test') {
  app.listen(process.env.PORT || 4100, () => console.log('reviews started'));
}

export default app;
