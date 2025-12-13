"""RAG 파이프라인 구현"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .prompt_templates import PromptTemplates, PromptType
from .document_processor import DocumentProcessor
from .retrieval_engine import RetrievalEngine
from .generation_engine import GenerationEngine
from .context_builder import ContextPromptBuilder
from .response_refiner import ResponseRefiner
from .query_expander import QueryExpander
from .semantic_cache import SemanticCache
from .prompt_optimizer import PromptOptimizer
from .llm_manager import LLMManager
from ..services.mcp_integration import get_mcp_service

try:
    from ..monitoring.langfuse import LangfuseIntegration  # type: ignore
except Exception:
    LangfuseIntegration = None  # type: ignore

logger = logging.getLogger(__name__)


class RAGPipeline:
    """최신 RAG 파이프라인"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("RAGPipeline")
        
        # 컴포넌트 초기화
        self.prompt_templates = PromptTemplates()
        self.document_processor = DocumentProcessor(self.config.get('document_processor', {}))

        retrieval_config = dict(self.config.get('retrieval', {}))
        embedding_model = self.config.get('embedding_model')
        vector_db = self.config.get('vector_db')
        if embedding_model:
            retrieval_config.setdefault('embedding_model', embedding_model)
        if vector_db:
            retrieval_config.setdefault('vector_db', vector_db)
        # 2025: GraphRAG-lite is a practical default (can be disabled via config)
        retrieval_config.setdefault("graph_enabled", True)
        retrieval_config.setdefault("graph_weight", float(retrieval_config.get("graph_weight", 0.3)))
        self.retrieval_engine = RetrievalEngine(retrieval_config)

        generation_config = dict(self.config.get('generation', {}))
        preferred_llms = self.config.get('llm_models') or self.config.get('llm_candidates')
        if preferred_llms:
            generation_config.setdefault('default_model', preferred_llms[0])
            if len(preferred_llms) > 1:
                generation_config.setdefault('fast_model', preferred_llms[1])
        self.generation_engine = GenerationEngine(generation_config)
        self.context_builder = ContextPromptBuilder()
        self.response_refiner = ResponseRefiner(self.generation_engine)
        self.query_expander = QueryExpander(self.generation_engine)
        
        # Optimization Components
        self.semantic_cache = SemanticCache()
        self.prompt_optimizer = PromptOptimizer()
        self.llm_manager = LLMManager(self.generation_engine)
        
        self.mcp_service = get_mcp_service()
        # Observability (optional)
        if LangfuseIntegration is not None:
            self.langfuse = LangfuseIntegration(self.config.get('langfuse', {}))
        else:
            self.langfuse = None
        
        # 파이프라인 설정
        self.max_retrieval_docs = self.config.get('max_retrieval_docs', 5)
        self.rerank_top_k = self.config.get('rerank_top_k', 3)
        self.enable_reranking = self.config.get('enable_reranking', True)
        self.enable_hybrid_search = self.config.get('enable_hybrid_search', True)
        
    async def process_query(
        self,
        query: str,
        query_type: PromptType,
        user_context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """RAG 파이프라인 메인 처리"""
        try:
            start_time = datetime.now()
            trace_id = None
            if self.langfuse:
                trace_id = await self.langfuse.start_trace(
                    name="rag_query",
                    user_id=(user_context or {}).get('user_id') if user_context else None,
                    session_id=(user_context or {}).get('session_id') if user_context else None,
                    metadata={"query_type": query_type.value}
                )
            
            # 0. Check Semantic Cache
            cached_response = await self.semantic_cache.get_cached_response(query)
            if cached_response:
                return {
                    'success': True,
                    'response': cached_response,
                    'cached': True,
                    'metadata': {'query_type': query_type.value}
                }

            # 1. 쿼리 전처리 및 확장 (Query Expansion)
            # Wrtn Style: Multi-query expansion
            queries = await self.query_expander.expand_query(query, n_variations=3)
            processed_query = queries[0] # Main query for logging/primary use
            
            # 2~5. 검색/컨텍스트/프롬프트를 병렬로 준비해 레이턴시 단축
            import asyncio
            
            # Hybrid Search with Multi-Query (Parallelized)
            search_tasks = [self._hybrid_retrieval(q, user_context) for q in queries]
            search_results_list = await asyncio.gather(*search_tasks)
            
            # Flatten and deduplicate results from all queries
            all_docs = []
            seen_ids = set()
            for docs in search_results_list:
                for doc in docs:
                    if doc['id'] not in seen_ids:
                        all_docs.append(doc)
                        seen_ids.add(doc['id'])
            
            # Rerank the consolidated list (Cross-Encoder)
            retrieved_docs = await self.retrieval_engine.rerank_documents(query, all_docs, top_k=self.rerank_top_k)

            ctx_task = asyncio.create_task(self._create_context(retrieved_docs, user_context))
            # 컨텍스트가 프롬프트에 필요하므로 컨텍스트 완료 후 프롬프트 생성
            context = await ctx_task
            # ANALYTICS 쿼리의 경우, 분석 관련 데이터를 상위 컨텍스트에 노출
            if query_type == PromptType.ANALYTICS:
                context = self._augment_analytics_context(context, user_context or {})
            prompt = await self._create_prompt(query_type, processed_query, retrieved_docs, context, conversation_history)
            
            # 6. 생성 수행 (with Intelligent Routing & Optimization)
            # Route model
            user_tier = (user_context or {}).get('user_tier', 'free')
            complexity = 'high' if len(retrieved_docs) > 3 or len(processed_query) > 50 else 'low'
            routing_config = self.llm_manager.route_request(user_tier, complexity)
            
            # Apply routing config to context
            if context:
                context.update(routing_config)

            # Optimize Prompt (Token Reduction)
            optimized_prompt, _ = self.prompt_optimizer.optimize(prompt, []) # Prompt string optimization
            
            # Streaming check (if client supports it)
            if (user_context or {}).get('stream', False):
                # Return stream iterator directly (requires architectural change in caller)
                # For now, we simulate streaming by logging or just using standard gen
                pass

            response = await self._generate_response(optimized_prompt, query_type, context)
            
            # 7. 후처리 및 검증
            final_response = await self._postprocess_response(response, retrieved_docs)
            
            # Cache the result
            await self.semantic_cache.cache_response(query, final_response)
            
            # 성능 메트릭 계산
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result: Dict[str, Any] = {
                'success': True,
                'response': final_response,
                'retrieved_documents': retrieved_docs[:self.rerank_top_k],
                'context': context,
                'processing_time': processing_time,
                'metadata': {
                    'query_type': query_type.value,
                    'num_retrieved': len(retrieved_docs),
                    'reranking_enabled': self.enable_reranking,
                    'hybrid_search_enabled': self.enable_hybrid_search
                }
            }
            # Observability log
            try:
                if self.langfuse and trace_id:
                    from typing import cast, Dict as _Dict, Any as _Any
                    meta: _Dict[str, _Any] = cast(_Dict[str, _Any], result.get('metadata', {}))
                    await self.langfuse.log_rag_pipeline(
                        trace_id=trace_id,
                        query=processed_query,
                        retrieved_docs=retrieved_docs[:self.rerank_top_k],
                        response=final_response,
                        processing_time=processing_time,
                        metadata=meta
                    )
                    await self.langfuse.end_trace(trace_id, output=final_response)
            except Exception:
                pass
            return result
            
        except Exception as e:
            self.logger.error(f"RAG pipeline processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': None
            }
    
    async def _hybrid_retrieval(
        self, 
        query: str, 
        user_context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """하이브리드 검색 수행"""
        try:
            retrieved_docs = []
            
            # 1. 벡터 검색
            vector_results = await self.retrieval_engine.vector_search(
                query=query,
                limit=self.max_retrieval_docs,
                filters=(user_context or {}).get('filters', {})
            )
            retrieved_docs.extend(vector_results)
            
            # 2. 키워드 검색 (하이브리드 모드)
            if self.enable_hybrid_search:
                keyword_results = await self.retrieval_engine.keyword_search(
                    query=query,
                    limit=self.max_retrieval_docs
                )
                retrieved_docs.extend(keyword_results)
            
            # 3. 중복 제거 및 점수 정규화
            unique_docs = self._deduplicate_documents(retrieved_docs)
            
            # 4. 점수 기반 정렬
            unique_docs.sort(key=lambda x: x.get('score', 0.0), reverse=True)
            
            return unique_docs[:self.max_retrieval_docs]
            
        except Exception as e:
            self.logger.error(f"Hybrid retrieval failed: {e}")
            return []
    
    async def _create_context(
        self, 
        documents: List[Dict[str, Any]], 
        user_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """컨텍스트 생성"""
        try:
            context = {
                'retrieved_documents': documents,
                'user_context': user_context or {},
                'timestamp': datetime.now().isoformat(),
                'num_documents': len(documents)
            }
            
            # 문서 요약 생성
            if documents:
                context['document_summary'] = await self._create_document_summary(documents)

            spec = self._infer_mcp_spec(user_context or {})
            if spec:
                try:
                    enrichment = await self.mcp_service.enrich_context(spec, user_context or {})
                    if enrichment:
                        context["mcp_enrichment"] = enrichment
                        if enrichment.get("external_snippets"):
                            context["external_snippets"] = enrichment["external_snippets"]
                        if enrichment.get("youtube_insights"):
                            context["youtube_insights"] = enrichment["youtube_insights"]
                except Exception:
                    pass
            
            return context
            
        except Exception as e:
            self.logger.error(f"Context creation failed: {e}")
            return {'retrieved_documents': documents, 'user_context': user_context or {}}

    def _infer_mcp_spec(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Infer MCP spec from user context (legacy keys supported)."""
        spec = dict(user_context.get("mcp") or {})
        if user_context.get("mcp_search_query") and "search_query" not in spec:
            spec["search_query"] = user_context["mcp_search_query"]
        if user_context.get("mcp_http_urls") and "urls" not in spec:
            spec["urls"] = user_context["mcp_http_urls"]
        youtube_hint = user_context.get("youtube")
        if youtube_hint and "youtube" not in spec:
            spec["youtube"] = youtube_hint
        return spec

    def _augment_analytics_context(
        self,
        context: Dict[str, Any],
        user_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        ANALYTICS 쿼리용 컨텍스트 보강.

        - user_context에 포함된 분석 관련 데이터를 상위 레벨 키로 노출
        - 'analytics_context' 하위에 정리하여 프롬프트 템플릿에서 바로 사용할 수 있게 함
        """
        try:
            if not user_context:
                return context

            ctx: Dict[str, Any] = dict(context)
            analytics_ctx: Dict[str, Any] = dict(ctx.get("analytics_context", {}))

            # 보고서/필터/도메인별 통계 등 분석용 데이터 키
            keys = [
                "report_type",
                "date_range",
                "filters",
                "creator_stats",
                "mission_stats",
                "reward_stats",
                "creator_data",
                "mission_data",
                "reward_data",
                "analytics_data",
            ]

            for key in keys:
                if key in user_context:
                    value = user_context[key]
                    ctx[key] = value
                    analytics_ctx[key] = value

            if analytics_ctx:
                ctx["analytics_context"] = analytics_ctx

            # 프롬프트 템플릿에서 사용할 수 있도록 user_data 별도 노출
            if "user_data" not in ctx:
                ctx["user_data"] = user_context

            return ctx
        except Exception:
            # 컨텍스트 보강에 실패해도 기본 컨텍스트는 그대로 사용
            return context
    
    async def _create_prompt(
        self,
        query_type: PromptType,
        query: str,
        documents: List[Dict[str, Any]],
        context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> str:
        """프롬프트 생성 (Context Prompt Builder 사용)"""
        try:
            # Wrtn Style: Rich Context Construction via ContextPromptBuilder
            # 기존의 단순 템플릿 치환 대신, 구조화된 컨텍스트 프롬프트를 생성합니다.
            full_prompt = self.context_builder.build_context_prompt(
                query=query,
                user_context=context.get('user_context', {}),
                system_context={'os': 'darwin', 'query_type': query_type.value},
                retrieved_docs=documents,
                history=conversation_history,
                agent_specific_context=context
            )
            return full_prompt
                
        except Exception as e:
            self.logger.error(f"Prompt creation failed: {e}")
            return query
    
    async def _generate_response(
        self, 
        prompt: str, 
        query_type: PromptType, 
        context: Dict[str, Any]
    ) -> str:
        """응답 생성"""
        try:
            # 시스템 프롬프트 선택
            system_prompt = self._get_system_prompt_for_type(query_type)
            
            # 생성 수행
            # 사용자가 선택한 모델이 있으면 우선 적용 (context['model_name'])
            selected_model = None
            try:
                if isinstance(context, dict):
                    selected_model = context.get('model_name')
            except Exception:
                selected_model = None

            response = await self.generation_engine.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                model_name=selected_model,
                context=context
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Response generation failed: {e}")
            return "죄송합니다. 응답 생성 중 오류가 발생했습니다."
    
    async def _postprocess_response(
        self, 
        response: str, 
        documents: List[Dict[str, Any]]
    ) -> str:
        """응답 후처리"""
        try:
            # 1. 응답 검증
            validated_response = await self._validate_response(response)
            
            # 2. 출처 정보 추가
            if documents:
                source_info = self._create_source_info(documents)
                validated_response += f"\n\n**참고 자료**:\n{source_info}"
            
            # 3. Wrtn Style 정제 (Persona & Tone & Hallucination Check)
            # 기존 _refine_response 대신 ResponseRefiner 사용
            final_response = await self.response_refiner.refine(
                raw_response=validated_response,
                context={'retrieved_documents': documents}, # Pass docs for hallucination check
                style="wrtn_friendly",
                check_hallucination=True # Enable safety check
            )
            
            return final_response
            
        except Exception as e:
            self.logger.error(f"Response postprocessing failed: {e}")
            return response
    
    def _deduplicate_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """문서 중복 제거"""
        seen_ids = set()
        unique_docs = []
        
        for doc in documents:
            doc_id = doc.get('id', '')
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_docs.append(doc)
        
        return unique_docs
    
    async def _create_document_summary(self, documents: List[Dict[str, Any]]) -> str:
        """문서 요약 생성"""
        try:
            if not documents:
                return "관련 문서가 없습니다."
            
            summary_parts = []
            for i, doc in enumerate(documents[:3], 1):  # 상위 3개 문서만
                content = doc.get('content', '')[:200]  # 200자로 제한
                summary_parts.append(f"{i}. {content}...")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            self.logger.error(f"Document summary creation failed: {e}")
            return "문서 요약을 생성할 수 없습니다."
    
    def _get_system_prompt_for_type(self, query_type: PromptType) -> str:
        """쿼리 타입에 따른 시스템 프롬프트 선택"""
        prompt_mapping = {
            PromptType.COMPETENCY_ASSESSMENT: "competency_expert",
            PromptType.RECOMMENDATION: "recommendation_expert",
            PromptType.SEARCH: "default",
            PromptType.ANALYTICS: "default",
            PromptType.GENERAL_CHAT: "default",
            PromptType.DATA_COLLECTION: "default"
        }
        
        role = prompt_mapping.get(query_type, "default")
        return self.prompt_templates.get_system_prompt(role)
    
    async def _validate_response(self, response: str) -> str:
        """응답 검증"""
        try:
            # 기본 검증
            if not response or len(response.strip()) < 10:
                return "응답이 너무 짧습니다. 더 자세한 정보를 제공해주세요."
            
            # 부적절한 내용 필터링 (기본적인 검증)
            inappropriate_keywords = ['오류', '에러', '실패', '불가능']
            if any(keyword in response for keyword in inappropriate_keywords):
                return "죄송합니다. 적절한 답변을 제공할 수 없습니다."
            
            return response
            
        except Exception as e:
            self.logger.error(f"Response validation failed: {e}")
            return response
    
    def _create_source_info(self, documents: List[Dict[str, Any]]) -> str:
        """출처 정보 생성"""
        try:
            sources = []
            for i, doc in enumerate(documents[:3], 1):
                metadata = doc.get('metadata', {})
                source = metadata.get('source', 'Unknown')
                date = metadata.get('date', 'Unknown')
                sources.append(f"- {source} ({date})")
            
            return "\n".join(sources)
            
        except Exception as e:
            self.logger.error(f"Source info creation failed: {e}")
            return "출처 정보를 생성할 수 없습니다."
    
    async def _refine_response(self, response: str) -> str:
        """응답 정제"""
        try:
            # 불필요한 공백 제거
            refined = response.strip()
            
            # 중복 문장 제거 (간단한 정제)
            sentences = refined.split('.')
            unique_sentences = []
            seen = set()
            
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and sentence not in seen:
                    seen.add(sentence)
                    unique_sentences.append(sentence)
            
            return '. '.join(unique_sentences) + '.' if unique_sentences else refined
            
        except Exception as e:
            self.logger.error(f"Response refinement failed: {e}")
            return response
