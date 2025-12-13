"""
OpenTelemetry 분산 트레이싱 설정
"""

import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.propagators import set_global_textmap

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 전역 트레이서
_tracer: Optional[trace.Tracer] = None


def setup_tracing(
    service_name: str = "creator-onboarding-agent",
    otlp_endpoint: str = None,
    enable_console_export: bool = False,
) -> trace.Tracer:
    """
    OpenTelemetry 트레이싱 설정

    Args:
        service_name: 서비스 이름
        otlp_endpoint: OTLP 수집기 엔드포인트 (예: "localhost:4317")
        enable_console_export: 콘솔 출력 활성화 (디버깅용)

    Returns:
        Tracer 인스턴스
    """
    global _tracer

    # 리소스 정의
    resource = Resource(
        attributes={
            SERVICE_NAME: service_name,
            "service.version": "1.0.0",
            "deployment.environment": settings.ENV,
        }
    )

    # TracerProvider 설정
    provider = TracerProvider(resource=resource)

    # OTLP Exporter 설정
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint, insecure=True  # 개발 환경에서는 insecure
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(f"OTLP exporter configured: {otlp_endpoint}")

    # 콘솔 출력 (디버깅용)
    if enable_console_export:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("Console span exporter enabled")

    # 전역 TracerProvider 설정
    trace.set_tracer_provider(provider)

    # Propagator 설정 (W3C Trace Context)
    set_global_textmap(CompositeHTTPPropagator([TraceContextTextMapPropagator()]))

    # Tracer 생성
    _tracer = trace.get_tracer(service_name, "1.0.0")

    logger.info(f"OpenTelemetry tracing initialized for service: {service_name}")

    return _tracer


def instrument_app(app) -> None:
    """
    FastAPI 앱에 자동 계측 적용

    Args:
        app: FastAPI 애플리케이션
    """
    # FastAPI 계측
    FastAPIInstrumentor.instrument_app(app)
    logger.info("FastAPI instrumentation applied")

    # HTTPX 클라이언트 계측
    try:
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX client instrumentation applied")
    except Exception as e:
        logger.warning(f"Failed to instrument HTTPX: {e}")

    # Redis 계측
    try:
        RedisInstrumentor().instrument()
        logger.info("Redis instrumentation applied")
    except Exception as e:
        logger.warning(f"Failed to instrument Redis: {e}")

    # SQLAlchemy 계측
    try:
        SQLAlchemyInstrumentor().instrument()
        logger.info("SQLAlchemy instrumentation applied")
    except Exception as e:
        logger.warning(f"Failed to instrument SQLAlchemy: {e}")


def get_tracer() -> trace.Tracer:
    """트레이서 인스턴스 반환"""
    global _tracer
    if _tracer is None:
        _tracer = setup_tracing()
    return _tracer


# 데코레이터와 컨텍스트 매니저


def traced(name: str = None, attributes: dict = None):
    """
    함수에 트레이싱 적용하는 데코레이터

    Args:
        name: 스팬 이름 (기본: 함수 이름)
        attributes: 추가 속성

    Example:
        @traced("process_data")
        async def process_data():
            ...
    """

    def decorator(func):
        import functools
        import asyncio

        span_name = name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class TracingContext:
    """
    트레이싱 컨텍스트 매니저

    Example:
        with TracingContext("database_query", {"query_type": "select"}):
            # 작업 수행
            ...
    """

    def __init__(self, name: str, attributes: dict = None):
        self.name = name
        self.attributes = attributes or {}
        self.span = None

    def __enter__(self):
        tracer = get_tracer()
        self.span = tracer.start_span(self.name)
        self.span.__enter__()

        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)

        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            self.span.record_exception(exc_val)
        else:
            self.span.set_status(Status(StatusCode.OK))

        self.span.__exit__(exc_type, exc_val, exc_tb)
        return False


def add_span_attribute(key: str, value) -> None:
    """현재 스팬에 속성 추가"""
    span = trace.get_current_span()
    if span:
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: dict = None) -> None:
    """현재 스팬에 이벤트 추가"""
    span = trace.get_current_span()
    if span:
        span.add_event(name, attributes or {})


def get_current_trace_id() -> Optional[str]:
    """현재 트레이스 ID 반환"""
    span = trace.get_current_span()
    if span:
        context = span.get_span_context()
        if context.is_valid:
            return format(context.trace_id, "032x")
    return None


def get_current_span_id() -> Optional[str]:
    """현재 스팬 ID 반환"""
    span = trace.get_current_span()
    if span:
        context = span.get_span_context()
        if context.is_valid:
            return format(context.span_id, "016x")
    return None
