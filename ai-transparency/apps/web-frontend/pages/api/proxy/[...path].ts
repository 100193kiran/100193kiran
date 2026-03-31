import type { NextApiRequest, NextApiResponse } from 'next';

function resolveTarget(path: string) {
  if (path.startsWith('reviews/')) return `http://reviews:4100/${path}`;
  if (/^models\/[^/]+\/reviews/.test(path)) return `http://reviews:4100/${path}`;
  return `http://profiles:4000/${path}`;
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const pathParts = req.query.path;
  const path = Array.isArray(pathParts) ? pathParts.join('/') : String(pathParts || '');
  const target = resolveTarget(path);

  const response = await fetch(target, {
    method: req.method,
    headers: { 'content-type': 'application/json' },
    body: ['GET', 'HEAD'].includes(req.method || 'GET') ? undefined : JSON.stringify(req.body)
  });

  const contentType = response.headers.get('content-type') || 'application/json';
  const payload = await response.text();
  res.setHeader('content-type', contentType);
  res.status(response.status).send(payload);
}
