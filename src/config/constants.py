"""
Application constants.

Defines static values used throughout the application.
"""

# Application info
APP_NAME = "AI Learning System API"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "LangGraph 기반 자체 학습형 하이브리드 AI 교육 솔루션"

# API configuration
API_V1_PREFIX = "/api/v1"

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Rate limiting
DEFAULT_RATE_LIMIT_REQUESTS = 100
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60

# Cache TTL (seconds)
DEFAULT_CACHE_TTL = 300
LONG_CACHE_TTL = 3600

# File upload limits
MAX_FILE_SIZE_MB = 10
ALLOWED_FILE_EXTENSIONS = {".pdf", ".txt", ".md", ".doc", ".docx"}

# LLM configuration
MAX_TOKENS_DEFAULT = 4096
MAX_CONTEXT_LENGTH = 128000
TEMPERATURE_DEFAULT = 0.7

# RAG configuration
DEFAULT_VECTOR_WEIGHT = 0.7
DEFAULT_KEYWORD_WEIGHT = 0.3
DEFAULT_MAX_RETRIEVAL_DOCS = 10
DEFAULT_RERANK_TOP_K = 5

# Circuit breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 60
CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS = 3

# Agent types
AGENT_TYPES = [
    "general",
    "competency",
    "recommendation",
    "search",
    "analytics",
    "mission",
    "rag",
    "deep_agents",
]

# Creator evaluation grades
CREATOR_GRADES = ["S", "A", "B", "C", "D", "F"]

# Mission types
MISSION_TYPES = [
    "content_creation",
    "review",
    "campaign",
    "collaboration",
    "event",
]

# Workflow types
WORKFLOW_TYPES = [
    "competency",
    "recommendation",
    "search",
    "analytics",
    "mission",
]
