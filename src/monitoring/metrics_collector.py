"""메트릭 수집기"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
try:
    import psutil  # type: ignore
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None  # type: ignore

logger = logging.getLogger(__name__)


class MetricsCollector:
    """시스템 메트릭 수집기"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("MetricsCollector")
        
        # 메트릭 저장소
        self.metrics_history: List[Dict[str, Any]] = []
        self.max_history = self.config.get('max_history', 1000)
        # Deep Agents 특화 지표 누적
        self.deep_retry_count: int = 0
        self.deep_no_progress_count: int = 0
        self.deep_critic_scores: List[float] = []
        
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """시스템 메트릭 수집"""
        try:
            if not PSUTIL_AVAILABLE:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'psutil_available': False,
                    'cpu': {'percent': 0, 'count': 0},
                    'memory': {'percent': 0, 'used_gb': 0, 'total_gb': 0},
                    'disk': {'percent': 0, 'used_gb': 0, 'total_gb': 0},
                    'network': {'bytes_sent': 0, 'bytes_recv': 0},
                    'process': {'cpu_percent': 0, 'memory_mb': 0}
                }
            
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used / (1024**3)  # GB
            memory_total = memory.total / (1024**3)  # GB
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_used = disk.used / (1024**3)  # GB
            disk_total = disk.total / (1024**3)  # GB
            
            # 네트워크 통계
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
            
            # 프로세스 정보
            process = psutil.Process()
            process_cpu = process.cpu_percent()
            process_memory = process.memory_info()
            process_memory_mb = process_memory.rss / (1024**2)  # MB
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count
                },
                'memory': {
                    'percent': memory_percent,
                    'used_gb': round(memory_used, 2),
                    'total_gb': round(memory_total, 2)
                },
                'disk': {
                    'percent': round(disk_percent, 2),
                    'used_gb': round(disk_used, 2),
                    'total_gb': round(disk_total, 2)
                },
                'network': {
                    'bytes_sent': network_bytes_sent,
                    'bytes_recv': network_bytes_recv
                },
                'process': {
                    'cpu_percent': process_cpu,
                    'memory_mb': round(process_memory_mb, 2)
                }
            }
            
            # 메트릭 히스토리에 추가
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history:
                self.metrics_history.pop(0)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            return {}
    
    async def collect_application_metrics(
        self,
        active_sessions: int = 0,
        total_requests: int = 0,
        error_count: int = 0,
        avg_response_time: float = 0.0
    ) -> Dict[str, Any]:
        """애플리케이션 메트릭 수집"""
        try:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'application': {
                    'active_sessions': active_sessions,
                    'total_requests': total_requests,
                    'error_count': error_count,
                    'error_rate': error_count / total_requests if total_requests > 0 else 0.0,
                    'avg_response_time': avg_response_time
                }
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect application metrics: {e}")
            return {}
    
    async def collect_langgraph_metrics(
        self,
        graph_executions: int = 0,
        agent_executions: Optional[Dict[str, int]] = None,
        avg_execution_time: float = 0.0,
        success_rate: float = 1.0,
        deep_retry_delta: int = 0,
        deep_no_progress_delta: int = 0,
        deep_critic_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """LangGraph 메트릭 수집"""
        try:
            agent_executions = agent_executions or {}
            # Deep Agents 지표 갱신
            self.deep_retry_count += max(0, deep_retry_delta)
            self.deep_no_progress_count += max(0, deep_no_progress_delta)
            if isinstance(deep_critic_score, (int, float)):
                self.deep_critic_scores.append(float(deep_critic_score))
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'langgraph': {
                    'graph_executions': graph_executions,
                    'agent_executions': agent_executions,
                    'avg_execution_time': avg_execution_time,
                    'success_rate': success_rate,
                    'total_agent_executions': sum(agent_executions.values()),
                    'deep_agents': {
                        'retry_count': self.deep_retry_count,
                        'no_progress_count': self.deep_no_progress_count,
                        'avg_critic_score': (
                            sum(self.deep_critic_scores)/len(self.deep_critic_scores)
                            if self.deep_critic_scores else 0.0
                        )
                    }
                }
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect LangGraph metrics: {e}")
            return {}
    
    async def collect_rag_metrics(
        self,
        queries_processed: int = 0,
        avg_retrieval_time: float = 0.0,
        avg_generation_time: float = 0.0,
        documents_retrieved: int = 0,
        retrieval_accuracy: float = 1.0
    ) -> Dict[str, Any]:
        """RAG 메트릭 수집"""
        try:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'rag': {
                    'queries_processed': queries_processed,
                    'avg_retrieval_time': avg_retrieval_time,
                    'avg_generation_time': avg_generation_time,
                    'documents_retrieved': documents_retrieved,
                    'retrieval_accuracy': retrieval_accuracy,
                    'total_processing_time': avg_retrieval_time + avg_generation_time
                }
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect RAG metrics: {e}")
            return {}
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """메트릭 요약"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # 최근 메트릭 필터링
            recent_metrics = [
                m for m in self.metrics_history
                if datetime.fromisoformat(m['timestamp']) >= cutoff_time
            ]
            
            if not recent_metrics:
                return {'message': 'No metrics available for the specified time period'}
            
            # CPU 평균
            cpu_values = [m.get('cpu', {}).get('percent', 0) for m in recent_metrics]
            avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
            
            # 메모리 평균
            memory_values = [m.get('memory', {}).get('percent', 0) for m in recent_metrics]
            avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0
            
            # 디스크 평균
            disk_values = [m.get('disk', {}).get('percent', 0) for m in recent_metrics]
            avg_disk = sum(disk_values) / len(disk_values) if disk_values else 0
            
            return {
                'time_period_hours': hours,
                'metrics_count': len(recent_metrics),
                'avg_cpu_percent': round(avg_cpu, 2),
                'avg_memory_percent': round(avg_memory, 2),
                'avg_disk_percent': round(avg_disk, 2),
                'latest_metrics': recent_metrics[-1] if recent_metrics else None,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics summary: {e}")
            return {}
    
    def get_metrics_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """메트릭 히스토리 조회"""
        try:
            return self.metrics_history[-limit:] if self.metrics_history else []
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics history: {e}")
            return []
    
    async def clear_old_metrics(self, hours: int = 24) -> int:
        """오래된 메트릭 정리"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            original_count = len(self.metrics_history)
            
            self.metrics_history = [
                m for m in self.metrics_history
                if datetime.fromisoformat(m['timestamp']) >= cutoff_time
            ]
            
            removed_count = original_count - len(self.metrics_history)
            
            if removed_count > 0:
                self.logger.info(f"Cleared {removed_count} old metrics")
            
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Failed to clear old metrics: {e}")
            return 0
