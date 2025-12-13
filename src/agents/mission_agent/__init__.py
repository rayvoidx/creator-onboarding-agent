from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ...core.base import BaseAgent, BaseState
from ...data.models.mission_models import (
    Mission,
    MissionRequirement,
    MissionAssignment,
    MissionAssignmentStatus,
)
from ...utils.agent_config import get_agent_runtime_config


class MissionRecommendationState(BaseState):
    """미션 추천 상태

    - creator_profile: 크리에이터 기본 정보/메트릭
    - onboarding_result: CreatorOnboardingAgent 결과(점수/등급/리스크/태그 등)
    - missions: 추천 후보 미션 리스트
    - recommendations: 추천된 MissionAssignment 리스트
    """

    creator_id: Optional[str] = None
    creator_profile: Dict[str, Any] = {}
    onboarding_result: Dict[str, Any] = {}
    missions: List[Mission] = []
    recommendations: List[MissionAssignment] = []


@dataclass
class MissionAgentConfig:
    """미션 추천 규칙 설정"""

    min_score_for_recommendation: float = 50.0
    top_k: int = 5


class MissionAgent(BaseAgent[MissionRecommendationState]):
    """
    Mission recommendation agent (rule-based v0.1).

    - 크리에이터 온보딩 결과 + 크리에이터 메트릭을 기반으로
      MissionRequirement를 만족하는 미션을 필터링
    - 간단한 적합도 점수를 계산하여 상위 N개를 추천
    - LLM은 추후 추천 사유 natural language 설명에만 사용할 수 있도록 훅을 남겨둔다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        merged_config = get_agent_runtime_config("mission", config)
        super().__init__("MissionAgent", merged_config)
        self.agent_model_config = merged_config
        scoring_config = {
            "min_score_for_recommendation": merged_config.get(
                "min_score_for_recommendation", 50.0
            ),
            "top_k": merged_config.get("top_k", 5),
        }
        self.cfg = MissionAgentConfig(**scoring_config)

    async def execute(
        self, state: MissionRecommendationState
    ) -> MissionRecommendationState:
        try:
            creator = state.creator_profile or {}
            onboarding = state.onboarding_result or {}
            missions = state.missions or []

            if not missions:
                state.add_error("추천할 미션 후보가 없습니다.")
                return state

            followers = _to_int(
                creator.get("followers") or creator.get("followers_count"), 0
            )
            engagement_rate = float(creator.get("engagement_rate") or 0.0)
            posts_30d = _to_int(creator.get("posts_30d"), 0)
            reports_90d = _to_int(creator.get("reports_90d"), 0)
            platform = str(creator.get("platform", "")).lower()
            grade = str(onboarding.get("grade", "")).upper()
            tags: List[str] = list(onboarding.get("tags", []))
            risks: List[str] = list(onboarding.get("risks", []))
            category = str(creator.get("category", "")).lower()
            completed_missions = _to_int(creator.get("completed_missions"), 0)
            avg_quality_score = float(creator.get("avg_quality_score") or 0.0)
            current_active_missions = _to_int(creator.get("current_active_missions"), 0)
            recent_mission_types: List[str] = list(
                creator.get("recent_mission_types", [])
            )
            youtube_context = (
                state.context.get("youtube_insights", {}) if state.context else {}
            )
            recent_videos = (
                youtube_context.get("channel_overview", {}).get("recent_videos", [])
                if isinstance(youtube_context, dict)
                else []
            )
            latest_video = recent_videos[0] if recent_videos else {}
            channel_info = (
                youtube_context.get("channel_overview", {}).get("channel_info", {})
                if isinstance(youtube_context, dict)
                else {}
            )

            # 추가 필터 (API에서 전달한 mission_types, min_reward 등)
            filters: Dict[str, Any] = (
                state.context.get("filters", {}) if state.context else {}
            )
            filter_types: List[str] = [str(t) for t in filters.get("mission_types", [])]
            min_reward = float(filters.get("min_reward") or 0.0)

            assignments: List[MissionAssignment] = []
            for m in missions:
                # 타입/보상 필터
                if filter_types and m.type.value not in filter_types:
                    continue
                if min_reward and (m.reward_amount or 0.0) < min_reward:
                    continue

                score, reasons = self._score_mission_for_creator(
                    mission=m,
                    platform=platform,
                    followers=followers,
                    engagement_rate=engagement_rate,
                    posts_30d=posts_30d,
                    reports_90d=reports_90d,
                    grade=grade,
                    tags=tags,
                    risks=risks,
                    category=category,
                    completed_missions=completed_missions,
                    avg_quality_score=avg_quality_score,
                    current_active_missions=current_active_missions,
                    recent_mission_types=recent_mission_types,
                )
                if score < self.cfg.min_score_for_recommendation:
                    continue

                assignments.append(
                    MissionAssignment(
                        id=f"{state.creator_id or 'creator'}::{m.id}",
                        mission_id=m.id,
                        creator_id=state.creator_id or "",
                        status=MissionAssignmentStatus.RECOMMENDED,
                        score=score,
                        reasons=reasons,
                        metadata={
                            "mission_name": m.name,
                            "mission_type": m.type.value,
                            "reward_type": m.reward_type.value,
                            "external_signals": {
                                "youtube_channel": channel_info.get("title"),
                                "latest_video": (
                                    {
                                        "title": latest_video.get("title"),
                                        "view_count": latest_video.get("view_count"),
                                        "published_at": latest_video.get(
                                            "published_at"
                                        ),
                                    }
                                    if latest_video
                                    else None
                                ),
                            },
                        },
                    )
                )

            # 점수 순으로 정렬 후 top_k
            assignments.sort(key=lambda a: a.score, reverse=True)
            state.recommendations = assignments[: self.cfg.top_k]
            return state
        except Exception as e:
            state.add_error(f"Mission recommendation failed: {e}")
            return state

    def _score_mission_for_creator(
        self,
        mission: Mission,
        platform: str,
        followers: int,
        engagement_rate: float,
        posts_30d: int,
        reports_90d: int,
        grade: str,
        tags: List[str],
        risks: List[str],
        category: str,
        completed_missions: int,
        avg_quality_score: float,
        current_active_missions: int,
        recent_mission_types: List[str],
    ) -> tuple[float, List[str]]:
        """미션 요구 조건과 크리에이터 프로필을 비교하여 0~100 점수와 사유를 반환."""
        req: MissionRequirement = mission.requirement
        reasons: List[str] = []

        # 기본 자격 필터 (미션 수행 불가한 경우 즉시 0점)
        if req.allowed_platforms and platform and platform not in req.allowed_platforms:
            return 0.0, ["플랫폼이 미션 요구 조건에 맞지 않습니다."]
        if followers < req.min_followers:
            return 0.0, ["팔로워 수가 미션 최소 요구 조건보다 낮습니다."]
        if req.max_followers is not None and followers > req.max_followers:
            return 0.0, ["팔로워 수가 이 미션의 타겟 상한을 초과합니다."]
        if posts_30d < req.min_posts_30d:
            return 0.0, ["최근 30일 게시물 수가 부족합니다."]
        if req.disallow_high_reports and reports_90d >= 3:
            return 0.0, ["최근 신고 이력이 많아 이 미션에는 추천하지 않습니다."]
        if reports_90d > req.max_reports_90d:
            return 0.0, ["최근 90일 신고 수가 미션 허용 범위를 초과합니다."]

        # 최소 등급 체크
        if req.min_grade:
            if _grade_rank(grade) < _grade_rank(req.min_grade):
                return 0.0, [
                    f"온보딩 등급이 미션 최소 요구 등급({req.min_grade})에 미치지 못합니다."
                ]

        # 카테고리 필터
        if req.excluded_categories and category in req.excluded_categories:
            return 0.0, ["크리에이터 카테고리가 미션에서 제외됩니다."]
        if (
            req.allowed_categories
            and category
            and category not in req.allowed_categories
        ):
            return 0.0, [
                "크리에이터 카테고리가 미션 허용 카테고리에 포함되지 않습니다."
            ]

        # 리스크 필터
        if req.exclude_risks:
            for r in risks:
                if r in req.exclude_risks:
                    return 0.0, [f"리스크 태그({r})로 인해 이 미션에서는 제외됩니다."]

        # 점수 구성 요소 (도메인 스펙 기반 가중치)
        score = 0.0
        weights = {
            "grade_fit": 0.25,
            "engagement_fit": 0.20,
            "category_fit": 0.20,
            "history_fit": 0.15,
            "availability_fit": 0.10,
            "diversity_bonus": 0.10,
        }

        # 등급 적합도 (25%)
        if req.min_grade:
            grade_diff = _grade_rank(grade) - _grade_rank(req.min_grade)
            if grade_diff >= 0:
                grade_fit = min(grade_diff / 3.0, 1.0)
                score += weights["grade_fit"] * grade_fit * 100.0
                reasons.append("온보딩 등급이 미션 요구 등급과 잘 맞습니다.")

        # 참여율 적합도 (20%)
        if engagement_rate > 0 and req.min_engagement_rate > 0:
            er_ratio = engagement_rate / max(req.min_engagement_rate, 0.01)
            engagement_fit = min(er_ratio, 2.0)  # 최대 2배까지 인정
            score += weights["engagement_fit"] * engagement_fit * 50.0
            if engagement_rate >= req.min_engagement_rate:
                reasons.append("참여율이 미션 요구 조건을 충족합니다.")

        # 카테고리/태그 적합도 (20%)
        category_fit_score = 0.0
        if req.allowed_categories:
            if category in req.allowed_categories:
                category_fit_score = 100.0
        else:
            # 허용 카테고리가 없으면 중립 점수
            category_fit_score = 50.0

        # 태그 매칭 보너스
        if req.required_tags:
            matched = [t for t in tags if t in req.required_tags]
            if matched:
                category_fit_score = max(category_fit_score, 80.0)
                reasons.append(
                    f"미션이 요구하는 태그/카테고리와 크리에이터 태그가 잘 맞습니다: {', '.join(matched)}"
                )

        score += weights["category_fit"] * category_fit_score

        # 이력 적합도 (15%) - 기본값 없으면 0
        history_score = 0.0
        history_score += min(completed_missions / 10.0, 1.0) * 50.0
        history_score += min(avg_quality_score / 100.0, 1.0) * 50.0
        score += weights["history_fit"] * history_score

        # 가용성 (10%)
        availability_score = 100.0 if current_active_missions < 3 else 50.0
        score += weights["availability_fit"] * availability_score

        # 다양성 보너스 (10%)
        diversity_score = (
            100.0
            if mission.type.value and mission.type.value not in recent_mission_types
            else 0.0
        )
        score += weights["diversity_bonus"] * diversity_score

        # 리스크 패널티 (도메인 리스크 규칙 반영)
        if "high_reports" in risks:
            score -= 20.0
            reasons.append("최근 신고 이력이 많아 감점되었습니다.")
        if "low_engagement" in risks and mission.reward_type.value in {
            "performance",
            "hybrid",
        }:
            score -= 10.0
            reasons.append("낮은 참여율 리스크로 성과 기반 미션에서 감점되었습니다.")
        if "low_activity" in risks:
            score -= 5.0
            reasons.append("활동성이 낮아 일부 감점되었습니다.")

        score = max(0.0, min(100.0, round(score, 1)))
        return score, reasons


def _to_int(v: Any, default: int = 0) -> int:
    try:
        if v is None:
            return default
        if isinstance(v, (int, float)):
            return int(v)
        s = str(v).replace(",", "").strip()
        return int(float(s))
    except Exception:
        return default


def _grade_rank(grade: str) -> int:
    """등급을 정수 랭크로 변환 (높을수록 좋은 등급)."""
    mapping = {"S": 4, "A": 3, "B": 2, "C": 1}
    return mapping.get(grade.upper(), 0)
