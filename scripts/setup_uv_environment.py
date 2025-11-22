#!/usr/bin/env python3
"""
UV 환경 설정 스크립트

Deep Agents를 포함한 LangGraph AI 학습 시스템의 UV 환경을 설정합니다.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """명령어 실행"""
    print(f"🔄 {description}...")
    try:
        proc = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} 완료")
        if proc.stdout:
            print(proc.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 실패: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_uv_installed():
    """UV 설치 확인"""
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_uv():
    """UV 설치"""
    print("📦 UV 설치 중...")
    
    # pip로 UV 설치
    if not run_command("pip install uv", "UV 설치"):
        print("❌ UV 설치 실패. 수동으로 설치해주세요: https://github.com/astral-sh/uv")
        return False
    
    return True

def setup_uv_environment():
    """UV 환경 설정"""
    print("🚀 UV 환경 설정 시작")
    
    # UV 설치 확인
    if not check_uv_installed():
        if not install_uv():
            return False
    
    # 프로젝트 루트로 이동
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # UV 가상환경 생성
    if not run_command("uv venv", "가상환경 생성"):
        return False
    
    # 의존성 설치
    if not run_command("uv pip install -e .", "의존성 설치"):
        return False
    
    # Deep Agents 관련 추가 의존성 설치
    deep_agents_deps = [
        "tree-of-thoughts",
        "react-agent", 
        "self-reflection",
        "mcts",
        "beam-search"
    ]
    
    for dep in deep_agents_deps:
        if not run_command(f"uv pip install {dep}", f"{dep} 설치"):
            print(f"⚠️  {dep} 설치 실패 (선택적 의존성)")
    
    # 개발 의존성 설치
    if not run_command("uv pip install -e .[dev]", "개발 의존성 설치"):
        print("⚠️  개발 의존성 설치 실패")
    
    # 모니터링 의존성 설치
    if not run_command("uv pip install -e .[monitoring]", "모니터링 의존성 설치"):
        print("⚠️  모니터링 의존성 설치 실패")
    
    print("✅ UV 환경 설정 완료!")
    print("\n📋 사용 방법:")
    print("1. 가상환경 활성화: source .venv/bin/activate (Linux/Mac) 또는 .venv\\Scripts\\activate (Windows)")
    print("2. 서버 실행: uv run python main.py")
    print("3. 테스트 실행: uv run pytest")
    print("4. 코드 포맷팅: uv run black src/ main.py")
    print("5. 타입 체크: uv run mypy src/ main.py")
    
    return True

def verify_installation():
    """설치 검증"""
    print("\n🔍 설치 검증 중...")
    
    # Python 버전 확인
    if not run_command("python --version", "Python 버전 확인"):
        return False
    
    # 주요 패키지 import 테스트
    test_imports = [
        "import langgraph",
        "import langchain",
        "import fastapi",
        "import chromadb",
        "import pandas",
        "import numpy",
        "import sklearn"
    ]
    
    for test_import in test_imports:
        if not run_command(f"python -c '{test_import}'", f"{test_import} 테스트"):
            print(f"⚠️  {test_import} 실패")
    
    print("✅ 설치 검증 완료")
    return True

def main():
    """메인 함수"""
    print("🎯 LangGraph AI 학습 시스템 - UV 환경 설정")
    print("=" * 50)
    
    try:
        # UV 환경 설정
        if not setup_uv_environment():
            print("❌ UV 환경 설정 실패")
            sys.exit(1)
        
        # 설치 검증
        if not verify_installation():
            print("⚠️  일부 패키지 설치에 문제가 있을 수 있습니다")
        
        print("\n🎉 설정 완료! Deep Agents가 포함된 LangGraph AI 시스템이 준비되었습니다.")
        
    except KeyboardInterrupt:
        print("\n⏹️  사용자에 의해 중단되었습니다")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
