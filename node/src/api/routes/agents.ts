import { Router, type Request, type Response } from 'express';
import { authMiddleware } from '../middleware/auth';
import { AgentRunRequestSchema } from '../schemas/request';
import { runAgent } from '../../graphs/mainOrchestrator';
import type {
  AgentRunRequestDto,
  AgentRunResponseDto,
  AgentRunResult
} from '../../types/agentContracts';

const router = Router();

type RunRequest = Request<unknown, AgentRunResponseDto, AgentRunRequestDto>;
type RunResponse = Response<AgentRunResponseDto>;

router.post('/run', authMiddleware, async (req: RunRequest, res: RunResponse) => {
  const parse = AgentRunRequestSchema.safeParse(req.body);
  if (!parse.success) {
    const payload: AgentRunResponseDto = {
      success: false,
      error: { code: 400, message: 'Invalid request' },
      timestamp: Date.now()
    };
    return res.status(400).json(payload);
  }
  const { agentType, input, params } = parse.data;
  try {
    const result: AgentRunResult = await runAgent({ agentType, input, params });
    const payload: AgentRunResponseDto = {
      success: true,
      data: result,
      timestamp: Date.now()
    };
    return res.status(200).json(payload);
  } catch (err: any) {
    const payload: AgentRunResponseDto = {
      success: false,
      error: { code: 500, message: err?.message ?? 'Internal error' },
      timestamp: Date.now()
    };
    return res.status(500).json(payload);
  }
});

export default router;


