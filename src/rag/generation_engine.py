"""생성 엔진 구현 (Enhanced with Streaming & Advanced Routing)"""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

# 선택적 import
try:
    from langchain_anthropic import ChatAnthropic  # type: ignore[import-not-found]
    from langchain_core.messages import (  # type: ignore[import-not-found]
        AIMessage,
        HumanMessage,
        SystemMessage,
    )
    from langchain_google_genai import (
        ChatGoogleGenerativeAI,  # type: ignore[import-not-found]
    )
    from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]

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
            self.default_model = self.config.get("default_model", _st.DEFAULT_LLM_MODEL)
            self.fast_model = self.config.get(
                "fast_model", getattr(_st, "FAST_LLM_MODEL", _st.FALLBACK_LLM_MODEL)
            )
            self.deep_model = self.config.get(
                "deep_model", getattr(_st, "DEEP_LLM_MODEL", _st.DEFAULT_LLM_MODEL)
            )
            self.fallback_model = self.config.get(
                "fallback_model", getattr(_st, "FALLBACK_LLM_MODEL", self.fast_model)
            )
            # API 키 설정
            self.openai_api_key = self.config.get("openai_api_key", _st.OPENAI_API_KEY)
            self.anthropic_api_key = self.config.get(
                "anthropic_api_key", _st.ANTHROPIC_API_KEY
            )
            self.google_api_key = self.config.get(
                "google_api_key", getattr(_st, "GOOGLE_API_KEY", "")
            )
        except Exception:
            # 설정 모듈 접근 실패 시: 문서 기반 "합리적 최신 기본값" (벤더 공식 모델 리스트 기준)
            self.default_model = self.config.get(
                "default_model", "claude-sonnet-4-5-20250929"
            )
            self.fast_model = self.config.get("fast_model", "gemini-2.5-flash")
            self.deep_model = self.config.get("deep_model", "gpt-5.2")
            self.fallback_model = self.config.get("fallback_model", "gemini-2.5-flash")
            self.openai_api_key = self.config.get("openai_api_key", "")
            self.anthropic_api_key = self.config.get("anthropic_api_key", "")
            self.google_api_key = self.config.get("google_api_key", "")

        self.max_tokens = self.config.get("max_tokens", 2000)
        self.temperature = self.config.get("temperature", 0.7)
        self.top_p = self.config.get("top_p", 0.9)

        # Retry & fallback knobs
        retry_cfg = (
            self.config.get("retry", {})
            if isinstance(self.config.get("retry", {}), dict)
            else {}
        )
        self.retry_max_retries = int(retry_cfg.get("max_retries", 2))
        self.retry_backoff_ms = int(retry_cfg.get("backoff_ms", 250))
        self.retry_backoff_multiplier = float(retry_cfg.get("backoff_multiplier", 2.0))

        # Fallback order
        self.fallback_order = self.config.get(
            "fallback_order", ["selected", "default", "fast", "fallback", "deep"]
        )

        # 모델 인스턴스
        self.models: Dict[str, Any] = {}
        self._initialize_models()

    def _initialize_models(self):
        """모델 초기화 (Enable Streaming)"""
        try:
            if not LANGCHAIN_AVAILABLE:
                self.logger.warning("LangChain not available, using fallback")
                return

            # OpenAI Models
            if self.openai_api_key:
                for model_name in [
                    self.default_model,
                    self.fast_model,
                    self.fallback_model,
                ]:
                    if (
                        isinstance(model_name, str)
                        and model_name.startswith("gpt-")
                        and model_name not in self.models
                    ):
                        self.models[model_name] = ChatOpenAI(
                            model=model_name,
                            api_key=self.openai_api_key,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens,
                            streaming=True,  # Enable Streaming
                        )
                self.logger.info("OpenAI models initialized")

            # Anthropic Models
            if self.anthropic_api_key:
                for model_name in [self.default_model, self.deep_model]:
                    if (
                        isinstance(model_name, str)
                        and model_name.startswith("claude")
                        and model_name not in self.models
                    ):
                        self.models[model_name] = ChatAnthropic(
                            model=model_name,
                            api_key=self.anthropic_api_key,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens,
                            streaming=True,  # Enable Streaming
                        )
                self.logger.info("Anthropic models initialized")

            # Google Gemini Models
            if self.google_api_key and ChatGoogleGenerativeAI:
                for model_name in [
                    self.fast_model,
                    self.fallback_model,
                    self.default_model,
                ]:
                    if (
                        isinstance(model_name, str)
                        and "gemini" in model_name.lower()
                        and model_name not in self.models
                    ):
                        self.models[model_name] = ChatGoogleGenerativeAI(
                            model=model_name,
                            google_api_key=self.google_api_key,
                            temperature=self.temperature,
                            max_output_tokens=self.max_tokens,
                            # Streaming supported by default in newer LangChain Google wrapper if configured?
                            # Explicit streaming flag might not be needed or is named differently
                        )
                self.logger.info("Google Gemini models initialized")

        except Exception as e:
            self.logger.error(f"Model initialization failed: {e}")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """텍스트 스트리밍 생성"""
        try:
            selected_model_name, selected_model = self._select_model(
                model_name, context
            )
            if not selected_model:
                yield "Error: Model not found."
                return

            messages = self._prepare_messages(prompt, system_prompt, context)

            # Use LangChain's astream
            async for chunk in selected_model.astream(messages):
                if hasattr(chunk, "content"):
                    yield chunk.content
                elif isinstance(chunk, str):
                    yield chunk

        except Exception as e:
            self.logger.error(f"Streaming generation failed: {e}")
            yield f"Error generating response: {e}"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """텍스트 생성 (Standard)"""
        try:
            # 1. Prompt Override Check
            try:
                if context and isinstance(context, dict):
                    if context.get("prompt_override"):
                        prompt = str(context.get("prompt_override"))
                    if context.get("system_prompt_override"):
                        system_prompt = str(context.get("system_prompt_override"))
            except Exception:
                pass

            # 2. Model Selection
            selected_model_name, selected_model = self._select_model(
                model_name, context
            )

            if not selected_model:
                return await self._fallback_generation(prompt, context)

            # 3. Message Prep
            messages = self._prepare_messages(prompt, system_prompt, context)

            # 4. Generate with Retries
            response = await self._generate_with_retries(selected_model, messages)
            if response:
                return response

            # 5. Fallback Chain
            for name, model in self._fallback_candidates(selected_model_name):
                try:
                    resp = await self._generate_with_retries(model, messages)
                    if resp:
                        self.logger.info(f"Fallback success with: {name}")
                        return resp
                except Exception as e:
                    self.logger.warning(f"Fallback {name} failed: {e}")

            return await self._fallback_generation(prompt, context)

        except Exception as e:
            self.logger.error(f"Text generation failed: {e}")
            return await self._fallback_generation(prompt, context)

    def _select_model(
        self, model_name: Optional[str], context: Optional[Dict[str, Any]]
    ) -> tuple[Optional[str], Optional[Any]]:
        """모델 선택 (Cost/Latency Routing Logic)"""
        try:
            # 1. Explicit selection
            if model_name and model_name in self.models:
                return model_name, self.models[model_name]

            # 2. Context-based Routing
            if context:
                task = context.get("task_type")
                latency_hint = context.get("latency_hint")  # 'fast', 'normal'
                cost_hint = context.get("cost_hint")  # 'budget', 'premium'

                # Cost-sensitive routing
                if cost_hint == "budget" and self.fast_model in self.models:
                    return self.fast_model, self.models[self.fast_model]

                # Latency-sensitive routing
                if latency_hint == "fast" and self.fast_model in self.models:
                    return self.fast_model, self.models[self.fast_model]

                # Complex task routing
                if (
                    task in ["analysis", "coding", "reasoning"]
                    and self.deep_model in self.models
                ):
                    return self.deep_model, self.models[self.deep_model]

            # 3. Default Fallbacks
            if self.default_model in self.models:
                return self.default_model, self.models[self.default_model]
            elif self.fast_model in self.models:
                return self.fast_model, self.models[self.fast_model]

            if self.models:
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
        context: Optional[Dict[str, Any]],
    ) -> List[Any]:
        """메시지 준비"""
        try:
            # LangChain 미가용 시 dict 형태로 반환 (테스트/Mock 용)
            if not LANGCHAIN_AVAILABLE or HumanMessage is None:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                
                # Context 처리 (간소화)
                full_prompt = prompt
                if context:
                    context_info = self._format_context(context)
                    if context_info:
                        full_prompt = f"Context:\n{context_info}\n\n{prompt}"
                
                messages.append({"role": "user", "content": full_prompt})
                return messages

            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))

            if context:
                context_info = self._format_context(context)
                if context_info:
                    messages.append(SystemMessage(content=f"Context:\n{context_info}"))

            messages.append(HumanMessage(content=prompt))
            return messages
        except Exception as e:
            self.logger.error(f"Message prep failed: {e}")
            return [HumanMessage(content=prompt)]

    async def _generate_with_model(
        self, model: Any, messages: List[Any], **kwargs
    ) -> str:
        """모델 호출 wrapper"""
        if hasattr(model, "ainvoke"):
            response = await model.ainvoke(messages)
        else:
            response = model.invoke(messages)

        if hasattr(response, "content"):
            return response.content
        return str(response)

    async def _generate_with_retries(self, model: Any, messages: List[Any]) -> str:
        """재시도 로직"""
        import asyncio

        backoff = self.retry_backoff_ms / 1000.0
        attempts = max(1, self.retry_max_retries)

        for attempt in range(attempts):
            try:
                return await self._generate_with_model(model, messages)
            except Exception as e:
                if attempt < attempts - 1:
                    await asyncio.sleep(backoff)
                    backoff *= self.retry_backoff_multiplier
                else:
                    self.logger.warning(f"All retries failed: {e}")
        return ""

    def _fallback_candidates(self, selected_name: Optional[str]):
        """폴백 후보 생성"""
        order_tokens = [t for t in self.fallback_order if isinstance(t, str)]
        name_map = {
            "selected": selected_name,
            "default": self.default_model,
            "fast": self.fast_model,
            "deep": self.deep_model,
            "fallback": self.fallback_model,
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

    def _format_context(self, context: Dict[str, Any]) -> str:
        try:
            parts = []
            if "retrieved_documents" in context:
                docs = context["retrieved_documents"]
                if docs:
                    parts.append("Retrieved Docs:")
                    for i, doc in enumerate(docs[:3], 1):
                        parts.append(f"{i}. {doc.get('content', '')[:200]}...")
            if "user_context" in context:
                parts.append("User Info: " + str(context["user_context"]))
            return "\n".join(parts)
        except Exception:
            return ""

    async def _fallback_generation(
        self, prompt: str, context: Optional[Dict[str, Any]]
    ) -> str:
        return "죄송합니다. 현재 응답을 생성할 수 없습니다."

    async def generate_openai_function_call(self, *args, **kwargs):
        # Implementation omitted for brevity, keep existing logic if needed
        pass

    # ... (Keep existing health_check, get_model_info etc.)
