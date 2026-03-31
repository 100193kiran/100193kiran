import { Request, Response, NextFunction } from 'express';

export type Role = 'admin' | 'auditor' | 'publisher' | 'viewer';

export function requireAuth(req: Request, res: Response, next: NextFunction) {
  const token = req.headers.authorization?.replace(/^Bearer\s+/i, '');
  const expected = process.env.AUTH_TOKEN || 'dev-token';
  if (!token || token !== expected) {
    return res.status(401).json({ error: 'unauthorized' });
  }
  next();
}

export function requireRole(roles: Role[]) {
  return (req: Request, res: Response, next: NextFunction) => {
    const role = (req.headers['x-user-role'] as Role | undefined) || 'viewer';
    if (!roles.includes(role)) {
      return res.status(403).json({ error: 'forbidden', required_roles: roles });
    }
    next();
  };
}
