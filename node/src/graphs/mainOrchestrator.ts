import { AgentRunResponse } from '../api/schemas/response';
import { LlmManagerAgent } from '../agents/llmManagerAgent';
import { EnterpriseBriefingAgent } from '../agents/enterpriseBriefingAgent';
import { readNewsCache } from '../services/newsService';
import { SAMPLE_NEWS_PACK } from '../data/knowledge_packs';
import { callCreatorEvaluate, callMissionRecommend } from '../services/pythonApiClient';

type RunAgentArgs = {
  agentType: 'llmManager' | 'enterpriseBriefing' | 'creatorOnboarding' | 'missionRecommend';
  input: unknown;
  params?: Record<string, unknown>;
};

export async function runAgent(args: RunAgentArgs): Promise<AgentRunResponse> {
  switch (args.agentType) {
    case 'llmManager': {
      const agent = new LlmManagerAgent();
      const prompt = typeof args.input === 'string' ? args.input : JSON.stringify(args.input);
      const result = await agent.run({ input: prompt, params: args.params });
      return result;
    }
    case 'enterpriseBriefing': {
      const agent = new EnterpriseBriefingAgent();
      let enrichedInput: any = args.input;
      try {
        const inputObj = typeof args.input === 'string' ? { topic: args.input } : (args.input as any);
        const wantsLocalNews = Array.isArray(args.params?.sources)
          ? (args.params!.sources as string[]).includes('local:news')
          : Array.isArray(inputObj?.sources) && inputObj.sources.includes('local:news');
        if (wantsLocalNews) {
          const cache = readNewsCache();
          const items = (cache.items && cache.items.length > 0) ? cache.items : SAMPLE_NEWS_PACK.items;
          enrichedInput = { ...inputObj, context: items };
        }
      } catch {
        // keep original input
      }
      const result = await agent.run(enrichedInput);
      return result;
    }
    case 'creatorOnboarding': {
      const input: any = typeof args.input === 'string' ? JSON.parse(args.input) : args.input;
      const payload = {
        platform: String(input.platform || ''),
        handle: String(input.handle || ''),
        profile_url: input.profile_url,
        metrics: input.metrics || {}
      };
      const data = await callCreatorEvaluate(payload);
      return {
        id: `creator_${Date.now()}`,
        output: data,
        usage: { durationMs: 0 }
      };
    }
    case 'missionRecommend': {
      const input: any = typeof args.input === 'string' ? JSON.parse(args.input) : args.input;
      const payload = {
        creator_id: String(input.creator_id || input.creatorId || ''),
        creator_profile: input.creator_profile || input.creatorProfile || {},
        onboarding_result: input.onboarding_result || input.onboardingResult || {},
        missions: Array.isArray(input.missions) ? input.missions : [],
        filters: input.filters || {}
      };
      const data = await callMissionRecommend(payload);
      return {
        id: `mission_${Date.now()}`,
        output: data,
        usage: { durationMs: 0 }
      };
    }
    default:
      throw new Error(`Unsupported agentType: ${args.agentType}`);
  }
}


