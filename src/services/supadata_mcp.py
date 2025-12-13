"""Supadata MCP client for SNS data collection."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from config.settings import get_settings

from ..mcp.mcp import MCP_LIB_AVAILABLE

if MCP_LIB_AVAILABLE:  # pragma: no cover - optional dependency
    from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore
else:  # pragma: no cover
    MultiServerMCPClient = None  # type: ignore


# Supadata MCP 실제 도구 이름 (session.call_tool에서 사용)
TOOL_SCRAPE = "supadata_scrape"
TOOL_TRANSCRIPT = "supadata_transcript"
TOOL_MAP = "supadata_map"
TOOL_CRAWL = "supadata_crawl"


class SupadataMCPClient:
    """Wrapper around Supadata MCP tools."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("SupadataMCPClient")
        settings = get_settings()
        self.available = bool(
            MCP_LIB_AVAILABLE and MultiServerMCPClient and settings.SUPADATA_API_KEY
        )
        self.client: Optional[MultiServerMCPClient] = None

        if not self.available:
            self.logger.info(
                "Supadata MCP disabled (missing dependency or SUPADATA_API_KEY)."
            )
            return

        connection = {
            "transport": "stdio",
            "command": settings.SUPADATA_MCP_COMMAND or "npx",
            "args": settings.get_supadata_mcp_args(),
            "env": {
                "SUPADATA_API_KEY": settings.SUPADATA_API_KEY,
            },
        }

        try:
            self.client = MultiServerMCPClient({"supadata": connection})  # type: ignore[arg-type]
            self.logger.info("Supadata MCP client initialized")
        except Exception as exc:  # pragma: no cover - initialization failure
            self.logger.warning("Failed to initialize Supadata MCP client: %s", exc)
            self.available = False
            self.client = None

    async def scrape_urls(
        self,
        urls: List[str],
        *,
        lang: str = "ko",
        no_links: bool = False,
    ) -> List[Dict[str, Any]]:
        return await self._gather_results(
            TOOL_SCRAPE,
            [{"url": url, "lang": lang, "noLinks": no_links} for url in urls],
        )

    async def fetch_transcripts(
        self,
        urls: List[str],
        *,
        lang: str = "ko",
        text: bool = False,
        mode: str = "auto",
    ) -> List[Dict[str, Any]]:
        return await self._gather_results(
            TOOL_TRANSCRIPT,
            [{"url": url, "lang": lang, "text": text, "mode": mode} for url in urls],
        )

    async def map_site(self, url: str) -> Optional[Dict[str, Any]]:
        results = await self._gather_results(TOOL_MAP, [{"url": url}])
        return results[0] if results else None

    async def crawl_site(self, url: str, limit: int = 50) -> Optional[Dict[str, Any]]:
        results = await self._gather_results(
            TOOL_CRAWL,
            [{"url": url, "limit": max(1, min(limit, 5000))}],
        )
        return results[0] if results else None

    async def _gather_results(
        self,
        tool_name: str,
        args_list: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not self.available or not self.client or not args_list:
            return []

        tasks = [
            self._call_tool(tool_name, arguments)
            for arguments in args_list
            if arguments.get("url")
        ]
        if not tasks:
            return []

        # timeout 없이 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)

        parsed: List[Dict[str, Any]] = []
        for item in results:
            if isinstance(item, Exception):
                self.logger.warning("Supadata tool call failed: %s", item)
                continue
            if item:
                parsed.append(item)
        return parsed

    async def _call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("Supadata MCP client is not initialized")

        async with self.client.session("supadata") as session:  # type: ignore[union-attr]
            result = await session.call_tool(tool_name, arguments=arguments)

        if result.isError:
            raise RuntimeError(f"Supadata tool {tool_name} returned an error payload")

        if result.structuredContent is not None:
            return result.structuredContent

        if result.content:
            blocks = []
            for block in result.content:
                if hasattr(block, "model_dump"):
                    blocks.append(block.model_dump())
                else:
                    blocks.append(block)  # type: ignore[arg-type]
            return {"content": blocks}

        return {}
