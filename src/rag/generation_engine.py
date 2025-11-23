"""생성 엔진 구현"""

import logging
from typing import Dict, Any, List, Optional

# 선택적 import
try:
    from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]
    from langchain_anthropic import ChatAnthropic  # type: ignore[import-not-found]
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore[import-not-found]
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage  # type: ignore[import-not-found]
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    ChatOpenAI = None
    ChatAnthropic = None
    ChatGoogleGenerativeAI = None
    HumanMessage = None
    SystemMessage = None
    AIMessage = None

logger = logging.getLogger(__name__)


class GenerationEngine:
    """생성 엔진"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("GenerationEngine")
        
        # 생성 설정
        try:
            from config.settings import get_settings
            _st = get_settings()
            self.default_model = self.config.get('default_model', _st.DEFAULT_LLM_MODEL)
            self.fast_model = self.config.get('fast_model', getattr(_st, 'FAST_LLM_MODEL', _st.FALLBACK_LLM_MODEL))
            self.deep_model = self.config.get('deep_model', getattr(_st, 'DEEP_LLM_MODEL', _st.DEFAULT_LLM_MODEL))
            self.fallback_model = self.config.get('fallback_model', getattr(_st, 'FALLBACK_LLM_MODEL', self.fast_model))
            # API 키 설정 (설정 우선, 없으면 env 기반 설정 사용)
            self.openai_api_key = self.config.get('openai_api_key', _st.OPENAI_API_KEY)
            self.anthropic_api_key = self.config.get('anthropic_api_key', _st.ANTHROPIC_API_KEY)
            self.google_api_key = self.config.get('google_api_key', getattr(_st, 'GOOGLE_API_KEY', ''))
        except Exception:
            # 설정 모듈 접근 실패 시 합리적 기본값
            self.default_model = self.config.get('default_model', 'gpt-5.1')
            self.fast_model = self.config.get('fast_model', 'gemini-2.0-flash')
            self.deep_model = self.config.get('deep_model', 'gpt-5.1')
            self.fallback_model = self.config.get('fallback_model', 'gemini-2.0-flash')
            self.openai_api_key = self.config.get('openai_api_key', '')
            self.anthropic_api_key = self.config.get('anthropic_api_key', '')
            self.google_api_key = self.config.get('google_api_key', '')
        self.max_tokens = self.config.get('max_tokens', 2000)
        self.temperature = self.config.get('temperature', 0.7)
        self.top_p = self.config.get('top_p', 0.9)

        # Retry & fallback knobs
        retry_cfg = self.config.get('retry', {}) if isinstance(self.config.get('retry', {}), dict) else {}
        self.retry_max_retries = int(retry_cfg.get('max_retries', 2))
        self.retry_backoff_ms = int(retry_cfg.get('backoff_ms', 250))
        self.retry_backoff_multiplier = float(retry_cfg.get('backoff_multiplier', 2.0))

        # Fallback order – tokens: selected, default, fast, deep, fallback
        self.fallback_order = self.config.get('fallback_order', ['selected', 'default', 'fast', 'fallback', 'deep'])
        
        # 모델 인스턴스
        self.models: Dict[str, Any] = {}
        self._initialize_models()
    
    def _initialize_models(self):
        """모델 초기화"""
        try:
            if not LANGCHAIN_AVAILABLE:
                self.logger.warning("LangChain not available, using fallback")
                return
            
            # OpenAI 모델 초기화 (기본/가속/폴백 중 OpenAI 계열)
            if self.openai_api_key:
                try:
                    if isinstance(self.default_model, str) and self.default_model:
                        self.models[self.default_model] = ChatOpenAI(
                            model=self.default_model,
                            api_key=self.openai_api_key,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens
                        )
                    if isinstance(self.fast_model, str) and self.fast_model.startswith('gpt-'):
                        self.models[self.fast_model] = ChatOpenAI(
                            model=self.fast_model,
                            api_key=self.openai_api_key,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens
                        )
                    if isinstance(self.fallback_model, str) and self.fallback_model.startswith('gpt-'):
                        self.models[self.fallback_model] = ChatOpenAI(
                            model=self.fallback_model,
                            api_key=self.openai_api_key,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens
                        )
                    self.logger.info("OpenAI models initialized")
                except Exception as e:
                    self.logger.warning(f"OpenAI model init failed: {e}")
            
            # Anthropic 모델 초기화 (기본/심화 중 Anthropic 계열)
            if self.anthropic_api_key:
                try:
                    if isinstance(self.default_model, str) and self.default_model.startswith('claude'):
                        self.models[self.default_model] = ChatAnthropic(
                            model=self.default_model,
                            api_key=self.anthropic_api_key,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens
                        )
                    if isinstance(self.deep_model, str) and self.deep_model.startswith('claude'):
                        self.models[self.deep_model] = ChatAnthropic(
                            model=self.deep_model,
                            api_key=self.anthropic_api_key,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens
                        )
                    self.logger.info("Anthropic models initialized")
                except Exception as e:
                    self.logger.warning(f"Anthropic model init failed: {e}")

            # Google Gemini 모델 초기화
            if self.google_api_key and ChatGoogleGenerativeAI:
                try:
                    # fast_model 또는 fallback_model이 gemini인 경우
                    if isinstance(self.fast_model, str) and 'gemini' in self.fast_model.lower():
                        self.models[self.fast_model] = ChatGoogleGenerativeAI(
                            model=self.fast_model,
                            google_api_key=self.google_api_key,
                            temperature=self.temperature,
                            max_output_tokens=self.max_tokens
                        )
                    if isinstance(self.fallback_model, str) and 'gemini' in self.fallback_model.lower() and self.fallback_model not in self.models:
                        self.models[self.fallback_model] = ChatGoogleGenerativeAI(
                            model=self.fallback_model,
                            google_api_key=self.google_api_key,
                            temperature=self.temperature,
                            max_output_tokens=self.max_tokens
                        )
                    # default_model이 gemini인 경우
                    if isinstance(self.default_model, str) and 'gemini' in self.default_model.lower() and self.default_model not in self.models:
                        self.models[self.default_model] = ChatGoogleGenerativeAI(
                            model=self.default_model,
                            google_api_key=self.google_api_key,
                            temperature=self.temperature,
                            max_output_tokens=self.max_tokens
                        )
                    self.logger.info("Google Gemini models initialized")
                except Exception as e:
                    self.logger.warning(f"Gemini model init failed: {e}")

        except Exception as e:
            self.logger.error(f"Model initialization failed: {e}")
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        model_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """텍스트 생성"""
        try:
            # 안전 프롬프트 가드
            try:
                from src.api.middleware.security_utils import sanitize_prompt  # type: ignore
                prompt = sanitize_prompt(prompt)
                if system_prompt:
                    system_prompt = sanitize_prompt(system_prompt)
            except Exception:
                pass
            # 프롬프트 오버라이드: 컨텍스트에서 직접 문자열을 제공하면 사용
            try:
                if context and isinstance(context, dict):
                    if isinstance(context.get('prompt_override'), str) and context.get('prompt_override'):
                        prompt = str(context.get('prompt_override'))
                    if isinstance(context.get('system_prompt_override'), str) and context.get('system_prompt_override'):
                        system_prompt = str(context.get('system_prompt_override'))
            except Exception as e:
                self.logger.warning(f"Prompt override usage failed: {e}")

            # 모델 선택
            selected_model_name, selected_model = self._select_model(model_name, context)
            
            if not selected_model:
                return await self._fallback_generation(prompt, context)
            
            # 메시지 구성
            messages = self._prepare_messages(prompt, system_prompt, context)

            # OpenAI function calling (선택)
            if isinstance(selected_model_name, str) and selected_model_name.startswith('gpt-') and context and context.get('openai_functions'):
                fc_result = await self._generate_openai_function_call(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    functions=context.get('openai_functions', []),
                    function_call=context.get('function_call', 'auto'),
                    tool_handlers=context.get('tool_handlers', {}),
                )
                if fc_result and len(fc_result.strip()) > 0:
                    return fc_result

            # 일반 생성 수행
            # Try primary with retries, then cascade through fallback chain
            response = await self._generate_with_retries(selected_model, messages)
            if response and len(response.strip()) > 0:
                return response

            # Build fallback model list
            for name, model in self._fallback_candidates(selected_model_name):
                try:
                    resp = await self._generate_with_retries(model, messages)
                    if resp and len(resp.strip()) > 0:
                        self.logger.info(f"Generation succeeded with fallback model: {name}")
                        return resp
                except Exception as e:
                    self.logger.warning(f"Fallback model {name} failed: {e}")
            
            return await self._fallback_generation(prompt, context)
            
        except Exception as e:
            self.logger.error(f"Text generation failed: {e}")
            return await self._fallback_generation(prompt, context)
    
    def _select_model(self, model_name: Optional[str], context: Optional[Dict[str, Any]]) -> tuple[Optional[str], Optional[Any]]:
        """모델 선택"""
        try:
            # 명시적 모델 지정
            if model_name and model_name in self.models:
                return model_name, self.models[model_name]
            
            # 컨텍스트 기반 모델 선택
            if context:
                # 요청 특성 기반 라우팅: task_hint, latency_hint, complexity_hint
                task = context.get('task_type') if isinstance(context, dict) else None
                latency = context.get('latency_hint') if isinstance(context, dict) else None
                complexity = context.get('complexity_hint') if isinstance(context, dict) else None

                # 가속 요청
                if latency == 'fast' and self.fast_model in self.models:
                    return self.fast_model, self.models[self.fast_model]

                # 심화/복잡 요청
                if (complexity == 'deep' or task in ('analysis', 'code', 'reasoning')) and self.deep_model in self.models:
                    return self.deep_model, self.models[self.deep_model]
            
            # 기본 모델 선택
            if self.default_model in self.models:
                return self.default_model, self.models[self.default_model]
            elif self.fast_model in self.models:
                return self.fast_model, self.models[self.fast_model]
            elif self.fallback_model in self.models:
                return self.fallback_model, self.models[self.fallback_model]
            elif self.models:
                first_name = next(iter(self.models.keys()))
                return first_name, self.models[first_name]
            
            return None, None
            
        except Exception as e:
            self.logger.error(f"Model selection failed: {e}")
            return None, None
    
    def _prepare_messages(
        self, 
        prompt: str, 
        system_prompt: Optional[str], 
        context: Optional[Dict[str, Any]]
    ) -> List[Any]:
        """메시지 준비"""
        try:
            messages = []
            
            # 시스템 메시지
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            # 컨텍스트 정보 추가
            if context:
                context_info = self._format_context(context)
                if context_info:
                    messages.append(SystemMessage(content=f"컨텍스트 정보:\n{context_info}"))
            
            # 사용자 프롬프트
            messages.append(HumanMessage(content=prompt))
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Message preparation failed: {e}")
            return [HumanMessage(content=prompt)]
    
    async def _generate_with_model(self, model: Any, messages: List[Any], **kwargs) -> str:
        """모델을 사용한 생성"""
        try:
            # 비동기 호출 시도
            if hasattr(model, 'ainvoke'):
                response = await model.ainvoke(messages)
            else:
                response = model.invoke(messages)
            
            # 응답 추출
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                return str(response)
                
        except Exception as e:
            self.logger.error(f"Model generation failed: {e}")
            raise

    async def _generate_with_retries(self, model: Any, messages: List[Any]) -> str:
        """재시도 포함한 단일 모델 호출 (지수 백오프)"""
        import asyncio
        backoff = self.retry_backoff_ms / 1000.0
        attempts = max(1, self.retry_max_retries)
        last_error: Optional[Exception] = None
        for attempt in range(attempts):
            try:
                return await self._generate_with_model(model, messages)
            except Exception as e:
                last_error = e
                if attempt < attempts - 1:
                    await asyncio.sleep(backoff)
                    backoff *= self.retry_backoff_multiplier
        if last_error:
            self.logger.warning(f"All retries failed: {last_error}")
        return ""

    def _fallback_candidates(self, selected_name: Optional[str]):
        """선택 모델 이후의 폴백 후보 목록(name, model) 생성"""
        order_tokens = [t for t in self.fallback_order if isinstance(t, str)]
        name_map = {
            'selected': selected_name,
            'default': self.default_model,
            'fast': self.fast_model,
            'deep': self.deep_model,
            'fallback': self.fallback_model,
        }
        seen = set([selected_name])
        for token in order_tokens:
            name = name_map.get(token, token)
            if not name or name in seen:
                continue
            seen.add(name)
            model = self.models.get(name)
            if model is not None:
                yield name, model

    async def _generate_openai_function_call(
        self,
        prompt: str,
        system_prompt: Optional[str],
        functions: List[Dict[str, Any]],
        function_call: str = "auto",
        tool_handlers: Optional[Dict[str, Any]] = None,
    ) -> str:
        """OpenAI function calling 간단 구현 (최대 1회 툴 실행)."""
        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:
            self.logger.warning(f"OpenAI client not available: {e}")
            return ""

        try:
            client = OpenAI(api_key=self.openai_api_key) if self.openai_api_key else OpenAI()
            chat_messages: List[Dict[str, Any]] = []
            if system_prompt:
                chat_messages.append({"role": "system", "content": system_prompt})
            chat_messages.append({"role": "user", "content": prompt})

            tools_payload = [{"type": "function", "function": f} for f in functions] if functions else None
            choice_call = client.chat.completions.create(  # type: ignore[arg-type]
                model=str(self.default_model),
                messages=chat_messages,
                tools=tools_payload,
                tool_choice=(function_call if tools_payload else None),
            )
            choice = choice_call.choices[0]
            msg = choice.message
            tool_calls = getattr(msg, 'tool_calls', None)
            if tool_calls and len(tool_calls) > 0 and tool_handlers:
                tc = tool_calls[0]
                fn = getattr(tc, 'function', None)
                if fn and getattr(fn, 'name', None):
                    name = fn.name
                    import json as _json
                    try:
                        args = _json.loads(getattr(fn, 'arguments', "{}") or "{}")
                    except Exception:
                        args = {}
                    handler = tool_handlers.get(name)
                    result_text = None
                    if callable(handler):
                        try:
                            out = handler(args)
                            if isinstance(out, (dict, list)):
                                result_text = _json.dumps(out, ensure_ascii=False)
                            else:
                                result_text = str(out)
                        except Exception as e:
                            result_text = f"tool_error: {e}"
                    else:
                        result_text = "tool_unavailable"
                    chat_messages.append({"role": "assistant", "tool_calls": [tc.model_dump()]})  # type: ignore[attr-defined]
                    chat_messages.append({"role": "tool", "tool_call_id": getattr(tc, 'id', ''), "name": name, "content": result_text or ""})
                    final = client.chat.completions.create(  # type: ignore[arg-type]
                        model=str(self.default_model),
                        messages=chat_messages,
                    )
                    return final.choices[0].message.content or ""
            return msg.content or ""
        except Exception as e:
            self.logger.warning(f"OpenAI function calling failed: {e}")
            return ""
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """컨텍스트 포맷팅"""
        try:
            context_parts = []
            
            # 검색된 문서 정보
            if 'retrieved_documents' in context:
                docs = context['retrieved_documents']
                if docs:
                    context_parts.append("관련 문서:")
                    for i, doc in enumerate(docs[:3], 1):
                        content = doc.get('content', '')[:200]
                        score = doc.get('score', 0.0)
                        context_parts.append(f"{i}. {content}... (관련도: {score:.2f})")
            
            # 사용자 컨텍스트
            if 'user_context' in context:
                user_ctx = context['user_context']
                if user_ctx:
                    context_parts.append("사용자 정보:")
                    for key, value in user_ctx.items():
                        if value:
                            context_parts.append(f"- {key}: {value}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            self.logger.error(f"Context formatting failed: {e}")
            return ""
    
    async def _fallback_generation(self, prompt: str, context: Optional[Dict[str, Any]]) -> str:
        """폴백 생성 (모델 없을 때)"""
        try:
            # 간단한 템플릿 기반 응답
            if "역량" in prompt or "진단" in prompt:
                return """
