"""LangGraph 성능 테스트 스크립트"""

import asyncio
import time
import logging
import statistics
from typing import Dict, Any, List
import json
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graphs.main_orchestrator import get_orchestrator
from src.rag.rag_pipeline import RAGPipeline
from src.rag.prompt_templates import PromptType
from src.monitoring.performance_monitor import PerformanceMonitor
from src.monitoring.metrics_collector import MetricsCollector

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceTester:
    """성능 테스트 클래스"""
    
    def __init__(self):
        self.orchestrator = None
        self.rag_pipeline = None
        self.performance_monitor = PerformanceMonitor()
        self.metrics_collector = MetricsCollector()
        self.test_results = []
    
    async def initialize_systems(self):
        """시스템 초기화"""
        try:
            # 오케스트레이터 초기화
            self.orchestrator = get_orchestrator({
                'database_url': 'sqlite:///test.db',
                'redis_url': 'redis://localhost:6379/0',
                'vector_db_config': {'chroma_path': './test_chroma_db'},
                'llm_configs': {
                    'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
                    'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY', ''),
                    'default_model': 'gpt-5.1',
                    'fallback_model': 'claude-3-sonnet'
                }
            })
            
            # RAG 파이프라인 초기화
            self.rag_pipeline = RAGPipeline({
                'retrieval': {
                    'vector_weight': 0.7,
                    'keyword_weight': 0.3,
                    'max_results': 10
                },
                'generation': {
                    'default_model': 'gpt-5.1',
                    'fallback_model': 'claude-3-sonnet',
                    'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
                    'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY', '')
                }
            })
            
            logger.info("Systems initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize systems: {e}")
            raise
    
    async def test_langgraph_latency(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """LangGraph 지연시간 테스트"""
        logger.info("Starting LangGraph latency tests...")
        
        results = {
            'test_name': 'LangGraph Latency Test',
            'total_tests': len(test_cases),
            'successful_tests': 0,
            'failed_tests': 0,
            'latencies': [],
            'errors': []
        }
        
        for i, test_case in enumerate(test_cases):
            try:
                # 성능 모니터링 시작
                operation_id = await self.performance_monitor.start_operation(
                    f"langgraph_test_{i}",
                    {'test_case': test_case}
                )
                
                start_time = time.time()
                
                # 오케스트레이터 실행
                result = await self.orchestrator.run({
                    'message': test_case['message'],
                    'user_id': test_case.get('user_id', 'test_user'),
                    'session_id': test_case.get('session_id', f'test_session_{i}'),
                    'context': test_case.get('context', {})
                })
                
                end_time = time.time()
                latency = end_time - start_time
                
                # 성능 모니터링 종료
                await self.performance_monitor.end_operation(
                    operation_id,
                    success=result.get('success', False),
                    metadata={'latency': latency}
                )
                
                results['latencies'].append(latency)
                
                if result.get('success', False):
                    results['successful_tests'] += 1
                    logger.info(f"Test {i+1} completed successfully in {latency:.3f}s")
                else:
                    results['failed_tests'] += 1
                    results['errors'].append({
                        'test_case': i,
                        'error': result.get('error', 'Unknown error')
                    })
                    logger.warning(f"Test {i+1} failed: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                results['failed_tests'] += 1
                results['errors'].append({
                    'test_case': i,
                    'error': str(e)
                })
                logger.error(f"Test {i+1} failed with exception: {e}")
        
        # 통계 계산
        if results['latencies']:
            results['avg_latency'] = statistics.mean(results['latencies'])
            results['min_latency'] = min(results['latencies'])
            results['max_latency'] = max(results['latencies'])
            results['p95_latency'] = self._calculate_percentile(results['latencies'], 95)
            results['p99_latency'] = self._calculate_percentile(results['latencies'], 99)
        
        results['success_rate'] = results['successful_tests'] / results['total_tests'] if results['total_tests'] > 0 else 0
        
        return results
    
    async def test_rag_accuracy(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """RAG 정확도 테스트"""
        logger.info("Starting RAG accuracy tests...")
        
        results = {
            'test_name': 'RAG Accuracy Test',
            'total_tests': len(test_cases),
            'successful_tests': 0,
            'failed_tests': 0,
            'processing_times': [],
            'retrieval_scores': [],
            'generation_quality': [],
            'errors': []
        }
        
        for i, test_case in enumerate(test_cases):
            try:
                # 성능 모니터링 시작
                operation_id = await self.performance_monitor.start_operation(
                    f"rag_test_{i}",
                    {'test_case': test_case}
                )
                
                start_time = time.time()
                
                # RAG 파이프라인 실행
                result = await self.rag_pipeline.process_query(
                    query=test_case['query'],
                    query_type=test_case.get('query_type', PromptType.GENERAL_CHAT),
                    user_context=test_case.get('user_context', {}),
                    conversation_history=test_case.get('conversation_history', [])
                )
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                # 성능 모니터링 종료
                await self.performance_monitor.end_operation(
                    operation_id,
                    success=result.get('success', False),
                    metadata={
                        'processing_time': processing_time,
                        'num_documents': len(result.get('retrieved_documents', []))
                    }
                )
                
                results['processing_times'].append(processing_time)
                
                if result.get('success', False):
                    results['successful_tests'] += 1
                    
                    # 검색 점수 계산
                    retrieved_docs = result.get('retrieved_documents', [])
                    if retrieved_docs:
                        avg_score = sum(doc.get('score', 0) for doc in retrieved_docs) / len(retrieved_docs)
                        results['retrieval_scores'].append(avg_score)
                    
                    # 생성 품질 평가 (간단한 휴리스틱)
                    response = result.get('response', '')
                    quality_score = self._evaluate_response_quality(response, test_case.get('expected_keywords', []))
                    results['generation_quality'].append(quality_score)
                    
                    logger.info(f"RAG test {i+1} completed successfully in {processing_time:.3f}s")
                else:
                    results['failed_tests'] += 1
                    results['errors'].append({
                        'test_case': i,
                        'error': result.get('error', 'Unknown error')
                    })
                    logger.warning(f"RAG test {i+1} failed: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                results['failed_tests'] += 1
                results['errors'].append({
                    'test_case': i,
                    'error': str(e)
                })
                logger.error(f"RAG test {i+1} failed with exception: {e}")
        
        # 통계 계산
        if results['processing_times']:
            results['avg_processing_time'] = statistics.mean(results['processing_times'])
            results['min_processing_time'] = min(results['processing_times'])
            results['max_processing_time'] = max(results['processing_times'])
        
        if results['retrieval_scores']:
            results['avg_retrieval_score'] = statistics.mean(results['retrieval_scores'])
        
        if results['generation_quality']:
            results['avg_generation_quality'] = statistics.mean(results['generation_quality'])
        
        results['success_rate'] = results['successful_tests'] / results['total_tests'] if results['total_tests'] > 0 else 0
        
        return results
    
    def _calculate_percentile(self, data: List[float], percentile: int) -> float:
        """백분위수 계산"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _evaluate_response_quality(self, response: str, expected_keywords: List[str]) -> float:
        """응답 품질 평가"""
        if not response or not expected_keywords:
            return 0.5
        
        response_lower = response.lower()
        matched_keywords = sum(1 for keyword in expected_keywords if keyword.lower() in response_lower)
        
        return matched_keywords / len(expected_keywords)
    
    async def run_comprehensive_test(self):
        """종합 성능 테스트 실행"""
        logger.info("Starting comprehensive performance test...")
        
        # 테스트 케이스 정의
        langgraph_test_cases = [
            {
                'message': '육아에 대해 알려주세요',
                'user_id': 'test_user_1',
                'session_id': 'test_session_1',
                'context': {'interests': ['육아', '교육']}
            },
            {
                'message': '아이 발달 단계별 특징을 설명해주세요',
                'user_id': 'test_user_2',
                'session_id': 'test_session_2',
                'context': {'interests': ['발달', '육아']}
            },
            {
                'message': '부모교육 프로그램을 추천해주세요',
                'user_id': 'test_user_3',
                'session_id': 'test_session_3',
                'context': {'interests': ['교육', '프로그램']}
            }
        ]
        
        rag_test_cases = [
            {
                'query': '육아 정책에 대해 알려주세요',
                'query_type': PromptType.GENERAL_CHAT,
                'user_context': {'interests': ['정책', '육아']},
                'expected_keywords': ['정책', '육아', '지원']
            },
            {
                'query': '아동 발달 이론을 설명해주세요',
                'query_type': PromptType.SEARCH,
                'user_context': {'interests': ['발달', '이론']},
                'expected_keywords': ['발달', '이론', '단계']
            }
        ]
        
        try:
            # 시스템 초기화
            await self.initialize_systems()
            
            # LangGraph 지연시간 테스트
            langgraph_results = await self.test_langgraph_latency(langgraph_test_cases)
            self.test_results.append(langgraph_results)
            
            # RAG 정확도 테스트
            rag_results = await self.test_rag_accuracy(rag_test_cases)
            self.test_results.append(rag_results)
            
            # 성능 요약 생성
            performance_summary = self.performance_monitor.get_performance_summary()
            
            # 시스템 메트릭 수집
            system_metrics = await self.metrics_collector.collect_system_metrics()
            
            # 최종 결과 생성
            final_results = {
                'test_timestamp': datetime.now().isoformat(),
                'test_results': self.test_results,
                'performance_summary': performance_summary,
                'system_metrics': system_metrics,
                'overall_assessment': self._generate_overall_assessment()
            }
            
            # 결과 저장
            with open('performance_test_results.json', 'w', encoding='utf-8') as f:
                json.dump(final_results, f, ensure_ascii=False, indent=2)
            
            # 결과 출력
            self._print_test_results(final_results)
            
            return final_results
            
        except Exception as e:
            logger.error(f"Comprehensive test failed: {e}")
            raise
    
    def _generate_overall_assessment(self) -> Dict[str, Any]:
        """전체 평가 생성"""
        assessment = {
            'langgraph_performance': 'Good',
            'rag_accuracy': 'Good',
            'system_stability': 'Good',
            'recommendations': []
        }
        
        # LangGraph 성능 평가
        langgraph_result = next((r for r in self.test_results if r['test_name'] == 'LangGraph Latency Test'), None)
        if langgraph_result:
            avg_latency = langgraph_result.get('avg_latency', 0)
            success_rate = langgraph_result.get('success_rate', 0)
            
            if avg_latency > 10:
                assessment['langgraph_performance'] = 'Poor'
                assessment['recommendations'].append('LangGraph 지연시간이 높습니다. 워크플로우 최적화가 필요합니다.')
            elif avg_latency > 5:
                assessment['langgraph_performance'] = 'Fair'
                assessment['recommendations'].append('LangGraph 지연시간을 개선할 여지가 있습니다.')
            
            if success_rate < 0.8:
                assessment['system_stability'] = 'Poor'
                assessment['recommendations'].append('시스템 안정성을 개선해야 합니다.')
        
        # RAG 정확도 평가
        rag_result = next((r for r in self.test_results if r['test_name'] == 'RAG Accuracy Test'), None)
        if rag_result:
            avg_quality = rag_result.get('avg_generation_quality', 0)
            success_rate = rag_result.get('success_rate', 0)
            
            if avg_quality < 0.5:
                assessment['rag_accuracy'] = 'Poor'
                assessment['recommendations'].append('RAG 응답 품질을 개선해야 합니다.')
            elif avg_quality < 0.7:
                assessment['rag_accuracy'] = 'Fair'
                assessment['recommendations'].append('RAG 응답 품질을 향상시킬 수 있습니다.')
        
        return assessment
    
    def _print_test_results(self, results: Dict[str, Any]):
        """테스트 결과 출력"""
        print("\n" + "="*80)
        print("LangGraph AI Learning System - Performance Test Results")
        print("="*80)
        
        for test_result in results['test_results']:
            print(f"\n📊 {test_result['test_name']}")
            print("-" * 50)
            print(f"Total Tests: {test_result['total_tests']}")
            print(f"Successful: {test_result['successful_tests']}")
            print(f"Failed: {test_result['failed_tests']}")
            print(f"Success Rate: {test_result.get('success_rate', 0):.2%}")
            
            if 'avg_latency' in test_result:
                print(f"Average Latency: {test_result['avg_latency']:.3f}s")
                print(f"Min Latency: {test_result['min_latency']:.3f}s")
                print(f"Max Latency: {test_result['max_latency']:.3f}s")
                print(f"P95 Latency: {test_result['p95_latency']:.3f}s")
            
            if 'avg_processing_time' in test_result:
                print(f"Average Processing Time: {test_result['avg_processing_time']:.3f}s")
            
            if 'avg_generation_quality' in test_result:
                print(f"Average Generation Quality: {test_result['avg_generation_quality']:.2f}")
        
        print("🎯 Overall Assessment")
        print("-" * 50)
        assessment = results['overall_assessment']
        print(f"LangGraph Performance: {assessment['langgraph_performance']}")
        print(f"RAG Accuracy: {assessment['rag_accuracy']}")
        print(f"System Stability: {assessment['system_stability']}")
        
        if assessment['recommendations']:
            print("💡 Recommendations:")
            for i, rec in enumerate(assessment['recommendations'], 1):
                print(f"  {i}. {rec}")
        
        print("📁 Detailed results saved to: performance_test_results.json")
        print("="*80)


async def main():
    """메인 실행 함수"""
    tester = PerformanceTester()
    
    try:
        results = await tester.run_comprehensive_test()
        logger.info("Performance test completed successfully")
        return results
        
    except Exception as e:
        logger.error(f"Performance test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
