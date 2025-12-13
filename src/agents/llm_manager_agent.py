"""
LLM Manager Agent (2025 Compound AI).

- Goal: centralize model selection (cost/latency aware) for downstream agents.
- Design: "Planner makes a JSON plan, Manager selects models, Workers execute".
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage  # type: ignore[import-not-found]

from config.settings import get_settings
from src.core.base import BaseState
from src.tools.llm_tools import ModelSelector


class LLMManagerState(BaseState):
    """State for model selection / routing decisions."""

    task_type: str = "general"
    messages: List[BaseMessage] = []
    context: Dict[str, Any] = {}

    selected_model: Optional[str] = None
    model_selection_reason: str = ""


class LLMManagerAgent:
    """
    Picks the best model for the current task given:
    - task_type (routing/planning/coding/rag/general...)
    - plan outputs (cost_preference/complexity/needs_tools/needs_rag)
    - token budget approximation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.settings = get_settings()
        self.selector = ModelSelector()

    async def execute(self, state: LLMManagerState) -> LLMManagerState:
        start = time.time()
        try:
            latest = state.messages[-1] if state.messages else None
            text = ""
            if latest is not None:
                text = latest.content if hasattr(latest, "content") else str(latest)
                if not isinstance(text, str):
                    text = str(text)

            plan = state.context.get("plan") if isinstance(state.context, dict) else None
            if not isinstance(plan, dict):
                plan = {}

            cost_preference = plan.get("cost_preference") or state.context.get("cost_preference") or "balanced"
            if cost_preference not in ("budget", "balanced", "performance", "speed"):
                cost_preference = "balanced"

            complexity = plan.get("complexity") or ("high" if len(text) > 200 else "medium")
            if complexity not in ("simple", "medium", "high"):
                complexity = "medium"

            # heuristic token estimate (very rough)
            max_tokens = 1200 if complexity == "simple" else (2400 if complexity == "medium" else 6000)

            criteria = {
                "task_type": state.task_type or plan.get("workflow_type") or "general",
                "priority": "cost" if cost_preference == "budget" else ("speed" if cost_preference == "speed" else "balanced"),
                "max_tokens": max_tokens,
            }

            selected = await self.selector.select_model(criteria)
            state.selected_model = selected
            state.model_selection_reason = (
                f"task={criteria['task_type']}, priority={criteria['priority']}, "
                f"complexity={complexity}, max_tokens={max_tokens}"
            )

            # Expose to downstream nodes
            state.context = dict(state.context or {})
            state.context["selected_llm_model"] = selected
            state.context["cost_preference"] = cost_preference
            state.context["complexity"] = complexity
            state.context["execution_time"] = round((time.time() - start) * 1000)
            return state
        except Exception as exc:
            state.selected_model = state.selected_model or self.settings.DEFAULT_LLM_MODEL
            state.model_selection_reason = f"fallback_due_to_error: {exc}"
            state.context = dict(state.context or {})
            state.context["selected_llm_model"] = state.selected_model
            state.context["execution_time"] = round((time.time() - start) * 1000)
            return state


