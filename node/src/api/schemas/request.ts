import { z } from 'zod';
import type { AgentRunRequestDto, AgentType } from '../../types/agentContracts.js';

// The "satisfies" constraint was causing type issues with ZodEnum inference vs TS types.
// We explicitly list the values to match the AgentType union.
export const AgentTypeEnum = z.enum([
  'llmManager',
  'enterpriseBriefing',
  'creatorOnboarding',
  'missionRecommend'
]);

export const AgentRunRequestSchema = z.object({
  // Use z.nativeEnum or ensure the enum values align with the type.
  // Since AgentType is a string union, z.enum is correct, but the default inference caused a mismatch.
  agentType: AgentTypeEnum.default('llmManager') as z.ZodType<AgentType>, 
  input: z.union([z.string(), z.record(z.any())]),
  params: z.record(z.any()).optional()
});

export type AgentRunRequest = AgentRunRequestDto;
