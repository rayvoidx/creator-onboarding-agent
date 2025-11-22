"""MCP integration helpers for web/Youtube enrichment."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from ..mcp.mcp import HttpMCP, WebSearchMCP, YouTubeMCP
from .supadata_mcp import SupadataMCPClient


class MCPIntegrationService:
    """Collects external data via MCP utilities to enrich agent contexts."""

    def __init__(self) -> None:
        self.http_mcp = HttpMCP()
        try:
            self.web_mcp = WebSearchMCP()
        except Exception:
            self.web_mcp = None
        try:
            self.youtube_mcp = YouTubeMCP()
        except Exception:
            self.youtube_mcp = None
        try:
            self.supadata_client = SupadataMCPClient()
        except Exception:
            self.supadata_client = None

    async def enrich_context(
        self,
        spec: Optional[Dict[str, Any]],
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Fetch external data based on the provided MCP spec."""
        if not spec:
            return {}

        results: Dict[str, Any] = {}
        web_spec = self._extract_web_spec(spec)
        youtube_spec = spec.get("youtube")
        supadata_spec = spec.get("supadata")

        web_data = await self._fetch_web_data(web_spec) if web_spec else None
        if web_data and web_data.get("snippets"):
            results["external_snippets"] = web_data["snippets"]
            results.setdefault("external_sources", {})["web"] = {
                "query": web_data.get("query"),
                "urls": web_data.get("urls"),
            }

        youtube_data = (
            await self._fetch_youtube_data(youtube_spec, user_context)
            if youtube_spec
            else None
        )
        if youtube_data:
            results["youtube_insights"] = youtube_data

        supadata_data = (
            await self._fetch_supadata(supadata_spec, user_context)
            if supadata_spec
            else None
        )
        if supadata_data:
            results["supadata"] = supadata_data
            results.setdefault("external_sources", {})["supadata"] = supadata_spec

        return results

    def _extract_web_spec(self, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        query = spec.get("search_query")
        urls = spec.get("urls") or spec.get("web_urls")
        if not query and not urls:
            return None
        return {
            "search_query": query,
            "urls": urls or [],
            "limit": int(spec.get("web_limit") or spec.get("limit") or 3),
        }

    async def _fetch_web_data(self, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not spec:
            return None

        query: Optional[str] = spec.get("search_query")
        urls: List[str] = list(spec.get("urls") or [])
        limit: int = spec.get("limit", 3)

        if not urls and query and self.web_mcp:
            try:
                urls = await asyncio.to_thread(self.web_mcp.search, query, top_k=limit)
            except Exception:
                urls = []

        if not urls:
            return None

        snippets = await asyncio.to_thread(self.http_mcp.fetch_many, urls, limit)
        return {"query": query, "urls": urls, "snippets": snippets}

    async def _fetch_youtube_data(
        self,
        spec: Dict[str, Any],
        user_context: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        youtube_client = getattr(self, "youtube_mcp", None)
        if not youtube_client or not youtube_client.youtube:
            return None

        resolved_channel = youtube_client.resolve_channel_id(
            channel_id=spec.get("channel_id"),
            channel_username=spec.get("channel_username"),
            channel_handle=spec.get("channel_handle"),
        )

        tasks: List[tuple[str, asyncio.Future]] = []
        if resolved_channel and spec.get("fetch_channel", True):
            tasks.append(
                (
                    "overview",
                    asyncio.to_thread(
                        youtube_client.get_channel_overview,
                        resolved_channel,
                        None,
                        None,
                        spec.get("max_results", 5),
                        spec.get("order", "date"),
                    ),
                )
            )

        video_ids = spec.get("video_ids") or []
        if isinstance(video_ids, str):
            video_ids = [video_ids]
        if video_ids:
            tasks.append(
                (
                    "details",
                    asyncio.to_thread(
                        youtube_client.get_video_details_by_ids,
                        video_ids,
                    ),
                )
            )

        search_query = spec.get("search_query") or (user_context or {}).get(
            "mcp_search_query"
        )
        restrict_to_channel = spec.get("restrict_to_channel", True)
        if search_query:
            tasks.append(
                (
                    "search",
                    asyncio.to_thread(
                        youtube_client.search_videos,
                        search_query,
                        spec.get("search_max_results", 5),
                        resolved_channel if restrict_to_channel else spec.get("channel_id"),
                        spec.get("search_order", "relevance"),
                    ),
                )
            )

        overview_result: Optional[Dict[str, Any]] = None
        video_details: Optional[Dict[str, Any]] = None
        search_results: Optional[List[Dict[str, Any]]] = None

        if tasks:
            gathered = await asyncio.gather(
                *(task for _, task in tasks), return_exceptions=True
            )
            for (label, _), result in zip(tasks, gathered):
                if isinstance(result, Exception):
                    continue
                if label == "overview" and isinstance(result, dict):
                    overview_result = result
                elif label == "details" and isinstance(result, dict):
                    video_details = result
                elif label == "search" and isinstance(result, list):
                    search_results = result

        if not any([overview_result, video_details, search_results]):
            return None

        return {
            "channel_overview": overview_result,
            "video_details": video_details,
            "search_results": search_results,
            "channel_id": resolved_channel or spec.get("channel_id"),
        }

    async def _fetch_supadata(
        self,
        spec: Dict[str, Any],
        user_context: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        client = getattr(self, "supadata_client", None)
        if not client or not getattr(client, "available", False):
            return None

        lang = spec.get("lang", "ko")
        no_links = bool(spec.get("no_links", False))
        text_mode = bool(spec.get("transcript_text", False))
        transcript_mode = spec.get("transcript_mode", "auto")

        result: Dict[str, Any] = {}

        scrape_urls = [
            url for url in spec.get("scrape_urls", []) if isinstance(url, str)
        ]
        if scrape_urls:
            scrapes = await client.scrape_urls(
                scrape_urls,
                lang=lang,
                no_links=no_links,
            )
            if scrapes:
                result["scrapes"] = scrapes

        transcript_urls = [
            url for url in spec.get("transcript_urls", []) if isinstance(url, str)
        ]
        if transcript_urls:
            transcripts = await client.fetch_transcripts(
                transcript_urls,
                lang=lang,
                text=text_mode,
                mode=transcript_mode,
            )
            if transcripts:
                result["transcripts"] = transcripts

        map_url = spec.get("map_url")
        if isinstance(map_url, str) and map_url:
            site_map = await client.map_site(map_url)
            if site_map:
                result["mapped"] = site_map

        crawl_url = spec.get("crawl_url")
        if isinstance(crawl_url, str) and crawl_url:
            crawl_limit = int(spec.get("crawl_limit") or 50)
            crawl = await client.crawl_site(crawl_url, limit=crawl_limit)
            if crawl:
                result["crawl"] = crawl

        if not result:
            return None

        result["requested_spec"] = spec
        return result


_MCP_SERVICE: Optional[MCPIntegrationService] = None


def get_mcp_service() -> MCPIntegrationService:
    global _MCP_SERVICE
    if _MCP_SERVICE is None:
        _MCP_SERVICE = MCPIntegrationService()
    return _MCP_SERVICE

