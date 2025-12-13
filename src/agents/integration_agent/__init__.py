"""
Integration Agent - 외부 서비스 통합 에이전트

외부 API 연동 및 데이터 통합을 담당합니다.
"""

from typing import Dict, Any, Optional, List
from pydantic import Field
import logging

from ..base import BaseAgent
from ...core.base import BaseState

logger = logging.getLogger(__name__)


class IntegrationState(BaseState):
    """통합 에이전트 상태"""

    integration_type: Optional[str] = None
    integration_config: Dict[str, Any] = Field(default_factory=dict)
    integration_results: Dict[str, Any] = Field(default_factory=dict)
    external_data: List[Dict[str, Any]] = Field(default_factory=list)
    success: bool = False


class IntegrationAgent(BaseAgent):
    """외부 서비스 통합 에이전트"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("IntegrationAgent")

    async def execute(self, state: IntegrationState) -> IntegrationState:
        """통합 에이전트 실행"""
        try:
            self.logger.info("Starting integration agent execution")

            integration_type = state.integration_type or state.context.get(
                "integration_type", "default"
            )

            # 통합 타입에 따른 처리
            if integration_type == "api":
                result = await self._process_api_integration(state)
            elif integration_type == "webhook":
                result = await self._process_webhook_integration(state)
            elif integration_type == "batch":
                result = await self._process_batch_integration(state)
            else:
                result = await self._process_default_integration(state)

            state.integration_results = result
            state.success = True

            self.logger.info(f"Integration completed: {integration_type}")

        except Exception as e:
            self.logger.error(f"Integration failed: {e}")
            state.add_error(f"통합 처리 실패: {str(e)}")
            state.success = False

        return state

    async def _process_api_integration(self, state: IntegrationState) -> Dict[str, Any]:
        """API 통합 처리"""
        return {
            "type": "api",
            "status": "completed",
            "data": state.context.get("api_data", {}),
        }

    async def _process_webhook_integration(
        self, state: IntegrationState
    ) -> Dict[str, Any]:
        """Webhook 통합 처리"""
        return {
            "type": "webhook",
            "status": "completed",
            "data": state.context.get("webhook_data", {}),
        }

    async def _process_batch_integration(
        self, state: IntegrationState
    ) -> Dict[str, Any]:
        """배치 통합 처리"""
        return {
            "type": "batch",
            "status": "completed",
            "data": state.context.get("batch_data", {}),
        }

    async def _process_default_integration(
        self, state: IntegrationState
    ) -> Dict[str, Any]:
        """기본 통합 처리"""
        return {
            "type": "default",
            "status": "completed",
            "data": state.context.get("data", {}),
        }


__all__ = ["IntegrationAgent", "IntegrationState"]
