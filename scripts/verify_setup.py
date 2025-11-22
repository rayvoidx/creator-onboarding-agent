#!/usr/bin/env python3
"""
프로젝트 설정 검증 스크립트

이 스크립트는 LangGraph AI Learning System의 설정이 올바른지 확인합니다.
"""
import sys
import os
from urllib.parse import urlparse
from pathlib import Path

def check_python_version() -> bool:
    """Python 버전 확인"""
    print("🐍 Python 버전 확인...")
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 9:
        print(f"   ✓ Python {major}.{minor} (요구사항: 3.9+)")
        return True
    else:
        print(f"   ✗ Python {major}.{minor} (요구사항: 3.9+ 필요)")
        return False

def check_required_files() -> bool:
    """필수 파일 존재 확인"""
    print("\n📁 필수 파일 확인...")
    required_files = [
        'requirements.txt',
        'README.md',
        'src/core/base.py',
        'main.py',
        '.env',
        '.gitignore',
        'docs/INSTALL.md'
    ]

    all_exist = True
    for file in required_files:
        if Path(file).exists():
            print(f"   ✓ {file}")
        else:
            print(f"   ✗ {file} (파일 없음)")
            all_exist = False

    return all_exist

def check_file_naming() -> bool:
    """파일명 표준화 확인"""
    print("\n📝 파일명 표준화 확인...")

    # 하이픈이 있는 Python 파일 확인
    py_files = list(Path('.').glob('*.py'))
    invalid_files = [f for f in py_files if '-' in f.name]

    if invalid_files:
        print("   ✗ 하이픈이 포함된 파일 발견 (언더스코어 사용 권장):")
        for f in invalid_files:
            print(f"      - {f.name}")
        return False
    else:
        print("   ✓ 모든 Python 파일이 표준 명명 규칙을 따릅니다")
        return True

def check_imports() -> bool:
    """주요 패키지 임포트 확인"""
    print("\n📦 주요 패키지 임포트 확인...")

    packages = {
        'langgraph': 'LangGraph',
        'langchain': 'LangChain',
        'fastapi': 'FastAPI',
        'pydantic': 'Pydantic',
        'pandas': 'Pandas',
        'numpy': 'NumPy'
    }

    all_imported = True
    for package, name in packages.items():
        try:
            __import__(package)
            print(f"   ✓ {name}")
        except ImportError:
            print(f"   ✗ {name} (미설치)")
            all_imported = False

    return all_imported

def check_env_file() -> bool:
    """환경 변수 파일 확인"""
    print("\n🔐 환경 설정 확인...")

    if Path('.env').exists():
        print("   ✓ .env 존재")

        if Path('.env').exists():
            print("   ✓ .env 파일 존재")
            return True
        else:
            print("   ⚠ .env 파일 없음 (cp .env 실행 필요)")
            return False
    else:
        print("   ✗ .env 파일 없음")
        return False

def check_runtime_env() -> bool:
    """런타임 환경 변수 및 연결 문자열 기본 검증 (네트워크 미사용)"""
    print("\n⚙️  런타임 환경 변수 확인...")

    keys = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DATABASE_URL",
        "REDIS_URL",
        "CHROMA_DB_PATH",
        "ALLOWED_ORIGINS",
        "DEBUG",
    ]

    ok = True
    for k in keys:
        v = os.getenv(k, "")
        mark = "✓" if v else "⚠"
        print(f"   {mark} {k}: {'설정됨' if v else '미설정'}")

    # URL 파싱 유효성 (접속 시도 없음)
    for url_key in ["DATABASE_URL", "REDIS_URL"]:
        url = os.getenv(url_key, "")
        if not url:
            ok = False
            print(f"   ✗ {url_key} 미설정")
            continue
        parsed = urlparse(url)
        if not parsed.scheme:
            ok = False
            print(f"   ✗ {url_key} 스킴 없음: {url}")
        else:
            print(f"   ✓ {url_key} 형식 확인: {parsed.scheme}")

    # CORS 화이트리스트 최소 1개 확인
    allowed = os.getenv("ALLOWED_ORIGINS", "").strip()
    if not allowed:
        ok = False
        print("   ✗ ALLOWED_ORIGINS 미설정 (운영 시 필수)")
    else:
        print("   ✓ ALLOWED_ORIGINS 설정됨")

    # Chroma 경로 확인
    chroma_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    p = Path(chroma_path)
    try:
        p.mkdir(parents=True, exist_ok=True)
        print(f"   ✓ CHROMA_DB_PATH 접근 가능: {p}")
    except Exception as e:
        ok = False
        print(f"   ✗ CHROMA_DB_PATH 생성 실패: {e}")

    return ok

def check_project_structure() -> bool:
    """프로젝트 구조 확인"""
    print("\n🏗️  프로젝트 구조 확인...")

    key_files = [
        'src/core/base.py',
        'main.py',
        'src/agents/competency_agent.py',
        'src/agents/llm_manager_agent.py',
        'src/graphs/main_orchestrator.py'
    ]

    all_exist = True
    for file in key_files:
        if Path(file).exists():
            print(f"   ✓ {file}")
        else:
            print(f"   ✗ {file} (파일 없음)")
            all_exist = False

    return all_exist

def main() -> int:
    """메인 검증 함수"""
    print("="*60)
    print("LangGraph AI Learning System - 설정 검증")
    print("="*60)

    results = {
        'Python 버전': check_python_version(),
        '필수 파일': check_required_files(),
        '파일명 표준화': check_file_naming(),
        '환경 설정': check_env_file(),
        '프로젝트 구조': check_project_structure(),
        '런타임 환경': check_runtime_env(),
    }

    # 패키지 임포트는 선택사항 (설치 전에도 검증 가능하도록)
    print("\n" + "="*60)
    print("선택사항: 패키지 설치 확인")
    print("="*60)
    package_check = check_imports()

    print("\n" + "="*60)
    print("검증 결과 요약")
    print("="*60)

    for check, passed in results.items():
        status = "✓ 통과" if passed else "✗ 실패"
        print(f"{check}: {status}")

    if package_check:
        print("패키지 설치: ✓ 통과")
    else:
        print("패키지 설치: ⚠ 미설치 (pip install -r requirements.txt 실행)")

    all_passed = all(results.values())

    print("\n" + "="*60)
    if all_passed:
        print("🎉 모든 필수 검증을 통과했습니다!")
        if package_check:
            print("프로젝트 실행 준비가 완료되었습니다.")
        else:
            print("패키지 설치 후 프로젝트를 실행할 수 있습니다.")
        print("="*60)
        return 0
    else:
        print("⚠️  일부 검증에 실패했습니다. 위 내용을 확인해주세요.")
        print("="*60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
