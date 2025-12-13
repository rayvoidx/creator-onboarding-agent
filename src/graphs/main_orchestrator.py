"""
LangGraph 기반 메인 오케스트레이터

모든 DER 요구사항을 통합하여 실행하는 메인 워크플로우 그래프입니다.
LangGraph를 활용한 하이브리드 AI 시스템의 핵심 오케스트레이션을 담당합니다.
"""
from typing import Dict, Any, List, Optional, Annotated, Sequence, Iterable
from datetime import datetime
import logging

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
try:
    from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore
    _CHECKPOINTER_AVAILABLE = True
except Exception:
    SqliteSaver = None  # type: ignore
    _CHECKPOINTER_AVAILABLE = False
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import sqlite3
import os

from config.settings import get_settings

from ..core.base import BaseState
from ..agents.competency_agent import CompetencyAgent, CompetencyDiagnosisState
from ..agents.recommendation_agent import RecommendationAgent, RecommendationState
from ..agents.search_agent import SearchAgent, SearchState
from ..agents.integration_agent import IntegrationAgent, IntegrationState
from ..agents.analytics_agent import AnalyticsAgent, AnalyticsState
from ..agents.mission_agent import MissionAgent, MissionRecommendationState
from ..agents.llm_manager_agent import LLMManagerAgent, LLMManagerState
from ..agents.data_collection_agent import DataCollectionAgent, DataCollectionState
from ..agents.deep_agents import UnifiedDeepAgents, DeepAgentsState
from ..rag.rag_pipeline import RAGPipeline
from ..rag.prompt_templates import PromptType
from ..rag.intent_analyzer import IntentAnalyzer, UserIntent
from ..rag.generation_engine import GenerationEngine
from ..services.mcp_integration import get_mcp_service
from ..utils.agent_config import (
    attach_agent_config_to_context,
    get_agent_runtime_config,
)
from ..data.models.mission_models import Mission

logger = logging.getLogger(__name__)


