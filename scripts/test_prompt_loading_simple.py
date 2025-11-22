"""프롬프트 로딩 간단 테스트 스크립트"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from utils.prompt_loader import get_prompt_loader


def test_prompt_loader():
    """PromptLoader 단위 테스트"""
    print("=" * 80)
    print("프롬프트 로더 테스트")
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

    total_tests = 0
    passed_tests = 0

    for agent_name in agents:
        print(f"\n[{agent_name}]")

        # 사용 가능한 프롬프트 목록
        available = loader.list_available_prompts(agent_name)
        print(f"  Available prompts: {', '.join(available)}")

        # 시스템 프롬프트 로드
        total_tests += 1
        try:
            system_prompt = loader.load(agent_name, "system")
            print(f"  ✓ System prompt loaded ({len(system_prompt)} chars)")
            print(f"    Preview: {system_prompt[:100].replace(chr(10), ' ')}...")
            passed_tests += 1
        except FileNotFoundError as e:
            print(f"  ✗ System prompt not found")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        # 기타 프롬프트 로드
        for prompt_type in available:
            if prompt_type != "system":
                total_tests += 1
                try:
                    prompt = loader.load(agent_name, prompt_type)
                    print(f"  ✓ {prompt_type} prompt loaded ({len(prompt)} chars)")
                    passed_tests += 1
                except Exception as e:
                    print(f"  ✗ {prompt_type} failed: {e}")

    # 변수 치환 테스트
    print("\n" + "=" * 80)
    print("변수 치환 테스트")
    print("=" * 80)

    print("\n[Search Agent - Search Prompt]")
    total_tests += 1
    try:
        prompt = loader.load(
            "search_agent",
            "search",
            query="크리에이터 등급",
            filters='{"grade": "Gold"}',
            search_results="결과1, 결과2, 결과3"
        )
        print(f"  ✓ Variables substituted")

        # 치환된 변수 확인
        if "크리에이터 등급" in prompt:
            print(f"  ✓ 'query' variable correctly substituted")
            passed_tests += 1
        else:
            print(f"  ✗ 'query' variable not substituted")

        # 일부 출력
        lines = prompt.split('\n')
        print(f"\n  First 10 lines:")
        for i, line in enumerate(lines[:10], 1):
            print(f"    {i:2d}: {line}")

    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()

    # 캐시 테스트
    print("\n" + "=" * 80)
    print("캐시 테스트")
    print("=" * 80)

    import time

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

    # 결과 요약
    print("\n" + "=" * 80)
    print(f"테스트 결과: {passed_tests}/{total_tests} 통과 ({100 * passed_tests / total_tests:.1f}%)")
    print("=" * 80)


def main():
    """메인 테스트 실행"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "프롬프트 로딩 시스템 테스트" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        test_prompt_loader()
        print("\n✓ 테스트 완료\n")

    except Exception as e:
        print(f"\n✗ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
