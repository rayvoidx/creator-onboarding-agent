"""
A/B 테스팅 프레임워크 - 프롬프트 버전 관리 및 실험 추적
"""

import hashlib
import logging
import random
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ExperimentStatus(str, Enum):
    """실험 상태"""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class VariantType(str, Enum):
    """변형 타입"""

    CONTROL = "control"
    TREATMENT = "treatment"


class PromptVariant(BaseModel):
    """프롬프트 변형"""

    id: str
    name: str
    type: VariantType
    content: str
    weight: float = 0.5  # 트래픽 비율 (0.0 ~ 1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Experiment(BaseModel):
    """A/B 테스트 실험"""

    id: str
    name: str
    description: str
    status: ExperimentStatus = ExperimentStatus.DRAFT

    # 변형 목록
    variants: List[PromptVariant] = Field(default_factory=list)

    # 타겟팅
    target_prompt_type: str  # competency, recommendation, analytics 등
    user_percentage: float = 100.0  # 실험 대상 사용자 비율

    # 기간
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # 메트릭
    primary_metric: str = "response_quality"  # 주요 측정 지표
    secondary_metrics: List[str] = Field(default_factory=list)

    # 메타데이터
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


class ExperimentResult(BaseModel):
    """실험 결과"""

    experiment_id: str
    variant_id: str
    user_id: str
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # 응답 데이터
    prompt_used: str
    response_time_ms: float
    token_count: int = 0

    # 품질 메트릭
    quality_score: Optional[float] = None
    user_feedback: Optional[int] = None  # 1-5 점수
    success: bool = True

    # 추가 메트릭
    metrics: Dict[str, Any] = Field(default_factory=dict)


