import { Request, Response, NextFunction } from 'express-serve-static-core';
import { config } from '../../config/index.js';

// Explicitly use types from express-serve-static-core which Express re-exports but sometimes gets confused
export function authMiddleware(req: Request, res: Response, next: NextFunction): void {
  if (!config.apiToken) {
    next();
    return;
  }

  const auth = (req.headers as any)['authorization'];
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
