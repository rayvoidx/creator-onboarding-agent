from typing import Dict, Any, Optional
import logging
from ..rag.generation_engine import GenerationEngine

logger = logging.getLogger(__name__)


class LLMManager:
    """
    Intelligent Routing Manager (Cost & Latency Aware).
    Decides which model to use based on user tier, query complexity, and system load.
    Reflects 2025 Trend: Uses SLM for routing and High-Intelligence models for planning.
    """

    def __init__(self, generation_engine: GenerationEngine):
        self.engine = generation_engine

    def route_request(
        self,
        user_tier: str,
        complexity: str,
        task_type: str = "general",
        cost_preference: str = "balanced",
    ) -> Dict[str, str]:
        """
        Determines the optimal model configuration based on 2025 Architecture.

        Args:
            user_tier: 'free' | 'pro'
            complexity: 'simple' | 'medium' | 'high'
            task_type: 'routing' | 'planning' | 'coding' | 'rag' | 'general'
            cost_preference: 'budget' | 'balanced' | 'performance' | 'speed'
        """

        # Default Configuration
        routing_config = {
            "model_name": self.engine.default_model,
            "cost_hint": "balanced",
            "latency_hint": "normal",
        }

        # 1. Router & Gateway (SLM - Llama 3 8B equivalent)
        if task_type == "routing":
            # In 2025, use extremely fast/cheap models for classification
            # fast_model should map to something like gpt-5-mini / gemini-2.5-flash or a local SLM
            routing_config["model_name"] = self.engine.fast_model
            routing_config["cost_hint"] = "budget"
            routing_config["latency_hint"] = "fast"
            return routing_config

        # 2. Reasoning & Planning (System 2 - o1 / Claude 3.5 Sonnet)
        if task_type == "planning" or complexity == "high":
            # For complex reasoning, use the "Deep" model (e.g. o1-preview, Claude 3.5 Sonnet)
            # Only use if user tier permits or system requires it
            if user_tier == "pro" or cost_preference == "performance":
                routing_config["model_name"] = self.engine.deep_model
                routing_config["cost_hint"] = "premium"
                routing_config["latency_hint"] = "slow"  # Reasoning takes time
                return routing_config

        # 3. Tool Execution & Action (Coding/Function Calling optimized)
        if task_type == "coding":
            # Use models strong in code generation
            routing_config["model_name"] = (
                self.engine.deep_model
            )  # Often coincides with smart models
            return routing_config

        # 4. RAG & Knowledge (Long Context - Gemini 2.5 Pro / GPT-5.x)
        if task_type == "rag":
            # If context is massive, prefer models with large context windows and lower cost per token
            # Here we default to 'default_model' but in a real setup we might select specific long-ctx model
            routing_config["model_name"] = self.engine.default_model
            if cost_preference == "budget":
                routing_config["model_name"] = self.engine.fast_model

        # 5. General Fallback Logic
        if user_tier == "free":
            routing_config["model_name"] = self.engine.fast_model
            routing_config["cost_hint"] = "budget"
            routing_config["latency_hint"] = "fast"

        elif user_tier == "pro":
            if cost_preference == "speed":
                routing_config["model_name"] = self.engine.fast_model
                routing_config["latency_hint"] = "fast"

        logger.info(
            f"Routed request: Tier={user_tier}, Task={task_type}, Complexity={complexity} -> Model={routing_config['model_name']}"
        )
        return routing_config