역량진단 결과를 분석해드리겠습니다.

**분석 결과**:
- 현재 역량 수준을 종합적으로 평가한 결과입니다.
- 개인별 특성과 학습 성향을 고려한 맞춤형 분석입니다.
- 향후 학습 방향에 대한 구체적인 제안을 포함합니다.

**추천사항**:
1. 현재 수준에 맞는 학습 자료 활용
2. 단계적 학습 계획 수립
3. 정기적인 역량 재평가

더 자세한 분석을 원하시면 구체적인 데이터를 제공해주세요.
"""
            
            elif "추천" in prompt or "학습자료" in prompt:
                return """
맞춤형 학습 추천을 제공해드리겠습니다.

**추천 학습 자료**:
1. 기초 육아 이론 (초급자용)
2. 아동 발달 단계별 이해 (중급자용)
3. 부모-자녀 소통 기법 (고급자용)

**학습 순서**:
1. 현재 수준 파악
2. 단계별 학습 계획 수립
3. 실습 및 피드백

개인별 맞춤 추천을 위해 더 많은 정보가 필요합니다.
"""
            
            elif "검색" in prompt or "찾기" in prompt:
                return """
검색 결과를 제공해드리겠습니다.

**검색 결과**:
- 관련 문서들을 종합적으로 분석한 결과입니다.
- 신뢰할 수 있는 출처의 정보를 우선적으로 제공합니다.
- 최신 정보와 정책 동향을 반영합니다.

