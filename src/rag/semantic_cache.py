from typing import Optional, Dict, Any, List
import logging
import json
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SemanticCache:
    """
    Semantic Cache Layer (Cost & Latency Optimization).
    
    Stores:
    1. Query Embeddings -> Retrieval Results (Avoids searching)
    2. Exact Queries -> Final LLM Responses (Avoids generation)
    """

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        # In-memory cache for demo (In prod, use Redis)
        self._cache: Dict[str, Dict[str, Any]] = {}
        # Simple similarity threshold
        self.similarity_threshold = 0.95 

    async def get_cached_response(self, query: str, query_embedding: Optional[List[float]] = None) -> Optional[str]:
        """
        Tries to find a cached response for the query.
        1. Exact match first.
        2. Semantic match if embedding provided (TODO).
        """
        # 1. Exact Match
        key = self._hash_query(query)
        if key in self._cache:
            entry = self._cache[key]
            if not self._is_expired(entry):
                logger.info(f"Cache Hit (Exact): {query[:20]}...")
                return entry['response']
            else:
                del self._cache[key]
        
        # 2. Semantic Match (Simplified for in-memory)
        # Real semantic cache would use a Vector DB for the cache keys
        
        return None

    async def cache_response(self, query: str, response: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Saves the response to cache.
        """
        key = self._hash_query(query)
        self._cache[key] = {
            'response': response,
            'metadata': metadata or {},
            'timestamp': datetime.now(),
            'expires_at': datetime.now() + timedelta(seconds=self.ttl)
        }

    def _hash_query(self, query: str) -> str:
        return hashlib.md5(query.strip().lower().encode()).hexdigest()

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        return datetime.now() > entry['expires_at']
        
    def clear(self):
        self._cache.clear()

