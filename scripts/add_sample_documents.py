"""
RAG 파이프라인에 샘플 문서 추가 스크립트

사용법:
    python scripts/add_sample_documents.py
"""
import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rag.rag_pipeline import RAGPipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 크리에이터 온보딩 관련 샘플 문서
SAMPLE_DOCUMENTS = [
    {
        "id": "doc_001",
        "content": """
        크리에이터 온보딩 프로세스

        1. 신청 및 검토
        크리에이터는 플랫폼에 가입 신청을 하고, 기본 정보와 소셜 미디어 계정을 제출합니다.
        검토 팀은 제출된 정보를 바탕으로 팔로워 수, 참여율, 콘텐츠 품질을 평가합니다.

        2. 자동 평가 시스템
        AI 기반 평가 시스템이 다음 항목을 자동으로 분석합니다:
        - 팔로워 수 및 성장률
        - 평균 좋아요 및 댓글 수
        - 게시물 빈도 및 일관성
        - 브랜드 적합성 점수
        - 과거 신고 이력

        3. 등급 부여
        평가 결과에 따라 A부터 F까지 등급이 부여됩니다.
        A등급: 최우수 크리에이터 (즉시 승인)
        B등급: 우수 크리에이터 (승인)
        C등급: 양호 (조건부 승인)
        D등급: 보통 (재검토 필요)
        F등급: 부적합 (거부)
        """,
        "metadata": {
            "title": "크리에이터 온보딩 프로세스",
            "category": "onboarding",
            "type": "guide",
            "date": "2025-01-01"
        }
    },
    {
        "id": "doc_002",
        "content": """
        크리에이터 평가 기준

        1. 팔로워 수
        - 50만 이상: 10점
        - 10만-50만: 8점
        - 5만-10만: 6점
        - 1만-5만: 4점
        - 1만 미만: 2점

        2. 참여율 (Engagement Rate)
        참여율 = (좋아요 + 댓글) / 팔로워 수 × 100
        - 5% 이상: 10점
        - 3-5%: 8점
        - 2-3%: 6점
        - 1-2%: 4점
        - 1% 미만: 2점

        3. 게시 빈도
        - 주 5회 이상: 10점
        - 주 3-5회: 8점
        - 주 1-3회: 6점
        - 월 2-4회: 4점
        - 월 2회 미만: 2점

        4. 브랜드 적합성
        - 매우 적합 (0.8-1.0): 10점
        - 적합 (0.6-0.8): 8점
        - 보통 (0.4-0.6): 6점
        - 부적합 (0.4 미만): 0점

        5. 신고 이력
        - 신고 없음: 10점
        - 1-2회: 5점
        - 3회 이상: 0점 (자동 거부)
        """,
        "metadata": {
            "title": "크리에이터 평가 기준",
            "category": "evaluation",
            "type": "reference",
            "date": "2025-01-01"
        }
    },
    {
        "id": "doc_003",
        "content": """
        크리에이터 등급별 혜택

        A등급 (90점 이상)
        - 즉시 승인 및 우선 배정
        - 프리미엄 브랜드 캠페인 참여 기회
        - 전담 매니저 배정
        - 높은 수수료율 (80%)

        B등급 (70-89점)
        - 승인
        - 일반 브랜드 캠페인 참여
        - 표준 수수료율 (70%)
        - 월간 성과 리포트 제공

        C등급 (50-69점)
        - 조건부 승인
        - 선별된 캠페인만 참여 가능
        - 표준 수수료율 (60%)
        - 3개월 재평가 필요

        D등급 (30-49점)
        - 재검토 대기
        - 추가 정보 제출 요청
        - 개선 후 재신청 가능

        F등급 (30점 미만)
        - 거부
        - 90일 후 재신청 가능
        """,
        "metadata": {
            "title": "크리에이터 등급별 혜택",
            "category": "benefits",
            "type": "reference",
            "date": "2025-01-01"
        }
    },
    {
        "id": "doc_004",
        "content": """
        플랫폼별 크리에이터 가이드

        TikTok 크리에이터
        - 숏폼 비디오 콘텐츠에 특화
        - 15초-3분 길이의 영상
        - 트렌드에 민감한 콘텐츠 선호
        - 평균 참여율: 3-8%

        Instagram 크리에이터
        - 피드, 스토리, 릴스 다양한 포맷
        - 비주얼 중심의 콘텐츠
        - 브랜드 협업에 적합
        - 평균 참여율: 1-5%

        YouTube 크리에이터
        - 롱폼 콘텐츠에 특화
        - 깊이 있는 리뷰 및 튜토리얼
        - 높은 신뢰도
        - 평균 참여율: 2-4%

        각 플랫폼의 특성에 맞는 콘텐츠 제작이 중요합니다.
        """,
        "metadata": {
            "title": "플랫폼별 크리에이터 가이드",
            "category": "platform",
            "type": "guide",
            "date": "2025-01-02"
        }
    },
    {
        "id": "doc_005",
        "content": """
        크리에이터 온보딩 FAQ

        Q: 승인까지 얼마나 걸리나요?
        A: 일반적으로 영업일 기준 3-5일이 소요됩니다. A등급 크리에이터는 24시간 내 자동 승인됩니다.

        Q: 거부된 경우 재신청이 가능한가요?
        A: 네, 90일 후 재신청이 가능합니다. 거부 사유를 개선한 후 신청하시기 바랍니다.

        Q: 팔로워가 적어도 가능한가요?
        A: 팔로워 수보다 참여율과 콘텐츠 품질이 더 중요합니다. 1만 명 이상의 팔로워와 높은 참여율을 보이면 승인 가능합니다.

        Q: 어떤 플랫폼을 지원하나요?
        A: 현재 TikTok, Instagram, YouTube를 지원합니다. 추후 더 많은 플랫폼을 추가할 예정입니다.

        Q: 수수료율은 어떻게 되나요?
        A: 등급에 따라 60-80%의 수수료율이 적용됩니다. 성과에 따라 추가 인센티브도 제공됩니다.
        """,
        "metadata": {
            "title": "크리에이터 온보딩 FAQ",
            "category": "faq",
            "type": "qa",
            "date": "2025-01-02"
        }
    }
]


