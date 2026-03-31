import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';

const app = express();
const PORT = Number(process.env.PORT || 8080);
const AUTH_TOKEN = process.env.AUTH_TOKEN || 'dev-token';
const WINDOW_MS = 60_000;
const MAX_REQ = 120;
const hits = new Map<string, { count: number; resetAt: number }>();

app.use((req, res, next) => {
  const apiKey = req.headers.authorization;
  if (!apiKey || apiKey !== `Bearer ${AUTH_TOKEN}`) {
    return res.status(401).json({ error: 'unauthorized' });
  }
  const key = req.ip || 'unknown';
  const now = Date.now();
  const current = hits.get(key);
  if (!current || now > current.resetAt) {
    hits.set(key, { count: 1, resetAt: now + WINDOW_MS });
    return next();
  }
  if (current.count >= MAX_REQ) return res.status(429).json({ error: 'rate_limited' });
  current.count += 1;
  next();
});

app.use('/profiles', createProxyMiddleware({ target: 'http://profiles:4000', changeOrigin: true, pathRewrite: { '^/profiles': '' } }));
app.use('/reviews', createProxyMiddleware({ target: 'http://reviews:4100', changeOrigin: true, pathRewrite: { '^/reviews': '' } }));
app.use('/benchmarks', createProxyMiddleware({ target: 'http://benchmarks:5000', changeOrigin: true, pathRewrite: { '^/benchmarks': '' } }));
app.use('/analytics', createProxyMiddleware({ target: 'http://analytics:6000', changeOrigin: true, pathRewrite: { '^/analytics': '' } }));
app.get('/health', (_req, res) => res.json({ status: 'ok' }));

app.listen(PORT, () => console.log(`api-gateway on ${PORT}`));
