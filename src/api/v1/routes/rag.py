"""RAG (Retrieval-Augmented Generation) endpoints."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from config.settings import get_settings
from src.api.middleware.security_utils import sanitize_output
from src.app.dependencies import get_dependencies
from src.rag.prompt_templates import PromptType

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])
logger = logging.getLogger(__name__)


@router.post("/query")
async def rag_query(
    query: str,
    query_type: str = "general_chat",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """RAG-based intelligent Q&A."""
    try:
        deps = get_dependencies()
        if not deps.rag_pipeline:
            raise HTTPException(
                status_code=500, detail="RAG 파이프라인이 초기화되지 않았습니다."
            )

        try:
            prompt_type = PromptType(query_type)
        except ValueError:
            prompt_type = PromptType.GENERAL_CHAT

        result = await deps.rag_pipeline.process_query(
            query=query,
            query_type=prompt_type,
            user_context=context or {},
            conversation_history=[],
        )

        if result.get("success"):
            payload = {
                "success": True,
                "response": result.get("response", ""),
                "retrieved_documents": result.get("retrieved_documents", []),
                "processing_time": result.get("processing_time", 0),
                "metadata": result.get("metadata", {}),
                "timestamp": datetime.now().isoformat(),
            }
            return sanitize_output(payload)
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "RAG 처리 중 오류가 발생했습니다."),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(
            status_code=500, detail="RAG 질의응답 처리 중 오류가 발생했습니다."
        )


@router.get("/query/stream")
async def rag_query_stream(
    query: str,
    query_type: str = "general_chat",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
):
    """RAG SSE streaming: stream retrieved documents and final response as events."""
    try:
        deps = get_dependencies()
        settings = get_settings()

        if not deps.rag_pipeline:
            raise HTTPException(
                status_code=500, detail="RAG 파이프라인이 초기화되지 않았습니다."
            )

        try:
            ptype = PromptType(query_type)
        except ValueError:
            ptype = PromptType.GENERAL_CHAT

        async def event_generator():
            yield "event: start\ndata: {}\n\n"

            # Retrieval
            try:
                vector_results = await deps.rag_pipeline.retrieval_engine.vector_search(
                    query=query, limit=deps.rag_pipeline.max_retrieval_docs, filters={}
                )
                keyword_results: List[Dict[str, Any]] = []
                if getattr(deps.rag_pipeline, "enable_hybrid_search", True):
                    keyword_results = (
                        await deps.rag_pipeline.retrieval_engine.keyword_search(
                            query=query, limit=deps.rag_pipeline.max_retrieval_docs
                        )
                    )
                retrieved = vector_results + keyword_results
                try:
                    retrieved.sort(key=lambda x: x.get("score", 0.0), reverse=True)
                except Exception:
                    pass
                top_docs = retrieved[: deps.rag_pipeline.rerank_top_k]
                yield "event: docs\n" + "data: " + json.dumps(
                    {"documents": top_docs}, ensure_ascii=False
                ) + "\n\n"
            except Exception as e:
                yield f'event: docs\ndata: {{"error": "{str(e)}"}}\n\n'
                top_docs = []

            # Build context and prompt
            try:
                context = {
                    "retrieved_documents": top_docs,
                    "user_context": {"user_id": user_id, "session_id": session_id},
                }
                prompt = deps.rag_pipeline.prompt_templates.create_rag_prompt(
                    prompt_type=ptype,
                    user_input=query,
                    retrieved_documents=top_docs,
                    context=context,
                )
                system_prompt = deps.rag_pipeline._get_system_prompt_for_type(ptype)
            except Exception:
                context = {"retrieved_documents": top_docs}
                prompt = query
                system_prompt = None

            # Generate answer
            used_stream = False
            try:
                from openai import OpenAI

                if (
                    isinstance(settings.DEFAULT_LLM_MODEL, str)
                    and settings.DEFAULT_LLM_MODEL.startswith("gpt-")
                    and settings.OPENAI_API_KEY
                ):
                    client = OpenAI(api_key=settings.OPENAI_API_KEY)
                    chat_msgs = []
                    if system_prompt:
                        chat_msgs.append({"role": "system", "content": system_prompt})
                    chat_msgs.append({"role": "user", "content": prompt})
                    stream = client.chat.completions.create(
                        model=settings.DEFAULT_LLM_MODEL,
                        messages=chat_msgs,
                        stream=True,
                    )
                    for evt in stream:
                        choice = getattr(evt, "choices", None)
                        if not choice:
                            continue
                        delta = choice[0].delta if hasattr(choice[0], "delta") else None
                        if not delta:
                            continue
                        text = getattr(delta, "content", None)
                        if not text:
                            continue
                        payload = sanitize_output({"text": text})
                        yield "event: answer\n" + "data: " + json.dumps(
                            payload, ensure_ascii=False
                        ) + "\n\n"
                    used_stream = True
            except Exception:
                used_stream = False

            if not used_stream:
                try:
                    answer = await deps.rag_pipeline.generation_engine.generate(
                        prompt=prompt, system_prompt=system_prompt, context=context
                    )
                    chunks = [s.strip() for s in answer.split(".") if s.strip()]
                    for i, ch in enumerate(chunks):
                        payload = sanitize_output(
                            {"text": (ch + ("." if i < len(chunks) - 1 else ""))}
                        )
                        yield "event: answer\n" + "data: " + json.dumps(
                            payload, ensure_ascii=False
                        ) + "\n\n"
                except Exception as e:
                    yield f'event: answer\ndata: {{"error": "{str(e)}"}}\n\n'

            yield "event: end\ndata: {}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"RAG SSE failed: {e}")
        raise HTTPException(
            status_code=500, detail="RAG SSE 처리 중 오류가 발생했습니다."
        )


@router.post("/add-documents")
async def add_documents_to_rag(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Add documents to RAG system."""
    try:
        deps = get_dependencies()
        if not deps.rag_pipeline:
            raise HTTPException(
                status_code=500, detail="RAG 파이프라인이 초기화되지 않았습니다."
            )

        success = await deps.rag_pipeline.retrieval_engine.add_documents(documents)

        if success:
            return {
                "success": True,
                "message": f"{len(documents)}개 문서가 성공적으로 추가되었습니다.",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            raise HTTPException(
                status_code=500, detail="문서 추가 중 오류가 발생했습니다."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document addition failed: {e}")
        raise HTTPException(status_code=500, detail="문서 추가 중 오류가 발생했습니다.")


@router.get("/stats")
async def get_rag_stats() -> Dict[str, Any]:
    """Get RAG system statistics."""
    try:
        deps = get_dependencies()
        if not deps.rag_pipeline:
            raise HTTPException(
                status_code=500, detail="RAG 파이프라인이 초기화되지 않았습니다."
            )

        search_stats = await deps.rag_pipeline.retrieval_engine.get_search_stats()
        generation_health = await deps.rag_pipeline.generation_engine.health_check()

        return {
            "success": True,
            "search_stats": search_stats,
            "generation_health": generation_health,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"RAG stats retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail="RAG 통계 조회 중 오류가 발생했습니다."
        )
