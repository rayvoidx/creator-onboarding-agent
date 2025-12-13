"""
벡터 검색 MCP 서버

ChromaDB 기반 벡터 검색을 MCP 프로토콜로 노출합니다.
"""

import logging
from typing import Any, Dict, List, Optional

from .base_server import MCPServer, HTTPMCPServer, MCPTool

logger = logging.getLogger(__name__)


class VectorSearchMCPServer(HTTPMCPServer):
    """벡터 검색 MCP 서버

    RetrievalEngine을 사용하여 벡터/하이브리드 검색 기능을 제공합니다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(name="vector-search", version="1.0.0")
        self.config = config or {}
        self._retrieval_engine = None

    def _get_retrieval_engine(self):
        """RetrievalEngine 인스턴스 가져오기 (지연 로딩)"""
        if self._retrieval_engine is None:
            from src.rag.retrieval_engine import RetrievalEngine

            self._retrieval_engine = RetrievalEngine(self.config.get("retrieval", {}))
        return self._retrieval_engine

    async def initialize(self) -> None:
        """서버 초기화 - 검색 도구 등록"""

        # 벡터 검색 도구
        self.register_tool(
            MCPTool(
                name="vector_search",
                description="ChromaDB를 사용한 시맨틱 벡터 검색. 질의와 의미적으로 유사한 문서를 검색합니다.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "검색 질의 텍스트"},
                        "limit": {
                            "type": "integer",
                            "description": "반환할 최대 결과 수",
                            "default": 10,
                        },
                        "filters": {
                            "type": "object",
                            "description": "메타데이터 필터",
                            "default": {},
                        },
                    },
                    "required": ["query"],
                },
                handler=self._vector_search,
            )
        )

        # 키워드 검색 도구
        self.register_tool(
            MCPTool(
                name="keyword_search",
                description="BM25 기반 키워드 검색. 정확한 키워드 매칭이 필요할 때 사용합니다.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "검색 키워드"},
                        "limit": {
                            "type": "integer",
                            "description": "반환할 최대 결과 수",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
                handler=self._keyword_search,
            )
        )

        # 하이브리드 검색 도구
        self.register_tool(
            MCPTool(
                name="hybrid_search",
                description="벡터 검색과 키워드 검색을 결합한 하이브리드 검색. 가장 정확한 결과를 제공합니다.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "검색 질의 텍스트"},
                        "limit": {
                            "type": "integer",
                            "description": "반환할 최대 결과 수",
                            "default": 10,
                        },
                        "filters": {
                            "type": "object",
                            "description": "메타데이터 필터",
                            "default": {},
                        },
                        "vector_weight": {
                            "type": "number",
                            "description": "벡터 검색 가중치 (0-1)",
                            "default": 0.7,
                        },
                    },
                    "required": ["query"],
                },
                handler=self._hybrid_search,
            )
        )

        # 문서 추가 도구
        self.register_tool(
            MCPTool(
                name="add_documents",
                description="벡터 스토어에 문서를 추가합니다.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "documents": {
                            "type": "array",
                            "description": "추가할 문서 배열",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "content": {"type": "string"},
                                    "metadata": {"type": "object"},
                                },
                                "required": ["content"],
                            },
                        }
                    },
                    "required": ["documents"],
                },
                handler=self._add_documents,
            )
        )

        # 문서 삭제 도구
        self.register_tool(
            MCPTool(
                name="delete_documents",
                description="벡터 스토어에서 문서를 삭제합니다.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "document_ids": {
                            "type": "array",
                            "description": "삭제할 문서 ID 배열",
                            "items": {"type": "string"},
                        }
                    },
                    "required": ["document_ids"],
                },
                handler=self._delete_documents,
            )
        )

        # 검색 통계 도구
        self.register_tool(
            MCPTool(
                name="get_search_stats",
                description="검색 엔진 통계 정보를 반환합니다.",
                input_schema={"type": "object", "properties": {}},
                handler=self._get_search_stats,
            )
        )

        # 유사 크리에이터 검색 도구
        self.register_tool(
            MCPTool(
                name="find_similar_creators",
                description="주어진 크리에이터와 유사한 크리에이터를 검색합니다.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "creator_profile": {
                            "type": "object",
                            "description": "기준 크리에이터 프로필",
                            "properties": {
                                "platform": {"type": "string"},
                                "handle": {"type": "string"},
                                "category": {"type": "string"},
                                "followers": {"type": "integer"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                        "limit": {
                            "type": "integer",
                            "description": "반환할 최대 결과 수",
                            "default": 5,
                        },
                    },
                    "required": ["creator_profile"],
                },
                handler=self._find_similar_creators,
            )
        )

        self.logger.info("Vector Search MCP Server initialized with 7 tools")

    async def _vector_search(
        self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """벡터 검색 실행"""
        engine = self._get_retrieval_engine()
        results = await engine.vector_search(query, limit, filters)

        # 결과 포맷팅
        formatted = []
        for r in results:
            formatted.append(
                {
                    "id": r.get("id", ""),
                    "content": r.get("content", "")[:500],  # 최대 500자
                    "score": round(r.get("score", 0), 4),
                    "metadata": r.get("metadata", {}),
                    "search_type": "vector",
                }
            )

        return formatted

    async def _keyword_search(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """키워드 검색 실행"""
        engine = self._get_retrieval_engine()
        results = await engine.keyword_search(query, limit)

        formatted = []
        for r in results:
            formatted.append(
                {
                    "id": r.get("id", ""),
                    "content": r.get("content", "")[:500],
                    "score": round(r.get("score", 0), 4),
                    "metadata": r.get("metadata", {}),
                    "search_type": "keyword",
                }
            )

        return formatted

    async def _hybrid_search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        vector_weight: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """하이브리드 검색 실행"""
        engine = self._get_retrieval_engine()

        # 임시로 가중치 조정
        original_weight = engine.vector_weight
        engine.vector_weight = vector_weight
        engine.keyword_weight = 1 - vector_weight

        try:
            results = await engine.hybrid_search(query, limit, filters)
        finally:
            # 원래 가중치로 복원
            engine.vector_weight = original_weight
            engine.keyword_weight = 1 - original_weight

        formatted = []
        for r in results:
            formatted.append(
                {
                    "id": r.get("id", ""),
                    "content": r.get("content", "")[:500],
                    "score": round(r.get("score", 0), 4),
                    "vector_score": round(r.get("vector_score", 0), 4),
                    "keyword_score": round(r.get("keyword_score", 0), 4),
                    "metadata": r.get("metadata", {}),
                    "search_type": "hybrid",
                }
            )

        return formatted

    async def _add_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """문서 추가"""
        engine = self._get_retrieval_engine()
        success = await engine.add_documents(documents)

        return {
            "success": success,
            "added_count": len(documents) if success else 0,
            "message": (
                f"Successfully added {len(documents)} documents"
                if success
                else "Failed to add documents"
            ),
        }

    async def _delete_documents(self, document_ids: List[str]) -> Dict[str, Any]:
        """문서 삭제"""
        engine = self._get_retrieval_engine()
        success = await engine.delete_documents(document_ids)

        return {
            "success": success,
            "deleted_count": len(document_ids) if success else 0,
            "message": (
                f"Successfully deleted {len(document_ids)} documents"
                if success
                else "Failed to delete documents"
            ),
        }

    async def _get_search_stats(self) -> Dict[str, Any]:
        """검색 통계 조회"""
        engine = self._get_retrieval_engine()
        return await engine.get_search_stats()

    async def _find_similar_creators(
        self, creator_profile: Dict[str, Any], limit: int = 5
    ) -> List[Dict[str, Any]]:
        """유사 크리에이터 검색"""
        # 프로필 정보를 검색 쿼리로 변환
        query_parts = []

        if creator_profile.get("platform"):
            query_parts.append(f"platform:{creator_profile['platform']}")

        if creator_profile.get("category"):
            query_parts.append(creator_profile["category"])

        if creator_profile.get("tags"):
            query_parts.extend(creator_profile["tags"][:3])  # 최대 3개 태그

        # 팔로워 수에 따른 등급 추가
        followers = creator_profile.get("followers", 0)
        if followers >= 1_000_000:
            query_parts.append("mega influencer")
        elif followers >= 100_000:
            query_parts.append("macro influencer")
        elif followers >= 10_000:
            query_parts.append("micro influencer")
        else:
            query_parts.append("nano influencer")

        query = " ".join(query_parts)

        # 하이브리드 검색 실행
        engine = self._get_retrieval_engine()
        results = await engine.hybrid_search(query, limit * 2)

        # 동일한 크리에이터 필터링
        similar = []
        current_handle = creator_profile.get("handle", "").lower()

        for r in results:
            metadata = r.get("metadata", {})
            handle = metadata.get("handle", "").lower()

            # 자기 자신 제외
            if handle and handle == current_handle:
                continue

            similar.append(
                {
                    "id": r.get("id", ""),
                    "content": r.get("content", "")[:300],
                    "score": round(r.get("score", 0), 4),
                    "metadata": metadata,
                    "similarity_reason": f"Similar based on: {query}",
                }
            )

            if len(similar) >= limit:
                break

        return similar


# stdio 모드로 실행할 때 사용
async def main():
    """메인 진입점"""
    import sys

    server = VectorSearchMCPServer()

    if "--http" in sys.argv:
        port = 8001
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])

        await server.run_http(port=port)
    else:
        await server.run_stdio()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
