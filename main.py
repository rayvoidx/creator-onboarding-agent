"""
FastAPI 기반 메인 API 애플리케이션

LangGraph를 활용한 AI 챗봇 학습 시스템의 REST API를 제공합니다.
KICCE 외부 API 연동 및 GPT 기반 대화형 학습 기능을 제공합니다.

NOTE: 이 파일은 하위 호환성을 위해 유지됩니다.
새로운 진입점은 src/app/main.py를 사용하세요.
"""

# Re-export from new location for backward compatibility
from src.app import app, create_app

# Also support direct import of app for uvicorn
__all__ = ["app", "create_app"]

if __name__ == "__main__":
    import uvicorn
    from config.settings import get_settings

    settings = get_settings()
    uvicorn.run(
        "src.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
