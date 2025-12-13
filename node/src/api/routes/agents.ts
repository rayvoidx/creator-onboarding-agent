import { Router } from 'express';
import { Request, Response } from 'express-serve-static-core';
import { authMiddleware } from '../middleware/auth.js';
import { AgentRunRequestSchema } from '../schemas/request.js';
import { runAgent } from '../../graphs/mainOrchestrator.js';

const router = Router();

// Force explicit casting to handle potential express version mismatch
router.post('/run', authMiddleware as any, async (req: Request, res: Response) => {
  const parse = AgentRunRequestSchema.safeParse(req.body);
  if (!parse.success) {
    const payload = {
      success: false,
      error: { code: 400, message: 'Invalid request' },
      timestamp: Date.now()
    };
    res.status(400).json(payload);
    return;
  }
  const { agentType, input, params } = parse.data;
  try {
    const result = await runAgent({ agentType: agentType as any, input, params });
    
    const payload = { success: true, data: result, timestamp: Date.now() };
    res.status(200).json(payload);
  } catch (err: any) {
    const payload = {
      success: false,
      error: { code: 500, message: err?.message ?? 'Internal error' },
      timestamp: Date.now()
    };
    res.status(500).json(payload);
  }
});

export default router;
