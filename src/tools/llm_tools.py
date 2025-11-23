"""LLM 도구"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ModelPerformance:
    """모델 성능 데이터"""
    model_name: str
    response_time: float
    success_rate: float
    cost: float
    timestamp: datetime
    request_count: int = 1


class ModelPerformanceMonitor:
    """모델 성능 모니터"""

    def __init__(self):
        self.performance_history: List[ModelPerformance] = []
        self.model_stats: Dict[str, Dict[str, Any]] = {}

    async def record_performance(self, performance: Any) -> None:
        """성능 기록"""
        try:
            if isinstance(performance, dict):
                perf = ModelPerformance(
                    model_name=performance.get('model_name', 'unknown'),
                    response_time=performance.get('response_time', 0.0),
                    success_rate=performance.get('success_rate', 1.0),
                    cost=performance.get('cost', 0.0),
                    timestamp=datetime.now()
                )
                
                self.performance_history.append(perf)
                
                # 모델별 통계 업데이트
                model_name = perf.model_name
                if model_name not in self.model_stats:
                    self.model_stats[model_name] = {
                        'total_requests': 0,
                        'total_response_time': 0.0,
                        'total_cost': 0.0,
                        'success_count': 0,
                        'last_used': None
                    }
                
                stats = self.model_stats[model_name]
                stats['total_requests'] += 1
                stats['total_response_time'] += perf.response_time
                stats['total_cost'] += perf.cost
                if perf.success_rate > 0.5:
                    stats['success_count'] += 1
                stats['last_used'] = perf.timestamp
                
                logger.info(f"Recorded performance for {model_name}: {perf.response_time:.2f}s")
                
        except Exception as e:
            logger.error(f"Failed to record performance: {e}")

    def get_model_stats(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """모델 통계 조회"""
        if model_name:
            return self.model_stats.get(model_name, {})
        return self.model_stats

    def get_best_performing_model(self, criteria: str = "response_time") -> str:
        """최고 성능 모델 조회"""
        if not self.model_stats:
            return "gpt-5.1"  # 기본값
        
        best_model = None
        best_score = float('inf') if criteria == "response_time" else 0.0
        
        for model_name, stats in self.model_stats.items():
            if stats['total_requests'] == 0:
                continue
                
            if criteria == "response_time":
                avg_time = stats['total_response_time'] / stats['total_requests']
                if avg_time < best_score:
                    best_score = avg_time
                    best_model = model_name
            elif criteria == "success_rate":
                success_rate = stats['success_count'] / stats['total_requests']
                if success_rate > best_score:
                    best_score = success_rate
                    best_model = model_name
            elif criteria == "cost":
                avg_cost = stats['total_cost'] / stats['total_requests']
                if avg_cost < best_score:
                    best_score = avg_cost
                    best_model = model_name
        
        return best_model or "gpt-5.1"


class ModelSelector:
    """모델 선택기"""

    def __init__(self, monitor: Optional[ModelPerformanceMonitor] = None):
        self.monitor = monitor or ModelPerformanceMonitor()
        self.available_models = [
            "gpt-5.1",
            "gpt-5.1-mini",
            "claude-sonnet-4-5-20250929"
        ]
        self.model_capabilities = {
            "gpt-5.1": {"max_tokens": 128000, "cost_per_1k": 0.03, "speed": "medium"},
            "gpt-5.1-mini": {"max_tokens": 128000, "cost_per_1k": 0.0015, "speed": "fast"},
            "claude-sonnet-4-5-20250929": {"max_tokens": 200000, "cost_per_1k": 0.015, "speed": "medium"}
        }

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """간단한 토큰 수 추정기 (대략 4문자=1토큰)"""
        try:
            length = len(text or "")
            return max(1, length // 4)
        except Exception:
            return 1

    async def select_model(self, criteria: Dict[str, Any]) -> str:  # type: ignore
        """모델 선택"""
        try:
            # 우선순위 기준
            priority = criteria.get('priority', 'balanced')
            max_tokens = criteria.get('max_tokens', 1000)
            
            # 토큰 제한 필터링
            suitable_models = [
                model for model in self.available_models
                if self.model_capabilities[model]['max_tokens'] >= max_tokens
            ]
            
            if not suitable_models:
                return "gpt-5.1-mini"  # 폴백
            
            # 우선순위에 따른 선택
            if priority == "performance":
                # 성능 기반 선택
                best_model = self.monitor.get_best_performing_model("success_rate")
                if best_model in suitable_models:
                    return best_model
            elif priority == "speed":
                # 속도 기반 선택
                fast_models = [
                    model for model in suitable_models
                    if self.model_capabilities[model]['speed'] == 'fast'
                ]
                if fast_models:
                    return fast_models[0]
            elif priority == "cost":
                # 비용 기반 선택
                def get_cost(model: str) -> float:  # type: ignore
                    cost = self.model_capabilities[model]['cost_per_1k']
                    try:
                        return float(cost)  # type: ignore[arg-type,assignment,return-value,misc,unused-ignore,no-redef]
                    except (ValueError, TypeError):
                        return 0.0
                
                cost_sorted = sorted(suitable_models, key=get_cost)
                return cost_sorted[0]
            
            # 기본 선택: gpt-5.1-mini (균형잡힌 선택)
            if "gpt-5.1-mini" in suitable_models:
                return "gpt-5.1-mini"
            elif "gpt-5.1" in suitable_models:
                return "gpt-5.1"
            else:
                return suitable_models[0]
                
        except Exception as e:
            logger.error(f"Model selection failed: {e}")
            return "gpt-5.1-mini"  # 안전한 폴백

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """모델 정보 조회"""
        return self.model_capabilities.get(model_name, {})

    def is_model_available(self, model_name: str) -> bool:
        """모델 사용 가능 여부"""
        return model_name in self.available_models

    async def get_recommended_model(self, use_case: str) -> str:
        """사용 사례별 추천 모델"""
        recommendations = {
            "chat": "gpt-5.1",
            "analysis": "gpt-5.1",
            "creative": "claude-sonnet-4-5-20250929",
            "fast_response": "gpt-5.1-mini",
            "long_context": "claude-sonnet-4-5-20250929"
        }

        return recommendations.get(use_case, "gpt-5.1-mini")