#!/bin/bash
# Ralph Wiggum Style Auto-Verification Loop
# Claude가 자체 테스트를 반복 실행하여 모든 검증이 통과할 때까지 수정
# Supports --session <name> for domain-scoped verification

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
SESSION_NAME=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --session)
            SESSION_NAME="$2"
            shift 2
            ;;
        --max-iterations)
            MAX_ITERATIONS="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

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

# ============================================================
# Session-scoped paths
# ============================================================

get_lint_paths() {
    case "$SESSION_NAME" in
        rag)            echo "src/rag/" ;;
        agents)         echo "src/agents/ src/domain/ src/tools/" ;;
        api)            echo "src/api/ src/app/ src/data/" ;;
        mcp)            echo "src/mcp/ src/services/ src/tasks/ src/core/" ;;
        monitor|monitoring) echo "src/monitoring/" ;;
        qa)             echo "src/" ;;
        orchestrator)   echo "src/core/base.py src/graphs/ config/" ;;
        frontend)       echo "" ;;
        "")             echo "src/" ;;
        *)              echo "src/" ;;
    esac
}

get_test_paths() {
    case "$SESSION_NAME" in
        rag)            echo "tests/unit/rag/" ;;
        agents)         echo "tests/unit/agents/" ;;
        api)            echo "tests/integration/" ;;
        mcp)            echo "tests/unit/services/" ;;
        monitor|monitoring) echo "tests/unit/monitoring/" ;;
        qa)             echo "tests/" ;;
        orchestrator)   echo "tests/" ;;
        frontend)       echo "tests/e2e/" ;;
        "")             echo "tests/" ;;
        *)              echo "tests/" ;;
    esac
}

get_cov_paths() {
    case "$SESSION_NAME" in
        rag)            echo "src/rag" ;;
        agents)         echo "src/agents" ;;
        api)            echo "src/api" ;;
        mcp)            echo "src/services" ;;
        monitor|monitoring) echo "src/monitoring" ;;
        qa)             echo "src" ;;
        orchestrator)   echo "src" ;;
        frontend)       echo "" ;;
        "")             echo "src" ;;
        *)              echo "src" ;;
    esac
}

has_frontend() {
    case "$SESSION_NAME" in
        frontend|qa|"") return 0 ;;
        *)              return 1 ;;
    esac
}

has_python() {
    case "$SESSION_NAME" in
        frontend) return 1 ;;
        *)        return 0 ;;
    esac
}

# ============================================================
# Verification steps
# ============================================================

run_linting() {
    local lint_paths=$(get_lint_paths)

    if [ -z "$lint_paths" ]; then
        log "${GREEN}SKIP${NC}" "No Python linting for session: $SESSION_NAME"
        return 0
    fi

    log "${YELLOW}LINT${NC}" "Running linting checks on: $lint_paths"

    if command -v ruff &> /dev/null && has_python; then
        ruff check $lint_paths --fix || return 1
        ruff format $lint_paths || return 1
    fi

    # JS/TS linting for full scope only
    if [ -f "package.json" ] && [ "$SESSION_NAME" = "" ]; then
        if npm run lint &> /dev/null; then
            log "${GREEN}PASS${NC}" "JS/TS linting passed"
        else
            return 1
        fi
    fi

    return 0
}

run_type_check() {
    log "${YELLOW}TYPE${NC}" "Running type checks..."

    if has_python; then
        local lint_paths=$(get_lint_paths)
        if command -v mypy &> /dev/null && { [ -f "mypy.ini" ] || [ -f "pyproject.toml" ]; }; then
            mypy $lint_paths || return 1
        fi
    fi

    if has_frontend && [ -f "frontend/tsconfig.json" ]; then
        cd frontend && npx tsc --noEmit && cd "$PROJECT_ROOT" || { cd "$PROJECT_ROOT"; return 1; }
    fi

    log "${GREEN}PASS${NC}" "Type checks passed"
    return 0
}

run_tests() {
    local test_paths=$(get_test_paths)
    local cov_paths=$(get_cov_paths)

    log "${YELLOW}TEST${NC}" "Running tests: $test_paths"

    if has_python && [ -d "$test_paths" ] && [ -n "$cov_paths" ]; then
        pytest "$test_paths" --cov="$cov_paths" --tb=short -q || return 1
    fi

    if has_frontend && [ -f "package.json" ] && grep -q "\"test\"" package.json 2>/dev/null; then
        npm test || return 1
    fi

    log "${GREEN}PASS${NC}" "All tests passed"
    return 0
}

run_build() {
    if ! has_frontend; then
        return 0
    fi

    log "${YELLOW}BUILD${NC}" "Running build..."

    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        cd frontend && npm run build && cd "$PROJECT_ROOT" || { cd "$PROJECT_ROOT"; return 1; }
    fi

    log "${GREEN}PASS${NC}" "Build completed"
    return 0
}

verify_all() {
    local iteration=$1
    local scope_label="${SESSION_NAME:-full}"
    log "${BLUE}VERIFY${NC}" "=== Iteration $iteration/$MAX_ITERATIONS (scope: $scope_label) ==="

    run_linting || return 1
    run_type_check || return 1
    run_tests || return 1
    run_build || return 1

    return 0
}

main() {
    local scope_label="${SESSION_NAME:-full}"
    log "${BLUE}START${NC}" "Starting Auto-Verification (scope: $scope_label, max: $MAX_ITERATIONS)"
    notify_slack "자동 검증 시작 - $scope_label (최대 $MAX_ITERATIONS회 반복)" "info"

    mkdir -p "$(dirname $VERIFICATION_LOG)"

    for ((i=1; i<=MAX_ITERATIONS; i++)); do
        if verify_all $i; then
            log "${GREEN}SUCCESS${NC}" "All verifications passed on iteration $i!"
            notify_slack "검증 통과 - $scope_label (반복 $i회)" "success"
            exit 0
        else
            log "${RED}FAIL${NC}" "Verification failed on iteration $i"

            if [ $i -eq $MAX_ITERATIONS ]; then
                log "${RED}ABORT${NC}" "Max iterations reached. Manual intervention required."
                notify_slack "검증 실패 - $scope_label ($MAX_ITERATIONS회 시도)" "error"
                exit 1
            fi

            log "${YELLOW}RETRY${NC}" "Waiting 5 seconds before retry..."
            notify_slack "검증 실패, 재시도 중 - $scope_label ($i/$MAX_ITERATIONS)" "warning"
            sleep 5
        fi
    done
}

# 스크립트 실행
main "$@"