**추가 정보**:
- 더 구체적인 검색어를 사용하면 정확한 결과를 얻을 수 있습니다.
- 특정 주제에 대한 심화 검색도 가능합니다.

구체적인 검색어나 주제를 알려주시면 더 정확한 정보를 제공해드리겠습니다.
"""
            
            else:
                return """
안녕하세요! 육아정책연구소 디지털연수 AI 어시스턴트입니다.

**제공 서비스**:
- 역량진단 및 분석
- 맞춤형 학습 추천
- 지능형 정보 검색
- 학습 분석 리포트

**도움말**:
- "역량진단" - 개인 역량 평가
- "추천" - 맞춤형 학습 자료 추천
- "검색" - 관련 정보 검색
- "분석" - 학습 성과 분석

어떤 도움이 필요하신지 구체적으로 말씀해주세요.
"""
                
        except Exception as e:
            self.logger.error(f"Fallback generation failed: {e}")
            return "죄송합니다. 응답을 생성할 수 없습니다. 다시 시도해주세요."
    
    async def generate_with_retry(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """재시도가 포함된 생성"""
        try:
            for attempt in range(max_retries):
                try:
                    response = await self.generate(prompt, system_prompt, **kwargs)
                    if response and len(response.strip()) > 10:
                        return response
                except Exception as e:
                    self.logger.warning(f"Generation attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise
            
            return await self._fallback_generation(prompt, kwargs.get('context'))
            
        except Exception as e:
            self.logger.error(f"Generate with retry failed: {e}")
            return await self._fallback_generation(prompt, kwargs.get('context'))
    
    async def batch_generate(
        self, 
        prompts: List[str], 
        system_prompts: Optional[List[str]] = None,
        **kwargs
    ) -> List[str]:
        """배치 생성"""
        try:
            results = []
            
            for i, prompt in enumerate(prompts):
                system_prompt = system_prompts[i] if system_prompts and i < len(system_prompts) else None
                
                response = await self.generate(prompt, system_prompt, **kwargs)
                results.append(response)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch generation failed: {e}")
            return [await self._fallback_generation(prompt, kwargs.get('context')) for prompt in prompts]
    
    def get_available_models(self) -> List[str]:
        """사용 가능한 모델 목록"""
        return list(self.models.keys())
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """모델 정보 조회"""
        try:
            if model_name not in self.models:
                return {'error': 'Model not found'}
            
            model = self.models[model_name]
            info = {
                'name': model_name,
                'type': type(model).__name__,
                'available': True
            }
            
            # 모델별 특성 정보
            if 'gpt' in model_name.lower():
                info['provider'] = 'OpenAI'
                info['max_tokens'] = getattr(model, 'max_tokens', self.max_tokens)
            elif 'claude' in model_name.lower():
                info['provider'] = 'Anthropic'
                info['max_tokens'] = getattr(model, 'max_tokens', self.max_tokens)
            
            return info
            
        except Exception as e:
            self.logger.error(f"Model info retrieval failed: {e}")
            return {'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """생성 엔진 상태 확인"""
        try:
            health_status = {
                'status': 'healthy',
                'available_models': len(self.models),
                'model_list': list(self.models.keys()),
                'langchain_available': LANGCHAIN_AVAILABLE,
                'config': {
                    'default_model': self.default_model,
                    'fallback_model': self.fallback_model,
                    'max_tokens': self.max_tokens,
                    'temperature': self.temperature
                }
            }
            
            # 모델별 상태 확인
            model_status = {}
            for model_name, model in self.models.items():
                try:
                    # 간단한 테스트 생성
                    test_response = await self._generate_with_model(
                        model, 
                        [HumanMessage(content="테스트")]
                    )
                    model_status[model_name] = {
                        'status': 'healthy',
                        'response_length': len(test_response)
                    }
                except Exception as e:
                    model_status[model_name] = {
                        'status': 'unhealthy',
                        'error': str(e)
                    }
            
            health_status['model_status'] = model_status
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