def _dedup_strings(values: Iterable[Any]) -> List[str]:
    seen = set()
    deduped: List[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped

class MainOrchestratorState(BaseState):
    """메인 오케스트레이터 상태"""
    # 공통 상태
    messages: Annotated[List[BaseMessage], add_messages]
    current_step: str = "init"
    workflow_type: str = "default"
    agent_model_config: Optional[Dict[str, Any]] = None
    
    # DER별 상태 데이터
    competency_data: Optional[Dict[str, Any]] = None
    recommendation_data: Optional[Dict[str, Any]] = None
    mission_recommendations: List[Dict[str, Any]] = []
    search_results: List[Dict[str, Any]] = []
    analytics_results: Optional[Dict[str, Any]] = None
    external_api_results: Dict[str, Any] = {}
    
    # LLM 관리 상태
    llm_manager_state: Optional[LLMManagerState] = None
    selected_llm_model: Optional[str] = None
    
    # 데이터 수집 상태
    data_collection_state: Optional[DataCollectionState] = None
    collected_data: List[Dict[str, Any]] = []
    
    # RAG 상태
    rag_result: Optional[Dict[str, Any]] = None
    retrieved_documents: List[Dict[str, Any]] = []
    rag_context: Optional[Dict[str, Any]] = None
    
    # Deep Agents 상태
    deep_agents_state: Optional[DeepAgentsState] = None
    use_deep_agents: bool = False
    deep_agents_result: Optional[Dict[str, Any]] = None

    # Router/Planner (Compound AI System)
    routing: Dict[str, Any] = {}
    plan: Optional[Dict[str, Any]] = None

    # Loop safety (Compound system often needs 1-2 corrective loops)
    loop_count: int = 0
    max_loops: int = 2

    # Tool Worker
    tool_enrichment_result: Dict[str, Any] = {}
    replan_result: Dict[str, Any] = {}
    
    # 보안 및 모니터링
    security_level: str = "standard"
    performance_metrics: Dict[str, Any] = {}
    audit_trail: List[Dict[str, Any]] = []
    errors: List[str] = []

class MainOrchestrator:
    """메인 오케스트레이터 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("MainOrchestrator")
        self.settings = get_settings()
        self.mcp_service = get_mcp_service()
        
        # 에이전트 초기화
        self.competency_agent = CompetencyAgent(
            get_agent_runtime_config("competency", self.config.get('competency'))
        )
        self.recommendation_agent = RecommendationAgent(
            get_agent_runtime_config("recommendation", self.config.get('recommendation'))
        )
        self.search_agent = SearchAgent(
            get_agent_runtime_config("search", self.config.get('search'))
        )
        self.integration_agent = IntegrationAgent(
            get_agent_runtime_config("integration", self.config.get('integration'))
        )
        self.analytics_agent = AnalyticsAgent(
            get_agent_runtime_config("analytics", self.config.get('analytics'))
        )
        self.mission_agent = MissionAgent(
            get_agent_runtime_config("mission", self.config.get('mission'))
        )
        self.llm_manager = LLMManagerAgent(
            get_agent_runtime_config("llm_manager", self.config.get('llm_manager'))
        )
        self.data_collection_agent = DataCollectionAgent(
            get_agent_runtime_config("data_collection", self.config.get('data_collection'))
        )
        
        # RAG 파이프라인 초기화
        self.rag_pipeline = RAGPipeline(
            get_agent_runtime_config("rag", self.config.get('rag'))
        )

        # Router (SLM) + Planner (System 2) 엔진
        # - Router: fast_model 기반 intent classification
        # - Planner: deep_model 기반 JSON plan 생성
        self.intent_analyzer = IntentAnalyzer(self.rag_pipeline.generation_engine)
        self.planner_engine = GenerationEngine(
            {
                "default_model": self.settings.DEFAULT_LLM_MODEL,
                "fast_model": self.settings.FAST_LLM_MODEL,
                "deep_model": self.settings.DEEP_LLM_MODEL,
                "fallback_model": self.settings.FALLBACK_LLM_MODEL,
                "openai_api_key": self.settings.OPENAI_API_KEY,
                "anthropic_api_key": self.settings.ANTHROPIC_API_KEY,
                "google_api_key": self.settings.GOOGLE_API_KEY,
                # planning은 determinism 우선
                "temperature": 0.0,
            }
        )
        
        # Deep Agents 초기화 (통합)
        self.deep_agents = UnifiedDeepAgents(
            get_agent_runtime_config("deep_agents", self.config.get('deep_agents'))
        )
        
        # 체크포인터 설정 (영속적 저장용)
        self._setup_checkpointer()
        
        # 그래프 빌드
        self.graph = self._build_graph()

    def _with_agent_context(self, state: MainOrchestratorState, agent_key: str) -> Dict[str, Any]:
        """상태 컨텍스트에 에이전트별 모델 구성을 포함."""
        context = attach_agent_config_to_context(state.context, agent_key)
        # Compound system metadata (Router/Planner outputs)
        context["routing"] = state.routing
        context["plan"] = state.plan
        state.agent_model_config = context.get("agent_model_config")
        return context

    def _build_mcp_spec(self, agent_key: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """에이전트별 MCP 스펙 구성."""
        spec = dict(ctx.get("mcp") or {})

        if agent_key == "mission":
            creator_profile = ctx.get("creator_profile", {})
            youtube_cfg = dict(spec.get("youtube", {}))
            supadata_cfg = dict(spec.get("supadata", {}))
            if creator_profile:
                for key in ("youtube_channel_id", "channel_id"):
                    if creator_profile.get(key):
                        youtube_cfg.setdefault("channel_id", creator_profile[key])
                        break
                if creator_profile.get("youtube_handle"):
                    youtube_cfg.setdefault("channel_handle", creator_profile["youtube_handle"])
                if creator_profile.get("creator_handle"):
                    youtube_cfg.setdefault("channel_handle", creator_profile["creator_handle"])
                keywords = creator_profile.get("keywords") or creator_profile.get("tags")
                if keywords and "search_query" not in spec:
                    spec["search_query"] = ", ".join(keywords[:3]) + " 미션 캠페인"
                scrape_candidates: List[str] = []
                social_links = creator_profile.get("social_links") or []
                if isinstance(social_links, list):
                    scrape_candidates.extend([link for link in social_links if isinstance(link, str)])
                for key in (
                    "instagram_url",
                    "tiktok_url",
                    "youtube_url",
                    "twitter_url",
                    "facebook_url",
                    "website",
                ):
                    value = creator_profile.get(key)
                    if isinstance(value, str):
                        scrape_candidates.append(value)
                if scrape_candidates:
                    existing_scrapes = supadata_cfg.get("scrape_urls", [])
                    supadata_cfg["scrape_urls"] = _dedup_strings(
                        list(existing_scrapes) + scrape_candidates
                    )
                recent_videos = creator_profile.get("recent_video_urls") or []
                if isinstance(recent_videos, list) and recent_videos:
                    existing_transcripts = supadata_cfg.get("transcript_urls", [])
                    supadata_cfg["transcript_urls"] = _dedup_strings(
                        list(existing_transcripts)
                        + [url for url in recent_videos if isinstance(url, str)]
                    )
            if youtube_cfg:
                spec["youtube"] = youtube_cfg
            if supadata_cfg:
                spec["supadata"] = supadata_cfg

        elif agent_key == "analytics":
            filters = ctx.get("filters", {})
            filter_mcp = filters.get("mcp") if isinstance(filters, dict) else {}
            for key, value in (filter_mcp or {}).items():
                spec.setdefault(key, value)
            supadata_filter = filters.get("supadata") if isinstance(filters, dict) else {}
            if supadata_filter:
                supadata_cfg = dict(spec.get("supadata", {}))
                for key, value in supadata_filter.items():
                    supadata_cfg.setdefault(key, value)
                spec["supadata"] = supadata_cfg

        return spec

    async def _prepare_agent_context(
        self,
        state: MainOrchestratorState,
        agent_key: str,
    ) -> Dict[str, Any]:
        """Attach agent config and enrich context via MCP."""
        ctx = self._with_agent_context(state, agent_key)
        spec = self._build_mcp_spec(agent_key, ctx)

        if spec and self.mcp_service:
            try:
                enrichment = await self.mcp_service.enrich_context(spec, ctx)
                if enrichment:
                    ctx.update(enrichment)
                    ctx.setdefault("mcp_enrichment", {}).update(enrichment)
            except Exception as mcp_error:
                self.logger.warning(
                    "MCP enrichment failed for %s: %s", agent_key, mcp_error
                )

        state.context.update({k: v for k, v in ctx.items() if k != "messages"})
        return ctx
    
    def _setup_checkpointer(self) -> None:
        """SQLite 체크포인터 설정"""
        if not _CHECKPOINTER_AVAILABLE:
            self.logger.warning("LangGraph SqliteSaver not available; proceeding without persistent checkpoints")
            self.checkpointer = None
            return
        try:
            # 데이터베이스 파일 경로 설정
            db_path = self.config.get('checkpoint_db_path', 'checkpoints.sqlite')
            # 경로 보존 (삭제 용도에 대비해 저장)
            self._checkpoint_db_path = db_path  # type: ignore[attr-defined]

            # 디렉토리가 없으면 생성
            os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
            
            # SQLite 연결 생성
            conn = sqlite3.connect(db_path, check_same_thread=False)
            # 연결 보존 (세션 삭제 등에 사용)
            self._checkpoint_conn = conn  # type: ignore[attr-defined]
            
            # SqliteSaver 인스턴스 생성
            self.checkpointer = SqliteSaver(conn)  # type: ignore
            
            self.logger.info(f"SQLite checkpointer initialized: {db_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize SQLite checkpointer: {e}")
            # 폴백: 메모리 체크포인터 사용 가능 시 사용
            try:
                if SqliteSaver is not None:
                    self.checkpointer = SqliteSaver.from_conn_string(":memory:")  # type: ignore
                    self.logger.info("Using in-memory checkpointer as fallback")
                else:
                    self.checkpointer = None
            except Exception:
                self.checkpointer = None
    
    def _build_graph(self) -> Any:
        """LangGraph 워크플로우 구성"""
        
        # StateGraph 생성
        workflow = StateGraph(MainOrchestratorState)
        
        # 노드 추가
        workflow.add_node("route_request", self._route_request)
        workflow.add_node("plan_request", self._plan_request)
        workflow.add_node("tool_enrichment", self._tool_enrichment)
        workflow.add_node("replan_request", self._replan_request)
        workflow.add_node("deep_agents_processing", self._deep_agents_processing)
        workflow.add_node("rag_processing", self._rag_processing)
        workflow.add_node("llm_manager", self._manage_llm)
        workflow.add_node("competency_diagnosis", self._competency_diagnosis)
        workflow.add_node("recommendation", self._generate_recommendations)
        workflow.add_node("mission_recommendation", self._mission_recommendation)
        workflow.add_node("vector_search", self._vector_search)
        workflow.add_node("external_integration", self._external_integration)
        workflow.add_node("analytics", self._analytics_processing)
        workflow.add_node("data_collection", self._data_collection)
        workflow.add_node("final_synthesis", self._final_synthesis)
        
        # 시작점 설정
        workflow.set_entry_point("route_request")

        # Router -> Planner (Planner는 필요할 때만 작동, 아니면 pass-through)
        workflow.add_edge("route_request", "plan_request")

        # Planner -> Tool Worker (필요할 때만 MCP 호출, 아니면 no-op)
        workflow.add_edge("plan_request", "tool_enrichment")
        # Replan -> Tool Worker (replan 결과에 따라 재시도 or no-op)
        workflow.add_edge("replan_request", "tool_enrichment")
        
        # 조건부 엣지 추가
        workflow.add_conditional_edges(
            "tool_enrichment",
            self._post_tool_enrichment_condition,
            {
                "replan": "replan_request",
                "deep_agents": "deep_agents_processing",
                "rag": "rag_processing",
                "competency": "competency_diagnosis",
                "recommendation": "recommendation", 
                "mission": "mission_recommendation",
                "search": "vector_search",
                "analytics": "analytics",
                "data_collection": "data_collection",
                "general": "llm_manager"
            }
        )
        
        # RAG 처리 후 라우팅
        workflow.add_conditional_edges(
            "rag_processing",
            self._rag_route_condition,
            {
                "replan": "replan_request",
                "competency": "competency_diagnosis",
                "recommendation": "recommendation",
                "search": "vector_search",
                "analytics": "analytics",
                "final": "final_synthesis"
            }
        )
        
        # Deep Agents 처리 후 라우팅
        workflow.add_conditional_edges(
            "deep_agents_processing",
            self._deep_agents_route_condition,
            {
                "final": "final_synthesis",
                "rag": "rag_processing",
                "competency": "competency_diagnosis",
                "recommendation": "recommendation"
            }
        )
        
        # 일반 엣지 추가
        workflow.add_edge("competency_diagnosis", "recommendation")
        workflow.add_edge("recommendation", "final_synthesis")
        workflow.add_edge("vector_search", "external_integration")
        # Tool/action 단계 이후: 필요하면 RAG로 한 번 더 보강하고, 아니면 종료
        workflow.add_conditional_edges(
            "external_integration",
            self._post_tool_route_condition,
            {"rag": "rag_processing", "final": "final_synthesis"},
        )
        workflow.add_edge("analytics", "final_synthesis")
        workflow.add_edge("data_collection", "final_synthesis")
        workflow.add_edge("llm_manager", "final_synthesis")
        workflow.add_edge("final_synthesis", END)
        
        if getattr(self, 'checkpointer', None) is not None:
            return workflow.compile(checkpointer=self.checkpointer)
        return workflow.compile()
    
    async def _route_request(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """요청을 분석하여 적절한 워크플로우로 라우팅"""
        try:
            self.logger.info("Starting request routing")
            
            if not state.messages:
                state.add_error("처리할 메시지가 없습니다")
                return state
            
            # 최신 메시지에서 의도 분석
            latest_message = state.messages[-1]
            message_content = latest_message.content if hasattr(latest_message, 'content') else str(latest_message)
            
            # 메시지 내용이 문자열인지 확인
            if not isinstance(message_content, str):
                message_content = str(message_content)
            
            # 1) Fast Router (SLM) — 비용/레이턴시 최적화
            # 2) Hard override: deep_agents는 별도 게이트로 유지(복잡도/루프 기반)
            if self.deep_agents.should_use_deep_agents(message_content):
                state.workflow_type = "deep_agents"
                state.use_deep_agents = True
                state.routing = {"strategy": "deep_agents_gate", "confidence": 1.0}
            else:
                intent_result = await self.intent_analyzer.analyze_intent(message_content)
                intent_str = intent_result.get("intent")
                confidence = float(intent_result.get("confidence") or 0.0)
                state.routing = {
                    "strategy": "slm_intent",
                    "intent": intent_str,
                    "confidence": confidence,
                    "raw": intent_result,
                }

                if intent_str == UserIntent.COMPETENCY_ASSESSMENT.value:
                    state.workflow_type = "competency"
                elif intent_str == UserIntent.RECOMMENDATION.value:
                    state.workflow_type = "recommendation"
                elif intent_str == UserIntent.MISSION_MATCHING.value:
                    state.workflow_type = "mission"
                elif intent_str == UserIntent.SEARCH.value:
                    state.workflow_type = "search"
                elif intent_str == UserIntent.ANALYTICS.value:
                    state.workflow_type = "analytics"
                elif intent_str == UserIntent.DATA_COLLECTION.value:
                    state.workflow_type = "data_collection"
                else:
                    # Ambiguous / general: RAG 필요성 재확인
                    state.workflow_type = "rag" if self._should_use_rag(message_content) else "general"
            
            try:
                state.agent_model_config = self.settings.get_agent_config(state.workflow_type)
            except Exception:
                state.agent_model_config = None
            
            state.current_step = "routed"
            
            # 감사 추적
            state.audit_trail.append({
                'step': 'route_request',
                'workflow_type': state.workflow_type,
                'timestamp': datetime.now().isoformat(),
                'message_preview': message_content[:100]
            })
            
            self.logger.info(f"Request routed to: {state.workflow_type}")
            
        except Exception as e:
            self.logger.error(f"Request routing failed: {e}")
            state.add_error(f"요청 라우팅 실패: {str(e)}")
            state.workflow_type = "general"  # 기본값으로 설정
        
        return state

    async def _plan_request(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """
        System-2 Planner 단계.
        - 목적: 고비용 추론 모델은 "계획서(JSON)"만 만들고, 실제 답변/실행은 다음 단계에서 수행
        - 트리거: 라우팅 confidence 낮음, 멀티 인텐트/복잡 요청, RAG+툴 혼합 가능성
        """
        try:
            if not state.messages:
                return state

            latest = state.messages[-1]
            text = latest.content if hasattr(latest, "content") else str(latest)
            if not isinstance(text, str):
                text = str(text)

            routing_conf = float((state.routing or {}).get("confidence") or 0.0)

            # 매우 단순한 요청(짧고 확신 높음)은 Planner 스킵
            should_plan = False
            if state.workflow_type in ("general", "rag"):
                should_plan = True
            if routing_conf < 0.65:
                should_plan = True
            if len(text) > 200:
                should_plan = True
            if any(k in text for k in ["설계", "아키텍처", "구현", "리팩터링", "최적", "전략", "완성해줘"]):
                should_plan = True

            if not should_plan:
                state.plan = None
                return state

            system_prompt = """
You are a System-2 Planner for an agentic, compound AI system.
Create a concise execution plan ONLY in JSON (no markdown, no prose).

Output schema:
{
  "workflow_type": "general|rag|competency|recommendation|mission|search|analytics|data_collection|deep_agents",
  "needs_rag": boolean,
  "needs_tools": boolean,
  "complexity": "simple|medium|high",
  "cost_preference": "budget|balanced|performance|speed",
  "notes": "short string"
}
Rules:
- Do NOT answer the user. Only produce the plan JSON.
- Prefer low cost: routing/summary uses fast models; planning only when needed.
"""
            resp = await self.planner_engine.generate(
                prompt=f"User request:\n{text}\n\nCurrent route: {state.workflow_type}\nRouter confidence: {routing_conf}",
                system_prompt=system_prompt,
                model_name=getattr(self.planner_engine, "deep_model", None),
                temperature=0.0,
            )
            cleaned = str(resp).replace("```json", "").replace("```", "").strip()
            plan = None
            try:
                import json as _json
                plan = _json.loads(cleaned)
            except Exception:
                # 실패 시 최소 plan
                plan = {
                    "workflow_type": state.workflow_type,
                    "needs_rag": state.workflow_type == "rag",
                    "needs_tools": state.workflow_type in ("data_collection", "mission"),
                    "complexity": "high" if len(text) > 200 else "medium",
                    "cost_preference": "balanced",
                    "notes": "planner_parse_failed",
                }

            if isinstance(plan, dict):
                state.plan = plan
                # planner가 workflow_type을 더 명확히 판단했으면 반영
                wf = plan.get("workflow_type")
                if isinstance(wf, str) and wf:
                    state.workflow_type = wf
                # deep_agents는 planner가 명시했을 때만 켬
                state.use_deep_agents = state.workflow_type == "deep_agents"

                # 감사 추적
                state.audit_trail.append(
                    {
                        "step": "plan_request",
                        "timestamp": datetime.now().isoformat(),
                        "plan": plan,
                    }
                )

        except Exception as e:
            self.logger.warning("Planner step failed: %s", e)
            state.plan = None
        return state

    async def _tool_enrichment(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """
        Tool Worker 단계 (2025 Compound AI).
        - Planner의 needs_tools에 근거해 MCP enrichment를 '조건부' 수행
        - 목표: 불필요한 외부 호출 최소화 + 사고 구간(툴)을 중앙에서 통제
        """
        try:
            plan = state.plan if isinstance(state.plan, dict) else {}
            needs_tools = bool(plan.get("needs_tools", False))
            cost_pref = str(plan.get("cost_preference") or "balanced")

            # workflow 자체가 외부 데이터를 기대하는 경우엔 plan이 없어도 실행 가능
            toolish_workflows = {"mission", "analytics", "data_collection"}
            should_run = needs_tools or (state.workflow_type in toolish_workflows)

            if not should_run:
                state.tool_enrichment_result = {"ran": False, "reason": "not_needed"}
                return state

            agent_key = state.workflow_type or "general"
            ctx = self._with_agent_context(state, agent_key)
            spec = self._build_mcp_spec(agent_key, ctx)
            if not spec or not self.mcp_service:
                state.tool_enrichment_result = {"ran": False, "reason": "no_spec_or_service"}
                return state

            # More aggressive tool usage when planner asks for tools (and budget allows)
            # - ensure search_query exists to drive web_mcp
            # - increase web_limit
            try:
                latest = state.messages[-1] if state.messages else None
                user_text = latest.content if hasattr(latest, "content") else str(latest)
                if not isinstance(user_text, str):
                    user_text = str(user_text)
            except Exception:
                user_text = ""

            if needs_tools and cost_pref != "budget":
                if user_text and not spec.get("search_query"):
                    spec["search_query"] = user_text
                spec.setdefault("web_limit", 6)
                # allow caller override, but keep it within sanitize cap
                try:
                    spec["web_limit"] = max(1, min(int(spec.get("web_limit") or 6), 6))
                except Exception:
                    spec["web_limit"] = 6
                # Tool priority policy (planner-driven):
                # - speed: web + supadata parallel (best latency when both are meaningful)
                # - otherwise: supadata-first when URLs exist; web fallback
                if cost_pref == "speed":
                    spec.setdefault("tool_priority", "parallel")
                else:
                    spec.setdefault("tool_priority", "supadata_first")

            enrichment = await self.mcp_service.enrich_context(spec, ctx)

            # If planner explicitly wants tools and we have web URLs, do a 2nd pass to scrape via supadata
            # (This is the practical "tool replacement" path when raw web snippets aren't enough.)
            try:
                if needs_tools and cost_pref != "budget":
                    got_supadata = isinstance(enrichment, dict) and bool(enrichment.get("supadata"))
                    if not got_supadata:
                        urls = []
                        if isinstance(enrichment, dict):
                            urls = (
                                ((enrichment.get("external_sources") or {}).get("web") or {}).get("urls")
                                if isinstance(enrichment.get("external_sources"), dict)
                                else []
                            ) or []
                        if isinstance(urls, list) and urls:
                            sup_spec = {"supadata": {"scrape_urls": [u for u in urls if isinstance(u, str)]}}
                            sup_enrichment = await self.mcp_service.enrich_context(sup_spec, ctx)
                            if isinstance(sup_enrichment, dict) and sup_enrichment:
                                enrichment = dict(enrichment or {})
                                enrichment.update(sup_enrichment)
            except Exception:
                pass

            if enrichment:
                ctx.update(enrichment)
                ctx.setdefault("mcp_enrichment", {}).update(enrichment)
                state.context.update({k: v for k, v in ctx.items() if k != "messages"})

            state.tool_enrichment_result = {
                "ran": True,
                "agent_key": agent_key,
                "needs_tools": needs_tools,
                "cost_preference": cost_pref,
                "timestamp": datetime.now().isoformat(),
                "enriched_keys": sorted(list(enrichment.keys())) if isinstance(enrichment, dict) else [],
            }
            state.audit_trail.append(
                {
                    "step": "tool_enrichment",
                    "timestamp": datetime.now().isoformat(),
                    "agent_key": agent_key,
                    "needs_tools": needs_tools,
                    "enriched_keys": state.tool_enrichment_result.get("enriched_keys", []),
                }
            )
            return state

        except Exception as e:
            self.logger.warning("Tool enrichment failed: %s", e)
            state.tool_enrichment_result = {"ran": False, "reason": "error", "error": str(e)}
            return state

    def _post_tool_enrichment_condition(self, state: MainOrchestratorState) -> str:
        """
        Tool Worker 이후 라우팅.
        - tool이 필요했는데 실패한 경우: replan으로 복구(최대 N회)
        - 그 외: planner가 정한 workflow_type으로 진행
        """
        try:
            plan = state.plan if isinstance(state.plan, dict) else {}
            needs_tools = bool(plan.get("needs_tools", False))
            te = state.tool_enrichment_result if isinstance(state.tool_enrichment_result, dict) else {}
            ran = bool(te.get("ran", False))
            reason = str(te.get("reason") or "")

            # Tool이 필요하다고 판단했는데 tool_enrichment가 실패/불가면 replan
            if needs_tools and (not ran) and reason in ("error", "no_spec_or_service"):
                if state.loop_count < state.max_loops:
                    state.loop_count += 1
                    state.workflow_type = state.workflow_type or "general"
                    return "replan"

            return self._route_condition(state)
        except Exception:
            return self._route_condition(state)

    async def _replan_request(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """
        Replan 단계:
        - Tool이 실패했거나 사용 불가할 때, 플랜을 수정해서 '툴 없이 진행' 또는 'RAG 대체'로 전환
        - RAG 결과가 빈약/불확실할 때, 플랜을 수정해서 '추가 검색/다른 소스/tool 대체'로 전환
        - 출력은 plan JSON(기존 _plan_request 스키마 준수)
        """
        try:
            if not state.messages:
                return state

            latest = state.messages[-1]
            text = latest.content if hasattr(latest, "content") else str(latest)
            if not isinstance(text, str):
                text = str(text)

            prev_plan = state.plan if isinstance(state.plan, dict) else {}
            tool_state = state.tool_enrichment_result if isinstance(state.tool_enrichment_result, dict) else {}
            routing = state.routing if isinstance(state.routing, dict) else {}
            rag_state = state.rag_result if isinstance(state.rag_result, dict) else {}
            retrieved_count = len(state.retrieved_documents or [])
            rag_answer = ""
            try:
                ra = rag_state.get("response")
                if isinstance(ra, str):
                    rag_answer = ra[:500]
            except Exception:
                rag_answer = ""

            system_prompt = """
You are a System-2 Planner for an agentic, compound AI system.
You MUST update the plan based on tool execution constraints.

Output JSON only (no markdown, no prose).

Output schema:
{
  "workflow_type": "general|rag|competency|recommendation|mission|search|analytics|data_collection|deep_agents",
  "needs_rag": boolean,
  "needs_tools": boolean,
  "complexity": "simple|medium|high",
  "cost_preference": "budget|balanced|performance|speed",
  "notes": "short string"
}

Rules:
- If tools are failing/unavailable, set needs_tools=false and prefer needs_rag=true if knowledge/context is needed.
- If RAG answer is weak/uncertain, prefer:
  (a) workflow_type="search" or "rag" with needs_rag=true and/or
  (b) enabling needs_tools=true to fetch external context (web/supadata/youtube), but only if cost is justified.
- Do NOT answer the user. Only produce the plan JSON.
"""

            resp = await self.planner_engine.generate(
                prompt=(
                    "User request:\n"
                    + text
                    + "\n\nRouter:\n"
                    + str(routing)
                    + "\n\nPrevious plan:\n"
                    + str(prev_plan)
                    + "\n\nRAG status:\n"
                    + f"retrieved_docs_count={retrieved_count}\n"
                    + "rag_answer_preview:\n"
                    + rag_answer
                    + "\n\nTool enrichment result:\n"
                    + str(tool_state)
                ),
                system_prompt=system_prompt,
                model_name=getattr(self.planner_engine, "deep_model", None),
                temperature=0.0,
            )

            cleaned = str(resp).replace("```json", "").replace("```", "").strip()
            import json as _json
            try:
                plan = _json.loads(cleaned)
            except Exception:
                plan = dict(prev_plan or {})
                plan.setdefault("notes", "replan_parse_failed")
                # 최소 안전: tool 실패 시 tools off + rag on
                if not plan:
                    plan = {
                        "workflow_type": state.workflow_type or "rag",
                        "needs_rag": True,
                        "needs_tools": False,
                        "complexity": "medium",
                        "cost_preference": "balanced",
                        "notes": "replan_fallback",
                    }
                else:
                    plan["needs_tools"] = False
                    plan["needs_rag"] = True

            if isinstance(plan, dict):
                # Policy hardening:
                # - If planner chose "search", we ALWAYS want downstream RAG re-entry enabled.
                #   (search -> external_integration -> rag loop is guarded by needs_rag)
                try:
                    wf_val = plan.get("workflow_type")
                    if isinstance(wf_val, str) and wf_val == "search":
                        plan["needs_rag"] = True
                except Exception:
                    pass

                state.plan = plan
                wf = plan.get("workflow_type")
                if isinstance(wf, str) and wf:
                    state.workflow_type = wf

                # Replan이 "재실행"을 의도한 경우, 기존 RAG 결과를 리셋해서
                # search -> external_integration -> rag 재실행 경로가 실제로 동작하게 한다.
                try:
                    needs_rag = bool(plan.get("needs_rag", False))
                    if needs_rag and state.rag_result:
                        state.rag_result = None
                        state.retrieved_documents = []
                        state.rag_context = None
                except Exception:
                    pass

                state.replan_result = {
                    "ran": True,
                    "timestamp": datetime.now().isoformat(),
                    "loop_count": state.loop_count,
                    "tool_enrichment": tool_state,
                }
                state.audit_trail.append(
                    {
                        "step": "replan_request",
                        "timestamp": datetime.now().isoformat(),
                        "plan": plan,
                        "loop_count": state.loop_count,
                    }
                )

        except Exception as e:
            self.logger.warning("Replan step failed: %s", e)
            state.replan_result = {"ran": False, "error": str(e)}
        return state
    
    def _route_condition(self, state: MainOrchestratorState) -> str:
        """라우팅 조건 결정"""
        return state.workflow_type
    
    
    async def _deep_agents_processing(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """Deep Agents 처리"""
        try:
            self.logger.info("Starting Deep Agents processing")
            
            # 최신 메시지에서 쿼리 추출
            latest_message = state.messages[-1]
            if hasattr(latest_message, 'content'):
                query = str(latest_message.content)
            else:
                query = str(latest_message)
            
            # 통합 Deep Agents 실행
            deep_agents_result = await self.deep_agents.execute(query)
            
            # 결과 저장
            state.deep_agents_result = deep_agents_result
            state.use_deep_agents = True
            
            # 성능 메트릭 업데이트
            state.performance_metrics['deep_agents'] = {
                'success': deep_agents_result.get('success', False),
                'iterations': deep_agents_result.get('iterations', 0),
                'quality_score': deep_agents_result.get('quality_score', 0.0),
                'processing_time': deep_agents_result.get('result', {}).get('metadata', {}).get('processing_time', 0)
            }
            
            # 감사 추적
            state.audit_trail.append({
                'step': 'deep_agents_processing',
                'success': deep_agents_result.get('success', False),
                'iterations': deep_agents_result.get('iterations', 0),
                'quality_score': deep_agents_result.get('quality_score', 0.0),
                'timestamp': datetime.now().isoformat()
            })
            
            self.logger.info(f"Deep Agents processing completed: {deep_agents_result.get('success', False)}")
            
        except Exception as e:
            self.logger.error(f"Deep Agents processing failed: {e}")
            state.add_error(f"Deep Agents 처리 오류: {str(e)}")
            state.deep_agents_result = {'success': False, 'error': str(e)}
        
        return state
    
    def _deep_agents_route_condition(self, state: MainOrchestratorState) -> str:
        """Deep Agents 처리 후 라우팅 조건"""
        if not state.deep_agents_result or not state.deep_agents_result.get('success', False):
            return "final"  # 실패 시 최종 합성으로
        
        # Deep Agents 결과에 따라 추가 처리 결정
        result = state.deep_agents_result.get('result', {})
        metadata = result.get('metadata', {})
        
        # 추가 RAG 처리 필요 여부
        if metadata.get('needs_rag', False):
            return "rag"
        
        # 역량진단 필요 여부
        if metadata.get('needs_competency', False):
            return "competency"
        
        # 추천 필요 여부
        if metadata.get('needs_recommendation', False):
            return "recommendation"
        
        # 완료된 경우 최종 합성
        return "final"
    
    async def _manage_llm(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """LLM 관리 및 선택"""
        try:
            self.logger.info("Managing LLM selection")
            
            # LLM Manager 상태 생성
            agent_key = state.workflow_type or "general"
            llm_state = LLMManagerState(
                user_id=state.user_id,
                session_id=state.session_id,
                task_type=state.workflow_type,
                messages=list(state.messages),
                context=self._with_agent_context(state, agent_key),
            )
            
            # LLM Manager 실행
            llm_result = await self.llm_manager.execute(llm_state)
            
            # 결과 상태에 반영
            state.llm_manager_state = llm_result
            state.selected_llm_model = llm_result.selected_model
            state.context.update(llm_result.context)
            
            # 성능 메트릭 업데이트
            state.performance_metrics['llm_selection'] = {
                'selected_model': llm_result.selected_model,
                'selection_reason': llm_result.model_selection_reason,
                'execution_time': llm_result.context.get('execution_time', 0)
            }
            
            state.current_step = "llm_managed"
            
        except Exception as e:
            self.logger.error(f"LLM management failed: {e}")
            state.add_error(f"LLM 관리 실패: {str(e)}")
        
        return state
    
    async def _competency_diagnosis(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """역량진단 처리 (DER-001)"""
        try:
            self.logger.info("Processing competency diagnosis")
            
            # Competency Agent 실행
            competency_state = CompetencyDiagnosisState(
                user_id=state.user_id,
                session_id=state.session_id,
                context=self._with_agent_context(state, "competency"),
            )
            
            result = await self.competency_agent.execute(competency_state)
            
            # 결과 저장
            state.competency_data = {
                'analysis_result': result.analysis_result,
                'recommendations': result.recommendations,
                'assessment_id': result.assessment_id
            }
            
            state.current_step = "competency_completed"
            
        except Exception as e:
            self.logger.error(f"Competency diagnosis failed: {e}")
            state.add_error(f"역량진단 처리 실패: {str(e)}")
        
        return state
    
    async def _generate_recommendations(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """맞춤형 추천 생성 (DER-002)"""
        try:
            self.logger.info("Generating personalized recommendations")
            
            # 추천 에이전트 실행
            recommendation_state = RecommendationState(
                user_id=state.user_id,
                session_id=state.session_id,
                user_profile=state.competency_data,
                learning_preferences=state.context.get('learning_preferences', {}),
                competency_data=state.competency_data,
                context=self._with_agent_context(state, "recommendation"),
            )
            
            recommendation_result = await self.recommendation_agent.execute(recommendation_state)
            
            state.recommendation_data = {
                'recommendations': getattr(recommendation_result, 'recommendations', []),
                'reasoning': getattr(recommendation_result, 'reasoning', '')
            }
            state.current_step = "recommendations_generated"
            
        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {e}")
            state.add_error(f"추천 생성 실패: {str(e)}")
        
        return state

    async def _mission_recommendation(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """크리에이터-미션 매칭 추천 (Mission v0.1)"""
        try:
            self.logger.info("Generating mission recommendations")

            ctx = await self._prepare_agent_context(state, "mission")
            # creator_profile / onboarding_result / mission_list는 상위 레이어(API 등)에서 채워 넣는 것을 기대
            creator_profile = ctx.get("creator_profile", {})
            onboarding_result = ctx.get("onboarding_result", {})
            missions_data = ctx.get("missions", [])

            missions: List[Mission] = []

            for m in missions_data:
                try:
                    missions.append(Mission(**m))  # type: ignore[arg-type]
                except Exception as exc:
                    self.logger.warning(f"Invalid mission payload skipped: {exc}")

            mission_state = MissionRecommendationState(
                user_id=state.user_id,
                session_id=state.session_id,
                context=ctx,
                creator_id=str(creator_profile.get("creator_id") or creator_profile.get("id") or ""),
                creator_profile=creator_profile,
                onboarding_result=onboarding_result,
                missions=missions,  # type: ignore[list-item]
            )

            mission_state = await self.mission_agent.execute(mission_state)

            # 상태에 추천 결과 반영 (직렬화-friendly dict 형태)
            state.mission_recommendations = [
                ma.model_dump() for ma in mission_state.recommendations
            ]
            state.current_step = "mission_recommendations_generated"
        except Exception as e:
            self.logger.error(f"Mission recommendation failed: {e}")
            state.add_error(f"미션 추천 실패: {str(e)}")

        return state
    
    async def _vector_search(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """벡터 검색 처리 (DER-003)"""
        try:
            self.logger.info("Processing vector search")
            
            # 검색 쿼리 추출
            search_query = self._extract_search_query(state.messages)
            
            # 검색 에이전트 실행
            search_state = SearchState(
                user_id=state.user_id,
                session_id=state.session_id,
                query=search_query,
                context=self._with_agent_context(state, "search"),
            )
            
            search_result = await self.search_agent.execute(search_state)
            
            state.search_results = getattr(search_result, 'search_results', [])
            state.current_step = "search_completed"
            
        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            state.add_error(f"벡터 검색 실패: {str(e)}")
        
        return state
    
    async def _external_integration(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """외부 API 연동 처리 (DER-004)"""
        try:
            self.logger.info("Processing external API integration")
            
            # 통합 에이전트 실행
            integration_state = IntegrationState(
                user_id=state.user_id,
                session_id=state.session_id,
                context=self._with_agent_context(state, "integration"),
            )
            
            integration_result = await self.integration_agent.execute(integration_state)
            
            state.external_api_results = getattr(integration_result, 'integration_results', {})
            state.current_step = "integration_completed"
            
        except Exception as e:
            self.logger.error(f"External integration failed: {e}")
            state.add_error(f"외부 API 연동 실패: {str(e)}")
        
        return state

    def _post_tool_route_condition(self, state: MainOrchestratorState) -> str:
        """Tool/Integration 이후 후속 라우팅(Loop-safe)."""
        try:
            plan = state.plan if isinstance(state.plan, dict) else {}
            needs_rag = bool(plan.get("needs_rag", False))
            if needs_rag and state.loop_count < state.max_loops:
                # 이미 RAG 결과가 없을 때만 재진입 (무한루프 방지)
                if not state.rag_result:
                    state.loop_count += 1
                    state.workflow_type = "rag"
                    return "rag"
            return "final"
        except Exception:
            return "final"
    
    async def _analytics_processing(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """분석 처리 (DER-005, DER-007)"""
        try:
            self.logger.info("Processing analytics")
            # 분석 에이전트 실행
            ctx = await self._prepare_agent_context(state, "analytics")
            analytics_state = AnalyticsState(
                user_id=state.user_id,
                session_id=state.session_id,
                # API / 상위 컨텍스트에서 전달된 리포트 타입/기간을 그대로 반영
                report_type=ctx.get('report_type'),
                date_range=ctx.get('date_range', {}),
                context=ctx,
            )
            
            analytics_result = await self.analytics_agent.execute(analytics_state)
            
            state.analytics_results = {
                "analysis": getattr(analytics_result, "analysis", {}),
                "metrics": getattr(analytics_result, "metrics", {}),
                "insights": getattr(analytics_result, "insights", []),
                "recommendations": getattr(analytics_result, "recommendations", []),
                "external_data": getattr(analytics_result, "external_data", {}),
                "youtube_insights": getattr(analytics_result, "youtube_insights", {}),
            }
            state.current_step = "analytics_completed"
            
        except Exception as e:
            self.logger.error(f"Analytics processing failed: {e}")
            state.add_error(f"분석 처리 실패: {str(e)}")
        
        return state
    
    async def _final_synthesis(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """최종 결과 종합"""
        try:
            self.logger.info("Synthesizing final results")
            
            # 모든 결과 종합
            final_response = await self._synthesize_results(state)
            
            # 최종 응답 메시지 생성
            response_message = AIMessage(content=final_response)
            state.messages = list(state.messages) + [response_message]
            
            # 최종 성능 메트릭
            if state.audit_trail and len(state.audit_trail) > 0:
                state.performance_metrics['total_execution_time'] = (
                    datetime.now() - datetime.fromisoformat(state.audit_trail[0]['timestamp'])
                ).total_seconds()
            else:
                state.performance_metrics['total_execution_time'] = 0
            
            state.current_step = "completed"
            
            # 감사 추적 완료
            state.audit_trail.append({
                'step': 'final_synthesis',
                'status': 'completed',
                'timestamp': datetime.now().isoformat(),
                'total_steps': len(state.audit_trail)
            })
            
        except Exception as e:
            self.logger.error(f"Final synthesis failed: {e}")
            state.add_error(f"최종 결과 종합 실패: {str(e)}")
        
        return state
    
    async def _synthesize_results(self, state: MainOrchestratorState) -> str:
        """모든 결과를 종합하여 최종 응답 생성 (Compound 시스템용)."""
        # 1) RAG 결과만으로 충분한 케이스는 그대로 반환(중복 합성 방지)
        if state.rag_result and isinstance(state.rag_result, dict):
            resp = state.rag_result.get("response")
            if isinstance(resp, str) and resp.strip() and not any(
                [
                    state.competency_data,
                    state.recommendation_data,
                    state.analytics_results,
                    state.mission_recommendations,
                    state.collected_data,
                ]
            ):
                return resp.strip()

        # 2) 가능한 경우: 선택된 모델로 "최종 답변" 생성
        try:
            latest = state.messages[-1] if state.messages else None
            user_text = latest.content if hasattr(latest, "content") else str(latest)
            if not isinstance(user_text, str):
                user_text = str(user_text)

            plan = state.plan if isinstance(state.plan, dict) else {}
            routing = state.routing if isinstance(state.routing, dict) else {}

            payload: Dict[str, Any] = {
                "routing": routing,
                "plan": plan,
                "competency": state.competency_data,
                "recommendation": state.recommendation_data,
                "missions": state.mission_recommendations[:5]
                if isinstance(state.mission_recommendations, list)
                else state.mission_recommendations,
                "analytics": state.analytics_results,
                "search_results_count": len(state.search_results or []),
                "external_api_results": state.external_api_results,
                "data_collection_count": len(state.collected_data or []),
                "rag": {
                    "retrieved_docs_count": len(state.retrieved_documents or []),
                    "answer": (state.rag_result or {}).get("response")
                    if isinstance(state.rag_result, dict)
                    else None,
                },
            }

            import json as _json

            system_prompt = """
You are the Final Synthesizer for a compound AI system.
Write the final user-facing answer in Korean.

Rules:
- Use the provided results; do not fabricate.
- If RAG answer exists, incorporate it.
- If some parts are missing, say what is missing and what to do next.
- Keep it structured with clear headings and bullet points.
"""
            model = state.selected_llm_model or self.settings.DEFAULT_LLM_MODEL
            return await self.rag_pipeline.generation_engine.generate(
                prompt=(
                    "User request:\n"
                    + user_text
                    + "\n\nSystem outputs(JSON):\n"
                    + _json.dumps(payload, ensure_ascii=False)
                ),
                system_prompt=system_prompt,
                model_name=model,
                temperature=0.2,
            )
        except Exception:
            # 3) 최후 폴백: 텍스트 요약
            parts: List[str] = []
            if state.rag_result and isinstance(state.rag_result, dict) and isinstance(
                state.rag_result.get("response"), str
            ):
                parts.append(str(state.rag_result.get("response")))
            if state.competency_data:
                parts.append(f"역량진단 분석: {state.competency_data}")
            if state.recommendation_data:
                parts.append(f"맞춤형 추천: {state.recommendation_data}")
            if state.analytics_results:
                parts.append(f"분석 리포트: {state.analytics_results}")
            if state.mission_recommendations:
                parts.append(f"미션 추천: {len(state.mission_recommendations)}개")
            if state.selected_llm_model:
                parts.append(f"사용된 LLM: {state.selected_llm_model}")
            return "\n\n".join([p for p in parts if p]) if parts else "처리가 완료되었습니다."
    
    async def _data_collection(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """데이터 수집 처리"""
        try:
            # 데이터 수집 상태 초기화
            ctx = self._with_agent_context(state, "data_collection")
            collection_state = DataCollectionState(
                collection_id=f"collection_{state.session_id}_{datetime.now().timestamp()}",
                source_type=ctx.get('source_type'),
                collection_config=ctx.get('collection_config'),
                user_id=state.user_id,
                session_id=state.session_id,
                context=ctx,
            )
            
            # 데이터 수집 에이전트 실행
            collection_state = await self.data_collection_agent.execute(collection_state)
            
            # 결과를 메인 상태에 저장
            state.data_collection_state = collection_state
            state.collected_data = getattr(collection_state, 'processed_items', [])
            
            # 성능 메트릭 업데이트
            end_time = getattr(collection_state, 'end_time', None)
            start_time = getattr(collection_state, 'start_time', None)
            collection_time = 0
            if end_time and start_time:
                try:
                    collection_time = (end_time - start_time).total_seconds()
                except (TypeError, AttributeError):
                    collection_time = 0
            
            state.performance_metrics.update({
                'data_collection_time': collection_time,
                'collected_items': getattr(collection_state, 'success_count', 0),
                'failed_items': getattr(collection_state, 'error_count', 0)
            })
            
            # 감사 로그 추가
            state.audit_trail.append({
                'timestamp': datetime.now().isoformat(),
                'action': 'data_collection',
                'status': collection_state.collection_status.value,
                'items_collected': collection_state.success_count,
                'items_failed': collection_state.error_count
            })
            
        except Exception as e:
            self.logger.error(f"Data collection failed: {e}")
            state.add_error(f"데이터 수집 실패: {str(e)}")
            
        return state
    
    def _extract_search_query(self, messages: Sequence[BaseMessage]) -> str:
        """메시지에서 검색 쿼리 추출"""
        if messages:
            latest_message = messages[-1]
            content = latest_message.content if hasattr(latest_message, 'content') else str(latest_message)
            return str(content) if content else ""
        return ""
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """메인 오케스트레이터 실행 (영속적 저장)"""
        try:
            # 초기 상태 설정
            initial_state = MainOrchestratorState(
                messages=[HumanMessage(content=input_data.get('message', ''))],
                user_id=input_data.get('user_id'),
                session_id=input_data.get('session_id'),
                context=input_data.get('context', {}),
                security_level=input_data.get('security_level', 'standard')
            )
            
            # 영속적 저장을 위한 설정
            thread_id = input_data.get('session_id', f"session_{datetime.now().timestamp()}")
            config = {"configurable": {"thread_id": thread_id}}
            
            # 그래프 실행 (상태가 자동으로 SQLite에 저장됨)
            result = await self.graph.ainvoke(initial_state, config)
            
            # 현재 상태 조회 (저장된 상태 확인)
            current_state = self.graph.get_state(config)
            
            return {
                'success': True,
                'response': result.messages[-1].content if result.messages else None,
                'workflow_type': result.workflow_type,
                'performance_metrics': result.performance_metrics,
                'audit_trail': result.audit_trail,
                'errors': result.errors,
                'thread_id': thread_id,
                'state_saved': current_state is not None,
                # 미션 추천 결과를 API에서 바로 사용할 수 있도록 노출
                'mission_recommendations': getattr(result, 'mission_recommendations', []),
            }
            
        except Exception as e:
            self.logger.error(f"Main orchestrator execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': None
            }

    def _should_use_rag(self, message_content: str) -> bool:
        """RAG 사용 여부 판단"""
        try:
            # 복잡한 질문이나 컨텍스트가 필요한 경우 RAG 사용
            rag_indicators = [
                '어떻게', '왜', '무엇을', '언제', '어디서',  # 질문어
                '설명해주세요', '알려주세요', '도와주세요',  # 요청어
                '관련', '정보', '자료', '내용',  # 정보 요청
                '최신', '현재', '최근',  # 최신 정보 요청
                '정책', '제도', '법률', '규정'  # 정책 관련
            ]
            
            message_lower = message_content.lower()
            
            # 질문어나 요청어가 포함된 경우
            if any(indicator in message_lower for indicator in rag_indicators):
                return True
            
            # 긴 문장이나 복잡한 질문의 경우
            if len(message_content.split()) > 10:
                return True
            
            # 특정 도메인 키워드가 포함된 경우
            domain_keywords = ['육아', '아동', '부모', '교육', '정책', '발달']
            if any(keyword in message_lower for keyword in domain_keywords):
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"RAG usage decision failed: {e}")
            return False
    
    async def _rag_processing(self, state: MainOrchestratorState) -> MainOrchestratorState:
        """RAG 처리"""
        try:
            self.logger.info("Starting RAG processing")
            
            if not state.messages:
                state.add_error("처리할 메시지가 없습니다")
                return state
            
            # 최신 메시지 추출
            latest_message = state.messages[-1]
            message_content = latest_message.content if hasattr(latest_message, 'content') else str(latest_message)
            
            # 쿼리 타입 결정
            query_type = self._determine_query_type(str(message_content))
            
            # 사용자 컨텍스트 준비
            rag_ctx = self._with_agent_context(state, "rag")
            user_context = {
                'user_id': state.user_id,
                'session_id': state.session_id,
                'competency_level': state.competency_data.get('level') if state.competency_data else None,
                'interests': rag_ctx.get('interests', []),
                'learning_style': rag_ctx.get('learning_style', 'balanced'),
                'agent_model_config': rag_ctx.get('agent_model_config'),
            }
            
            # 대화 히스토리 준비
            conversation_history = []
            for msg in state.messages[:-1]:  # 마지막 메시지 제외
                if hasattr(msg, 'content'):
                    role = 'assistant' if isinstance(msg, AIMessage) else 'user'
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    conversation_history.append({
                        'role': role,
                        'content': content
                    })
            
            # RAG 파이프라인 실행
            rag_result = await self.rag_pipeline.process_query(
                query=str(message_content),
                query_type=query_type,
                user_context=user_context,
                conversation_history=conversation_history
            )
            
            if rag_result.get('success', False):
                # RAG 결과를 상태에 저장
                state.rag_result = rag_result
                state.retrieved_documents = rag_result.get('retrieved_documents', [])
                state.rag_context = rag_result.get('context', {})
                
                # 후속 워크플로우 결정
                state.workflow_type = self._determine_post_rag_workflow(rag_result, str(message_content))
                state.current_step = "rag_processed"
                
                # 감사 추적
                state.audit_trail.append({
                    "step": "rag_processing",
                    "timestamp": datetime.now().isoformat(),
                    "query_type": query_type.value,
                    "retrieved_docs": len(state.retrieved_documents),
                    "processing_time": rag_result.get('processing_time', 0)
                })
                
            else:
                state.add_error(f"RAG 처리 실패: {rag_result.get('error', 'Unknown error')}")
            
        except Exception as e:
            self.logger.error(f"RAG processing failed: {e}")
            state.add_error(f"RAG 처리 중 오류: {str(e)}")
        
        return state
    
    def _determine_query_type(self, message_content: str) -> PromptType:
        """쿼리 타입 결정"""
        try:
            message_lower = message_content.lower()
            
            # 역량 관련
            if any(keyword in message_lower for keyword in ['역량', '진단', '평가', '수준', '능력']):
                return PromptType.COMPETENCY_ASSESSMENT
            
            # 추천 관련
            elif any(keyword in message_lower for keyword in ['추천', '학습자료', '과정', '프로그램']):
                return PromptType.RECOMMENDATION
            
            # 검색 관련
            elif any(keyword in message_lower for keyword in ['검색', '찾기', '정보', '자료']):
                return PromptType.SEARCH
            
            # 분석 관련
            elif any(keyword in message_lower for keyword in ['분석', '리포트', '통계', '성과']):
                return PromptType.ANALYTICS
            
            # 데이터 수집 관련
            elif any(keyword in message_lower for keyword in ['수집', '데이터', 'API', '외부']):
                return PromptType.DATA_COLLECTION
            
            # 일반 대화
            else:
                return PromptType.GENERAL_CHAT
                
        except Exception as e:
            self.logger.error(f"Query type determination failed: {e}")
            return PromptType.GENERAL_CHAT
    
    def _determine_post_rag_workflow(self, rag_result: Dict[str, Any], message_content: str) -> str:
        """RAG 처리 후 워크플로우 결정"""
        try:
            # RAG 결과에 따른 후속 처리 결정
            retrieved_docs = rag_result.get('retrieved_documents', [])
            
            # 검색된 문서가 특정 타입인 경우
            for doc in retrieved_docs:
                metadata = doc.get('metadata', {})
                category = metadata.get('category', '')
                
                if category == 'parenting':
                    return 'competency'
                elif category == 'policy':
                    return 'analytics'
                elif category == 'education':
                    return 'recommendation'
            
            # 메시지 내용에 따른 결정
            message_lower = message_content.lower()
            if any(keyword in message_lower for keyword in ['역량', '진단']):
                return 'competency'
            elif any(keyword in message_lower for keyword in ['추천', '학습']):
                return 'recommendation'
            elif any(keyword in message_lower for keyword in ['분석', '리포트']):
                return 'analytics'
            
            # 기본적으로 최종 합성으로
            return 'final'
            
        except Exception as e:
            self.logger.error(f"Post-RAG workflow determination failed: {e}")
            return 'final'
    
    def _rag_route_condition(self, state: MainOrchestratorState) -> str:
        """RAG 처리 후 라우팅 조건"""
        try:
            # RAG answer quality gate:
            # If answer is weak/uncertain, run System-2 replan (loop-safe) to decide:
            # - additional search
            # - tool enrichment
            # - alternate workflow
            if self._should_replan_after_rag(state) and state.loop_count < state.max_loops:
                state.loop_count += 1
                state.audit_trail.append(
                    {
                        "step": "rag_quality_gate",
                        "timestamp": datetime.now().isoformat(),
                        "decision": "replan",
                        "loop_count": state.loop_count,
                    }
                )
                return "replan"
            return state.workflow_type
        except Exception:
            return state.workflow_type

    def _should_replan_after_rag(self, state: MainOrchestratorState) -> bool:
        """RAG 결과가 빈약/불확실하면 replan 트리거."""
        try:
            if not state.rag_result or not isinstance(state.rag_result, dict):
                return False

            resp = state.rag_result.get("response")
            text = resp if isinstance(resp, str) else ""
            text_stripped = text.strip()

            retrieved_count = len(state.retrieved_documents or [])

            # Hard signals: no docs or empty answer
            if retrieved_count == 0:
                return True
            if not text_stripped:
                return True

            # Weak answer heuristics (Korean uncertainty patterns)
            lowered = text_stripped.lower()
            uncertainty_markers = [
                "잘 모르", "알 수 없", "확인할 수 없", "찾을 수 없", "제공된 문서",
                "근거가 없", "정보가 없", "추가 정보", "확실하지", "추정",
                "cannot", "unknown", "not sure", "insufficient",
            ]
            if any(m in lowered for m in uncertainty_markers):
                return True

            # Very short answer with many docs usually indicates low-quality synthesis
            if len(text_stripped) < 120 and retrieved_count >= 2:
                return True

            return False
        except Exception:
            return False
    
    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 상태 조회"""
        try:
            config = {"configurable": {"thread_id": session_id}}
            state = self.graph.get_state(config)
            
            if state and state.values:
                return {
                    'session_id': session_id,
                    'current_step': state.values.get('current_step', ''),
                    'workflow_type': state.values.get('workflow_type', ''),
                    'messages_count': len(state.values.get('messages', [])),
                    'performance_metrics': state.values.get('performance_metrics', {}),
                    'audit_trail_count': len(state.values.get('audit_trail', [])),
                    'errors_count': len(state.values.get('errors', [])),
                    'last_updated': state.config.get('configurable', {}).get('thread_id', ''),
                    'state_exists': True
                }
            else:
                return {
                    'session_id': session_id,
                    'state_exists': False
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get session state: {e}")
            return None
    
    async def resume_session(self, session_id: str, new_message: str) -> Dict[str, Any]:
        """세션 복원 및 계속 실행"""
        try:
            config = {"configurable": {"thread_id": session_id}}
            
            # 기존 상태 조회
            current_state = self.graph.get_state(config)
            
            if not current_state or not current_state.values:
                return {
                    'success': False,
                    'error': 'Session not found',
                    'response': None
                }
            
            # 새 메시지 추가
            new_message_obj = HumanMessage(content=new_message)
            updated_messages = list(current_state.values.get('messages', [])) + [new_message_obj]
            
            # 상태 업데이트
            updated_state = MainOrchestratorState(
                messages=updated_messages,
                user_id=current_state.values.get('user_id'),
                session_id=session_id,
                context=current_state.values.get('context', {}),
                security_level=current_state.values.get('security_level', 'standard'),
                competency_data=current_state.values.get('competency_data'),
                recommendation_data=current_state.values.get('recommendation_data'),
                search_results=current_state.values.get('search_results', []),
                analytics_results=current_state.values.get('analytics_results'),
                external_api_results=current_state.values.get('external_api_results', {}),
                llm_manager_state=current_state.values.get('llm_manager_state'),
                selected_llm_model=current_state.values.get('selected_llm_model'),
                data_collection_state=current_state.values.get('data_collection_state'),
                collected_data=current_state.values.get('collected_data', []),
                rag_result=current_state.values.get('rag_result'),
                retrieved_documents=current_state.values.get('retrieved_documents', []),
                rag_context=current_state.values.get('rag_context'),
                performance_metrics=current_state.values.get('performance_metrics', {}),
                audit_trail=current_state.values.get('audit_trail', []),
                errors=current_state.values.get('errors', [])
            )
            
            # 그래프 재실행
            result = await self.graph.ainvoke(updated_state, config)
            
            return {
                'success': True,
                'response': result.messages[-1].content if result.messages else None,
                'workflow_type': result.workflow_type,
                'performance_metrics': result.performance_metrics,
                'audit_trail': result.audit_trail,
                'errors': result.errors,
                'thread_id': session_id,
                'resumed': True
            }
            
        except Exception as e:
            self.logger.error(f"Session resume failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': None
            }
    
    async def clear_session(self, session_id: str) -> bool:
        """세션 상태 삭제"""
        try:
            # Redis/SQLite 등 체크포인터에 저장된 상태를 삭제
            # 1) SqliteSaver 기반일 경우 내부 DB에서 thread_id 기준 삭제 시도
            if getattr(self, 'checkpointer', None) is None:
                self.logger.warning("No checkpointer configured; nothing to clear")
                return False

            # 우선 SqliteSaver가 제공하는 delete/clear API가 있으면 사용
            try:
                deleter = getattr(self.checkpointer, 'delete', None)
                if callable(deleter):
                    # 일부 구현은 dict 컨피그를 인수로 받음
                    deleter({"configurable": {"thread_id": session_id}})  # type: ignore[misc]
                    self.logger.info(f"Cleared session via checkpointer API: {session_id}")
                    return True
            except Exception:
                # 아래 로우 SQL 경로로 폴백
                pass

            # 로우 SQL 경로 (테이블 존재 시 삭제)
            conn = getattr(self, '_checkpoint_conn', None)
            if conn is None:
                self.logger.info(f"Checkpointer connection not available; marking session cleared: {session_id}")
                return True

            cur = conn.cursor()
            deleted = 0
            for table in ("checkpoints", "checkpoint_blobs", "writes"):
                try:
                    cur.execute(f"DELETE FROM {table} WHERE thread_id = ?", (session_id,))
                    deleted += cur.rowcount if cur.rowcount is not None else 0
                except Exception:
                    # 테이블이 없거나 스키마가 다른 경우 무시
                    continue
            try:
                conn.commit()
            except Exception:
                pass
            self.logger.info(f"Session {session_id} cleared from checkpointer (rows: {deleted})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear session: {e}")
            return False


# 전역 오케스트레이터 인스턴스
orchestrator = None


def get_orchestrator(config: Optional[Dict[str, Any]] = None) -> MainOrchestrator:
    """오케스트레이터 싱글톤 인스턴스 반환"""
    global orchestrator
    if orchestrator is None:
        orchestrator = MainOrchestrator(config)
    return orchestrator