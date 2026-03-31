import express from 'express';
import { Pool } from 'pg';
import fetch from 'node-fetch';

const app = express();
app.use(express.json());
const pool = new Pool({
  host: process.env.POSTGRES_HOST || 'localhost',
  port: Number(process.env.POSTGRES_PORT || 5432),
  user: process.env.POSTGRES_USER || 'postgres',
  password: process.env.POSTGRES_PASSWORD || 'postgres',
  database: process.env.POSTGRES_DB || 'ai_transparency'
});

app.get('/health', (_req, res) => res.json({ status: 'ok' }));

app.post('/models/:id/reviews', async (req, res) => {
  const { author, rating, text, tags } = req.body;
  const created = await pool.query(
    'INSERT INTO reviews(model_id, author, rating, text, tags) VALUES ($1,$2,$3,$4,$5) RETURNING *',
    [req.params.id, author, rating, text, tags || []]
  );
  await fetch(`${process.env.PROFILES_URL || 'http://profiles:4000'}/models/${req.params.id}/recompute_trust`, { method: 'POST' });
  res.status(201).json(created.rows[0]);
});

app.get('/models/:id/reviews', async (req, res) => {
  const rows = await pool.query('SELECT * FROM reviews WHERE model_id=$1 ORDER BY created_at DESC', [req.params.id]);
  res.json(rows.rows);
});

if (process.env.NODE_ENV !== 'test') {
  app.listen(process.env.PORT || 4100, () => console.log('reviews started'));
}

export default app;
