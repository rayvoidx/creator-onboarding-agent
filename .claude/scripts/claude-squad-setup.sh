#!/bin/bash
# Claude Squad Integration Setup
# https://github.com/smtg-ai/claude-squad

set -e

SQUAD_CONFIG=".claude-squad.yaml"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"
}

# Claude Squad 설치 확인
check_claude_squad() {
    if ! command -v cs &> /dev/null; then
        log "${YELLOW}Claude Squad not installed${NC}"
        echo ""
        echo "Install options:"
        echo "  brew install claude-squad"
        echo "  npm install -g @smtg-ai/claude-squad"
        echo ""
        return 1
    fi
    return 0
}

# 설정 파일 생성
create_config() {
    if [ -f "$SQUAD_CONFIG" ]; then
        log "Config already exists: $SQUAD_CONFIG"
        return 0
    fi

    cat > "$SQUAD_CONFIG" << 'EOF'
# Claude Squad Configuration
# https://github.com/smtg-ai/claude-squad

name: creator-onboarding-agent
description: AI 기반 크리에이터 온보딩 및 미션 추천 시스템

# 에이전트 정의
agents:
  - name: main
    description: 메인 개발 에이전트
    path: .
    auto_start: true

  - name: backend
    description: FastAPI 백엔드 개발
    path: .
    prompt: "Focus on src/api and src/agents development"

  - name: frontend
    description: React 프론트엔드 개발
    path: frontend
    prompt: "Focus on frontend development"

  - name: tests
    description: 테스트 작성 및 실행
    path: .
    prompt: "Write and run tests, maintain 95% coverage"

  - name: rag
    description: RAG 파이프라인 최적화
    path: .
    prompt: "Optimize RAG pipeline in src/rag"

# 워크플로우 정의
workflows:
  feature:
    description: 새 기능 개발
    agents: [main, backend, frontend, tests]
    parallel: true

  bugfix:
    description: 버그 수정
    agents: [main, tests]

  refactor:
    description: 코드 리팩토링
    agents: [main, tests]

# 알림 설정
notifications:
  slack:
    enabled: true
    webhook: ${SLACK_WEBHOOK_URL}
    channel: "#dev-notifications"

# 동기화 설정
sync:
  auto_commit: false
  branch_prefix: "cs/"

# 리소스 제한
limits:
  max_agents: 5
  session_timeout: 3600  # 1시간
EOF

    log "${GREEN}Created config: $SQUAD_CONFIG${NC}"
}

# Claude Squad 워크플로우 시작
start_workflow() {
    local workflow=${1:-feature}

    if ! check_claude_squad; then
        log "Falling back to tmux multi-session..."
        ./.claude/scripts/multi-session.sh setup
        return
    fi

    log "Starting Claude Squad workflow: $workflow"
    cs start --workflow "$workflow"
}

# 상태 확인
show_status() {
    if check_claude_squad; then
        cs status
    else
        ./.claude/scripts/multi-session.sh list
    fi
}

# 도움말
show_help() {
    cat << EOF
Claude Squad Integration

Usage: $0 <command> [options]

Commands:
  install     - Check/install Claude Squad
  config      - Generate configuration file
  start       - Start workflow (default: feature)
  status      - Show status
  stop        - Stop all agents
  help        - Show this help

Workflows:
  feature     - Full feature development (4 agents)
  bugfix      - Bug fixing (2 agents)
  refactor    - Code refactoring (2 agents)

Examples:
  $0 config
  $0 start feature
  $0 status

EOF
}

case "${1:-help}" in
    install)
        check_claude_squad
        ;;
    config)
        create_config
        ;;
    start)
        start_workflow "${2:-feature}"
        ;;
    status)
        show_status
        ;;
    stop)
        if check_claude_squad; then
            cs stop --all
        else
            ./.claude/scripts/multi-session.sh stop-all
        fi
        ;;
    help|*)
        show_help
        ;;
esac
