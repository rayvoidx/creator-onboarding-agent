#!/bin/bash
# Ralph Wiggum Style Auto-Verification Loop
# Claude가 자체 테스트를 반복 실행하여 모든 검증이 통과할 때까지 수정

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

MAX_ITERATIONS="${CLAUDE_MAX_ITERATIONS:-${MAX_ITERATIONS:-10}}"
VERIFICATION_LOG=".claude/hooks/verification.log"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    local level=$1
    local message=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${BLUE}[$timestamp]${NC} ${level}: $message"
    echo "[$timestamp] $level: $message" >> "$VERIFICATION_LOG"
}

notify_slack() {
    local message=$1
    local type=${2:-info}
    if [ -f ".claude/hooks/slack-notify.sh" ]; then
        ./.claude/hooks/slack-notify.sh "$message" "#dev-notifications" "$type" 2>/dev/null || true
    fi
}

run_linting() {
    log "${YELLOW}LINT${NC}" "Running linting checks..."

    # Python linting with ruff
    if command -v ruff &> /dev/null; then
        ruff check src/ --fix || return 1
        ruff format src/ || return 1
    fi

    # TypeScript/JavaScript linting
    if [ -f "package.json" ]; then
        if npm run lint &> /dev/null; then
            log "${GREEN}PASS${NC}" "Linting passed"
        else
            return 1
        fi
    fi

    return 0
}

run_type_check() {
    log "${YELLOW}TYPE${NC}" "Running type checks..."

    # Python type checking with mypy
    if command -v mypy &> /dev/null && [ -f "mypy.ini" ] || [ -f "pyproject.toml" ]; then
        mypy src/ || return 1
    fi

    # TypeScript type checking
    if [ -f "tsconfig.json" ]; then
        npx tsc --noEmit || return 1
    fi

    log "${GREEN}PASS${NC}" "Type checks passed"
    return 0
}

run_tests() {
    log "${YELLOW}TEST${NC}" "Running test suite..."

    # Python tests
    if [ -d "tests" ]; then
        pytest tests/ --tb=short -q || return 1
    fi

    # JavaScript/TypeScript tests
    if [ -f "package.json" ] && grep -q "\"test\"" package.json; then
        npm test || return 1
    fi

    log "${GREEN}PASS${NC}" "All tests passed"
    return 0
}

run_build() {
    log "${YELLOW}BUILD${NC}" "Running build..."

    # Frontend build
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        cd frontend && npm run build && cd ..
    fi

    log "${GREEN}PASS${NC}" "Build completed"
    return 0
}

verify_all() {
    local iteration=$1
    log "${BLUE}VERIFY${NC}" "=== Verification Iteration $iteration/$MAX_ITERATIONS ==="

    # 순차적으로 모든 검증 실행
    run_linting || return 1
    run_type_check || return 1
    run_tests || return 1
    run_build || return 1

    return 0
}

main() {
    log "${BLUE}START${NC}" "Starting Ralph Wiggum Auto-Verification"
    notify_slack "자동 검증 시작 (최대 $MAX_ITERATIONS회 반복)" "info"

    mkdir -p "$(dirname $VERIFICATION_LOG)"

    for ((i=1; i<=MAX_ITERATIONS; i++)); do
        if verify_all $i; then
            log "${GREEN}SUCCESS${NC}" "All verifications passed on iteration $i!"
            notify_slack "모든 검증 통과! (반복 $i회)" "success"
            exit 0
        else
            log "${RED}FAIL${NC}" "Verification failed on iteration $i"

            if [ $i -eq $MAX_ITERATIONS ]; then
                log "${RED}ABORT${NC}" "Max iterations reached. Manual intervention required."
                notify_slack "자동 검증 실패 - 수동 개입 필요 ($MAX_ITERATIONS회 시도)" "error"
                exit 1
            fi

            log "${YELLOW}RETRY${NC}" "Waiting 5 seconds before retry..."
            notify_slack "검증 실패, 재시도 중... ($i/$MAX_ITERATIONS)" "warning"
            sleep 5
        fi
    done
}

# 스크립트 실행
main "$@"
