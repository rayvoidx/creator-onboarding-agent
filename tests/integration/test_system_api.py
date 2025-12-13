import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient

from config.settings import get_settings
from src.app.main import create_app


def test_agent_model_status_endpoint() -> None:
    # Recreate app with ENABLE_AUTH=false to bypass AuthMiddleware
    with patch.dict(os.environ, {"ENABLE_AUTH": "false"}):
        # Reset settings singleton to force reload env vars
        # Direct access via sys.modules to avoid import attribute issues
        if "config.settings" in sys.modules:
            sys.modules["config.settings"]._settings = None

        test_app = create_app()
        client = TestClient(test_app)

        response = client.get("/api/v1/system/agent-models")
        assert response.status_code == 200

        data = response.json()
        assert "agent_models" in data
        assert "llm_status" in data
        assert "timestamp" in data

        agent_models = data["agent_models"]
        assert isinstance(agent_models, dict)

        settings = get_settings()
        configs = settings.AGENT_MODEL_CONFIGS

        # 대표 워크플로우 구성이 노출되는지 검증
        for key in ("mission", "analytics", "rag"):
            assert key in agent_models
            assert agent_models[key] == configs.get(key)

        # LLM 상태는 orchestrator 초기화 여부에 따라 비어 있을 수 있으므로 타입만 확인
        assert isinstance(data["llm_status"], dict)
