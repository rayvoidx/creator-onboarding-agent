import type { Request, Response, NextFunction } from 'express';
import { randomUUID } from 'crypto';

const HEADER = 'X-Request-ID';

export function correlationIdMiddleware(req: Request, res: Response, next: NextFunction): void {
  const incoming = req.header(HEADER);
  const id = incoming && incoming.length > 0 ? incoming : randomUUID();
  (req as any).requestId = id;
  res.setHeader(HEADER, id);
  next();
}


