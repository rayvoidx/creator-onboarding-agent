#!/bin/bash
# Claude Code Multi-Session Manager
# tmux를 활용한 병렬 Claude Code 세션 관리
#
# NOTE: 팀 개발에는 Claude Squad(cs)를 사용하세요:
#   brew install smtg-ai/tap/claude-squad && cs
#   자세한 내용: .claude/scripts/claude-squad-setup.sh

set -e

SESSION_PREFIX="claude"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
LOG_DIR=".claude/hooks"
WORKTREE_BASE=".worktrees"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"
}

# tmux 설치 확인
check_tmux() {
    if ! command -v tmux &> /dev/null; then
        echo -e "${RED}Error: tmux is not installed${NC}"
        echo "Install with: brew install tmux"
        exit 1
    fi
}

# Git worktree 생성 (병렬 작업용)
create_worktree() {
    local name=$1
    local branch=${2:-"feature/$name"}

    if [ ! -d "$WORKTREE_BASE" ]; then
        mkdir -p "$WORKTREE_BASE"
    fi

    local worktree_path="$WORKTREE_BASE/$name"

    if [ -d "$worktree_path" ]; then
        log "Worktree '$name' already exists"
        return 0
    fi

    # 브랜치 생성 (없으면)
    if ! git show-ref --verify --quiet "refs/heads/$branch"; then
        git branch "$branch" 2>/dev/null || true
    fi

    git worktree add "$worktree_path" "$branch"
    log "Created worktree: $worktree_path on branch $branch"
}

# Claude Code 세션 시작
start_session() {
    local name=$1
    local task=${2:-""}
    local worktree=${3:-""}

    local session_name="${SESSION_PREFIX}-${name}"
    local work_dir="$PROJECT_ROOT"

    # worktree 사용 시
    if [ -n "$worktree" ] && [ -d "$WORKTREE_BASE/$worktree" ]; then
        work_dir="$WORKTREE_BASE/$worktree"
    fi

    # 이미 실행 중인지 확인
    if tmux has-session -t "$session_name" 2>/dev/null; then
        log "Session '$session_name' already exists"
        return 0
    fi

    # 새 세션 생성
    tmux new-session -d -s "$session_name" -c "$work_dir"

    # Claude Code 실행
    if [ -n "$task" ]; then
        tmux send-keys -t "$session_name" "claude -p \"$task\"" C-m
    else
        tmux send-keys -t "$session_name" "claude" C-m
    fi

    log "${GREEN}Started session: $session_name${NC}"
    log "Attach with: tmux attach -t $session_name"
}

# 모든 세션 목록
list_sessions() {
    log "Active Claude Code sessions:"
    tmux list-sessions 2>/dev/null | grep "^${SESSION_PREFIX}" || echo "No active sessions"
}

# 세션 종료
stop_session() {
    local name=$1
    local session_name="${SESSION_PREFIX}-${name}"

    if tmux has-session -t "$session_name" 2>/dev/null; then
        tmux kill-session -t "$session_name"
        log "Stopped session: $session_name"
    else
        log "Session '$session_name' not found"
    fi
}

# 모든 세션 종료
stop_all() {
    local sessions=$(tmux list-sessions 2>/dev/null | grep "^${SESSION_PREFIX}" | cut -d: -f1)

    if [ -z "$sessions" ]; then
        log "No active sessions"
        return 0
    fi

    for session in $sessions; do
        tmux kill-session -t "$session"
        log "Stopped session: $session"
    done
}

# 병렬 개발 환경 설정
setup_parallel_dev() {
    log "Setting up parallel development environment..."

    # 기본 worktrees 생성
    create_worktree "feature" "feature/main"
    create_worktree "bugfix" "bugfix/main"
    create_worktree "refactor" "refactor/main"

    # 세션 시작
    start_session "main" "" ""
    start_session "feature" "" "feature"
    start_session "tests" "Run and fix tests" ""

    log "${GREEN}Parallel dev environment ready!${NC}"
    list_sessions
}

# 도움말
show_help() {
    cat << EOF
Claude Code Multi-Session Manager (tmux)

Usage: $0 <command> [options]

Commands:
  start <name> [task] [worktree]  - Start a new Claude session
  stop <name>                      - Stop a specific session
  stop-all                         - Stop all Claude sessions
  list                             - List all active sessions
  attach <name>                    - Attach to a session
  worktree <name> [branch]         - Create a git worktree
  setup                            - Setup parallel dev environment
  help                             - Show this help

Examples:
  $0 start feature "Implement user auth"
  $0 start tests "Run all tests" tests
  $0 worktree feature feature/new-feature
  $0 setup
  $0 list

For team development, use Claude Squad instead:
  brew install smtg-ai/tap/claude-squad
  cs
  ./.claude/scripts/claude-squad-setup.sh prompts

EOF
}

# 메인 명령어 처리
check_tmux

case "${1:-help}" in
    start)
        start_session "${2:-default}" "${3:-}" "${4:-}"
        ;;
    stop)
        stop_session "${2:-default}"
        ;;
    stop-all)
        stop_all
        ;;
    list)
        list_sessions
        ;;
    attach)
        tmux attach -t "${SESSION_PREFIX}-${2:-default}"
        ;;
    worktree)
        create_worktree "$2" "$3"
        ;;
    setup)
        setup_parallel_dev
        ;;
    help|*)
        show_help
        ;;
esac
