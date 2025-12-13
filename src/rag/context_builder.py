from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ContextPromptBuilder:
    """
    Wrtn-style Context Prompt Builder (Preprocessing Layer).

    Responsible for assembling a rich, structured context prompt from various sources
    (User Profile, System State, Retrieved Documents, Session History).

    [2025 Optimization]
    - Long-Context Support: Optimized for 1M+ token windows (Gemini 1.5 Pro).
    - Intelligent Summarization: Summarizes redundant docs if context exceeds limit.
    """

    def __init__(self, max_context_tokens: int = 128000):
        self.max_context_tokens = max_context_tokens

    def build_context_prompt(
        self,
        query: str,
        user_context: Dict[str, Any],
        system_context: Optional[Dict[str, Any]] = None,
        retrieved_docs: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        agent_specific_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Builds a comprehensive context prompt string.
        """
        parts = []

        # 1. System/Meta Context (Time, Environment)
        parts.append(self._build_system_section(system_context))

        # 2. User Profile Context
        parts.append(self._build_user_section(user_context))

        # 3. Agent/Task Specific Context
        if agent_specific_context:
            parts.append(self._build_agent_section(agent_specific_context))

        # 4. Retrieved Knowledge (RAG) - Optimized for Long Context
        if retrieved_docs:
            parts.append(self._build_retrieval_section(retrieved_docs))

        # 5. Conversation History
        if history:
            parts.append(self._build_history_section(history))

        # 6. The Current Query (The "Trigger")
        parts.append(self._build_query_section(query))

        return "\n\n".join(filter(None, parts))

    def _build_system_section(self, context: Optional[Dict[str, Any]]) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "### System Context",
            f"- Current Time: {now}",
            f"- OS/Environment: {context.get('os', 'Unknown') if context else 'Unknown'}",
        ]
        return "\n".join(lines)

    def _build_user_section(self, user_context: Dict[str, Any]) -> str:
        if not user_context:
            return ""

        lines = ["### User Profile"]
        for k, v in user_context.items():
            if v:
                lines.append(f"- {k.replace('_', ' ').title()}: {v}")
        return "\n".join(lines)

    def _build_agent_section(self, context: Dict[str, Any]) -> str:
        if not context:
            return ""

        lines = ["### Task Context"]
        for k, v in context.items():
            if isinstance(v, (str, int, float, bool)):
                lines.append(f"- {k}: {v}")
            elif isinstance(v, list) and v and isinstance(v[0], str):
                lines.append(f"- {k}: {', '.join(v)}")
        return "\n".join(lines)

    def _build_retrieval_section(self, docs: List[Dict[str, Any]]) -> str:
        if not docs:
            return ""

        lines = ["### Retrieved Information (Reference Material)"]

        total_chars = 0
        limit_chars = self.max_context_tokens * 4  # Approximation (4 chars ≈ 1 token)

        def clip(text: str, max_len: int) -> str:
            if not text:
                return ""
            if len(text) <= max_len:
                return text
            # Preserve head + tail for better "raw" context fidelity
            head = max(0, int(max_len * 0.7))
            tail = max(0, max_len - head - 40)
            return (
                f"{text[:head]}\n...\n[TRUNCATED]\n...\n{text[-tail:]}"
                if tail > 0
                else f"{text[:max_len]}\n...\n[TRUNCATED]"
            )

        # 2025: Prefer keeping raw content, but enforce a per-doc cap so we don't drop *all* remaining docs.
        per_doc_cap = int((limit_chars * 0.65) / max(1, min(len(docs), 6)))
        per_doc_cap = max(800, min(per_doc_cap, 8000))

        for i, doc in enumerate(docs, 1):
            content = doc.get("content") or doc.get("page_content", "")
            metadata = doc.get("metadata", {})
            source = metadata.get("source", "Unknown")

            raw = content if isinstance(content, str) else str(content)
            safe_content = clip(raw, per_doc_cap)
            doc_str = f"[{i}] Source: {source}\nContent: {safe_content}\n"

            if total_chars + len(doc_str) > limit_chars:
                lines.append(
                    f"\n... (Context budget reached. Remaining {len(docs) - i + 1} documents omitted.) ..."
                )
                break

            lines.append(doc_str)
            total_chars += len(doc_str)

        lines.append(
            "\n*Note: Use the above information to answer. If the answer is not found, state that you don't know based on the provided context.*"
        )
        return "\n".join(lines)

    def _build_history_section(self, history: List[Dict[str, str]]) -> str:
        if not history:
            return ""

        lines = ["### Conversation History"]
        # Limit to last 20 messages (Increased for better context)
        recent = history[-20:]
        for msg in recent:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _build_query_section(self, query: str) -> str:
        return f"### Current User Query\n{query}"
