import asyncio
import logging
from typing import Any, Dict, List

from ..rag.generation_engine import GenerationEngine

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Batch Processing Utility (Efficiency).
    Handles multiple similar requests in parallel or combined batches.
    """

    def __init__(self, generation_engine: GenerationEngine):
        self.engine = generation_engine

    async def process_batch(self, requests: List[Dict[str, Any]]) -> List[str]:
        """
        Processes a list of requests.
        Currently uses parallel execution (asyncio.gather).
        Future optimization: Combine short prompts into single API call if supported.
        """
        if not requests:
            return []

        tasks = []
        for req in requests:
            prompt = req.get("prompt")
            context = req.get("context")
            # Use engine's batch handling or individual generation
            tasks.append(self.engine.generate(prompt=prompt, context=context))

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions gracefully
            processed_results = []
            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"Batch item failed: {res}")
                    processed_results.append("Error processing request.")
                else:
                    processed_results.append(res)

            return processed_results

        except Exception as e:
            logger.error(f"Batch processing critical failure: {e}")
            return ["Error"] * len(requests)
