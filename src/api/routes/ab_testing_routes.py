"""
A/B 테스팅 API 라우터
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.services.ab_testing_service import (
    get_ab_testing_service,
    ExperimentStatus,
)
from src.api.middleware.auth import require_permission
from src.data.models.user_models import TokenData, Permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/experiments", tags=["A/B Testing"])


class VariantCreate(BaseModel):
    """변형 생성 요청"""
    name: str
    type: str = "treatment"  # control 또는 treatment
    content: str
    weight: float = 0.5
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExperimentCreate(BaseModel):
    """실험 생성 요청"""
    name: str
    description: str
    target_prompt_type: str
    variants: List[VariantCreate]
    user_percentage: float = 100.0
    primary_metric: str = "response_quality"
    secondary_metrics: List[str] = Field(default_factory=list)


class ResultRecord(BaseModel):
    """결과 기록 요청"""
    experiment_id: str
    variant_id: str
    user_id: str
    prompt_used: str
    response_time_ms: float
    success: bool = True
    quality_score: Optional[float] = None
    user_feedback: Optional[int] = None
    token_count: int = 0
    session_id: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


@router.post("/create")
async def create_experiment(
    request: ExperimentCreate,
    current_user: TokenData = Depends(require_permission(Permission.SYSTEM_ADMIN))
) -> Dict[str, Any]:
    """새 A/B 테스트 실험 생성"""
    ab_service = get_ab_testing_service()

    # 변형 데이터 변환
    variants = [v.model_dump() for v in request.variants]

    experiment = ab_service.create_experiment(
        name=request.name,
        description=request.description,
        target_prompt_type=request.target_prompt_type,
        variants=variants,
        user_percentage=request.user_percentage,
        primary_metric=request.primary_metric,
        created_by=current_user.user_id
    )

    return {
        "success": True,
        "experiment_id": experiment.id,
        "name": experiment.name,
        "status": experiment.status.value,
        "variants": [
            {"id": v.id, "name": v.name, "type": v.type.value, "weight": v.weight}
            for v in experiment.variants
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/{experiment_id}/start")
async def start_experiment(
    experiment_id: str,
    current_user: TokenData = Depends(require_permission(Permission.SYSTEM_ADMIN))
) -> Dict[str, Any]:
    """실험 시작"""
    ab_service = get_ab_testing_service()

    success = ab_service.start_experiment(experiment_id)

    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return {
        "success": True,
        "message": f"Experiment {experiment_id} started",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/{experiment_id}/stop")
async def stop_experiment(
    experiment_id: str,
    current_user: TokenData = Depends(require_permission(Permission.SYSTEM_ADMIN))
) -> Dict[str, Any]:
    """실험 중지"""
    ab_service = get_ab_testing_service()

    success = ab_service.stop_experiment(experiment_id)

    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return {
        "success": True,
        "message": f"Experiment {experiment_id} stopped",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    current_user: TokenData = Depends(require_permission(Permission.ANALYTICS_READ))
) -> Dict[str, Any]:
    """실험 정보 조회"""
    ab_service = get_ab_testing_service()

    experiment = ab_service.get_experiment(experiment_id)

    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return {
        "success": True,
        "experiment": experiment.model_dump(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/{experiment_id}/stats")
async def get_experiment_stats(
    experiment_id: str,
    current_user: TokenData = Depends(require_permission(Permission.ANALYTICS_READ))
) -> Dict[str, Any]:
    """실험 통계 조회"""
    ab_service = get_ab_testing_service()

    stats = ab_service.get_experiment_stats(experiment_id)

    if "error" in stats:
        raise HTTPException(status_code=404, detail=stats["error"])

    return {
        "success": True,
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/")
async def list_experiments(
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: TokenData = Depends(require_permission(Permission.ANALYTICS_READ))
) -> Dict[str, Any]:
    """실험 목록 조회"""
    ab_service = get_ab_testing_service()

    status_filter = None
    if status:
        try:
            status_filter = ExperimentStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    experiments = ab_service.list_experiments(status_filter)

    return {
        "success": True,
        "experiments": [
            {
                "id": e.id,
                "name": e.name,
                "status": e.status.value,
                "target_prompt_type": e.target_prompt_type,
                "created_at": e.created_at.isoformat(),
                "variants_count": len(e.variants)
            }
            for e in experiments
        ],
        "total": len(experiments),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/record-result")
async def record_experiment_result(
    request: ResultRecord,
    current_user: TokenData = Depends(require_permission(Permission.ANALYTICS_READ))
) -> Dict[str, Any]:
    """실험 결과 기록"""
    ab_service = get_ab_testing_service()

    result = ab_service.record_result(
        experiment_id=request.experiment_id,
        variant_id=request.variant_id,
        user_id=request.user_id,
        prompt_used=request.prompt_used,
        response_time_ms=request.response_time_ms,
        success=request.success,
        quality_score=request.quality_score,
        user_feedback=request.user_feedback,
        token_count=request.token_count,
        session_id=request.session_id,
        metrics=request.metrics
    )

    return {
        "success": True,
        "recorded": True,
        "timestamp": result.timestamp.isoformat()
    }


@router.get("/variant/{prompt_type}")
async def get_variant_for_prompt(
    prompt_type: str,
    user_id: str = Query(..., description="User ID for variant assignment"),
    current_user: TokenData = Depends(require_permission(Permission.ANALYTICS_READ))
) -> Dict[str, Any]:
    """특정 프롬프트 타입에 대한 사용자 변형 조회"""
    ab_service = get_ab_testing_service()

    variant = ab_service.get_variant_for_user(user_id, prompt_type)

    if not variant:
        return {
            "success": True,
            "variant": None,
            "message": "No active experiment for this prompt type",
            "timestamp": datetime.utcnow().isoformat()
        }

    return {
        "success": True,
        "variant": {
            "id": variant.id,
            "name": variant.name,
            "type": variant.type.value,
            "content": variant.content
        },
        "timestamp": datetime.utcnow().isoformat()
    }
