import { z } from 'zod';

export const AgentRunResponseSchema = z.object({
  id: z.string(),
  output: z.any(),
  usage: z
    .object({
      durationMs: z.number().int().nonnegative(),
      model: z.string().optional()
    })
    .optional()
});

export type AgentRunResponse = z.infer<typeof AgentRunResponseSchema>;


