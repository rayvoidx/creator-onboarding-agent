import type { Request, Response, NextFunction } from 'express';
import { config } from '../../config';

export function authMiddleware(req: Request, res: Response, next: NextFunction): void {
  if (!config.apiToken) {
    return next();
  }

  const auth = req.headers.authorization;
  if (!auth || !auth.startsWith('Bearer ')) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }

  const token = auth.slice('Bearer '.length);
  if (token !== config.apiToken) {
    res.status(403).json({ error: 'Forbidden' });
    return;
  }

  next();
}


