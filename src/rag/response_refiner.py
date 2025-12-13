from typing import Dict, Any, Optional
import logging
from .generation_engine import GenerationEngine

logger = logging.getLogger(__name__)


class ResponseRefiner:
    """
    Post-processing Layer (Wrtn Style).

    Refines the raw model output to ensure:
    1. Persona consistency (Friendly, Helpful, Professional).
    2. Fact/Safety verification (Hallucination Check).
    3. Structural formatting (Markdown).
    """

    def __init__(self, generation_engine: GenerationEngine):
        self.engine = generation_engine

    async def refine(
        self,
        raw_response: str,
        context: Optional[Dict[str, Any]] = None,
        style: str = "wrtn_friendly",
        check_hallucination: bool = False,
    ) -> str:
        """
        Refines the response using a fast model or heuristics.
        """
        if not raw_response:
            return ""

        # 1. Hallucination Check (Optional but recommended for key facts)
        if check_hallucination and context and context.get("retrieved_documents"):
            is_valid = await self._check_hallucination(
                raw_response, context["retrieved_documents"]
            )
            if not is_valid:
                logger.warning("Potential hallucination detected. Adding warning.")
                raw_response += "\n\n*(주의: 생성된 답변이 제공된 문서의 내용과 일치하지 않을 수 있습니다. 원본 출처를 확인해주세요.)*"

        # If the response is very short, maybe don't use LLM to save latency.
        if len(raw_response) < 50:
            return raw_response

        # Persona definition
        persona_instruction = """
        You are a Response Refiner. Your job is to polish the following AI response.
        
        Style Guidelines (Wrtn Persona):
        1. **Friendly & Helpful**: Use a warm, encouraging tone. (e.g., "안녕하세요!", "도움이 되셨나요?")
        2. **Professional**: Maintain accuracy but avoid overly stiff bureaucratic language.
        3. **Structured**: Use clear Markdown headers, bullet points, and bold text for key insights.
        4. **Korean Native**: Ensure natural Korean phrasing.
        
        Task:
        - Fix any formatting issues.
        - Add a polite opening/closing if missing.
        - Ensure the content answers the user's core intent.
        - Do NOT change the core facts or numbers.
        
        Original Response:
        """

        try:
            refined_response = await self.engine.generate(
                prompt=f"{persona_instruction}\n\n{raw_response}",
                # Always prefer the generation engine's fast model (keeps us aligned with fleet defaults)
                model_name=getattr(self.engine, "fast_model", "gpt-5-mini"),
                temperature=0.3,
            )
            return refined_response

        except Exception as e:
            logger.warning(f"Response refinement failed: {e}. Returning raw response.")
            return raw_response

    async def _check_hallucination(self, response: str, documents: list) -> bool:
        """
        Simple Self-Correction Check.
        Asks LLM if the response is supported by the documents.
        """
        try:
            docs_text = "\n".join([d.get("content", "")[:300] for d in documents[:3]])
            prompt = f"""
            Task: Verify if the Claim is supported by the Context.
            
            Context:
            {docs_text}
            
            Claim:
            {response[:1000]}
            
            Does the Context support the Claim? Answer only "YES" or "NO".
            """

            verification = await self.engine.generate(
                prompt=prompt,
                model_name=getattr(self.engine, "fast_model", "gpt-5-mini"),
                temperature=0.0,
            )

            return "YES" in verification.strip().upper()
        except Exception as e:
            logger.error(f"Hallucination check failed: {e}")
            return True  # Fail open to avoid blocking
