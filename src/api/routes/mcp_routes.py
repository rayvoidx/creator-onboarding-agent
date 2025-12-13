"""
MCP 서버 API 라우트

MCP 도구를 REST API로 노출합니다.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mcp", tags=["MCP"])


# Request/Response 모델
class VectorSearchRequest(BaseModel):
    query: str
    limit: int = 10
    filters: Optional[Dict[str, Any]] = None


class HybridSearchRequest(BaseModel):
    query: str
    limit: int = 10
    filters: Optional[Dict[str, Any]] = None
    vector_weight: float = 0.7


class AddDocumentsRequest(BaseModel):
    documents: List[Dict[str, Any]]


class DeleteDocumentsRequest(BaseModel):
    document_ids: List[str]


class SimilarCreatorsRequest(BaseModel):
    creator_profile: Dict[str, Any]
    limit: int = 5


class FetchUrlRequest(BaseModel):
    url: str


class FetchUrlsRequest(BaseModel):
    urls: List[str]
    limit: int = 3


class WebSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    prioritize_gov: bool = True


class SearchAndFetchRequest(BaseModel):
    query: str
    top_k: int = 3
    fetch_limit: int = 2


class CreatorProfileRequest(BaseModel):
    profile_url: str
    platform: str = "unknown"


# 전역 서버 인스턴스 (지연 로딩)
_vector_search_server = None
_http_fetch_server = None


def get_vector_search_server():
    """VectorSearchMCPServer 인스턴스 가져오기"""
    global _vector_search_server
    if _vector_search_server is None:
        from src.mcp.servers import VectorSearchMCPServer

        _vector_search_server = VectorSearchMCPServer()
        import asyncio

        asyncio.get_event_loop().run_until_complete(_vector_search_server.initialize())
    return _vector_search_server


def get_http_fetch_server():
    """HttpFetchMCPServer 인스턴스 가져오기"""
    global _http_fetch_server
    if _http_fetch_server is None:
        from src.mcp.servers import HttpFetchMCPServer

        _http_fetch_server = HttpFetchMCPServer()
        import asyncio

        asyncio.get_event_loop().run_until_complete(_http_fetch_server.initialize())
    return _http_fetch_server


# Vector Search 엔드포인트
@router.post("/vector-search")
async def vector_search(request: VectorSearchRequest):
    """벡터 검색 실행"""
    try:
        server = get_vector_search_server()
        results = await server._vector_search(
            query=request.query, limit=request.limit, filters=request.filters
        )
        return {"success": True, "results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Vector search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keyword-search")
async def keyword_search(request: VectorSearchRequest):
    """키워드 검색 실행"""
    try:
        server = get_vector_search_server()
        results = await server._keyword_search(query=request.query, limit=request.limit)
        return {"success": True, "results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Keyword search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hybrid-search")
async def hybrid_search(request: HybridSearchRequest):
    """하이브리드 검색 실행"""
    try:
        server = get_vector_search_server()
        results = await server._hybrid_search(
            query=request.query,
            limit=request.limit,
            filters=request.filters,
            vector_weight=request.vector_weight,
        )
        return {"success": True, "results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/add")
async def add_documents(request: AddDocumentsRequest):
    """문서 추가"""
    try:
        server = get_vector_search_server()
        result = await server._add_documents(request.documents)
        return result
    except Exception as e:
        logger.error(f"Add documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/delete")
async def delete_documents(request: DeleteDocumentsRequest):
    """문서 삭제"""
    try:
        server = get_vector_search_server()
        result = await server._delete_documents(request.document_ids)
        return result
    except Exception as e:
        logger.error(f"Delete documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-stats")
async def get_search_stats():
    """검색 통계 조회"""
    try:
        server = get_vector_search_server()
        stats = await server._get_search_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"Get search stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/similar-creators")
async def find_similar_creators(request: SimilarCreatorsRequest):
    """유사 크리에이터 검색"""
    try:
        server = get_vector_search_server()
        results = await server._find_similar_creators(
            creator_profile=request.creator_profile, limit=request.limit
        )
        return {"success": True, "similar_creators": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Find similar creators error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# HTTP Fetch 엔드포인트
@router.post("/fetch-url")
async def fetch_url(request: FetchUrlRequest):
    """URL 콘텐츠 가져오기"""
    try:
        server = get_http_fetch_server()
        result = await server._fetch_url(request.url)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Fetch URL error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch-urls")
async def fetch_urls(request: FetchUrlsRequest):
    """다중 URL 콘텐츠 가져오기"""
    try:
        server = get_http_fetch_server()
        results = await server._fetch_urls(urls=request.urls, limit=request.limit)
        return {"success": True, "results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Fetch URLs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web-search")
async def web_search(request: WebSearchRequest):
    """웹 검색"""
    try:
        server = get_http_fetch_server()
        result = await server._web_search(
            query=request.query,
            top_k=request.top_k,
            prioritize_gov=request.prioritize_gov,
        )
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Web search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-and-fetch")
async def search_and_fetch(request: SearchAndFetchRequest):
    """검색 후 콘텐츠 가져오기"""
    try:
        server = get_http_fetch_server()
        result = await server._search_and_fetch(
            query=request.query, top_k=request.top_k, fetch_limit=request.fetch_limit
        )
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Search and fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch-creator-profile")
async def fetch_creator_profile(request: CreatorProfileRequest):
    """크리에이터 프로필 가져오기"""
    try:
        server = get_http_fetch_server()
        result = await server._fetch_creator_profile(
            profile_url=request.profile_url, platform=request.platform
        )
        return {"success": True, "profile": result}
    except Exception as e:
        logger.error(f"Fetch creator profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def list_tools():
    """사용 가능한 MCP 도구 목록"""
    vector_server = get_vector_search_server()
    http_server = get_http_fetch_server()

    tools = []

    for tool in vector_server.tools.values():
        tools.append(
            {
                "name": tool.name,
                "description": tool.description,
                "server": "vector-search",
                "input_schema": tool.input_schema,
            }
        )

    for tool in http_server.tools.values():
        tools.append(
            {
                "name": tool.name,
                "description": tool.description,
                "server": "http-fetch",
                "input_schema": tool.input_schema,
            }
        )

    return {"tools": tools, "count": len(tools)}
