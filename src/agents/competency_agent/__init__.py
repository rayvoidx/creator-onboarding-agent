"""
DER-001: AI 기반 역량진단 모델 개발을 위한 에이전트

역량진단 문항과 응답, 학습자 데이터를 실시간으로 분석해
개인별 맞춤형 학습 방향에 참고할 수 있는 역량진단 모델을 구현합니다.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
from pydantic import Field

# 선택적 임포트 (머신러닝 라이브러리)
try:
    import numpy as np  # type: ignore
    import pandas as pd  # type: ignore
    from sklearn.preprocessing import StandardScaler  # type: ignore
    from sklearn.ensemble import RandomForestClassifier  # type: ignore

    ML_AVAILABLE = True
except ImportError:
    np = None  # type: ignore
    pd = None  # type: ignore
    StandardScaler = None  # type: ignore
    RandomForestClassifier = None  # type: ignore
    ML_AVAILABLE = False

from ...core.base import BaseAgent, BaseState
from ...data.models.competency_models import CompetencyQuestion, UserResponse
from ...tools.competency_tools import CompetencyAnalyzer, SecurityTool
from ...utils.agent_config import get_agent_runtime_config

logger = logging.getLogger(__name__)


class CompetencyDiagnosisState(BaseState):
    """역량진단 상태 관리"""

    assessment_id: Optional[str] = None
    questions: List[CompetencyQuestion] = Field(default_factory=list)
    responses: List[UserResponse] = Field(default_factory=list)
    analysis_result: Optional[Dict[str, Any]] = None
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    security_level: str = "standard"


class CompetencyAgent(BaseAgent[CompetencyDiagnosisState]):
    """역량진단 AI 에이전트 (DER-001)"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        merged_config = get_agent_runtime_config("competency", config)
        super().__init__("CompetencyAgent", merged_config)
        self.agent_model_config = merged_config
        self.analyzer = CompetencyAnalyzer()
        self.security_tool = SecurityTool()
        self.scaler = StandardScaler()
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)

    async def execute(
        self, state: CompetencyDiagnosisState
    ) -> CompetencyDiagnosisState:
        """역량진단 메인 실행 로직"""
        try:
            state = await self.pre_execute(state)

            # 1. 데이터 전처리 및 보안 검증
            state = await self._preprocess_data(state)

            # 2. 역량 분석 실행
            state = await self._analyze_competency(state)

            # 3. 개인별 맞춤형 추천 생성
            state = await self._generate_recommendations(state)

            # 4. 결과 후처리 및 보안 적용
            state = await self._postprocess_results(state)

            state = await self.post_execute(state)

        except Exception as e:
            self.logger.error(f"Competency diagnosis failed: {e}")
            state.add_error(f"역량진단 실행 오류: {str(e)}")

        return state

    async def _preprocess_data(
        self, state: CompetencyDiagnosisState
    ) -> CompetencyDiagnosisState:
        """데이터 전처리 및 보안 검증"""
        try:
            # 모델 인스턴스 정규화: dict 등으로 들어온 경우 Pydantic 모델로 변환
            normalized_responses: List[UserResponse] = []
            for r in state.responses:
                if isinstance(r, UserResponse):
                    normalized_responses.append(r)
                elif isinstance(r, dict):
                    try:
                        normalized_responses.append(UserResponse.model_validate(r))
                    except Exception:
                        # 최소 필드 보정 후 시도
                        rid = r.get("response_id") or r.get("id") or ""
                        qid = r.get("question_id") or ""
                        uid = r.get("user_id") or ""
                        ans = r.get("answer") or ""
                        normalized_responses.append(
                            UserResponse.model_validate(
                                {
                                    "id": rid or qid or uid or "resp",
                                    "response_id": rid or qid or uid or "resp",
                                    "question_id": qid,
                                    "user_id": uid,
                                    "answer": ans,
                                    "response_value": r.get("response_value"),
                                    "response_time": r.get("response_time"),
                                    "confidence_score": r.get("confidence_score", 0.5),
                                }
                            )
                        )
                else:
                    # 알 수 없는 타입은 스킵
                    continue

            # 개인정보 익명화 처리
            anonymized_data = await self.security_tool.anonymize_personal_data(
                normalized_responses
            )

            # 데이터 검증 및 정제
            validated_responses = []
            for response in anonymized_data:
                if await self._validate_response(response):
                    validated_responses.append(response)
                else:
                    self.logger.warning(f"Invalid response filtered: {response.id}")

            state.responses = validated_responses
            state.context["preprocessing_completed"] = True

            self.logger.info(f"Preprocessed {len(validated_responses)} valid responses")

        except Exception as e:
            self.logger.error(f"Data preprocessing failed: {e}")
            state.add_error("데이터 전처리 실패")

        return state

    async def _analyze_competency(
        self, state: CompetencyDiagnosisState
    ) -> CompetencyDiagnosisState:
        """역량 분석 실행"""
        try:
            if not state.responses:
                state.add_error("분석할 응답 데이터가 없습니다")
                return state

            # 질문 리스트도 모델 인스턴스로 정규화
            normalized_questions: List[CompetencyQuestion] = []
            for q in state.questions:
                if isinstance(q, CompetencyQuestion):
                    normalized_questions.append(q)
                elif isinstance(q, dict):
                    try:
                        normalized_questions.append(
                            CompetencyQuestion.model_validate(q)
                        )
                    except Exception:
                        # 필수 필드 최소 보정
                        qid = q.get("question_id") or q.get("id") or ""
                        normalized_questions.append(
                            CompetencyQuestion.model_validate(
                                {
                                    "id": qid or "q",
                                    "question_id": qid or "q",
                                    "question_text": q.get("question_text")
                                    or q.get("text")
                                    or "",
                                    "domain": q.get("domain") or "education",
                                    "competency_area": q.get("competency_area")
                                    or "general",
                                }
                            )
                        )
                else:
                    continue
            state.questions = normalized_questions

            # 응답 데이터를 DataFrame으로 변환
            df = pd.DataFrame(
                [
                    {
                        "question_id": r.question_id,
                        "response_value": r.response_value,
                        "response_time": r.response_time,
                        "confidence_score": getattr(r, "confidence_score", 0.5),
                    }
                    for r in state.responses
                ]
            )

            # NaN 값 처리
            df = df.fillna(
                {"response_value": 0, "response_time": 0, "confidence_score": 0.5}
            )

            # 역량 영역별 분석
            competency_scores = await self._calculate_competency_scores(
                df, state.questions
            )

            # 강점/약점 분석
            strengths, weaknesses = await self._identify_strengths_weaknesses(
                competency_scores
            )

            # 학습 패턴 분석
            learning_patterns = await self._analyze_learning_patterns(df)

            # 분석 결과 종합
            state.analysis_result = {
                "competency_scores": competency_scores,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "learning_patterns": learning_patterns,
                "overall_level": await self._calculate_overall_level(competency_scores),
                "analysis_timestamp": datetime.now().isoformat(),
            }

            self.logger.info("Competency analysis completed successfully")

        except Exception as e:
            self.logger.error(f"Competency analysis failed: {e}")
            state.add_error("역량 분석 실행 실패")

        return state

    async def _generate_recommendations(
        self, state: CompetencyDiagnosisState
    ) -> CompetencyDiagnosisState:
        """개인별 맞춤형 추천 생성"""
        try:
            if not state.analysis_result:
                state.add_error("분석 결과가 없어 추천을 생성할 수 없습니다")
                return state

            analysis = state.analysis_result

            # 약점 기반 학습 추천
            weakness_recommendations = await self._generate_weakness_recommendations(
                analysis["weaknesses"]
            )

            # 강점 확장 추천
            strength_recommendations = await self._generate_strength_recommendations(
                analysis["strengths"]
            )

            # 학습 패턴 기반 추천
            pattern_recommendations = await self._generate_pattern_recommendations(
                analysis["learning_patterns"]
            )

            # 추천 우선순위 결정
            prioritized_recommendations = await self._prioritize_recommendations(
                [
                    *weakness_recommendations,
                    *strength_recommendations,
                    *pattern_recommendations,
                ]
            )

            state.recommendations = prioritized_recommendations

            self.logger.info(
                f"Generated {len(prioritized_recommendations)} recommendations"
            )

        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {e}")
            state.add_error("추천 생성 실패")

        return state

    async def _postprocess_results(
        self, state: CompetencyDiagnosisState
    ) -> CompetencyDiagnosisState:
        """결과 후처리 및 보안 적용"""
        try:
            # 결과 데이터 암호화
            if state.analysis_result:
                encrypted_result = await self.security_tool.encrypt_sensitive_data(
                    state.analysis_result
                )
                state.context["encrypted_analysis"] = encrypted_result

            # 접근 권한 설정
            state.context["access_level"] = await self._determine_access_level(state)

            # 데이터 보존 정책 적용
            state.context["retention_policy"] = {
                "retention_days": 365,
                "anonymization_required": True,
                "deletion_date": (
                    datetime.now().replace(year=datetime.now().year + 1)
                ).isoformat(),
            }

            self.logger.info("Results postprocessing completed")

        except Exception as e:
            self.logger.error(f"Results postprocessing failed: {e}")
            state.add_error("결과 후처리 실패")

        return state

    async def _validate_response(self, response: UserResponse) -> bool:
        """응답 데이터 유효성 검증"""
        if not response.question_id or response.response_value is None:
            return False

        if response.response_time and response.response_time < 0:
            return False

        return True

    async def _calculate_competency_scores(
        self, df: pd.DataFrame, questions: List[CompetencyQuestion]
    ) -> Dict[str, float]:
        """역량 영역별 점수 계산"""
        competency_scores = {}

        # 질문별 역량 영역 매핑
        question_mapping = {q.id: q.competency_area for q in questions}

        # 영역별 점수 집계
        for area in set(question_mapping.values()):
            area_questions = [
                qid for qid, area_name in question_mapping.items() if area_name == area
            ]
            area_responses = df[df["question_id"].isin(area_questions)]

            if not area_responses.empty:
                # 가중 평균 계산 (신뢰도 고려)
                weights = area_responses["confidence_score"]
                # weights의 합이 0인 경우 처리 (ZeroDivisionError 방지)
                if weights.sum() > 0:
                    if ML_AVAILABLE and np is not None:
                        weighted_score = np.average(
                            area_responses["response_value"], weights=weights
                        )
                    else:
                        # numpy 없을 때 fallback
                        values = area_responses["response_value"].tolist()
                        weights_list = weights.tolist()
                        weighted_score = sum(
                            v * w for v, w in zip(values, weights_list)
                        ) / sum(weights_list)
                else:
                    # weights가 모두 0이면 단순 평균 사용
                    weighted_score = area_responses["response_value"].mean()
                competency_scores[area] = float(weighted_score)

        return competency_scores

    async def _identify_strengths_weaknesses(
        self, competency_scores: Dict[str, float]
    ) -> Tuple[List[str], List[str]]:
        """강점/약점 영역 식별"""
        if not competency_scores:
            return [], []

        scores = list(competency_scores.values())
        if ML_AVAILABLE and np is not None:
            threshold_high = np.percentile(scores, 75)
            threshold_low = np.percentile(scores, 25)
        else:
            # numpy 없을 때 fallback
            sorted_scores = sorted(scores)
            n = len(sorted_scores)
            threshold_high = sorted_scores[int(n * 0.75)] if n > 0 else 0
            threshold_low = sorted_scores[int(n * 0.25)] if n > 0 else 0

        strengths = [
            area for area, score in competency_scores.items() if score >= threshold_high
        ]
        weaknesses = [
            area for area, score in competency_scores.items() if score <= threshold_low
        ]

        return strengths, weaknesses

    async def _analyze_learning_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """학습 패턴 분석"""
        patterns = {}

        if "response_time" in df.columns:
            patterns["avg_response_time"] = df["response_time"].mean()
            patterns["response_time_std"] = df["response_time"].std()

        if "confidence_score" in df.columns:
            patterns["avg_confidence"] = df["confidence_score"].mean()
            patterns["confidence_consistency"] = 1 - df["confidence_score"].std()

        patterns["response_pattern"] = (
            "consistent"
            if patterns.get("confidence_consistency", 0) > 0.8
            else "variable"
        )

        return patterns

    async def _calculate_overall_level(
        self, competency_scores: Dict[str, float]
    ) -> str:
        """전체 역량 수준 계산"""
        if not competency_scores:
            return "미평가"

        if ML_AVAILABLE and np is not None:
            avg_score = float(np.mean(list(competency_scores.values())))
        else:
            # numpy 없을 때 fallback
            values = list(competency_scores.values())
            avg_score = sum(values) / len(values) if values else 0.0

        # Epsilon 기반 비교 (부동소수점 정밀도 문제 해결)
        EPSILON = 1e-9
        if avg_score >= (0.8 - EPSILON):
            return "고급"
        elif avg_score >= (0.6 - EPSILON):
            return "중급"
        elif avg_score >= (0.4 - EPSILON):
            return "초급"
        else:
            return "기초"

    async def _generate_weakness_recommendations(
        self, weaknesses: List[str]
    ) -> List[Dict[str, Any]]:
        """약점 기반 추천 생성"""
        recommendations = []

        for weakness in weaknesses:
            recommendations.append(
                {
                    "type": "weakness_improvement",
                    "competency_area": weakness,
                    "priority": "high",
                    "recommendation": f"{weakness} 영역 집중 학습 필요",
                    "suggested_actions": [
                        f"{weakness} 기초 과정 수강",
                        f"{weakness} 실습 프로젝트 참여",
                        f"{weakness} 관련 멘토링 신청",
                    ],
                }
            )

        return recommendations

    async def _generate_strength_recommendations(
        self, strengths: List[str]
    ) -> List[Dict[str, Any]]:
        """강점 확장 추천 생성"""
        recommendations = []

        for strength in strengths:
            recommendations.append(
                {
                    "type": "strength_expansion",
                    "competency_area": strength,
                    "priority": "medium",
                    "recommendation": f"{strength} 영역 고급 학습 추천",
                    "suggested_actions": [
                        f"{strength} 고급 과정 도전",
                        f"{strength} 관련 프로젝트 리딩",
                        f"{strength} 영역 지식 공유 활동",
                    ],
                }
            )

        return recommendations

    async def _generate_pattern_recommendations(
        self, patterns: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """학습 패턴 기반 추천 생성"""
        recommendations = []

        if patterns.get("response_pattern") == "variable":
            recommendations.append(
                {
                    "type": "learning_pattern",
                    "priority": "medium",
                    "recommendation": "학습 일관성 향상 필요",
                    "suggested_actions": [
                        "정기적인 복습 계획 수립",
                        "학습 진도 체크리스트 활용",
                        "자기주도 학습 전략 개발",
                    ],
                }
            )

        return recommendations

    async def _prioritize_recommendations(
        self, recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """추천 우선순위 결정"""
        priority_order = {"high": 1, "medium": 2, "low": 3}

        return sorted(
            recommendations,
            key=lambda x: priority_order.get(x.get("priority", "low"), 3),
        )

    async def _determine_access_level(self, state: CompetencyDiagnosisState) -> str:
        """접근 권한 수준 결정"""
        if state.security_level == "high":
            return "restricted"
        elif state.user_id and state.session_id:
            return "authorized"
        else:
            return "anonymous"
