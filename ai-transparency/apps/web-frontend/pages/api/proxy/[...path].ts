import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const path = (req.query.path as string[]).join('/');
  let target = `http://profiles:4000/${path}`;
  if (path.includes('/reviews') || path.startsWith('reviews/')) {
    target = path.startsWith('reviews/') ? `http://reviews:4100/${path}` : `http://reviews:4100/${path.replace(/^models\//, 'models/')}`;
  }
  const response = await fetch(target, {
    method: req.method,
    headers: { 'content-type': 'application/json' },
    body: req.method === 'GET' ? undefined : JSON.stringify(req.body)
  });
  const text = await response.text();
  res.status(response.status).send(text);
}
