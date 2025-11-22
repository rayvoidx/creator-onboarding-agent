import { z } from 'zod';
import type { AgentRunRequestDto, AgentType } from '../../types/agentContracts';

export const AgentTypeEnum = z.enum([
  'llmManager',
  'enterpriseBriefing',
  'creatorOnboarding',
  'missionRecommend'
] satisfies AgentType[]);

export const AgentRunRequestSchema = z.object({
  agentType: AgentTypeEnum.default('llmManager'),
  input: z.union([z.string(), z.record(z.any())]),
  params: z.record(z.any()).optional()
}) satisfies z.ZodSchema<AgentRunRequestDto>;

export type AgentRunRequest = AgentRunRequestDto;

