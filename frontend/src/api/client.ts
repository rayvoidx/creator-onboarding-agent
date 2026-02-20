import axios, { AxiosInstance } from "axios";
import {
  AgentModelStatusResponse,
  AnalyticsRequestPayload,
  AnalyticsResponse,
  CreatorEvaluationPayload,
  CreatorEvaluationResponse,
  HealthResponse,
  MissionRecommendPayload,
  MissionRecommendationResponse,
  LoginPayload,
  TokenResponse,
  UserResponse,
  RegisterPayload,
  AuditLogResponse,
  AuditLogQuery,
  CreatorHistoryResponse,
  ExperimentStats,
  CircuitBreakerStatus,
  VectorSearchResult,
  SearchStatsResponse,
  SimilarCreator,
  FetchUrlResult,
  WebSearchResult,
  MCPTool,
} from "./types";

const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001",
  timeout: 20000,
});

// Token management
let accessToken: string | null = null;
let refreshToken: string | null = null;

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}

export function getAccessToken(): string | null {
  if (!accessToken) {
    accessToken = localStorage.getItem("access_token");
  }
  return accessToken;
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

// Add auth header interceptor
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refresh = refreshToken || localStorage.getItem("refresh_token");
      if (refresh) {
        try {
          const { data } = await axios.post<TokenResponse>(
            `${api.defaults.baseURL}/api/v1/auth/refresh`,
            { refresh_token: refresh }
          );
          setTokens(data.access_token, data.refresh_token);
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          console.error("Token refresh failed", refreshError);
          clearTokens();
          window.location.href = "/login";
        }
      }
    }

    return Promise.reject(error);
  }
);

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/health");
  return data;
}

export async function fetchAgentModelStatus(): Promise<AgentModelStatusResponse> {
  const { data } = await api.get<AgentModelStatusResponse>("/api/v1/system/agent-models");
  return data;
}

export async function evaluateCreator(payload: CreatorEvaluationPayload) {
  const { data } = await api.post<CreatorEvaluationResponse>(
    "/api/v1/creator/evaluate",
    payload
  );
  return data;
}

export async function recommendMissions(payload: MissionRecommendPayload) {
  const { data } = await api.post<MissionRecommendationResponse>(
    "/api/v1/missions/recommend",
    payload
  );
  return data;
}

export async function createAnalyticsReport(payload: AnalyticsRequestPayload) {
  const { data } = await api.post<AnalyticsResponse>(
    "/api/v1/analytics/report",
    payload
  );
  return data;
}

// Authentication APIs
export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const formData = new URLSearchParams();
  formData.append("username", payload.username);
  formData.append("password", payload.password);

  const { data } = await api.post<TokenResponse>("/api/v1/auth/login", formData, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });

  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function register(payload: RegisterPayload): Promise<UserResponse> {
  const { data } = await api.post<UserResponse>("/api/v1/auth/register", payload);
  return data;
}

export async function getCurrentUser(): Promise<UserResponse> {
  const { data } = await api.get<UserResponse>("/api/v1/auth/me");
  return data;
}

export async function logout(): Promise<void> {
  await api.post("/api/v1/auth/logout");
  clearTokens();
}

// Audit Log APIs
export async function getAuditLogs(query?: AuditLogQuery): Promise<AuditLogResponse> {
  const { data } = await api.get<AuditLogResponse>("/api/v1/audit/logs", {
    params: query,
  });
  return data;
}

export async function getAuditStats(startDate?: string, endDate?: string) {
  const { data } = await api.get("/api/v1/audit/stats", {
    params: { start_date: startDate, end_date: endDate },
  });
  return data;
}

// Creator History APIs
export async function getCreatorHistory(
  creatorId: string,
  params?: {
    start_date?: string;
    end_date?: string;
    change_type?: string;
    limit?: number;
    offset?: number;
  }
): Promise<CreatorHistoryResponse> {
  const { data } = await api.get<CreatorHistoryResponse>(
    `/api/v1/creators/${creatorId}/history`,
    { params }
  );
  return data;
}

export async function getCreatorTrend(creatorId: string, periodDays: number = 30) {
  const { data } = await api.get(`/api/v1/creators/${creatorId}/trend`, {
    params: { period_days: periodDays },
  });
  return data;
}

// A/B Testing APIs
export async function listExperiments(status?: string) {
  const { data } = await api.get("/api/v1/experiments/", {
    params: status ? { status } : undefined,
  });
  return data;
}

export async function getExperimentStats(experimentId: string): Promise<{ stats: ExperimentStats }> {
  const { data } = await api.get<{ stats: ExperimentStats }>(
    `/api/v1/experiments/${experimentId}/stats`
  );
  return data;
}

