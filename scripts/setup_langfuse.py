"""Langfuse 설정 및 테스트 스크립트"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any, Optional

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.monitoring.langfuse import LangfuseIntegration
from src.monitoring.performance_monitor import PerformanceMonitor
from src.monitoring.metrics_collector import MetricsCollector

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LangfuseSetup:
    """Langfuse 설정 및 테스트"""
    
    def __init__(self):
        self.langfuse_integration = None
        self.performance_monitor = PerformanceMonitor()
        self.metrics_collector = MetricsCollector()
    
    async def setup_langfuse(self, config: Optional[Dict[str, Any]] = None):
        """Langfuse 설정"""
        try:
            config = config or {
                'public_key': os.getenv('LANGFUSE_PUBLIC_KEY'),
                'secret_key': os.getenv('LANGFUSE_SECRET_KEY'),
                'host': os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
            }
            
            self.langfuse_integration = LangfuseIntegration(config)
            
            # 상태 확인
            health_status = await self.langfuse_integration.health_check()
            
            if health_status['available'] and health_status['configured']:
                logger.info("✅ Langfuse setup completed successfully")
                logger.info(f"   Host: {health_status['host']}")
                logger.info(f"   Connected: {health_status['connected']}")
                return True
            else:
                logger.warning("⚠️ Langfuse setup completed but not fully configured")
                logger.warning(f"   Available: {health_status['available']}")
                logger.warning(f"   Configured: {health_status['configured']}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Langfuse setup failed: {e}")
            return False
    
    async def test_langfuse_integration(self):
        """Langfuse 통합 테스트"""
        logger.info("Starting Langfuse integration test...")
        
        try:
            if not self.langfuse_integration:
                logger.error("Langfuse integration not initialized")
                return False
            
            # 테스트 추적 시작
            trace_id = await self.langfuse_integration.start_trace(
                name="langfuse_setup_test",
                user_id="test_user",
                session_id="test_session",
                metadata={"test_type": "setup_verification"}
            )
            
            if not trace_id:
                logger.error("Failed to start trace")
                return False
            
            logger.info(f"✅ Trace started: {trace_id}")
            
            # 성능 모니터링 테스트
            operation_id = await self.performance_monitor.start_operation(
                "langfuse_test_operation",
                {"test": "integration"}
            )
            
            # 가상 작업 시뮬레이션
            await asyncio.sleep(0.1)
            
            await self.performance_monitor.end_operation(
                operation_id,
                success=True,
                metadata={"test_completed": True}
            )
            
            # RAG 파이프라인 로그 테스트
            await self.langfuse_integration.log_rag_pipeline(
                trace_id=trace_id,
                query="테스트 쿼리",
                retrieved_documents=[
                    {"content": "테스트 문서 1", "score": 0.9, "metadata": {"source": "test"}},
                    {"content": "테스트 문서 2", "score": 0.8, "metadata": {"source": "test"}}
                ],
                response="테스트 응답입니다.",
                processing_time=0.5,
                metadata={"test": True}
            )
            
            # 에이전트 실행 로그 테스트
            await self.langfuse_integration.log_agent_execution(
                trace_id=trace_id,
                agent_name="test_agent",
                input_data={"test_input": "test"},
                output_data={"test_output": "test"},
                execution_time=0.2,
                metadata={"test": True}
            )
            
            # 성능 메트릭 로그
            performance_stats = self.performance_monitor.get_performance_summary()
            await self.langfuse_integration.log_performance_metrics(
                trace_id=trace_id,
                metrics=performance_stats,
                metadata={"test": True}
            )
            
            # 추적 종료
            await self.langfuse_integration.end_trace(
                trace_id=trace_id,
                output={"test_completed": True},
                metadata={"test_result": "success"}
            )
            
            # 데이터 플러시
            await self.langfuse_integration.flush()
            
            logger.info("✅ Langfuse integration test completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Langfuse integration test failed: {e}")
            return False
    
    async def test_monitoring_systems(self):
        """모니터링 시스템 테스트"""
        logger.info("Testing monitoring systems...")
        
        try:
            # 성능 모니터 테스트
            operation_id = await self.performance_monitor.start_operation(
                "monitoring_test",
                {"test": "performance_monitor"}
            )
            
            await asyncio.sleep(0.1)
            
            await self.performance_monitor.end_operation(
                operation_id,
                success=True,
                metadata={"test": "completed"}
            )
            
            performance_summary = self.performance_monitor.get_performance_summary()
            logger.info("✅ Performance monitor test completed")
            logger.info(f"Operations tracked: {performance_summary.get('overall_stats', {}).get('total_operations', 0)}")
            
            # 메트릭 수집기 테스트
            system_metrics = await self.metrics_collector.collect_system_metrics()
            logger.info("✅ Metrics collector test completed")
            logger.info(f"CPU: {system_metrics.get('cpu', {}).get('percent', 0):.1f}%")
            logger.info(f"Memory: {system_metrics.get('memory', {}).get('percent', 0):.1f}%")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Monitoring systems test failed: {e}")
            return False
    
    async def generate_test_report(self):
        """테스트 리포트 생성"""
        logger.info("Generating test report...")
        
        try:
            # Langfuse 상태
            langfuse_status = await self.langfuse_integration.health_check() if self.langfuse_integration else {}
            
            # 성능 통계
            performance_stats = self.performance_monitor.get_performance_summary()
            
            # 시스템 메트릭
            system_metrics = await self.metrics_collector.collect_system_metrics()
            
            report = {
                "test_timestamp": asyncio.get_event_loop().time(),
                "langfuse_status": langfuse_status,
                "performance_stats": performance_stats,
                "system_metrics": system_metrics,
                "recommendations": self._generate_recommendations(langfuse_status, performance_stats)
            }
            
            # 리포트 출력
            self._print_report(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate test report: {e}")
            return {}
    
    def _generate_recommendations(self, langfuse_status: Dict[str, Any], performance_stats: Dict[str, Any]) -> list:
        """권장사항 생성"""
        recommendations = []
        
        # Langfuse 설정 확인
        if not langfuse_status.get('configured', False):
            recommendations.append("Langfuse API 키를 설정하세요 (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY)")
        
        if not langfuse_status.get('connected', False):
            recommendations.append("Langfuse 연결을 확인하세요")
        
        # 성능 권장사항
        overall_stats = performance_stats.get('overall_stats', {})
        if overall_stats.get('overall_error_rate', 0) > 0.1:
            recommendations.append("에러율이 높습니다. 시스템 안정성을 확인하세요")
        
        avg_duration = overall_stats.get('avg_duration', 0)
        if avg_duration > 5.0:
            recommendations.append("평균 응답 시간이 높습니다. 성능 최적화를 고려하세요")
        
        return recommendations
    
    def _print_report(self, report: Dict[str, Any]):
        """리포트 출력"""
        print("\n" + "="*80)
        print("Langfuse Setup & Monitoring Test Report")
        print("="*80)
        
        # Langfuse 상태
        langfuse_status = report.get('langfuse_status', {})
        print("\n🔍 Langfuse Status:")
        print(f"   Available: {langfuse_status.get('available', False)}")
        print(f"   Configured: {langfuse_status.get('configured', False)}")
        print(f"   Connected: {langfuse_status.get('connected', False)}")
        print(f"   Host: {langfuse_status.get('host', 'N/A')}")
        
        # 성능 통계
        performance_stats = report.get('performance_stats', {})
        overall_stats = performance_stats.get('overall_stats', {})
        print("\n📊 Performance Statistics:")
        print(f"   Total Operations: {overall_stats.get('total_operations', 0)}")
        print(f"   Error Rate: {overall_stats.get('overall_error_rate', 0):.2%}")
        print(f"   Average Duration: {overall_stats.get('avg_duration', 0):.3f}s")
        
        # 시스템 메트릭
        system_metrics = report.get('system_metrics', {})
        print("\n💻 System Metrics:")
        print(f"   CPU: {system_metrics.get('cpu', {}).get('percent', 0):.1f}%")
        print(f"   Memory: {system_metrics.get('memory', {}).get('percent', 0):.1f}%")
        print(f"   Disk: {system_metrics.get('disk', {}).get('percent', 0):.1f}%")
        
        # 권장사항
        recommendations = report.get('recommendations', [])
        if recommendations:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        else:
            print("\n✅ All systems are properly configured!")
        
        print("="*80)


async def main():
    """메인 실행 함수"""
    setup = LangfuseSetup()
    
    try:
        # Langfuse 설정
        langfuse_configured = await setup.setup_langfuse()
        
        # 모니터링 시스템 테스트
        monitoring_success = await setup.test_monitoring_systems()
        
        # Langfuse 통합 테스트 (설정된 경우에만)
        langfuse_test_success = True
        if langfuse_configured:
            langfuse_test_success = await setup.test_langfuse_integration()
        
        # 테스트 리포트 생성
        report = await setup.generate_test_report()
        
        # 최종 결과
        if langfuse_configured and monitoring_success and langfuse_test_success:
            logger.info("🎉 All tests completed successfully!")
        else:
            logger.warning("⚠️ Some tests failed. Check the report for details.")
        
        return report
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
