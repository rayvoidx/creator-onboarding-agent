import axios from 'axios';
import { config } from '../config';
import {
  CreatorEvaluationRequest,
  CreatorEvaluationResponse,
  MissionRecommendRequest,
  MissionRecommendationResponse
} from '../types/creatorContracts';

const PY_BACKEND_URL = process.env.PY_BACKEND_URL || 'http://ai-learning-api:8000';

export async function callCreatorEvaluate(
  payload: CreatorEvaluationRequest
): Promise<CreatorEvaluationResponse> {
  const url = `${PY_BACKEND_URL}/api/v1/creator/evaluate`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  };
  if (config.apiToken) {
    headers['Authorization'] = `Bearer ${config.apiToken}`;
  }
  const res = await axios.post<CreatorEvaluationResponse>(url, payload, { headers, timeout: 15000 });
  return res.data;
}

export async function callMissionRecommend(
  payload: MissionRecommendRequest
): Promise<MissionRecommendationResponse> {
  const url = `${PY_BACKEND_URL}/api/v1/missions/recommend`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  };
  if (config.apiToken) {
    headers['Authorization'] = `Bearer ${config.apiToken}`;
  }
  const res = await axios.post<MissionRecommendationResponse>(url, payload, { headers, timeout: 20000 });
  return res.data;
}


