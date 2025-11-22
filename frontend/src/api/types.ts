export interface HealthResponse {
  status: "healthy" | "unhealthy";
  version: string;
}

export interface AgentModelConfig {
  llm_models?: string[];
  embedding_model?: string;
  vector_db?: string;
  [key: string]: unknown;
}

export interface LLMStatusEntry {
  status: string;
  provider: string;
  priority: number;
  enabled?: boolean;
  last_health_check?: string;
  last_error?: string;
}

export interface AgentModelStatusResponse {
  agent_models: Record<string, AgentModelConfig>;
  llm_status?: Record<string, LLMStatusEntry>;
  timestamp: string;
}

export interface CreatorEvaluationPayload {
  platform: string;
  handle: string;
  profile_url?: string;
}

export interface CreatorEvaluationResponse {
  success: boolean;
  platform: string;
  handle: string;
  decision: string;
  grade: string;
  score: number;
  score_breakdown: Record<string, number>;
  tags: string[];
  risks: string[];
  report: string;
  timestamp: string;
}

export interface MissionRequirementDto {
  min_followers?: number;
  min_engagement_rate?: number;
  min_grade?: string;
  allowed_platforms?: string[];
  allowed_categories?: string[];
  required_tags?: string[];
}

export interface MissionDto {
  id: string;
  name: string;
  type: string;
  reward_type: string;
  reward_amount?: number;
  requirement?: MissionRequirementDto;
  metadata?: Record<string, unknown>;
}

export interface MissionRecommendPayload {
  creator_id: string;
  creator_profile: Record<string, unknown>;
  onboarding_result: Record<string, unknown>;
  missions: MissionDto[];
  filters?: Record<string, unknown>;
  external_sources?: Record<string, unknown>;
}

export interface MissionRecommendationItem {
  mission_id: string;
  mission_name: string;
  mission_type: string;
  reward_type: string;
  score: number;
  reasons: string[];
  metadata: Record<string, unknown>;
}

export interface MissionRecommendationResponse {
  success: boolean;
  creator_id: string;
  recommendations: MissionRecommendationItem[];
}

export interface AnalyticsRequestPayload {
  user_id: string;
  session_id?: string;
  report_type: string;
  date_range?: Record<string, string>;
  filters?: Record<string, unknown>;
  external_sources?: Record<string, unknown>;
}

export interface AnalyticsResponse {
  success: boolean;
  report_type: string;
  user_id: string;
  report_data: Record<string, unknown>;
  insights: string[];
  recommendations: Record<string, unknown>[];
  timestamp: string;
}

// Authentication Types
export interface LoginPayload {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  role: string;
  created_at: string;
  last_login?: string;
  permissions: string[];
}

export interface RegisterPayload {
  email: string;
  username: string;
  password: string;
  full_name?: string;
  role?: string;
}

// Audit Log Types
export interface AuditLogEntry {
  id: string;
  timestamp: string;
  user_id?: string;
  username?: string;
  role?: string;
  action: string;
  severity: string;
  resource_type?: string;
  resource_id?: string;
  details: Record<string, unknown>;
  success: boolean;
  error_message?: string;
}

export interface AuditLogResponse {
  logs: AuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditLogQuery {
  user_id?: string;
  action?: string;
  severity?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

// Creator History Types
export interface CreatorSnapshot {
  id: string;
  creator_id: string;
  timestamp: string;
  platform: string;
  handle: string;
  followers: number;
  avg_likes: number;
  avg_comments: number;
  posts_30d: number;
  engagement_rate: number;
  grade?: string;
  score?: number;
  decision?: string;
  tags: string[];
  risks: string[];
}

export interface CreatorTrend {
  creator_id: string;
  period_start: string;
  period_end: string;
  followers_start: number;
  followers_end: number;
  followers_change: number;
  followers_change_pct: number;
  engagement_start: number;
  engagement_end: number;
  engagement_change: number;
  score_start?: number;
  score_end?: number;
  grade_start?: string;
  grade_end?: string;
  grade_improved: boolean;
  missions_completed: number;
  trend_summary: string;
}

export interface CreatorHistoryResponse {
  creator_id: string;
  entries: Array<{
    id: string;
    creator_id: string;
    timestamp: string;
    change_type: string;
    description: string;
    metrics_delta: Record<string, unknown>;
    mission_id?: string;
    mission_name?: string;
  }>;
  snapshots: CreatorSnapshot[];
  trend?: CreatorTrend;
  total: number;
}

// A/B Testing Types
export interface ExperimentVariant {
  id: string;
  name: string;
  type: string;
  content: string;
  weight: number;
}

export interface Experiment {
  id: string;
  name: string;
  description: string;
  status: string;
  target_prompt_type: string;
  variants: ExperimentVariant[];
  user_percentage: number;
  created_at: string;
}

export interface ExperimentStats {
  experiment_id: string;
  experiment_name: string;
  status: string;
  total_samples: number;
  variant_stats: Record<string, {
    name: string;
    type: string;
    sample_size: number;
    metrics: {
      success_rate: number;
      avg_response_time_ms: number;
      avg_quality_score?: number;
      avg_user_feedback?: number;
    };
  }>;
  winner?: string;
  is_significant: boolean;
}

// Circuit Breaker Types
export interface CircuitBreakerStatus {
  name: string;
  state: string;
  fail_counter: number;
  stats: {
    total_calls: number;
    successes: number;
    failures: number;
  };
}

// MCP Types
export interface VectorSearchResult {
  id: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
  search_type: string;
  vector_score?: number;
  keyword_score?: number;
}

export interface SearchStatsResponse {
  total_documents: number;
  vector_store_available: boolean;
  embedding_model_available: boolean;
  reranker_available: boolean;
  vector_store_count?: number;
  search_config: {
    vector_weight: number;
    keyword_weight: number;
    max_results: number;
    similarity_threshold: number;
  };
}

export interface SimilarCreator {
  id: string;
  handle: string;
  platform: string;
  score: number;
  followers: number;
  grade: string;
  tags: string[];
  similarity_reason?: string;
}

export interface FetchUrlResult {
  url: string;
  status: number;
  content_type: string;
  site_name: string;
  text?: string;
  json?: unknown;
  error?: string;
}

export interface WebSearchResult {
  query: string;
  urls: string[];
  count: number;
  prioritize_gov: boolean;
  error?: string;
}

export interface MCPTool {
  name: string;
  description: string;
  server: string;
  input_schema: Record<string, unknown>;
}

// RAG Enhanced Types
export interface RAGEnhancedData {
  similar_creators: SimilarCreator[];
  category_insights: string;
  risk_analysis: string;
  market_context: string;
  recommendation_context: string;
}

