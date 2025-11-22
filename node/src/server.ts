import 'dotenv/config';
import express, { type Request, type Response } from 'express';
import { registerSecurity } from './api/middleware/security';
import { config } from './config';
import pino from 'pino';
import agentsRouter from './api/routes/agents';
import dataRouter from './api/routes/data';
import { correlationIdMiddleware } from './api/middleware/correlation';

const logger = pino({ level: process.env.LOG_LEVEL || 'info' });

const app = express();

// Base middleware
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: false }));
registerSecurity(app);
app.use(correlationIdMiddleware);

// Health endpoints
app.get('/healthz', (_req: Request, res: Response) => res.status(200).json({ ok: true }));
app.get('/readyz', (_req: Request, res: Response) => res.status(200).json({ ready: true }));

// API routes
app.use('/api/agents', agentsRouter);
app.use('/api/data', dataRouter);

const port = config.port;
app.listen(port, () => {
  logger.info({ port, env: config.nodeEnv }, 'Node+TS service started');
});

