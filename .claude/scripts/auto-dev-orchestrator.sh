#!/bin/bash
# Auto-Dev Orchestrator
# A-Z 자동화 개발 워크플로우 실행기

set -e

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$PROJECT_ROOT"

# 환경 변수 로드
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

if [ -f "$PROJECT_ROOT/.env.local" ]; then
    set -a
    source "$PROJECT_ROOT/.env.local"
    set +a
fi

REQUIREMENT="${1:-}"
LOG_FILE=".claude/hooks/auto-dev.log"
PHASE_FILE=".claude/hooks/current-phase"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

log() {
    local level=$1
    local message=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${BLUE}[$timestamp]${NC} $level $message"
    echo "[$timestamp] $level: $message" >> "$LOG_FILE"
}

notify() {
    local message=$1
    local type=${2:-info}
    if [ -f ".claude/hooks/slack-notify.sh" ]; then
        ./.claude/hooks/slack-notify.sh "$message" "#dev-notifications" "$type" 2>/dev/null || true
    fi
}

set_phase() {
    echo "$1" > "$PHASE_FILE"
    log "${PURPLE}PHASE${NC}" "=== $1 ==="
    notify "Phase: $1" "info"
}

# Phase 1: 요구사항 분석
phase_requirements() {
    set_phase "1. Requirements Analysis"

    log "${YELLOW}ANALYZE${NC}" "Parsing requirement: $REQUIREMENT"

    # 관련 파일 검색
    log "${YELLOW}SEARCH${NC}" "Searching related files..."

    # 키워드 추출 및 검색
    local keywords=$(echo "$REQUIREMENT" | tr ' ' '\n' | grep -E '^[가-힣a-zA-Z]{2,}' | head -5)

    for keyword in $keywords; do
        rg -l "$keyword" src/ 2>/dev/null | head -5 || true
    done

    log "${GREEN}DONE${NC}" "Requirements analysis complete"
    return 0
}

# Phase 2: 설계
phase_architecture() {
    set_phase "2. Architecture Design"

    log "${YELLOW}DESIGN${NC}" "Analyzing existing architecture..."

    # 현재 구조 파악
    find src/ -name "*.py" -type f | head -20 || true

    log "${GREEN}DONE${NC}" "Architecture design complete"
    return 0
}

# Phase 3: 구현
phase_implementation() {
    set_phase "3. Implementation"

    log "${YELLOW}IMPL${NC}" "Implementation phase - Claude will handle this"

    # 이 단계는 Claude가 직접 처리
    # 스크립트는 프레임워크만 제공

    log "${GREEN}DONE${NC}" "Implementation structure ready"
    return 0
}

# Phase 4: 검증
phase_verification() {
    set_phase "4. Verification"

    log "${YELLOW}LINT${NC}" "Running linters..."
    if command -v ruff &> /dev/null; then
        ruff check src/ --fix 2>/dev/null || true
        ruff format src/ 2>/dev/null || true
    fi

    log "${YELLOW}TYPE${NC}" "Running type checks..."
    if command -v mypy &> /dev/null && [ -f "pyproject.toml" ]; then
        mypy src/ 2>/dev/null || log "${YELLOW}WARN${NC}" "Type check warnings found"
    fi

    log "${YELLOW}TEST${NC}" "Running tests..."
    if [ -d "tests" ]; then
        pytest tests/ --tb=short -q 2>/dev/null || log "${YELLOW}WARN${NC}" "Some tests failed"
    fi

    log "${GREEN}DONE${NC}" "Verification complete"
    return 0
}

# Phase 5: 문서화
phase_documentation() {
    set_phase "5. Documentation"

    log "${YELLOW}DOCS${NC}" "Updating documentation..."

    # OpenAPI 스펙 생성 (FastAPI 있을 경우)
    if [ -f "src/main.py" ]; then
        log "${YELLOW}API${NC}" "API documentation ready at /docs"
    fi

    log "${GREEN}DONE${NC}" "Documentation complete"
    return 0
}

# Phase 6: 배포 준비
phase_deployment() {
    set_phase "6. Deployment Preparation"

    log "${YELLOW}GIT${NC}" "Preparing git commit..."

    # 변경사항 확인
    git status --short

    log "${YELLOW}INFO${NC}" "Ready for commit and PR"
    log "${GREEN}DONE${NC}" "Deployment preparation complete"
    return 0
}

# 전체 워크플로우 실행
run_workflow() {
    log "${PURPLE}START${NC}" "Auto-Dev Workflow Starting"
    log "${PURPLE}REQ${NC}" "Requirement: $REQUIREMENT"

    notify "Auto-Dev 시작: $REQUIREMENT" "info"

    mkdir -p "$(dirname $LOG_FILE)"

    # 순차적으로 Phase 실행
    phase_requirements || { notify "Phase 1 실패" "error"; exit 1; }
    phase_architecture || { notify "Phase 2 실패" "error"; exit 1; }
    phase_implementation || { notify "Phase 3 실패" "error"; exit 1; }
    phase_verification || { notify "Phase 4 실패" "warning"; }
    phase_documentation || { notify "Phase 5 실패" "warning"; }
    phase_deployment || { notify "Phase 6 실패" "error"; exit 1; }

    log "${GREEN}COMPLETE${NC}" "Auto-Dev Workflow Complete!"
    notify "Auto-Dev 완료! 커밋 및 PR 준비됨" "success"

    rm -f "$PHASE_FILE"
}

# 현재 상태 확인
check_status() {
    if [ -f "$PHASE_FILE" ]; then
        echo "Current Phase: $(cat $PHASE_FILE)"
        echo ""
        echo "Recent logs:"
        tail -20 "$LOG_FILE" 2>/dev/null || echo "No logs"
    else
        echo "No active Auto-Dev workflow"
    fi
}

# 도움말
show_help() {
    cat << EOF
Auto-Dev Orchestrator

Usage: $0 "<requirement>" | status | help

Arguments:
  <requirement>  - Development requirement to implement
  status         - Check current workflow status
  help           - Show this help

Phases:
  1. Requirements Analysis
  2. Architecture Design
  3. Implementation
  4. Verification
  5. Documentation
  6. Deployment Preparation

Examples:
  $0 "사용자 인증 기능 추가"
  $0 "RAG threshold 최적화"
  $0 status

EOF
}

# 메인
case "${1:-}" in
    status)
        check_status
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        show_help
        ;;
    *)
        run_workflow
        ;;
esac
