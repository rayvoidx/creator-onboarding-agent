"""SQLite 영속적 저장 테스트 스크립트"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graphs.main_orchestrator import get_orchestrator

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SQLitePersistenceTester:
    """SQLite 영속적 저장 테스트"""
    
    def __init__(self):
        self.orchestrator = None
        self.test_session_id = f"test_session_{datetime.now().timestamp()}"
    
    async def setup_orchestrator(self):
        """오케스트레이터 설정"""
        try:
            # SQLite 체크포인터 설정
            config = {
                'checkpoint_db_path': 'test_checkpoints.sqlite',
                'competency': {},
                'recommendation': {},
                'search': {},
                'integration': {},
                'analytics': {},
                'llm_manager': {},
                'data_collection': {},
                'rag': {
                    'retrieval': {
                        'vector_weight': 0.7,
                        'keyword_weight': 0.3,
                        'max_results': 10
                    },
                    'generation': {
                        'default_model': 'gpt-5.2',
                        'fallback_model': 'claude-sonnet-4-5-20250929',
                        'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
                        'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY', '')
                    }
                }
            }
            
            self.orchestrator = get_orchestrator(config)
            logger.info("✅ 오케스트레이터 설정 완료")
            logger.info(f"   체크포인터 DB: {config['checkpoint_db_path']}")
            
        except Exception as e:
            logger.error(f"❌ 오케스트레이터 설정 실패: {e}")
            raise
    
    async def test_basic_execution(self):
        """기본 실행 테스트"""
        logger.info("🧪 기본 실행 테스트 시작...")
        
        try:
            # 첫 번째 메시지 실행
            input_data = {
                'message': '육아에 대해 알려주세요',
                'user_id': 'test_user',
                'session_id': self.test_session_id,
                'context': {'interests': ['육아', '교육']}
            }
            
            result = await self.orchestrator.run(input_data)
            
            if result.get('success', False):
                logger.info("✅ 첫 번째 실행 성공")
                logger.info(f"   응답: {result.get('response', '')[:100]}...")
                logger.info(f"   워크플로우: {result.get('workflow_type', '')}")
                logger.info(f"   스레드 ID: {result.get('thread_id', '')}")
                logger.info(f"   상태 저장: {result.get('state_saved', False)}")
                return True
            else:
                logger.error(f"❌ 첫 번째 실행 실패: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 기본 실행 테스트 실패: {e}")
            return False
    
    async def test_session_state_retrieval(self):
        """세션 상태 조회 테스트"""
        logger.info("🧪 세션 상태 조회 테스트 시작...")
        
        try:
            # 세션 상태 조회
            session_state = await self.orchestrator.get_session_state(self.test_session_id)
            
            if session_state and session_state.get('state_exists', False):
                logger.info("✅ 세션 상태 조회 성공")
                logger.info(f"   세션 ID: {session_state.get('session_id', '')}")
                logger.info(f"   현재 단계: {session_state.get('current_step', '')}")
                logger.info(f"   워크플로우: {session_state.get('workflow_type', '')}")
                logger.info(f"   메시지 수: {session_state.get('messages_count', 0)}")
                logger.info(f"   감사 추적 수: {session_state.get('audit_trail_count', 0)}")
                return True
            else:
                logger.warning("⚠️ 세션 상태가 존재하지 않습니다")
                return False
                
        except Exception as e:
            logger.error(f"❌ 세션 상태 조회 실패: {e}")
            return False
    
    async def test_session_resume(self):
        """세션 복원 테스트"""
        logger.info("🧪 세션 복원 테스트 시작...")
        
        try:
            # 세션 복원
            new_message = "추가로 부모교육에 대해서도 알려주세요"
            result = await self.orchestrator.resume_session(self.test_session_id, new_message)
            
            if result.get('success', False):
                logger.info("✅ 세션 복원 성공")
                logger.info(f"   응답: {result.get('response', '')[:100]}...")
                logger.info(f"   워크플로우: {result.get('workflow_type', '')}")
                logger.info(f"   복원됨: {result.get('resumed', False)}")
                return True
            else:
                logger.error(f"❌ 세션 복원 실패: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 세션 복원 테스트 실패: {e}")
            return False
    
    async def test_multiple_sessions(self):
        """다중 세션 테스트"""
        logger.info("🧪 다중 세션 테스트 시작...")
        
        try:
            # 여러 세션 생성
            sessions = []
            for i in range(3):
                session_id = f"multi_session_{i}_{datetime.now().timestamp()}"
                
                input_data = {
                    'message': f'테스트 메시지 {i+1}',
                    'user_id': f'test_user_{i}',
                    'session_id': session_id,
                    'context': {'test_session': i+1}
                }
                
                result = await self.orchestrator.run(input_data)
                
                if result.get('success', False):
                    sessions.append(session_id)
                    logger.info(f"✅ 세션 {i+1} 생성 성공: {session_id}")
                else:
                    logger.error(f"❌ 세션 {i+1} 생성 실패")
            
            # 각 세션 상태 조회
            for i, session_id in enumerate(sessions):
                session_state = await self.orchestrator.get_session_state(session_id)
                if session_state and session_state.get('state_exists', False):
                    logger.info(f"✅ 세션 {i+1} 상태 조회 성공")
                else:
                    logger.warning(f"⚠️ 세션 {i+1} 상태 조회 실패")
            
            return len(sessions) > 0
            
        except Exception as e:
            logger.error(f"❌ 다중 세션 테스트 실패: {e}")
            return False
    
    async def test_persistence_after_restart(self):
        """재시작 후 영속성 테스트"""
        logger.info("🧪 재시작 후 영속성 테스트 시작...")
        
        try:
            # 새로운 오케스트레이터 인스턴스 생성 (재시작 시뮬레이션)
            config = {
                'checkpoint_db_path': 'test_checkpoints.sqlite',
                'competency': {},
                'recommendation': {},
                'search': {},
                'integration': {},
                'analytics': {},
                'llm_manager': {},
                'data_collection': {},
                'rag': {
                    'retrieval': {
                        'vector_weight': 0.7,
                        'keyword_weight': 0.3,
                        'max_results': 10
                    },
                    'generation': {
                        'default_model': 'gpt-5.2',
                        'fallback_model': 'claude-sonnet-4-5-20250929',
                        'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
                        'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY', '')
                    }
                }
            }
            
            # 새로운 오케스트레이터 인스턴스
            new_orchestrator = get_orchestrator(config)
            
            # 기존 세션 상태 조회
            session_state = await new_orchestrator.get_session_state(self.test_session_id)
            
            if session_state and session_state.get('state_exists', False):
                logger.info("✅ 재시작 후 세션 상태 복원 성공")
                logger.info(f"   세션 ID: {session_state.get('session_id', '')}")
                logger.info(f"   메시지 수: {session_state.get('messages_count', 0)}")
                return True
            else:
                logger.warning("⚠️ 재시작 후 세션 상태 복원 실패")
                return False
                
        except Exception as e:
            logger.error(f"❌ 재시작 후 영속성 테스트 실패: {e}")
            return False
    
    async def run_comprehensive_test(self):
        """종합 테스트 실행"""
        logger.info("🚀 SQLite 영속적 저장 종합 테스트 시작")
        logger.info("=" * 60)
        
        try:
            # 1. 오케스트레이터 설정
            await self.setup_orchestrator()
            
            # 2. 기본 실행 테스트
            basic_success = await self.test_basic_execution()
            
            # 3. 세션 상태 조회 테스트
            state_success = await self.test_session_state_retrieval()
            
            # 4. 세션 복원 테스트
            resume_success = await self.test_session_resume()
            
            # 5. 다중 세션 테스트
            multi_success = await self.test_multiple_sessions()
            
            # 6. 재시작 후 영속성 테스트
            persistence_success = await self.test_persistence_after_restart()
            
            # 결과 요약
            results = {
                'basic_execution': basic_success,
                'session_state_retrieval': state_success,
                'session_resume': resume_success,
                'multiple_sessions': multi_success,
                'persistence_after_restart': persistence_success
            }
            
            # 결과 출력
            self._print_test_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 종합 테스트 실패: {e}")
            return {}
    
    def _print_test_results(self, results: dict):
        """테스트 결과 출력"""
        print("\n" + "=" * 60)
        print("SQLite 영속적 저장 테스트 결과")
        print("=" * 60)
        
        total_tests = len(results)
        passed_tests = sum(1 for success in results.values() if success)
        
        print("\n📊 테스트 요약:")
        print(f"   총 테스트: {total_tests}")
        print(f"   통과: {passed_tests}")
        print(f"   실패: {total_tests - passed_tests}")
        print(f"   성공률: {passed_tests/total_tests*100:.1f}%")
        
        print("\n📋 상세 결과:")
        for test_name, success in results.items():
            status = "✅ 통과" if success else "❌ 실패"
            print(f"   {test_name}: {status}")
        
        if passed_tests == total_tests:
            print("\n🎉 모든 테스트 통과! SQLite 영속적 저장이 정상적으로 작동합니다.")
        else:
            print("\n⚠️ 일부 테스트 실패. 로그를 확인하여 문제를 해결하세요.")
        
        print("=" * 60)


async def main():
    """메인 실행 함수"""
    tester = SQLitePersistenceTester()
    
    try:
        results = await tester.run_comprehensive_test()
        return results
        
    except Exception as e:
        logger.error(f"테스트 실행 실패: {e}")
        return {}


if __name__ == "__main__":
    asyncio.run(main())
