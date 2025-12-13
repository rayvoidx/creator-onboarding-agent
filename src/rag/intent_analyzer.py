from typing import Dict, Any, List, Optional
import json
import logging
from enum import Enum
from .generation_engine import GenerationEngine

logger = logging.getLogger(__name__)

class UserIntent(Enum):
    COMPETENCY_ASSESSMENT = "competency_assessment"
    RECOMMENDATION = "recommendation"
    SEARCH = "search"
    ANALYTICS = "analytics"
    DATA_COLLECTION = "data_collection"
    MISSION_MATCHING = "mission_matching"
    GENERAL_CHAT = "general_chat"
    UNKNOWN = "unknown"

class IntentAnalyzer:
    """
    Semantic Intent Analyzer (Routing Layer).
    
    Replaces simple keyword matching with SLM-based intent classification.
    Optimized for Latency (Target < 0.1s logic overhead + fast model inference).
    """

    def __init__(self, generation_engine: GenerationEngine):
        self.engine = generation_engine
        
    async def analyze_intent(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyzes the user query to determine intent and extract entities.
        Uses the 'fast_model' (SLM/Llama-3-8B equivalent) for minimal latency.
        """
        system_prompt = """
        You are an intelligent router (Gateway) for a Creator Onboarding System.
        Analyze the user's input and classify it into one of the following intents.
        
        Intents:
        - competency_assessment: Diagnose/evaluate skills.
        - recommendation: Learning materials/courses.
        - search: Fact retrieval/documents.
        - analytics: Reports/stats.
        - data_collection: Scrape/fetch data.
        - mission_matching: Brand missions.
        - general_chat: Greetings/other.
        
        Output JSON only: {"intent": "...", "confidence": 0.0-1.0, "reasoning": "..."}
        """
        
        try:
            # 2025 Strategy: Use SLM (Fast Model) for Classification
            response = await self.engine.generate(
                prompt=f"User Input: {query}",
                system_prompt=system_prompt,
                model_name=self.engine.fast_model, # Explicitly use fast model (SLM)
                temperature=0.0
            )
            
            # Clean code block markers if present
            cleaned = response.replace("```json", "").replace("```", "").strip()
            result = json.loads(cleaned)
            
            # Validation
            intent_str = result.get("intent", "general_chat")
            try:
                # Normalize intent string to Enum
                if intent_str == "competency": intent_str = "competency_assessment"
                if intent_str == "mission": intent_str = "mission_matching"
                
                # Check against Enum values
                if intent_str not in [e.value for e in UserIntent]:
                     intent_str = "general_chat"
                     
                result["intent"] = intent_str
            except Exception:
                result["intent"] = "general_chat"
                
            return result
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return {
                "intent": "general_chat",
                "confidence": 0.0,
                "error": str(e)
            }
