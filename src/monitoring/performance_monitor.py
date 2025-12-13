"""성능 모니터링"""

import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """성능 메트릭"""

    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.end_time is not None:
            self.duration = self.end_time - self.start_time


class PerformanceMonitor:
    """성능 모니터링"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("PerformanceMonitor")

        # 메트릭 저장소
        self.metrics_history: deque = deque(maxlen=self.config.get("max_history", 1000))
        self.operation_stats: Dict[str, List[float]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)

        # 임계값 설정
        self.latency_threshold = self.config.get("latency_threshold", 5.0)  # 5초
        self.error_rate_threshold = self.config.get("error_rate_threshold", 0.1)  # 10%

        # 실시간 통계
        self.current_operations: Dict[str, PerformanceMetrics] = {}

        # 도메인 특화 메트릭 (creator onboarding / mission recommendation)
        self._creator_scores: List[float] = []
        self._creator_accepts: int = 0
        self._creator_total: int = 0
        self._mission_total_requests: int = 0
        self._mission_total_recommended: int = 0

    async def start_operation(
        self, operation_name: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """작업 시작"""
        try:
            operation_id = f"{operation_name}_{int(time.time() * 1000)}"

            metrics = PerformanceMetrics(
                operation_name=operation_name,
                start_time=time.time(),
                metadata=metadata or {},
            )

            self.current_operations[operation_id] = metrics

            self.logger.debug(
                f"Started operation: {operation_name} (ID: {operation_id})"
            )
            return operation_id

        except Exception as e:
            self.logger.error(f"Failed to start operation: {e}")
            return ""

    async def end_operation(
        self,
        operation_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[PerformanceMetrics]:
        """작업 종료"""
        try:
            if operation_id not in self.current_operations:
                self.logger.warning(f"Operation {operation_id} not found")
                return None

            metrics = self.current_operations.pop(operation_id)
            metrics.end_time = time.time()
            metrics.duration = metrics.end_time - metrics.start_time
            metrics.success = success
            metrics.error_message = error_message

            if metadata:
                metrics.metadata.update(metadata)

            # 메트릭 저장
            self.metrics_history.append(metrics)
            self.operation_stats[metrics.operation_name].append(metrics.duration)

            if not success:
                self.error_counts[metrics.operation_name] += 1

            # 임계값 확인
            await self._check_thresholds(metrics)

            self.logger.debug(
                f"Ended operation: {metrics.operation_name} (Duration: {metrics.duration:.3f}s)"
            )
            return metrics

        except Exception as e:
            self.logger.error(f"Failed to end operation: {e}")
            return None

    async def _check_thresholds(self, metrics: PerformanceMetrics):
        """임계값 확인"""
        try:
            # 지연시간 임계값 확인
            if metrics.duration and metrics.duration > self.latency_threshold:
                self.logger.warning(
                    f"High latency detected: {metrics.operation_name} "
                    f"took {metrics.duration:.3f}s (threshold: {self.latency_threshold}s)"
                )

            # 에러율 임계값 확인
            operation_name = metrics.operation_name
            total_operations = len(self.operation_stats[operation_name])
            error_count = self.error_counts[operation_name]

            if total_operations > 0:
                error_rate = error_count / total_operations
                if error_rate > self.error_rate_threshold:
                    self.logger.warning(
                        f"High error rate detected: {operation_name} "
                        f"error rate {error_rate:.2%} (threshold: {self.error_rate_threshold:.2%})"
                    )

        except Exception as e:
            self.logger.error(f"Failed to check thresholds: {e}")

    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """작업 통계 조회"""
        try:
            durations = self.operation_stats.get(operation_name, [])
            error_count = self.error_counts.get(operation_name, 0)
            total_count = len(durations)

            if not durations:
                return {
                    "operation_name": operation_name,
                    "total_count": 0,
                    "error_count": 0,
                    "error_rate": 0.0,
                    "avg_duration": 0.0,
                    "min_duration": 0.0,
                    "max_duration": 0.0,
                    "p95_duration": 0.0,
                }

            return {
                "operation_name": operation_name,
                "total_count": total_count,
                "error_count": error_count,
                "error_rate": error_count / total_count if total_count > 0 else 0.0,
                "avg_duration": statistics.mean(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "p95_duration": self._calculate_percentile(durations, 95),
                "p99_duration": self._calculate_percentile(durations, 99),
            }

        except Exception as e:
            self.logger.error(f"Failed to get operation stats: {e}")
            return {}

    def _calculate_percentile(self, data: List[float], percentile: int) -> float:
        """백분위수 계산"""
        try:
            if not data:
                return 0.0

            sorted_data = sorted(data)
            index = int((percentile / 100) * len(sorted_data))
            return sorted_data[min(index, len(sorted_data) - 1)]

        except Exception as e:
            self.logger.error(f"Failed to calculate percentile: {e}")
            return 0.0

    def get_overall_stats(self) -> Dict[str, Any]:
        """전체 통계 조회"""
        try:
            all_durations = []
            total_errors = 0
            total_operations = 0

            for operation_name in self.operation_stats:
                durations = self.operation_stats[operation_name]
                all_durations.extend(durations)
                total_operations += len(durations)
                total_errors += self.error_counts[operation_name]

            if not all_durations:
                return {
                    "total_operations": 0,
                    "total_errors": 0,
                    "overall_error_rate": 0.0,
                    "avg_duration": 0.0,
                    "min_duration": 0.0,
                    "max_duration": 0.0,
                    "p95_duration": 0.0,
                }

            return {
                "total_operations": total_operations,
                "total_errors": total_errors,
                "overall_error_rate": (
                    total_errors / total_operations if total_operations > 0 else 0.0
                ),
                "avg_duration": statistics.mean(all_durations),
                "min_duration": min(all_durations),
                "max_duration": max(all_durations),
                "p95_duration": self._calculate_percentile(all_durations, 95),
                "p99_duration": self._calculate_percentile(all_durations, 99),
                "operations": {
                    name: self.get_operation_stats(name)
                    for name in self.operation_stats.keys()
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to get overall stats: {e}")
            return {}

    def get_recent_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """최근 메트릭 조회"""
        try:
            recent_metrics = list(self.metrics_history)[-limit:]

            return [
                {
                    "operation_name": m.operation_name,
                    "duration": m.duration,
                    "success": m.success,
                    "error_message": m.error_message,
                    "metadata": m.metadata,
                    "timestamp": datetime.fromtimestamp(m.start_time).isoformat(),
                }
                for m in recent_metrics
            ]

        except Exception as e:
            self.logger.error(f"Failed to get recent metrics: {e}")
            return []

    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약"""
        try:
            overall_stats = self.get_overall_stats()
            recent_metrics = self.get_recent_metrics(50)

            # 현재 실행 중인 작업
            current_operations = len(self.current_operations)

            # 최근 1시간 통계
            one_hour_ago = time.time() - 3600
            recent_metrics_1h = [
                m for m in self.metrics_history if m.start_time >= one_hour_ago
            ]

            return {
                "overall_stats": overall_stats,
                "current_operations": current_operations,
                "recent_metrics": recent_metrics,
                "recent_1h_count": len(recent_metrics_1h),
                "thresholds": {
                    "latency_threshold": self.latency_threshold,
                    "error_rate_threshold": self.error_rate_threshold,
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get performance summary: {e}")
            return {}

    async def reset_stats(self) -> bool:
        """통계 초기화"""
        try:
            self.metrics_history.clear()
            self.operation_stats.clear()
            self.error_counts.clear()
            self.current_operations.clear()

            # 도메인 메트릭 초기화
            self._creator_scores.clear()
            self._creator_accepts = 0
            self._creator_total = 0
            self._mission_total_requests = 0
            self._mission_total_recommended = 0

            self.logger.info("Performance stats reset successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to reset stats: {e}")
            return False

    # ---- Domain-specific helpers -------------------------------------------------

    def record_creator_result(self, score: float, decision: str) -> None:
        """Creator 온보딩 결과를 도메인 메트릭에 반영."""
        try:
            self._creator_total += 1
            self._creator_scores.append(float(score))
            if str(decision).lower() == "accept":
                self._creator_accepts += 1
        except Exception as e:
            self.logger.error(f"Failed to record creator result: {e}")

    def record_mission_recommendation(self, recommended_count: int) -> None:
        """미션 추천 결과(추천 개수)를 도메인 메트릭에 반영."""
        try:
            self._mission_total_requests += 1
            if recommended_count > 0:
                self._mission_total_recommended += int(recommended_count)
        except Exception as e:
            self.logger.error(f"Failed to record mission recommendation: {e}")

    def get_domain_metrics(self) -> Dict[str, Any]:
        """Creator 온보딩 및 미션 추천 관련 도메인 메트릭 조회."""
        try:
            avg_score = (
                sum(self._creator_scores) / len(self._creator_scores)
                if self._creator_scores
                else 0.0
            )
            accept_rate = (
                self._creator_accepts / self._creator_total
                if self._creator_total > 0
                else 0.0
            )
            avg_missions_per_request = (
                self._mission_total_recommended / self._mission_total_requests
                if self._mission_total_requests > 0
                else 0.0
            )
            return {
                "creator_avg_score": avg_score,
                "creator_accept_rate": accept_rate,
                "creator_total": self._creator_total,
                "mission_avg_recommendations_per_request": avg_missions_per_request,
                "mission_total_requests": self._mission_total_requests,
            }
        except Exception as e:
            self.logger.error(f"Failed to get domain metrics: {e}")
            return {}
