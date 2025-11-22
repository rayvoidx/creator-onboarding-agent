"""
HTTP Fetch MCP 서버

웹 페이지 가져오기 및 웹 검색을 MCP 프로토콜로 노출합니다.
"""

import logging
from typing import Any, Dict, List, Optional

from .base_server import HTTPMCPServer, MCPTool

logger = logging.getLogger(__name__)


class HttpFetchMCPServer(HTTPMCPServer):
    """HTTP Fetch MCP 서버

    HttpMCP와 WebSearchMCP를 MCP 프로토콜 서버로 노출합니다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="http-fetch",
            version="1.0.0"
        )
        self.config = config or {}
        self._http_mcp = None
        self._web_search_mcp = None

    def _get_http_mcp(self):
        """HttpMCP 인스턴스 가져오기"""
        if self._http_mcp is None:
            from src.mcp import HttpMCP
            self._http_mcp = HttpMCP(
                timeout=self.config.get('timeout', 5.0),
                max_bytes=self.config.get('max_bytes', 200_000)
            )
        return self._http_mcp

    def _get_web_search_mcp(self):
        """WebSearchMCP 인스턴스 가져오기"""
        if self._web_search_mcp is None:
            from src.mcp import WebSearchMCP
            self._web_search_mcp = WebSearchMCP(
                timeout=self.config.get('timeout', 5.0)
            )
        return self._web_search_mcp

    async def initialize(self) -> None:
        """서버 초기화 - HTTP 도구 등록"""

        # URL 가져오기 도구
        self.register_tool(MCPTool(
            name="fetch_url",
            description="지정된 URL에서 콘텐츠를 가져옵니다. HTML, JSON, 텍스트 콘텐츠를 지원합니다.",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "가져올 URL"
                    }
                },
                "required": ["url"]
            },
            handler=self._fetch_url
        ))

        # 다중 URL 가져오기 도구
        self.register_tool(MCPTool(
            name="fetch_urls",
            description="여러 URL에서 동시에 콘텐츠를 가져옵니다.",
            input_schema={
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "array",
                        "description": "가져올 URL 배열",
                        "items": {"type": "string"}
                    },
                    "limit": {
                        "type": "integer",
                        "description": "처리할 최대 URL 수",
                        "default": 3
                    }
                },
                "required": ["urls"]
            },
            handler=self._fetch_urls
        ))

        # 웹 검색 도구
        self.register_tool(MCPTool(
            name="web_search",
            description="Brave Search 또는 SerpAPI를 사용하여 웹 검색을 수행합니다. 정부 사이트(.go.kr, .gov)를 우선합니다.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색 질의"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "반환할 최대 URL 수",
                        "default": 5
                    },
                    "prioritize_gov": {
                        "type": "boolean",
                        "description": "정부 사이트 우선 여부",
                        "default": True
                    }
                },
                "required": ["query"]
            },
            handler=self._web_search
        ))

        # 검색 후 콘텐츠 가져오기 도구
        self.register_tool(MCPTool(
            name="search_and_fetch",
            description="웹 검색을 수행하고 결과 URL의 콘텐츠를 가져옵니다.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색 질의"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "검색할 최대 URL 수",
                        "default": 3
                    },
                    "fetch_limit": {
                        "type": "integer",
                        "description": "콘텐츠를 가져올 최대 URL 수",
                        "default": 2
                    }
                },
                "required": ["query"]
            },
            handler=self._search_and_fetch
        ))

        # 크리에이터 프로필 가져오기 도구
        self.register_tool(MCPTool(
            name="fetch_creator_profile",
            description="소셜 미디어 크리에이터 프로필 URL에서 정보를 가져옵니다.",
            input_schema={
                "type": "object",
                "properties": {
                    "profile_url": {
                        "type": "string",
                        "description": "크리에이터 프로필 URL"
                    },
                    "platform": {
                        "type": "string",
                        "description": "플랫폼 (tiktok, instagram, youtube 등)",
                        "default": "unknown"
                    }
                },
                "required": ["profile_url"]
            },
            handler=self._fetch_creator_profile
        ))

        self.logger.info("HTTP Fetch MCP Server initialized with 5 tools")

    async def _fetch_url(self, url: str) -> Dict[str, Any]:
        """단일 URL 가져오기"""
        http_mcp = self._get_http_mcp()
        result = http_mcp.fetch(url)

        return {
            "url": result.get("url", url),
            "status": result.get("status", 0),
            "content_type": result.get("content_type", ""),
            "site_name": result.get("site_name", ""),
            "text": result.get("text", "")[:5000] if result.get("text") else None,
            "json": result.get("json"),
            "error": result.get("error")
        }

    async def _fetch_urls(
        self,
        urls: List[str],
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """다중 URL 가져오기"""
        http_mcp = self._get_http_mcp()
        results = http_mcp.fetch_many(urls, limit)

        formatted = []
        for r in results:
            formatted.append({
                "url": r.get("url", ""),
                "status": r.get("status", 0),
                "content_type": r.get("content_type", ""),
                "site_name": r.get("site_name", ""),
                "text_preview": r.get("text", "")[:1000] if r.get("text") else None,
                "has_json": r.get("json") is not None,
                "error": r.get("error")
            })

        return formatted

    async def _web_search(
        self,
        query: str,
        top_k: int = 5,
        prioritize_gov: bool = True
    ) -> Dict[str, Any]:
        """웹 검색"""
        try:
            web_search = self._get_web_search_mcp()
            urls = web_search.search(query, top_k=top_k)

            return {
                "query": query,
                "urls": urls,
                "count": len(urls),
                "prioritize_gov": prioritize_gov
            }
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {
                "query": query,
                "urls": [],
                "count": 0,
                "error": str(e)
            }

    async def _search_and_fetch(
        self,
        query: str,
        top_k: int = 3,
        fetch_limit: int = 2
    ) -> Dict[str, Any]:
        """검색 후 콘텐츠 가져오기"""
        # 먼저 검색
        search_result = await self._web_search(query, top_k)

        if search_result.get("error"):
            return search_result

        urls = search_result.get("urls", [])

        if not urls:
            return {
                "query": query,
                "search_results": 0,
                "fetched": [],
                "message": "No search results found"
            }

        # 검색 결과 URL에서 콘텐츠 가져오기
        fetch_results = await self._fetch_urls(urls, fetch_limit)

        return {
            "query": query,
            "search_results": len(urls),
            "fetched": fetch_results,
            "all_urls": urls
        }

    async def _fetch_creator_profile(
        self,
        profile_url: str,
        platform: str = "unknown"
    ) -> Dict[str, Any]:
        """크리에이터 프로필 가져오기"""
        http_mcp = self._get_http_mcp()
        result = http_mcp.fetch(profile_url)

        # 플랫폼 자동 감지
        if platform == "unknown":
            url_lower = profile_url.lower()
            if "tiktok.com" in url_lower:
                platform = "tiktok"
            elif "instagram.com" in url_lower:
                platform = "instagram"
            elif "youtube.com" in url_lower or "youtu.be" in url_lower:
                platform = "youtube"
            elif "twitter.com" in url_lower or "x.com" in url_lower:
                platform = "twitter"

        profile_data = {
            "url": profile_url,
            "platform": platform,
            "fetched": not bool(result.get("error")),
            "content_type": result.get("content_type", ""),
            "site_name": result.get("site_name", ""),
            "error": result.get("error")
        }

        # HTML 콘텐츠가 있으면 기본 메타데이터 추출 시도
        if result.get("text"):
            text = result["text"]

            # 간단한 메타데이터 추출 (실제로는 더 정교한 파싱 필요)
            import re

            # 팔로워 수 추출 시도 (다양한 패턴)
            follower_patterns = [
                r'(\d+(?:,\d{3})*(?:\.\d+)?[KkMm]?)\s*(?:followers?|팔로워)',
                r'followers?[:\s]*(\d+(?:,\d{3})*(?:\.\d+)?[KkMm]?)',
            ]

            for pattern in follower_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    profile_data["followers_text"] = match.group(1)
                    break

            # 설명 추출 시도
            desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', text, re.IGNORECASE)
            if desc_match:
                profile_data["description"] = desc_match.group(1)[:200]

        return profile_data


# stdio 모드로 실행할 때 사용
async def main():
    """메인 진입점"""
    import sys

    server = HttpFetchMCPServer()

    if "--http" in sys.argv:
        port = 8002
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])

        await server.run_http(port=port)
    else:
        await server.run_stdio()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
