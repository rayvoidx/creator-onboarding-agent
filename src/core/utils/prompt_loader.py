"""마크다운 프롬프트 파일 로더"""

import os
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PromptLoader:
    """
    에이전트별 마크다운 프롬프트 파일을 로드하는 유틸리티 클래스

    프롬프트 파일 구조:
    src/agents/{agent_name}/prompts/
        - system.md: 시스템 프롬프트
        - {action}.md: 액션별 프롬프트 (search.md, analyze.md 등)

    사용 예시:
        loader = PromptLoader()
        system_prompt = loader.load("search_agent", "system")
        search_prompt = loader.load("search_agent", "search", query="test", filters={})
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Args:
            base_path: 에이전트 디렉토리의 기본 경로. None이면 자동 탐지
        """
        if base_path is None:
            # src/utils에서 src/agents로 이동
            current_file = Path(__file__)
            self.base_path = current_file.parent.parent / "agents"
        else:
            self.base_path = Path(base_path)

        self._cache: Dict[str, str] = {}
        self._cache_enabled = True

        logger.info(f"PromptLoader initialized with base_path: {self.base_path}")

    def load(
        self, agent_name: str, prompt_type: str, use_cache: bool = True, **variables
    ) -> str:
        """
        특정 에이전트의 프롬프트 파일을 로드하고 변수를 치환합니다.

        Args:
            agent_name: 에이전트 이름 (예: "search_agent")
            prompt_type: 프롬프트 타입 (예: "system", "search", "analyze")
            use_cache: 캐시 사용 여부 (기본값: True)
            **variables: 프롬프트 내 변수 치환용 키워드 인자

        Returns:
            로드되고 변수가 치환된 프롬프트 문자열

        Raises:
            FileNotFoundError: 프롬프트 파일이 존재하지 않는 경우
        """
        cache_key = f"{agent_name}/{prompt_type}"

        # 캐시 확인
        if use_cache and self._cache_enabled and cache_key in self._cache:
            template = self._cache[cache_key]
        else:
            # 파일 경로 구성
            prompt_file = self.base_path / agent_name / "prompts" / f"{prompt_type}.md"

            if not prompt_file.exists():
                error_msg = f"Prompt file not found: {prompt_file}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            # 파일 읽기
            try:
                with open(prompt_file, "r", encoding="utf-8") as f:
                    template = f.read()

                # 캐시 저장
                if self._cache_enabled:
                    self._cache[cache_key] = template

                logger.debug(f"Loaded prompt: {cache_key}")

            except Exception as e:
                logger.error(f"Error loading prompt file {prompt_file}: {e}")
                raise

        # 변수 치환
        if variables:
            try:
                # 안전한 변수 치환 (KeyError 방지)
                # 제공되지 않은 변수는 그대로 유지
                import string

                class SafeFormatter(string.Formatter):
                    def get_value(self, key, args, kwargs):
                        if isinstance(key, str):
                            return kwargs.get(key, "{" + key + "}")
                        else:
                            return super().get_value(key, args, kwargs)

                formatter = SafeFormatter()
                return formatter.format(template, **variables)

            except Exception as e:
                logger.warning(f"Error formatting prompt with variables: {e}")
                # 변수 치환 실패 시 원본 템플릿 반환
                return template

        return template

    def load_agent_prompts(self, agent_name: str) -> Dict[str, str]:
        """
        특정 에이전트의 모든 프롬프트 파일을 로드합니다.

        Args:
            agent_name: 에이전트 이름

        Returns:
            {prompt_type: prompt_content} 딕셔너리
        """
        prompts = {}
        prompts_dir = self.base_path / agent_name / "prompts"

        if not prompts_dir.exists():
            logger.warning(f"Prompts directory not found for agent: {agent_name}")
            return prompts

        # 모든 .md 파일 읽기
        for prompt_file in prompts_dir.glob("*.md"):
            prompt_type = prompt_file.stem  # 파일명에서 확장자 제거
            try:
                prompts[prompt_type] = self.load(
                    agent_name, prompt_type, use_cache=True
                )
            except Exception as e:
                logger.error(f"Failed to load {agent_name}/{prompt_type}: {e}")

        logger.info(f"Loaded {len(prompts)} prompts for {agent_name}")
        return prompts

    def clear_cache(self):
        """프롬프트 캐시를 초기화합니다."""
        self._cache.clear()
        logger.info("Prompt cache cleared")

    def disable_cache(self):
        """캐시를 비활성화합니다 (개발/테스트용)."""
        self._cache_enabled = False
        logger.info("Prompt cache disabled")

    def enable_cache(self):
        """캐시를 활성화합니다."""
        self._cache_enabled = True
        logger.info("Prompt cache enabled")

    def list_available_prompts(self, agent_name: str) -> list[str]:
        """
        특정 에이전트에서 사용 가능한 프롬프트 타입 목록을 반환합니다.

        Args:
            agent_name: 에이전트 이름

        Returns:
            사용 가능한 프롬프트 타입 리스트
        """
        prompts_dir = self.base_path / agent_name / "prompts"

        if not prompts_dir.exists():
            return []

        return [f.stem for f in prompts_dir.glob("*.md")]

    def validate_prompts(self, agent_name: str, required_prompts: list[str]) -> bool:
        """
        에이전트에 필요한 프롬프트 파일이 모두 존재하는지 검증합니다.

        Args:
            agent_name: 에이전트 이름
            required_prompts: 필수 프롬프트 타입 리스트

        Returns:
            모든 필수 프롬프트가 존재하면 True, 아니면 False
        """
        available = self.list_available_prompts(agent_name)
        missing = [p for p in required_prompts if p not in available]

        if missing:
            logger.warning(f"Missing prompts for {agent_name}: {missing}")
            return False

        return True


# 싱글톤 인스턴스
_prompt_loader_instance: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """
    PromptLoader 싱글톤 인스턴스를 반환합니다.

    Returns:
        PromptLoader 인스턴스
    """
    global _prompt_loader_instance

    if _prompt_loader_instance is None:
        _prompt_loader_instance = PromptLoader()

    return _prompt_loader_instance
