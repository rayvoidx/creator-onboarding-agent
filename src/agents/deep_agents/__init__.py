"""
Deep Agents - 심층 분석 에이전트

다단계 추론, Self-Critique, 품질 검증을 담당합니다.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import Field

from ...core.base import BaseState

logger = logging.getLogger(__name__)


class DeepAgentsState(BaseState):
    """Deep Agents 상태"""

    query: str = ""
    iterations: int = 0
    max_iterations: int = 5
    quality_score: float = 0.0
    critique_history: List[Dict[str, Any]] = Field(default_factory=list)
    final_result: Optional[Dict[str, Any]] = None
    success: bool = False


class UnifiedDeepAgents:
    """
    통합 Deep Agents - 다단계 추론 및 자기 비평 기반 품질 향상

    복잡한 질의에 대해:
    1. 초기 응답 생성
    2. Self-Critique를 통한 품질 평가
    3. 반복적 개선
    4. 최종 품질 검증
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, generation_engine=None):
        self.config = config or {}
        self.logger = logging.getLogger("UnifiedDeepAgents")
        self.max_steps = self.config.get("max_steps", 8)
        self.critic_rounds = self.config.get("critic_rounds", 2)
        self.timeout_secs = self.config.get("timeout_secs", 60)
        self.quality_threshold = self.config.get("quality_threshold", 0.7)
        self.generation_engine = generation_engine

    def should_use_deep_agents(self, query: str) -> bool:
        """
        Deep Agents 사용 여부 판단

        복잡한 질문이나 다단계 추론이 필요한 경우 True 반환
        """
        if not query:
            return False

        query_lower = query.lower()

        # 복잡도 지표
        complexity_indicators = [
            # 다단계 추론 필요
            "비교",
            "분석",
            "종합",
            "평가",
            "장단점",
            "차이점",
            "공통점",
            # 전문적 질문
            "아키텍처",
            "설계",
            "구현",
            "최적화",
            "전략",
            "프레임워크",
            "시스템",
            # 복잡한 요청
            "단계별",
            "순차적",
            "체계적",
            "완성해줘",
            "만들어줘",
            "개발해줘",
            # 영어 패턴
            "compare",
            "analyze",
            "evaluate",
            "architecture",
            "design",
            "implement",
        ]

        # 복잡도 점수 계산
        complexity_score = sum(
            1 for indicator in complexity_indicators if indicator in query_lower
        )

        # 질문 길이도 고려
        if len(query) > 300:
            complexity_score += 1

        # 여러 문장인 경우
        sentences = re.split(r"[.?!。？！]", query)
        if len([s for s in sentences if s.strip()]) > 3:
            complexity_score += 1

        return complexity_score >= 2

    async def execute(self, query: str) -> Dict[str, Any]:
        """
        Deep Agents 실행

        Args:
            query: 사용자 질의

        Returns:
            처리 결과 딕셔너리
        """
        try:
            self.logger.info(
                f"Starting Deep Agents execution for query: {query[:100]}..."
            )

            iterations = 0
            quality_score = 0.0
            critique_history = []
            current_response = ""

            # 초기 응답 생성 (실제 구현에서는 LLM 호출)
            current_response = await self._generate_initial_response(query)
            iterations += 1

            # Self-Critique 루프
            for _ in range(self.critic_rounds):
                if iterations >= self.max_steps:
                    break

                # 품질 평가
                critique = await self._critique_response(query, current_response)
                critique_history.append(critique)
                quality_score = critique.get("score", 0.0)

                # 품질 기준 충족 시 종료
                if quality_score >= self.quality_threshold:
                    break

                # 응답 개선
                current_response = await self._improve_response(
                    query, current_response, critique
                )
                iterations += 1

            result = {
                "success": True,
                "response": current_response,
                "iterations": iterations,
                "quality_score": quality_score,
                "critique_history": critique_history,
                "result": {
                    "content": current_response,
                    "metadata": {
                        "iterations": iterations,
                        "quality_score": quality_score,
                        "processing_time": 0,
                        "needs_rag": False,
                        "needs_competency": False,
                        "needs_recommendation": False,
                    },
                },
            }

            self.logger.info(
                f"Deep Agents completed: iterations={iterations}, quality={quality_score:.2f}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Deep Agents execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "iterations": 0,
                "quality_score": 0.0,
            }

    async def _generate_initial_response(self, query: str) -> str:
        """초기 응답 생성 (LLM 호출)"""
        if self.generation_engine is None:
            return f"[초기 응답] {query}에 대한 분석 결과입니다."

        try:
            system_prompt = (
                "You are a deep analysis agent. Provide a thorough, structured analysis "
                "of the user's request in Korean. Use clear headings (##), bullet points, "
                "and concrete examples. Be comprehensive but concise."
            )
            return await self.generation_engine.generate(
                prompt=query,
                system_prompt=system_prompt,
                temperature=0.3,
            )
        except Exception as e:
            self.logger.warning("LLM generation failed, using fallback: %s", e)
            return f"[초기 응답] {query}에 대한 분석 결과입니다."

    async def _critique_response(self, query: str, response: str) -> Dict[str, Any]:
        """응답 품질 비평 (LLM 호출)"""
        if self.generation_engine is None:
            return self._heuristic_critique(response)

        try:
            system_prompt = (
                "You are a quality critic. Evaluate the response to the user query.\n"
                "Output ONLY valid JSON with this schema:\n"
                '{"score": 0.0-1.0, "feedback": "string", "improvements": ["string"]}\n'
                "Rules:\n"
                "- score 0.8+ means high quality\n"
                "- score <0.5 means needs significant improvement\n"
                "- List specific, actionable improvements"
            )
            raw = await self.generation_engine.generate(
                prompt=f"Query: {query}\n\nResponse to evaluate:\n{response}",
                system_prompt=system_prompt,
                temperature=0.1,
            )
            import json

            cleaned = raw.strip()
            # Strip markdown code fences if present
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            result = json.loads(cleaned)
            result["score"] = float(result.get("score", 0.5))
            return result
        except Exception as e:
            self.logger.warning("LLM critique failed, using heuristic: %s", e)
            return self._heuristic_critique(response)

    def _heuristic_critique(self, response: str) -> Dict[str, Any]:
        """Fallback heuristic-based critique."""
        score = 0.5
        if len(response) > 100:
            score += 0.1
        if len(response) > 300:
            score += 0.1
        if any(marker in response for marker in ["1.", "2.", "-", "•", "##"]):
            score += 0.1
        return {
            "score": min(score, 1.0),
            "feedback": "품질 평가 완료 (heuristic)",
            "improvements": ["더 구체적인 예시 추가", "구조화된 형식으로 정리"],
        }

    async def _improve_response(
        self, query: str, response: str, critique: Dict[str, Any]
    ) -> str:
        """응답 개선 (LLM 호출)"""
        if self.generation_engine is None:
            improvements = critique.get("improvements", [])
            improved = f"{response}\n\n[개선사항 반영]\n"
            for imp in improvements:
                improved += f"- {imp}\n"
            return improved

        try:
            feedback = critique.get("feedback", "")
            improvements = critique.get("improvements", [])
            improvements_text = "\n".join(f"- {imp}" for imp in improvements)

            system_prompt = (
                "You are a response improvement agent. Improve the original response "
                "based on the critique feedback. Write in Korean. Keep the improved "
                "response structured and comprehensive."
            )
            return await self.generation_engine.generate(
                prompt=(
                    f"Original query: {query}\n\n"
                    f"Original response:\n{response}\n\n"
                    f"Critique feedback: {feedback}\n"
                    f"Required improvements:\n{improvements_text}\n\n"
                    "Please provide an improved response."
                ),
                system_prompt=system_prompt,
                temperature=0.3,
            )
        except Exception as e:
            self.logger.warning("LLM improvement failed, using fallback: %s", e)
            improvements = critique.get("improvements", [])
            improved = f"{response}\n\n[개선사항 반영]\n"
            for imp in improvements:
                improved += f"- {imp}\n"
            return improved


__all__ = ["UnifiedDeepAgents", "DeepAgentsState"]
