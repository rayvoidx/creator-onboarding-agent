"""Correlation ID middleware.

Adds/propagates X-Request-ID header, binds request_id into structured logging
context, and exposes it via request.state.request_id.
"""

import uuid
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware  # type: ignore[import-not-found]
from starlette.requests import Request  # type: ignore[import-not-found]
from starlette.responses import Response  # type: ignore[import-not-found]

from src.monitoring.logging_setup import bind_request, clear_request


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # read or create request id
        req_id = request.headers.get(self.header_name)
        if not req_id:
            req_id = str(uuid.uuid4())

        # expose to app state and logging context
        request.state.request_id = req_id
        bind_request(req_id)

        try:
            response = await call_next(request)
        finally:
            # clear context regardless of outcome
            clear_request()

        # propagate header
        response.headers[self.header_name] = req_id
        return response
