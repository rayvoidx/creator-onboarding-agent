import { z } from 'zod';

export const ApiErrorSchema = z.object({
  code: z.union([z.string(), z.number()]),
  message: z.string()
});

export const ApiResponseSchema = <T extends z.ZodTypeAny>(dataSchema: T) =>
  z.object({
    success: z.literal(true),
    data: dataSchema,
    timestamp: z.number().int().nonnegative()
  });

export const ApiErrorResponseSchema = z.object({
  success: z.literal(false),
  error: ApiErrorSchema,
  timestamp: z.number().int().nonnegative()
});

export type ApiError = z.infer<typeof ApiErrorSchema>;
export type ApiErrorResponse = z.infer<typeof ApiErrorResponseSchema>;


