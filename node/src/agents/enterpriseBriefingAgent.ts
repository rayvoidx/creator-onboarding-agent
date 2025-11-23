import OpenAI from 'openai';
import { config } from '../config';

export interface EnterpriseBriefingParams {
  topic?: string;
  timeframe?: 'last_7d' | 'last_30d' | 'qtd' | 'mtd';
  audience?: 'exec' | 'ops' | 'sales' | 'it' | 'all';
  sources?: string[];
  context?: Array<{ title: string; link?: string; source?: string; pubDate?: string }>;
}

export class EnterpriseBriefingAgent {
  private client: OpenAI | null;

  constructor() {
    this.client = config.openaiApiKey ? new OpenAI({ apiKey: config.openaiApiKey }) : null;
  }

  async run(input: string | Record<string, unknown>): Promise<{
    id: string;
    output: Record<string, unknown>;
    usage?: { durationMs: number; model?: string };
  }> {
    const start = Date.now();
    const params: EnterpriseBriefingParams = typeof input === 'string' ? { topic: input } : (input as any);
    const topic = params.topic || 'business overview';
    const timeframe = params.timeframe || 'last_7d';
    const audience = params.audience || 'exec';
    const context = Array.isArray(params.context) ? params.context : [];

    if (!this.client) {
      return {
        id: `brief_${start}`,
        output: {
          title: `Executive Briefing: ${topic}`,
          timeframe,
          audience,
          summary: `Mock summary for ${topic} (${timeframe}).`,
          keyMetrics: [
            { name: 'Leads', value: 128, change: '+12%' },
            { name: 'Conversion Rate', value: '3.8%', change: '+0.3pp' },
            { name: 'Ticket Backlog', value: 42, change: '-18%' }
          ],
          risks: [
            { name: 'Vendor SLA drift', severity: 'medium' },
            { name: 'Data freshness gaps', severity: 'low' }
          ],
          recommendedActions: [
            'Enable weekly data sync validation',
            'Run pipeline healthcheck and alerting review'
          ],
          contextPreview: context.slice(0, 5)
        },
        usage: { durationMs: Date.now() - start, model: 'mock' }
      };
    }

    const ctxText = context.length
      ? `Use the following recent items as context (prefer summarizing trends over listing):\n${context
          .slice(0, 15)
          .map((c) => `- ${c.title}${c.source ? ` (${c.source})` : ''}`)
          .join('\n')}`
      : '';

    const sys = `You are an enterprise briefing generator. Return concise JSON with: 
{
  title, timeframe, audience,
  summary,
  keyMetrics: [{ name, value, change }],
  risks: [{ name, severity }],
  recommendedActions: [string]
}`;

    const completion = await this.client.chat.completions.create({
      model: process.env.OPENAI_MODEL || 'gpt-5.1',
      messages: [
        { role: 'system', content: sys },
        {
          role: 'user',
          content: `Generate an executive briefing about "${topic}" for ${audience} over ${timeframe}. ${ctxText}`
        }
      ]
    });

    const text = completion.choices[0]?.message?.content || '{}';
    let json: Record<string, unknown>;
    try {
      json = JSON.parse(text);
    } catch {
      json = { raw: text };
    }
    return {
      id: completion.id,
      output: json,
      usage: { durationMs: Date.now() - start, model: completion.model }
    };
  }
}