export async function createExperiment(payload: {
  name: string;
  description: string;
  target_prompt_type: string;
  variants: Array<{
    name: string;
    type: string;
    content: string;
    weight?: number;
  }>;
  user_percentage?: number;
}) {
  const { data } = await api.post("/api/v1/experiments/create", payload);
  return data;
}

export async function startExperiment(experimentId: string) {
  const { data } = await api.post(`/api/v1/experiments/${experimentId}/start`);
  return data;
}

export async function stopExperiment(experimentId: string) {
  const { data } = await api.post(`/api/v1/experiments/${experimentId}/stop`);
  return data;
}

// Circuit Breaker APIs
export async function getCircuitBreakerStatus(name?: string): Promise<{
  circuit_breakers: Record<string, CircuitBreakerStatus> | CircuitBreakerStatus;
}> {
  const { data } = await api.get("/api/v1/circuit-breaker/status", {
    params: name ? { name } : undefined,
  });
  return data;
}

export async function resetCircuitBreaker(name: string) {
  const { data } = await api.post(`/api/v1/circuit-breaker/reset/${name}`);
  return data;
}

// RAG Query with SSE streaming
export function createRAGStream(
  query: string,
  queryType: string = "general_chat",
  userId?: string
): EventSource {
  const params = new URLSearchParams({
    query,
    query_type: queryType,
  });
  if (userId) params.append("user_id", userId);

  return new EventSource(
    `${api.defaults.baseURL}/api/v1/rag/query/stream?${params.toString()}`
  );
}

// MCP Vector Search APIs
export async function vectorSearch(
  query: string,
  limit: number = 10,
  filters?: Record<string, unknown>
): Promise<{ success: boolean; results: VectorSearchResult[]; count: number }> {
  const { data } = await api.post("/api/v1/mcp/vector-search", {
    query,
    limit,
    filters,
  });
  return data;
}

export async function keywordSearch(
  query: string,
  limit: number = 10
): Promise<{ success: boolean; results: VectorSearchResult[]; count: number }> {
  const { data } = await api.post("/api/v1/mcp/keyword-search", {
    query,
    limit,
  });
  return data;
}

export async function hybridSearch(
  query: string,
  limit: number = 10,
  filters?: Record<string, unknown>,
  vectorWeight: number = 0.7
): Promise<{ success: boolean; results: VectorSearchResult[]; count: number }> {
  const { data } = await api.post("/api/v1/mcp/hybrid-search", {
    query,
    limit,
    filters,
    vector_weight: vectorWeight,
  });
  return data;
}

export async function getSearchStats(): Promise<{ success: boolean; stats: SearchStatsResponse }> {
  const { data } = await api.get("/api/v1/mcp/search-stats");
  return data;
}

export async function findSimilarCreators(
  creatorProfile: {
    platform?: string;
    handle?: string;
    category?: string;
    followers?: number;
    tags?: string[];
  },
  limit: number = 5
): Promise<{ success: boolean; similar_creators: SimilarCreator[]; count: number }> {
  const { data } = await api.post("/api/v1/mcp/similar-creators", {
    creator_profile: creatorProfile,
    limit,
  });
  return data;
}

// MCP HTTP Fetch APIs
export async function fetchUrl(url: string): Promise<{ success: boolean; result: FetchUrlResult }> {
  const { data } = await api.post("/api/v1/mcp/fetch-url", { url });
  return data;
}

export async function fetchUrls(
  urls: string[],
  limit: number = 3
): Promise<{ success: boolean; results: FetchUrlResult[]; count: number }> {
  const { data } = await api.post("/api/v1/mcp/fetch-urls", { urls, limit });
  return data;
}

export async function webSearch(
  query: string,
  topK: number = 5,
  prioritizeGov: boolean = true
): Promise<{ success: boolean; result: WebSearchResult }> {
  const { data } = await api.post("/api/v1/mcp/web-search", {
    query,
    top_k: topK,
    prioritize_gov: prioritizeGov,
  });
  return data;
}

export async function searchAndFetch(
  query: string,
  topK: number = 3,
  fetchLimit: number = 2
): Promise<{ success: boolean; result: { query: string; search_results: number; fetched: FetchUrlResult[]; all_urls: string[] } }> {
  const { data } = await api.post("/api/v1/mcp/search-and-fetch", {
    query,
    top_k: topK,
    fetch_limit: fetchLimit,
  });
  return data;
}

export async function fetchCreatorProfile(
  profileUrl: string,
  platform: string = "unknown"
): Promise<{ success: boolean; profile: FetchUrlResult & { platform: string; fetched: boolean } }> {
  const { data } = await api.post("/api/v1/mcp/fetch-creator-profile", {
    profile_url: profileUrl,
    platform,
  });
  return data;
}

export async function listMCPTools(): Promise<{ tools: MCPTool[]; count: number }> {
  const { data } = await api.get("/api/v1/mcp/tools");
  return data;
}

export default api;

