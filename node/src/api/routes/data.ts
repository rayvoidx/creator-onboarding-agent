import { Router } from 'express';
import { Request, Response } from 'express-serve-static-core';
import { refreshNewsCache, readNewsCache } from '../../services/newsService.js';

const router = Router();

router.get('/news', (_req: Request, res: Response) => {
  const cache = readNewsCache();
  res.status(200).json({ success: true, data: cache, timestamp: Date.now() });
});

router.post('/news/refresh', async (_req: Request, res: Response) => {
  try {
    const items = await refreshNewsCache();
    res.status(200).json({ success: true, data: { updatedAt: Date.now(), items }, timestamp: Date.now() });
  } catch (e: any) {
    res.status(500).json({ success: false, error: { code: 500, message: e?.message ?? 'failed to refresh news' }, timestamp: Date.now() });
  }
});

export default router;
