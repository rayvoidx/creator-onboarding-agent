"""프롬프트 로딩 테스트 스크립트"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from utils.prompt_loader import get_prompt_loader
from rag.prompt_templates import PromptTemplates, PromptType


def test_prompt_loader():
    """PromptLoader 단위 테스트"""
    print("=" * 80)
    print("1. PromptLoader 테스트")
    print("=" * 80)

    loader = get_prompt_loader()

    # 각 에이전트별 프롬프트 로딩 테스트
    agents = [
        "search_agent",
        "analytics_agent",
        "competency_agent",
        "recommendation_agent",
        "data_collection_agent",
        "creator_onboarding_agent"
    ]

    for agent_name in agents:
        print(f"\n[{agent_name}]")

        # 사용 가능한 프롬프트 목록
        available = loader.list_available_prompts(agent_name)
        print(f"  Available prompts: {', '.join(available)}")

        # 시스템 프롬프트 로드
        try:
            system_prompt = loader.load(agent_name, "system")
            print(f"  ✓ System prompt loaded ({len(system_prompt)} chars)")
            print(f"    Preview: {system_prompt[:100]}...")
        except FileNotFoundError as e:
            print(f"  ✗ System prompt not found: {e}")

        # 기타 프롬프트 로드
        for prompt_type in available:
            if prompt_type != "system":
                try:
                    prompt = loader.load(agent_name, prompt_type)
                    print(f"  ✓ {prompt_type} prompt loaded ({len(prompt)} chars)")
                except Exception as e:
                    print(f"  ✗ {prompt_type} failed: {e}")


def test_prompt_templates_integration():
    """PromptTemplates 통합 테스트"""
    print("\n" + "=" * 80)
    print("2. PromptTemplates 통합 테스트")
    print("=" * 80)

    templates = PromptTemplates()

    test_cases = [
        {
            "name": "Search Agent",
            "prompt_type": PromptType.SEARCH,
            "variables": {
                "query": "크리에이터 온보딩",
                "filters": {"category": "onboarding"},
                "search_results": [{"title": "Test", "content": "Sample content"}]
            }
        },
        {
            "name": "Analytics Agent",
            "prompt_type": PromptType.ANALYTICS,
            "variables": {
                "report_type": "learning_progress",
                "date_range": "2025-01-01 to 2025-01-31",
                "analytics_data": {"completions": 10},
                "user_data": {"user_id": "user123"}
            }
        },
        {
            "name": "Competency Agent",
            "prompt_type": PromptType.COMPETENCY_ASSESSMENT,
            "variables": {
                "user_responses": "사용자 응답 샘플",
                "competency_data": {"level": "intermediate"},
                "context": "평가 맥락"
            }
        },
        {
            "name": "Recommendation Agent",
            "prompt_type": PromptType.RECOMMENDATION,
            "variables": {
                "competency_level": "intermediate",
                "learning_preferences": "video, interactive",
                "interests": ["content creation", "marketing"],
                "learning_goals": "크리에이터로 성장하기",
                "retrieved_documents": "문서1, 문서2"
            }
        }
    ]

    for test_case in test_cases:
        print(f"\n[{test_case['name']}]")
        try:
            prompt = templates.get_prompt(
                test_case['prompt_type'],
                **test_case['variables']
            )
            print(f"  ✓ Prompt generated ({len(prompt)} chars)")
            print(f"    Preview: {prompt[:150].replace(chr(10), ' ')}...")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

    # 시스템 프롬프트 테스트
    print(f"\n[System Prompts]")
    for agent_name in ["search_agent", "analytics_agent", "competency_agent"]:
        try:
            system_prompt = templates.get_system_prompt(agent_name=agent_name)
            print(f"  ✓ {agent_name} system prompt ({len(system_prompt)} chars)")
        except Exception as e:
            print(f"  ✗ {agent_name} failed: {e}")


def test_variable_substitution():
    """변수 치환 테스트"""
    print("\n" + "=" * 80)
    print("3. 변수 치환 테스트")
    print("=" * 80)

    loader = get_prompt_loader()

    # 변수가 있는 프롬프트 테스트
    print("\n[Search Agent - Search Prompt]")
    try:
        prompt = loader.load(
            "search_agent",
            "search",
            query="크리에이터 등급",
            filters={"grade": "Gold"},
            search_results="결과1, 결과2, 결과3"
        )
        print(f"  ✓ Variables substituted")
        print(f"    Preview: {prompt[:200].replace(chr(10), ' ')}...")

        # 치환된 변수 확인
        if "{query}" in prompt:
            print(f"  ⚠ Warning: {{query}} not substituted")
        if "크리에이터 등급" in prompt:
            print(f"  ✓ 'query' variable correctly substituted")

    except Exception as e:
        print(f"  ✗ Failed: {e}")


def test_cache_performance():
    """캐시 성능 테스트"""
    print("\n" + "=" * 80)
    print("4. 캐시 성능 테스트")
    print("=" * 80)

    import time

    loader = get_prompt_loader()

    # 캐시 없이 로드
    loader.clear_cache()
    loader.disable_cache()

    start = time.time()
    for _ in range(100):
        loader.load("search_agent", "system", use_cache=False)
    no_cache_time = time.time() - start

    print(f"  No cache (100 loads): {no_cache_time:.4f}s")

    # 캐시 사용
    loader.enable_cache()
    loader.clear_cache()

    start = time.time()
    for _ in range(100):
        loader.load("search_agent", "system", use_cache=True)
    cache_time = time.time() - start

    print(f"  With cache (100 loads): {cache_time:.4f}s")
    print(f"  Speed improvement: {no_cache_time / cache_time:.1f}x faster")


def main():
    """메인 테스트 실행"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "프롬프트 로딩 시스템 테스트" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        test_prompt_loader()
        test_prompt_templates_integration()
        test_variable_substitution()
        test_cache_performance()

        print("\n" + "=" * 80)
        print("✓ 모든 테스트 완료")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
