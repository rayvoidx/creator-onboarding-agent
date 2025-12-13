"""
데이터 수집 관련 Celery 작업
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

from celery import shared_task

from src.services.audit.service import get_audit_service
from src.data.models.audit_models import AuditAction, AuditSeverity

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def collect_nile_data(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    국가평생교육진흥원(NILE) 데이터 수집

    Args:
        params: 수집 파라미터 (선택적)

    Returns:
        수집 결과
    """
    logger.info(f"Starting NILE data collection. Task ID: {self.request.id}")

    try:
        # DataCollectionAgent를 사용한 수집
        from src.agents.data_collection_agent import DataCollectionAgent, DataSourceType

        agent = DataCollectionAgent()

        # 동기적으로 실행
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                agent.collect(DataSourceType.NILE, params or {})
            )
        finally:
            loop.close()

        logger.info(
            f"NILE data collection completed: {result.get('collected_count', 0)} items"
        )

        return {
            "success": True,
            "source": "NILE",
            "collected_count": result.get("collected_count", 0),
            "task_id": self.request.id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"NILE data collection failed: {e}")
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def collect_mohw_data(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    보건복지부(MOHW) 데이터 수집
    """
    logger.info(f"Starting MOHW data collection. Task ID: {self.request.id}")

    try:
        from src.agents.data_collection_agent import DataCollectionAgent, DataSourceType

        agent = DataCollectionAgent()

        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                agent.collect(DataSourceType.MOHW, params or {})
            )
        finally:
            loop.close()

        logger.info(
            f"MOHW data collection completed: {result.get('collected_count', 0)} items"
        )

        return {
            "success": True,
            "source": "MOHW",
            "collected_count": result.get("collected_count", 0),
            "task_id": self.request.id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"MOHW data collection failed: {e}")
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def collect_kicce_data(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    육아정책연구소(KICCE) 데이터 수집
    """
    logger.info(f"Starting KICCE data collection. Task ID: {self.request.id}")

    try:
        from src.agents.data_collection_agent import DataCollectionAgent, DataSourceType

        agent = DataCollectionAgent()

        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                agent.collect(DataSourceType.KICCE, params or {})
            )
        finally:
            loop.close()

        logger.info(
            f"KICCE data collection completed: {result.get('collected_count', 0)} items"
        )

        return {
            "success": True,
            "source": "KICCE",
            "collected_count": result.get("collected_count", 0),
            "task_id": self.request.id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"KICCE data collection failed: {e}")
        raise


@shared_task(bind=True)
def collect_all_external_data(self) -> Dict[str, Any]:
    """
    모든 외부 데이터 소스에서 데이터 수집 (스케줄된 작업)
    """
    logger.info(f"Starting all external data collection. Task ID: {self.request.id}")

    results = []

    # 각 소스에 대해 비동기 작업 생성
    nile_task = collect_nile_data.delay()
    mohw_task = collect_mohw_data.delay()
    kicce_task = collect_kicce_data.delay()

    results.append(
        {
            "source": "NILE",
            "task_id": nile_task.id,
        }
    )
    results.append(
        {
            "source": "MOHW",
            "task_id": mohw_task.id,
        }
    )
    results.append(
        {
            "source": "KICCE",
            "task_id": kicce_task.id,
        }
    )

    # 감사 로그 기록
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        audit_service = get_audit_service()
        loop.run_until_complete(
            audit_service.log(
                action=AuditAction.DATA_IMPORT,
                details={
                    "type": "scheduled_collection",
                    "sources": ["NILE", "MOHW", "KICCE"],
                    "tasks": results,
                },
                severity=AuditSeverity.INFO,
            )
        )
    finally:
        loop.close()

    logger.info(f"Triggered {len(results)} data collection tasks")

    return {
        "success": True,
        "triggered_tasks": results,
        "timestamp": datetime.utcnow().isoformat(),
    }


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def index_documents_to_vector_db(
    self, documents: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    문서를 벡터 DB에 인덱싱

    Args:
        documents: 인덱싱할 문서 목록

    Returns:
        인덱싱 결과
    """
    logger.info(
        f"Starting document indexing. Task ID: {self.request.id}, Documents: {len(documents)}"
    )

    try:
        from src.rag.rag_pipeline import RAGPipeline
        from config.settings import get_settings

        settings = get_settings()

        pipeline = RAGPipeline(
            {
                "retrieval": {
                    "vector_weight": 0.7,
                    "keyword_weight": 0.3,
                    "max_results": 10,
                },
                "generation": {
                    "default_model": settings.DEFAULT_LLM_MODEL,
                    "fallback_model": settings.FALLBACK_LLM_MODEL,
                    "openai_api_key": settings.OPENAI_API_KEY,
                    "anthropic_api_key": settings.ANTHROPIC_API_KEY,
                },
            }
        )

        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            success = loop.run_until_complete(
                pipeline.retrieval_engine.add_documents(documents)
            )
        finally:
            loop.close()

        if success:
            logger.info(f"Document indexing completed: {len(documents)} documents")
            return {
                "success": True,
                "indexed_count": len(documents),
                "task_id": self.request.id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            raise Exception("Document indexing failed")

    except Exception as e:
        logger.error(f"Document indexing failed: {e}")
        raise
