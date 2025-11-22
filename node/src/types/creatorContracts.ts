// TypeScript contracts aligned with Python Pydantic schemas
// src/api/schemas/request_schemas.py & src/api/schemas/response_schemas.py

export interface CreatorEvaluationRequest {
  /** tiktok | instagram | youtube ... */
  platform: string;
  /** creator handle or id */
  handle: string;
  /** optional public profile URL */
  profile_url?: string;
  /** optional known metrics (followers, posts_30d, avg_likes, brand_fit, reports_90d, etc.) */
  metrics?: Record<string, unknown>;
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
  raw_profile: Record<string, unknown>;
  timestamp: string; // ISO datetime from FastAPI
}

export interface MissionCandidate {
  id: string;
  name: string;
  description?: string | null;
  type?: string; // default: "content"
  reward_type?: string; // default: "fixed"
  reward_amount?: number | null;
  currency?: string; // default: "KRW"
  requirement?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface MissionRecommendRequest {
  creator_id: string;
  creator_profile?: Record<string, unknown>;
  onboarding_result?: Record<string, unknown>;
  missions: MissionCandidate[];
  filters?: Record<string, unknown>;
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
  timestamp: string; // ISO datetime
}


