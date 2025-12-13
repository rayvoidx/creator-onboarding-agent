import pytest

from src.rag.prompt_templates import PromptType
from src.rag.rag_pipeline import RAGPipeline


@pytest.mark.asyncio
async def test_rag_analytics_context_shape(monkeypatch):
    """
    ANALYTICS 쿼리 타입일 때 RAGPipeline이 컨텍스트를 어떻게 구성하는지 검증한다.

    - user_context에 들어 있는 report_type / date_range / creator_stats 등 분석 관련 필드가
      최상위 컨텍스트 및 analytics_context에 노출되는지 확인한다.
    - 응답 구조가 success / response / retrieved_documents / context 필드를 포함하는지 확인한다.
    """
    pipeline = RAGPipeline(config={"enable_hybrid_search": False})

    async def fake_hybrid_retrieval(self, query, user_context):
        return [
            {
                "id": "doc1",
                "content": "크리에이터 미션 및 보상 관련 분석용 샘플 문서입니다.",
                "score": 0.9,
                "metadata": {"source": "test", "date": "2025-01-01"},
            }
        ]

    async def fake_rerank_documents(self, query, documents):
        return documents

    async def fake_generate(prompt, system_prompt=None, model_name=None, context=None):
        # 프롬프트/컨텍스트가 제대로 전달되는지만 검증하므로 간단한 더미 응답 사용
        return "분석 리포트 본문입니다."

    # 검색/재순위화/생성 단계는 더미 구현으로 대체
    monkeypatch.setattr(
        pipeline,
        "_hybrid_retrieval",
        fake_hybrid_retrieval.__get__(pipeline, RAGPipeline),
    )
    monkeypatch.setattr(
        pipeline.retrieval_engine,
        "rerank_documents",
        fake_rerank_documents,
    )
    monkeypatch.setattr(pipeline.generation_engine, "generate", fake_generate)

    user_context = {
        "user_id": "u-analytics-1",
        "session_id": "s-analytics-1",
        "report_type": "creator_mission_performance",
        "date_range": {"from": "2025-01-01", "to": "2025-01-31"},
        "filters": {"creator_grade": "S"},
        "creator_stats": {"total_missions": 3, "completed_missions": 2},
        "mission_stats": {"total": 5, "active": 3},
        "reward_stats": {"total_reward": 100000},
    }

    result = await pipeline.process_query(
        query="크리에이터 미션 성과 리포트를 생성해줘.",
        query_type=PromptType.ANALYTICS,
        user_context=user_context,
        conversation_history=[],
    )

    assert result["success"] is True
    assert isinstance(result["response"], str) and result["response"]
    assert "retrieved_documents" in result
    assert isinstance(result["retrieved_documents"], list)

    ctx = result["context"]
    # 원본 user_context는 user_context / user_data 두 위치에 보존된다.
    assert ctx["user_context"]["report_type"] == "creator_mission_performance"
    assert ctx["user_data"]["report_type"] == "creator_mission_performance"

    # 상위 컨텍스트에 분석 관련 필드가 노출되었는지 확인
    assert ctx.get("report_type") == "creator_mission_performance"
    assert ctx.get("date_range") == {"from": "2025-01-01", "to": "2025-01-31"}
    assert ctx.get("filters") == {"creator_grade": "S"}

    # analytics_context 하위에도 동일한 정보가 정리되어 있는지 확인
    analytics_ctx = ctx.get("analytics_context", {})
    assert analytics_ctx.get("creator_stats") == {
        "total_missions": 3,
        "completed_missions": 2,
    }
    assert analytics_ctx.get("mission_stats") == {"total": 5, "active": 3}
    assert analytics_ctx.get("reward_stats") == {"total_reward": 100000}
