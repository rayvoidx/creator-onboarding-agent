import logging
from typing import List

from .generation_engine import GenerationEngine

logger = logging.getLogger(__name__)


class QueryExpander:
    """
    Query Expansion Module (Wrtn Style).
    Generates multiple search queries from a single user input to increase recall.
    """

    def __init__(self, generation_engine: GenerationEngine):
        self.engine = generation_engine

    async def expand_query(
        self, original_query: str, n_variations: int = 3
    ) -> List[str]:
        """
        Generates extended queries for broader search coverage.
        """
        system_prompt = f"""
        You are a Query Expander for an AI Search Engine.
        Your goal is to generate {n_variations} alternative search queries based on the user's input.
        These variations should cover different aspects, synonyms, or related technical terms to maximize search recall.
        
        Output format: Just the queries, one per line. No numbering, no prefixes.
        User Input: "{original_query}"
        """

        try:
            response = await self.engine.generate(
                prompt=f"Generate {n_variations} variations.",
                system_prompt=system_prompt,
                # Keep model selection centralized in GenerationEngine settings
                model_name=getattr(self.engine, "fast_model", "gpt-5-mini"),
                temperature=0.5,
            )

            variations = [line.strip() for line in response.split("\n") if line.strip()]

            # Ensure original query is included and is first
            unique_queries = [original_query]
            for v in variations:
                if v and v != original_query and v not in unique_queries:
                    unique_queries.append(v)

            return unique_queries[: n_variations + 1]

        except Exception as e:
            logger.warning(f"Query expansion failed: {e}")
            return [original_query]
