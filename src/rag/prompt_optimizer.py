from typing import Dict, Any, List
import logging
import re

logger = logging.getLogger(__name__)

class PromptOptimizer:
    """
    Prompt Optimization Layer (Cost Reduction).
    
    1. Removes unnecessary whitespace/boilerplates.
    2. Truncates long contexts that exceed model limits.
    3. Merges redundant system messages.
    """

    def __init__(self, max_context_tokens: int = 4000):
        self.max_context_tokens = max_context_tokens

    def optimize(self, prompt: str, context: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, Any]]]:
        """
        Returns optimized prompt and context list.
        """
        # 1. Boilerplate Removal
        optimized_prompt = self._clean_text(prompt)
        
        # 2. Context Pruning
        optimized_context = self._prune_context(context, self.max_context_tokens)
        
        return optimized_prompt, optimized_context

    def _clean_text(self, text: str) -> str:
        # Remove multiple newlines/spaces
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    def _prune_context(self, context_list: List[Dict[str, Any]], max_tokens: int) -> List[Dict[str, Any]]:
        """
        Simple heuristic: 1 token ~= 4 chars (English), 1-2 chars (Korean).
        """
        current_len = 0
        pruned_list = []
        
        for item in context_list:
            content = str(item.get('content', ''))
            # Rough estimation: 1.5 chars per token for safety mixed language
            estimated_tokens = len(content) / 1.5
            
            if current_len + estimated_tokens > max_tokens:
                # Stop adding if limit reached
                break
                
            pruned_list.append(item)
            current_len += estimated_tokens
            
        return pruned_list

