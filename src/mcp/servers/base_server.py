"""
MCP 프로토콜 서버 기본 클래스

stdio 및 HTTP 전송을 지원하는 MCP 서버 구현
"""

import json
import sys
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MCPErrorCode(Enum):
    """MCP 에러 코드"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


@dataclass
class MCPTool:
    """MCP 도구 정의"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Awaitable[Any]]


@dataclass
class MCPRequest:
    """MCP 요청"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResponse:
    """MCP 응답"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPServer(ABC):
    """MCP 프로토콜 서버 기본 클래스

    stdio 또는 HTTP 전송을 통해 MCP 프로토콜을 구현합니다.
    """

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools: Dict[str, MCPTool] = {}
        self.logger = logging.getLogger(f"MCP.{name}")
        self._running = False

    def register_tool(self, tool: MCPTool) -> None:
        """도구 등록"""
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")

    @abstractmethod
    async def initialize(self) -> None:
        """서버 초기화 - 서브클래스에서 도구 등록"""
        pass

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """요청 처리"""
        try:
            method = request.method

            if method == "initialize":
                return await self._handle_initialize(request)
            elif method == "tools/list":
                return await self._handle_tools_list(request)
            elif method == "tools/call":
                return await self._handle_tools_call(request)
            elif method == "ping":
                return MCPResponse(id=request.id, result={"pong": True})
            else:
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": MCPErrorCode.METHOD_NOT_FOUND.value,
                        "message": f"Method not found: {method}"
                    }
                )

        except Exception as e:
            self.logger.error(f"Request handling error: {e}")
            return MCPResponse(
                id=request.id,
                error={
                    "code": MCPErrorCode.INTERNAL_ERROR.value,
                    "message": str(e)
                }
            )

    async def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """초기화 요청 처리"""
        return MCPResponse(
            id=request.id,
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True}
                },
                "serverInfo": {
                    "name": self.name,
                    "version": self.version
                }
            }
        )

    async def _handle_tools_list(self, request: MCPRequest) -> MCPResponse:
        """도구 목록 요청 처리"""
        tools_list = []
        for tool in self.tools.values():
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            })

        return MCPResponse(
            id=request.id,
            result={"tools": tools_list}
        )

    async def _handle_tools_call(self, request: MCPRequest) -> MCPResponse:
        """도구 호출 요청 처리"""
        params = request.params
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return MCPResponse(
                id=request.id,
                error={
                    "code": MCPErrorCode.METHOD_NOT_FOUND.value,
                    "message": f"Tool not found: {tool_name}"
                }
            )

        tool = self.tools[tool_name]

        try:
            result = await tool.handler(**arguments)

            # 결과를 MCP 콘텐츠 형식으로 변환
            if isinstance(result, str):
                content = [{"type": "text", "text": result}]
            elif isinstance(result, dict):
                content = [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]
            elif isinstance(result, list):
                content = [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]
            else:
                content = [{"type": "text", "text": str(result)}]

            return MCPResponse(
                id=request.id,
                result={"content": content, "isError": False}
            )

        except Exception as e:
            self.logger.error(f"Tool execution error ({tool_name}): {e}")
            return MCPResponse(
                id=request.id,
                result={
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True
                }
            )

    async def run_stdio(self) -> None:
        """stdio 모드로 서버 실행"""
        await self.initialize()
        self._running = True
        self.logger.info(f"MCP Server '{self.name}' started in stdio mode")

        try:
            while self._running:
                # stdin에서 한 줄 읽기
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )

                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    # JSON-RPC 요청 파싱
                    data = json.loads(line)
                    request = MCPRequest(
                        jsonrpc=data.get("jsonrpc", "2.0"),
                        id=data.get("id"),
                        method=data.get("method", ""),
                        params=data.get("params", {})
                    )

                    # 요청 처리
                    response = await self.handle_request(request)

                    # 응답 전송
                    response_data = {
                        "jsonrpc": response.jsonrpc,
                        "id": response.id
                    }
                    if response.error:
                        response_data["error"] = response.error
                    else:
                        response_data["result"] = response.result

                    print(json.dumps(response_data), flush=True)

                except json.JSONDecodeError as e:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": MCPErrorCode.PARSE_ERROR.value,
                            "message": f"Parse error: {str(e)}"
                        }
                    }
                    print(json.dumps(error_response), flush=True)

        except KeyboardInterrupt:
            self.logger.info("Server interrupted")
        finally:
            self._running = False
            self.logger.info(f"MCP Server '{self.name}' stopped")

    def stop(self) -> None:
        """서버 중지"""
        self._running = False


class HTTPMCPServer(MCPServer):
    """HTTP 기반 MCP 서버

    FastAPI를 사용하여 HTTP 엔드포인트로 MCP 프로토콜을 노출합니다.
    """

    def __init__(self, name: str, version: str = "1.0.0"):
        super().__init__(name, version)
        self.app = None

    def create_fastapi_app(self):
        """FastAPI 앱 생성"""
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        from typing import Any, Optional

        app = FastAPI(
            title=f"MCP Server - {self.name}",
            version=self.version,
            description=f"MCP Protocol Server for {self.name}"
        )

        class JSONRPCRequest(BaseModel):
            jsonrpc: str = "2.0"
            id: Optional[str] = None
            method: str
            params: Dict[str, Any] = {}

        @app.post("/mcp")
        async def handle_mcp_request(request: JSONRPCRequest):
            mcp_request = MCPRequest(
                jsonrpc=request.jsonrpc,
                id=request.id,
                method=request.method,
                params=request.params
            )

            response = await self.handle_request(mcp_request)

            result = {
                "jsonrpc": response.jsonrpc,
                "id": response.id
            }

            if response.error:
                result["error"] = response.error
            else:
                result["result"] = response.result

            return result

        @app.get("/health")
        async def health_check():
            return {"status": "healthy", "server": self.name, "version": self.version}

        @app.get("/tools")
        async def list_tools():
            tools = []
            for tool in self.tools.values():
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema
                })
            return {"tools": tools}

        self.app = app
        return app

    async def run_http(self, host: str = "0.0.0.0", port: int = 8001) -> None:
        """HTTP 모드로 서버 실행"""
        import uvicorn

        await self.initialize()
        app = self.create_fastapi_app()

        self.logger.info(f"MCP Server '{self.name}' starting on http://{host}:{port}")

        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