class ABTestingService:
    """A/B 테스팅 서비스"""

    def __init__(self):
        self._experiments: Dict[str, Experiment] = {}
        self._results: List[ExperimentResult] = []
        self._user_assignments: Dict[str, Dict[str, str]] = (
            {}
        )  # user_id -> {exp_id: variant_id}

        # 설정에서 A/B 테스트 활성화 여부 확인
        self.enabled = settings.PROMPT_AB_TEST_ENABLED

    def create_experiment(
        self,
        name: str,
        description: str,
        target_prompt_type: str,
        variants: List[Dict[str, Any]],
        user_percentage: float = 100.0,
        primary_metric: str = "response_quality",
        created_by: Optional[str] = None,
    ) -> Experiment:
        """새 실험 생성"""
        experiment_id = str(uuid.uuid4())

        # 변형 생성
        variant_objects = []
        for i, v in enumerate(variants):
            variant = PromptVariant(
                id=str(uuid.uuid4()),
                name=v.get("name", f"Variant {i+1}"),
                type=VariantType(v.get("type", "treatment" if i > 0 else "control")),
                content=v.get("content", ""),
                weight=v.get("weight", 1.0 / len(variants)),
                metadata=v.get("metadata", {}),
            )
            variant_objects.append(variant)

        # 가중치 정규화
        total_weight = sum(v.weight for v in variant_objects)
        if total_weight > 0:
            for v in variant_objects:
                v.weight = v.weight / total_weight

        experiment = Experiment(
            id=experiment_id,
            name=name,
            description=description,
            target_prompt_type=target_prompt_type,
            variants=variant_objects,
            user_percentage=user_percentage,
            primary_metric=primary_metric,
            created_by=created_by,
        )

        self._experiments[experiment_id] = experiment
        logger.info(f"Experiment created: {experiment_id} ({name})")

        return experiment

    def start_experiment(self, experiment_id: str) -> bool:
        """실험 시작"""
        if experiment_id not in self._experiments:
            return False

        experiment = self._experiments[experiment_id]
        experiment.status = ExperimentStatus.RUNNING
        experiment.start_date = datetime.utcnow()
        experiment.updated_at = datetime.utcnow()

        logger.info(f"Experiment started: {experiment_id}")
        return True

    def stop_experiment(self, experiment_id: str) -> bool:
        """실험 중지"""
        if experiment_id not in self._experiments:
            return False

        experiment = self._experiments[experiment_id]
        experiment.status = ExperimentStatus.COMPLETED
        experiment.end_date = datetime.utcnow()
        experiment.updated_at = datetime.utcnow()

        logger.info(f"Experiment stopped: {experiment_id}")
        return True

    def get_variant_for_user(
        self, user_id: str, prompt_type: str
    ) -> Optional[PromptVariant]:
        """
        사용자에게 할당할 변형 결정

        Args:
            user_id: 사용자 ID
            prompt_type: 프롬프트 타입

        Returns:
            할당된 변형 (또는 None)
        """
        if not self.enabled:
            return None

        # 해당 프롬프트 타입의 실행 중인 실험 찾기
        active_experiments = [
            exp
            for exp in self._experiments.values()
            if exp.status == ExperimentStatus.RUNNING
            and exp.target_prompt_type == prompt_type
        ]

        if not active_experiments:
            return None

        # 첫 번째 활성 실험 사용 (여러 실험이 있을 경우 확장 가능)
        experiment = active_experiments[0]

        # 사용자가 실험 대상인지 확인
        if not self._is_user_in_experiment(user_id, experiment):
            return None

        # 기존 할당 확인
        if user_id in self._user_assignments:
            if experiment.id in self._user_assignments[user_id]:
                variant_id = self._user_assignments[user_id][experiment.id]
                for v in experiment.variants:
                    if v.id == variant_id:
                        return v

        # 새 할당
        variant = self._assign_variant(user_id, experiment)

        # 할당 저장
        if user_id not in self._user_assignments:
            self._user_assignments[user_id] = {}
        self._user_assignments[user_id][experiment.id] = variant.id

        return variant

    def _is_user_in_experiment(self, user_id: str, experiment: Experiment) -> bool:
        """사용자가 실험 대상인지 확인"""
        # 사용자 ID를 해시하여 일관된 결정
        hash_value = int(
            hashlib.md5(f"{user_id}:{experiment.id}".encode()).hexdigest(), 16
        )
        percentage = (hash_value % 10000) / 100.0

        return percentage < experiment.user_percentage

    def _assign_variant(self, user_id: str, experiment: Experiment) -> PromptVariant:
        """변형 할당"""
        # 사용자 ID 기반 일관된 할당
        hash_value = int(
            hashlib.md5(f"{user_id}:{experiment.id}:variant".encode()).hexdigest(), 16
        )
        random_value = (hash_value % 10000) / 10000.0

        cumulative = 0.0
        for variant in experiment.variants:
            cumulative += variant.weight
            if random_value < cumulative:
                return variant

        # 기본값: 마지막 변형
        return experiment.variants[-1]

    def record_result(
        self,
        experiment_id: str,
        variant_id: str,
        user_id: str,
        prompt_used: str,
        response_time_ms: float,
        success: bool = True,
        quality_score: Optional[float] = None,
        user_feedback: Optional[int] = None,
        token_count: int = 0,
        session_id: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> ExperimentResult:
        """실험 결과 기록"""
        result = ExperimentResult(
            experiment_id=experiment_id,
            variant_id=variant_id,
            user_id=user_id,
            session_id=session_id,
            prompt_used=prompt_used,
            response_time_ms=response_time_ms,
            token_count=token_count,
            quality_score=quality_score,
            user_feedback=user_feedback,
            success=success,
            metrics=metrics or {},
        )

        self._results.append(result)

        return result

    def get_experiment_stats(self, experiment_id: str) -> Dict[str, Any]:
        """실험 통계 조회"""
        if experiment_id not in self._experiments:
            return {"error": "Experiment not found"}

        experiment = self._experiments[experiment_id]
        results = [r for r in self._results if r.experiment_id == experiment_id]

        # 변형별 통계
        variant_stats = {}
        for variant in experiment.variants:
            variant_results = [r for r in results if r.variant_id == variant.id]

            if not variant_results:
                variant_stats[variant.id] = {
                    "name": variant.name,
                    "type": variant.type.value,
                    "sample_size": 0,
                    "metrics": {},
                }
                continue

            # 메트릭 계산
            success_rate = sum(1 for r in variant_results if r.success) / len(
                variant_results
            )
            avg_response_time = sum(r.response_time_ms for r in variant_results) / len(
                variant_results
            )

            quality_scores = [
                r.quality_score for r in variant_results if r.quality_score is not None
            ]
            avg_quality = (
                sum(quality_scores) / len(quality_scores) if quality_scores else None
            )

            feedback_scores = [
                r.user_feedback for r in variant_results if r.user_feedback is not None
            ]
            avg_feedback = (
                sum(feedback_scores) / len(feedback_scores) if feedback_scores else None
            )

            variant_stats[variant.id] = {
                "name": variant.name,
                "type": variant.type.value,
                "sample_size": len(variant_results),
                "metrics": {
                    "success_rate": success_rate,
                    "avg_response_time_ms": avg_response_time,
                    "avg_quality_score": avg_quality,
                    "avg_user_feedback": avg_feedback,
                    "total_tokens": sum(r.token_count for r in variant_results),
                },
            }

        # 통계적 유의성 계산 (간단한 버전)
        winner = None
        if len(variant_stats) >= 2:
            sorted_variants = sorted(
                variant_stats.items(),
                key=lambda x: x[1]["metrics"].get("avg_quality_score") or 0,
                reverse=True,
            )
            if sorted_variants[0][1]["sample_size"] >= 30:  # 최소 샘플 크기
                winner = sorted_variants[0][1]["name"]

        return {
            "experiment_id": experiment_id,
            "experiment_name": experiment.name,
            "status": experiment.status.value,
            "total_samples": len(results),
            "variant_stats": variant_stats,
            "winner": winner,
            "is_significant": winner is not None,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """실험 조회"""
        return self._experiments.get(experiment_id)

    def list_experiments(
        self, status: Optional[ExperimentStatus] = None
    ) -> List[Experiment]:
        """실험 목록 조회"""
        experiments = list(self._experiments.values())

        if status:
            experiments = [e for e in experiments if e.status == status]

        return sorted(experiments, key=lambda x: x.created_at, reverse=True)

    def get_prompt_with_experiment(
        self, user_id: str, prompt_type: str, default_prompt: str
    ) -> tuple[str, Optional[str], Optional[str]]:
        """
        실험이 적용된 프롬프트 반환

        Returns:
            (prompt, experiment_id, variant_id)
        """
        variant = self.get_variant_for_user(user_id, prompt_type)

        if variant:
            # 활성 실험의 변형 프롬프트 사용
            experiment = next(
                (
                    e
                    for e in self._experiments.values()
                    if e.status == ExperimentStatus.RUNNING
                    and any(v.id == variant.id for v in e.variants)
                ),
                None,
            )
            if experiment:
                return variant.content, experiment.id, variant.id

        return default_prompt, None, None


# 싱글톤 인스턴스
_ab_testing_service: Optional[ABTestingService] = None


def get_ab_testing_service() -> ABTestingService:
    """A/B 테스팅 서비스 인스턴스 반환"""
    global _ab_testing_service
    if _ab_testing_service is None:
        _ab_testing_service = ABTestingService()
    return _ab_testing_service
