"""MCP integration helpers for web/Youtube enrichment."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import pybreaker

from ..mcp.mcp import HttpMCP, WebSearchMCP, YouTubeMCP
from .supadata_mcp import SupadataMCPClient
from src.core.circuit_breaker import get_circuit_breaker_manager
from config.settings import get_settings

logger = logging.getLogger(__name__)

class MCPIntegrationService:
    """Collects external data via MCP utilities to enrich agent contexts."""

    def __init__(self) -> None:
        settings = get_settings()
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

        self.cb_manager = get_circuit_breaker_manager()

        # Tool execution policy (2025: failures are common; contain blast radius)
        # - fail_max / reset_timeout: circuit breaker
        # - max_retries / backoff: retry policy
        self._tool_policies: Dict[str, Dict[str, Any]] = {
            "web": {
                "fail_max": settings.MCP_WEB_FAIL_MAX,
                "reset_timeout": settings.MCP_WEB_RESET_TIMEOUT_SECS,
                "timeout_s": settings.MCP_WEB_TIMEOUT_SECS,
                "max_retries": settings.MCP_WEB_MAX_RETRIES,
                "backoff_base_s": settings.MCP_WEB_BACKOFF_BASE_SECS,
                "backoff_max_s": settings.MCP_WEB_BACKOFF_MAX_SECS,
                "jitter_s": settings.MCP_WEB_JITTER_SECS,
            },
            "youtube": {
                "fail_max": settings.MCP_YOUTUBE_FAIL_MAX,
                "reset_timeout": settings.MCP_YOUTUBE_RESET_TIMEOUT_SECS,
                "timeout_s": settings.MCP_YOUTUBE_TIMEOUT_SECS,
                "max_retries": settings.MCP_YOUTUBE_MAX_RETRIES,
                "backoff_base_s": settings.MCP_YOUTUBE_BACKOFF_BASE_SECS,
                "backoff_max_s": settings.MCP_YOUTUBE_BACKOFF_MAX_SECS,
                "jitter_s": settings.MCP_YOUTUBE_JITTER_SECS,
            },
            "supadata": {
                "fail_max": settings.MCP_SUPADATA_FAIL_MAX,
                "reset_timeout": settings.MCP_SUPADATA_RESET_TIMEOUT_SECS,
                "timeout_s": settings.MCP_SUPADATA_TIMEOUT_SECS,
                "max_retries": settings.MCP_SUPADATA_MAX_RETRIES,
                "backoff_base_s": settings.MCP_SUPADATA_BACKOFF_BASE_SECS,
                "backoff_max_s": settings.MCP_SUPADATA_BACKOFF_MAX_SECS,
                "jitter_s": settings.MCP_SUPADATA_JITTER_SECS,
            },
        }

    async def enrich_context(
        self,
        spec: Optional[Dict[str, Any]],
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Fetch external data based on the provided MCP spec."""
        if not spec:
            return {}

        spec = self._sanitize_spec(spec)
        results: Dict[str, Any] = {}
        tool_policy: Dict[str, Any] = {}
        web_spec = self._extract_web_spec(spec)
        youtube_spec = spec.get("youtube")
        supadata_spec = spec.get("supadata")
        tool_priority = spec.get("tool_priority")

        youtube_data = None
        if youtube_spec:
            youtube_data, tool_policy["youtube"] = await self._run_tool(
                "youtube", lambda: self._fetch_youtube_data(youtube_spec, user_context)
            )
        if youtube_data:
            results["youtube_insights"] = youtube_data

        supadata_data = None
        prefer_supadata_first = False
        prefer_parallel = False
        try:
            if isinstance(tool_priority, str) and tool_priority.lower() == "supadata_first":
                prefer_supadata_first = True
            elif isinstance(tool_priority, str) and tool_priority.lower() == "parallel":
                prefer_parallel = True
            elif isinstance(tool_priority, list) and tool_priority and tool_priority[0] == "supadata":
                prefer_supadata_first = True
        except Exception:
            prefer_supadata_first = False
            prefer_parallel = False

        # Tool priority policy:
        # - If requested, run Supadata first (when URLs/spec exist),
        #   and only run Web as fallback when Supadata yields nothing.
        web_data = None
        if prefer_parallel:
            # Speed-first: run web + supadata concurrently when both are available.
            tasks = []
            labels = []
            if web_spec:
                labels.append("web")
                tasks.append(self._run_tool("web", lambda: self._fetch_web_data(web_spec)))
            if supadata_spec:
                labels.append("supadata")
                tasks.append(self._run_tool("supadata", lambda: self._fetch_supadata(supadata_spec, user_context)))

            if tasks:
                gathered = await asyncio.gather(*tasks, return_exceptions=True)
                for label, item in zip(labels, gathered):
                    if isinstance(item, Exception):
                        # Treat as tool failure; _run_tool already records breaker where applicable,
                        # but keep system resilient if gather itself surfaces an exception.
                        tool_policy[label] = {"ok": False, "last_error": str(item)}
                        continue
                    data, status = item
                    tool_policy[label] = status
                    if label == "web":
                        web_data = data
                    elif label == "supadata":
                        supadata_data = data
        else:
            if prefer_supadata_first and supadata_spec:
                supadata_data, tool_policy["supadata"] = await self._run_tool(
                    "supadata", lambda: self._fetch_supadata(supadata_spec, user_context)
                )
            if (not supadata_data) and web_spec:
                web_data, tool_policy["web"] = await self._run_tool(
                    "web", lambda: self._fetch_web_data(web_spec)
                )
        if web_data and web_data.get("snippets"):
            results["external_snippets"] = web_data["snippets"]
            results.setdefault("external_sources", {})["web"] = {
                "query": web_data.get("query"),
                "urls": web_data.get("urls"),
            }

        if (not supadata_data) and supadata_spec and (not prefer_supadata_first) and (not prefer_parallel):
            supadata_data, tool_policy["supadata"] = await self._run_tool(
                "supadata", lambda: self._fetch_supadata(supadata_spec, user_context)
            )
        if supadata_data:
            results["supadata"] = supadata_data
            results.setdefault("external_sources", {})["supadata"] = supadata_spec

        if tool_policy:
            results["tool_policy"] = tool_policy
        return results

    def _get_policy(self, tool_name: str) -> Dict[str, Any]:
        return dict(self._tool_policies.get(tool_name, {}))

    async def _run_tool(self, tool_name: str, coro_factory: Any) -> tuple[Any, Dict[str, Any]]:
        """
        Execute tool with:
        - circuit breaker (cooldown via reset_timeout)
        - retry w/ exponential backoff + jitter
        - timeout counted as failure
        """
        policy = self._get_policy(tool_name)
        breaker_name = f"mcp_{tool_name}"
        fail_max = int(policy.get("fail_max", 3))
        reset_timeout = int(policy.get("reset_timeout", 30))
        timeout_s = int(policy.get("timeout_s", 10))
        max_retries = int(policy.get("max_retries", 1))
        base = float(policy.get("backoff_base_s", 0.4))
        cap = float(policy.get("backoff_max_s", 3.0))
        jitter = float(policy.get("jitter_s", 0.2))

        breaker = self.cb_manager.get_breaker(
            breaker_name, fail_max=fail_max, reset_timeout=reset_timeout
        )

        status: Dict[str, Any] = {
            "breaker": breaker_name,
            "breaker_state": str(breaker.current_state),
            "fail_max": fail_max,
            "reset_timeout": reset_timeout,
            "timeout_s": timeout_s,
            "max_retries": max_retries,
            "attempts": 0,
            "ok": False,
            "skipped": False,
            "last_error": None,
            "started_at_ms": int(time.time() * 1000),
        }

        if breaker.current_state == pybreaker.STATE_OPEN:
            status["skipped"] = True
            status["last_error"] = "circuit_open"
            return None, status

        for attempt in range(1, max_retries + 2):
            status["attempts"] = attempt
            try:
                if breaker.current_state == pybreaker.STATE_OPEN:
                    raise pybreaker.CircuitBreakerError("circuit_open")

                result = await asyncio.wait_for(coro_factory(), timeout=timeout_s)
                breaker.success()
                self.cb_manager.record_call(breaker_name, True)
                status["ok"] = True
                status["breaker_state"] = str(breaker.current_state)
                status["duration_ms"] = int(time.time() * 1000) - status["started_at_ms"]
                return result, status

            except pybreaker.CircuitBreakerError as exc:
                status["skipped"] = True
                status["last_error"] = str(exc)
                self.cb_manager.record_call(breaker_name, False)
                status["breaker_state"] = str(breaker.current_state)
                status["duration_ms"] = int(time.time() * 1000) - status["started_at_ms"]
                return None, status

            except Exception as exc:
                try:
                    breaker.failure(exc)
                except Exception:
                    # breaker internals shouldn't take the system down
                    pass
                self.cb_manager.record_call(breaker_name, False)
                status["last_error"] = str(exc)
                status["breaker_state"] = str(breaker.current_state)

                if attempt <= max_retries:
                    # exponential backoff with jitter
                    sleep_s = min(cap, base * (2 ** (attempt - 1)))
                    sleep_s = max(0.0, sleep_s + random.uniform(0.0, jitter))
                    await asyncio.sleep(sleep_s)
                    continue

                status["duration_ms"] = int(time.time() * 1000) - status["started_at_ms"]
                return None, status

    def _sanitize_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool Execution safety layer (practical MCP hardening):
        - cap sizes (urls/transcripts)
        - allowlist URL schemes
        - normalize types
        """
        safe: Dict[str, Any] = dict(spec or {})

        def _clean_urls(urls: Any, max_n: int) -> List[str]:
            out: List[str] = []
            if isinstance(urls, str):
                urls = [urls]
            if not isinstance(urls, list):
                return out
            for u in urls:
                if not isinstance(u, str):
                    continue
                uu = u.strip()
                if not uu:
                    continue
                parsed = urlparse(uu)
                if parsed.scheme not in ("http", "https"):
                    continue
                out.append(uu)
                if len(out) >= max_n:
                    break
            return out

        # web
        safe["urls"] = _clean_urls(safe.get("urls") or safe.get("web_urls"), 6)
        if "web_limit" in safe:
            try:
                safe["web_limit"] = max(1, min(int(safe["web_limit"]), 6))
            except Exception:
                safe["web_limit"] = 3

        # youtube
        yt = safe.get("youtube")
        if isinstance(yt, dict):
            yt2 = dict(yt)
            yt2["video_ids"] = _clean_urls([] if yt2.get("video_ids") is None else yt2.get("video_ids"), 0)  # type: ignore[arg-type]
            # keep original ids list if provided correctly (non-url IDs)
            vid = yt.get("video_ids")
            if isinstance(vid, list):
                yt2["video_ids"] = [v for v in vid if isinstance(v, str)][:10]
            elif isinstance(vid, str) and vid:
                yt2["video_ids"] = [vid]
            safe["youtube"] = yt2

        # supadata
        sup = safe.get("supadata")
        if isinstance(sup, dict):
            sup2 = dict(sup)
            sup2["scrape_urls"] = _clean_urls(sup2.get("scrape_urls"), 8)
            sup2["transcript_urls"] = _clean_urls(sup2.get("transcript_urls"), 5)
            if "crawl_limit" in sup2:
                try:
                    sup2["crawl_limit"] = max(1, min(int(sup2["crawl_limit"]), 200))
                except Exception:
                    sup2["crawl_limit"] = 50
            safe["supadata"] = sup2

        return safe

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
            urls = await asyncio.to_thread(self.web_mcp.search, query, top_k=limit)

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
        had_error = False

        if tasks:
            gathered = await asyncio.gather(
                *(task for _, task in tasks), return_exceptions=True
            )
            for (label, _), result in zip(tasks, gathered):
                if isinstance(result, Exception):
                    had_error = True
                    continue
                if label == "overview" and isinstance(result, dict):
                    overview_result = result
                elif label == "details" and isinstance(result, dict):
                    video_details = result
                elif label == "search" and isinstance(result, list):
                    search_results = result

        if not any([overview_result, video_details, search_results]):
            # If we actually attempted calls and they failed, treat as failure to trigger retry/breaker
            if tasks and had_error:
                raise RuntimeError("youtube_fetch_failed")
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

