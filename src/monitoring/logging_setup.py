import logging
import sys
from typing import Any, Dict

try:
    import structlog  # type: ignore

    _STRUCTLOG_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    structlog = None  # type: ignore
    _STRUCTLOG_AVAILABLE = False


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured logging with structlog and stdlib.

    - Outputs JSON logs to stdout
    - Supports contextvars for request_id correlation
    """
    # Skip setup during tests to avoid conflict with pytest capture and httpx logging
    if "pytest" in sys.modules:
        return

    if _STRUCTLOG_AVAILABLE:
        shared_processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
        ]

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=[structlog.processors.add_log_level],
            )
        )
        try:
            # Attach PII masking filter if available
            from src.api.middleware.security_utils import PIILogFilter  # type: ignore

            handler.addFilter(PIILogFilter())
        except Exception:
            pass

        root_logger = logging.getLogger()
        root_logger.handlers = [handler]
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        structlog.configure(
            processors=[
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                *shared_processors,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,  # type: ignore[arg-type]
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Fallback: stdlib logging with basic formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        try:
            from src.api.middleware.security_utils import PIILogFilter  # type: ignore

            handler.addFilter(PIILogFilter())
        except Exception:
            pass
        root_logger = logging.getLogger()
        root_logger.handlers = [handler]
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))


def bind_request(request_id: str) -> None:
    """Bind request_id to structlog contextvars for correlation."""
    if _STRUCTLOG_AVAILABLE:
        structlog.contextvars.bind_contextvars(request_id=request_id)  # type: ignore[attr-defined]


def clear_request() -> None:
    """Clear structlog contextvars after request is done."""
    if _STRUCTLOG_AVAILABLE:
        structlog.contextvars.clear_contextvars()  # type: ignore[attr-defined]