async def add_documents_to_rag():
    """RAG 파이프라인에 샘플 문서 추가"""
    try:
        logger.info("RAG 파이프라인 초기화 중...")

        # RAG 파이프라인 생성
        rag_config = {
            'retrieval': {
                'vector_weight': 0.7,
                'keyword_weight': 0.3,
                'max_results': 10
            },
            'generation': {
                'default_model': os.getenv('DEFAULT_LLM_MODEL', 'gpt-5.1'),
                'fallback_model': os.getenv('FALLBACK_LLM_MODEL', 'gpt-5.1'),
                'openai_api_key': os.getenv('OPENAI_API_KEY'),
            }
        }

        rag_pipeline = RAGPipeline(rag_config)

        logger.info(f"{len(SAMPLE_DOCUMENTS)}개의 샘플 문서 추가 중...")

        # 문서 추가
        result = await rag_pipeline.add_documents(SAMPLE_DOCUMENTS)

        logger.info(f"✅ 문서 추가 완료!")
        logger.info(f"  - 성공: {result.get('success_count', 0)}개")
        logger.info(f"  - 실패: {result.get('failed_count', 0)}개")

        # 추가된 문서 테스트 검색
        logger.info("\n테스트 검색 수행...")
        test_queries = [
            "크리에이터 온보딩 프로세스는?",
            "평가 기준은 무엇인가요?",
            "등급별 혜택이 무엇인가요?"
        ]

        for query in test_queries:
            logger.info(f"\n질의: {query}")
            response = await rag_pipeline.query(
                query=query,
                query_type="general"
            )
            logger.info(f"응답: {response.get('answer', 'N/A')[:200]}...")
            logger.info(f"참조 문서 수: {len(response.get('sources', []))}")

        logger.info("\n✅ 모든 작업 완료!")

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(add_documents_to_rag())
