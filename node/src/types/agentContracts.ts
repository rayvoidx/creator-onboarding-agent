import type { ZodSchema } from 'zod';

// Agent types supported by the BFF
export type AgentType =
  | 'llmManager'
  | 'enterpriseBriefing'
  | 'creatorOnboarding'
  | 'missionRecommend';

// Request DTO for /api/agents/run
export interface AgentRunRequestDto {
  agentType: AgentType;
  input: string | Record<string, unknown>;
  params?: Record<string, unknown>;
}

// Result shape returned by graph/mainOrchestrator.runAgent
export interface AgentRunResult<TOutput = unknown> {
  id: string;
  output: TOutput;
  usage?: { durationMs: number; model?: string };
}

export interface ApiSuccessEnvelope<TData> {
  success: true;
  data: TData;
  timestamp: number;
}

export interface ApiErrorDetail {
  code: number | string;
  message: string;
}

export interface ApiErrorEnvelope {
  success: false;
  error: ApiErrorDetail;
  timestamp: number;
}

export type AgentRunResponseDto<TOutput = unknown> =
  | ApiSuccessEnvelope<AgentRunResult<TOutput>>
  | ApiErrorEnvelope;

// Helper type for validating with zod while keeping DTO types
export type ZodSchemaOf<T> = ZodSchema<T>;


