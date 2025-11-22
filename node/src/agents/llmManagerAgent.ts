import OpenAI from 'openai';
import { config } from '../config';

export interface LlmManagerAgentRunParams {
  input: string;
  params?: Record<string, unknown>;
}

export interface LlmManagerAgentResult {
  id: string;
  output: string;
  usage?: { durationMs: number; model?: string };
}

export class LlmManagerAgent {
  private client: OpenAI | null;

  constructor() {
    this.client = config.openaiApiKey ? new OpenAI({ apiKey: config.openaiApiKey }) : null;
  }

  async run({ input }: LlmManagerAgentRunParams): Promise<LlmManagerAgentResult> {
    const start = Date.now();

    if (!this.client) {
      return {
        id: `mock_${start}`,
        output: `[MOCK RESPONSE] ${input}`,
        usage: { durationMs: Date.now() - start, model: 'mock' }
      };
    }

    const completion = await this.client.chat.completions.create({
      model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
      messages: [{ role: 'user', content: input }]
    });

    const text = completion.choices[0]?.message?.content ?? '';
    return {
      id: completion.id,
      output: text,
      usage: { durationMs: Date.now() - start, model: completion.model }
    };
  }
}


