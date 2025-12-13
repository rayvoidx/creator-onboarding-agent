"""DER-003: 검색 에이전트 - RAG 기반 하이브리드 검색"""
from typing import Dict, Any, List, Optional
import logging
from pydantic import Field
from ...core.base import BaseAgent, BaseState  # type: ignore[import]
from ...utils.agent_config import get_agent_runtime_config

logger = logging.getLogger(__name__)


class SearchState(BaseState):
    """검색 상태 관리"""
    query: Optional[str] = None
    results: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = 10
    search_type: str = "hybrid"  # hybrid, vector, keyword


class SearchAgent(BaseAgent[SearchState]):
    """
    RAG 기반 하이브리드 검색 에이전트

    기능:
    - 벡터 검색 (의미적 유사도)
    - 키워드 검색 (BM25)
    - 하이브리드 검색 (벡터 + 키워드 결합)
    - 필터링 및 재순위화
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        merged_config = get_agent_runtime_config("search", config)
        super().__init__("SearchAgent", merged_config)
        self.agent_model_config = merged_config
        self.vector_weight = merged_config.get('vector_weight', 0.7)
        self.keyword_weight = merged_config.get('keyword_weight', 0.3)

    async def execute(self, state: SearchState) -> SearchState:
        """
        검색 실행

        Args:
            state: 검색 쿼리와 필터가 포함된 상태

        Returns:
            검색 결과가 포함된 업데이트된 상태
        """
        try:
            if not state.query:
                logger.warning("검색 쿼리가 비어있습니다")
                state.results = []
                state.total_count = 0
                return state

            logger.info(f"검색 시작 - 쿼리: {state.query}, 타입: {state.search_type}")

            # RAG 파이프라인이 설정되어 있으면 사용
            if hasattr(self, 'rag_pipeline') and self.rag_pipeline:
                results = await self._search_with_rag(state)
            else:
                # 폴백: 간단한 검색 시뮬레이션
                results = self._fallback_search(state)

            state.results = results
            state.total_count = len(results)

            logger.info(f"검색 완료 - {state.total_count}개 결과 발견")

        except Exception as e:
            logger.error(f"검색 실패: {e}", exc_info=True)
            state.results = []
            state.total_count = 0
            state.errors.append(f"검색 오류: {str(e)}")

        return state

    async def _search_with_rag(self, state: SearchState) -> List[Dict[str, Any]]:
        """RAG 파이프라인을 사용한 검색"""
        try:
            # retrieval_engine을 통한 검색
            if hasattr(self.rag_pipeline, 'retrieval_engine'):
                documents = await self.rag_pipeline.retrieval_engine.retrieve(
                    query=state.query,
                    limit=state.limit,
                    filters=state.filters
                )

                # 결과 포맷팅
                results = []
                for doc in documents:
                    results.append({
                        'id': doc.get('id', ''),
                        'content': doc.get('content', ''),
                        'metadata': doc.get('metadata', {}),
                        'score': doc.get('score', 0.0),
                        'source': doc.get('source', 'unknown')
                    })

                return results

        except Exception as e:
            logger.error(f"RAG 검색 실패: {e}")
            return self._fallback_search(state)

        return []

    def _fallback_search(self, state: SearchState) -> List[Dict[str, Any]]:
        """
        폴백 검색 (RAG 사용 불가 시)
        실제 운영에서는 이 부분을 Elasticsearch 등으로 대체할 수 있음
        """
        logger.info("폴백 검색 모드 사용")

        # 샘플 결과 반환 (실제로는 DB나 검색 엔진 사용)
        sample_results = [
            {
                'id': 'doc_001',
                'content': f"'{state.query}'에 대한 검색 결과입니다.",
                'metadata': {
                    'title': '검색 결과 1',
                    'category': 'general',
                    'date': '2025-01-01'
                },
                'score': 0.85,
                'source': 'fallback'
            },
            {
                'id': 'doc_002',
                'content': f"'{state.query}' 관련 문서입니다.",
                'metadata': {
                    'title': '검색 결과 2',
                    'category': 'reference',
                    'date': '2025-01-02'
                },
                'score': 0.72,
                'source': 'fallback'
            }
        ]

        # 필터 적용
        filtered_results = self._apply_filters(sample_results, state.filters)

        # limit 적용
        return filtered_results[:state.limit]

    def _apply_filters(
        self,
        results: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """검색 결과에 필터 적용"""
        if not filters:
            return results

        filtered = []
        for result in results:
            metadata = result.get('metadata', {})
            match = True

            for key, value in filters.items():
                if key in metadata and metadata[key] != value:
                    match = False
                    break

            if match:
                filtered.append(result)

        return filtered

    def set_rag_pipeline(self, rag_pipeline):
        """RAG 파이프라인 설정 (의존성 주입)"""
        self.rag_pipeline = rag_pipeline
        logger.info("RAG 파이프라인이 SearchAgent에 연결되었습니다")


