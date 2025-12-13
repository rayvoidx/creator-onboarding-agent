import { Request, Response, NextFunction } from 'express-serve-static-core';
import { randomUUID } from 'crypto';

const HEADER = 'X-Request-ID';

export function correlationIdMiddleware(req: Request, res: Response, next: NextFunction): void {
  const incoming = (req.headers as any)[HEADER.toLowerCase()];
  const id = incoming && incoming.length > 0 ? incoming : randomUUID();
  (req as any).requestId = id;
  res.setHeader(HEADER, id);
  next();
}
