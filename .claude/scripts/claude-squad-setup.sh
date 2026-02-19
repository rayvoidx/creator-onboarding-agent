#!/bin/bash
# Claude Squad Team Launcher
# cs CLI를 사용한 8-세션 병렬 개발 팀 빠른 시작
# https://github.com/smtg-ai/claude-squad
#
# 사용법:
#   ./claude-squad-setup.sh          # cs 설치 확인 + 팀 프롬프트 출력
#   ./claude-squad-setup.sh prompts  # 각 세션별 프롬프트 출력
#   ./claude-squad-setup.sh check    # cs 설치 확인
#
# cs를 실행한 후 TUI에서:
#   n → 새 인스턴스 (아래 프롬프트 복사/붙여넣기)
#   N → 프롬프트와 함께 새 인스턴스
#   ↑/↓ → 인스턴스 이동
#   Enter → 인스턴스 접속
#   c → 커밋 & 일시정지
#   s → 커밋 & 푸시
#   q → 종료

set -e

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TEAM_DIR="$PROJECT_ROOT/.claude/team"

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# cs 설치 확인
check_cs() {
    if command -v cs &> /dev/null; then
        local version=$(cs version 2>/dev/null || echo "unknown")
        echo -e "${GREEN}cs installed${NC} (${version})"
        return 0
    else
        echo -e "${RED}cs not installed${NC}"
        echo ""
        echo "Install Claude Squad:"
        echo "  brew install smtg-ai/tap/claude-squad"
        echo "  # or"
        echo "  go install github.com/smtg-ai/claude-squad@latest"
        echo ""
        echo "Requires: tmux, gh (GitHub CLI)"
        return 1
    fi
}

# 팀 세션 프롬프트 출력
show_prompts() {
    echo -e "${BOLD}${CYAN}"
    echo "=========================================="
    echo "  Claude Code Team - Session Prompts"
    echo "=========================================="
    echo -e "${NC}"
    echo ""
    echo -e "${DIM}cs 실행 후 'N' 키로 아래 프롬프트를 복사하여 인스턴스를 생성하세요.${NC}"
    echo -e "${DIM}각 인스턴스는 자동으로 독립 git worktree에서 실행됩니다.${NC}"
    echo ""

    echo -e "${BOLD}1. RAG Engineer${NC} ${DIM}(src/rag/ 전담)${NC}"
    echo -e "${BLUE}───────────────────────────────────────${NC}"
    if [ -f "$TEAM_DIR/rag.md" ]; then
        echo "Read .claude/team/rag.md for your role. You own src/rag/ exclusively. Focus on retrieval, reranking, caching, query expansion. Run tests: pytest tests/unit/rag/ --cov=src/rag. Target 98% coverage. NEVER edit files outside src/rag/."
    fi
    echo ""

    echo -e "${BOLD}2. Agent Developer${NC} ${DIM}(src/agents/ 전담)${NC}"
    echo -e "${BLUE}───────────────────────────────────────${NC}"
    echo "Read .claude/team/agents.md for your role. You own src/agents/ subdirectories, src/domain/, src/tools/. Implement BaseAgent pattern with async execute(). Run tests: pytest tests/unit/agents/ --cov=src/agents. Target 98% coverage. NEVER edit src/core/base.py."
    echo ""

    echo -e "${BOLD}3. API Developer${NC} ${DIM}(src/api/ 전담)${NC}"
    echo -e "${BLUE}───────────────────────────────────────${NC}"
    echo "Read .claude/team/api.md for your role. You own src/api/, src/app/, src/data/models/. FastAPI + Pydantic v2, Depends(), response_model. Run tests: pytest tests/integration/ --cov=src/api. Target 100% endpoint coverage. NEVER edit src/rag/ or src/agents/."
    echo ""

    echo -e "${BOLD}4. MCP/Infra Engineer${NC} ${DIM}(src/mcp/, src/services/, node/ 전담)${NC}"
    echo -e "${BLUE}───────────────────────────────────────${NC}"
    echo "Read .claude/team/mcp.md for your role. You own src/mcp/, src/services/, src/tasks/, node/, src/core/ (except base.py). Circuit breaker, Celery tasks, MCP servers. Run tests: pytest tests/unit/services/ --cov=src/services. Target 95% coverage."
    echo ""

    echo -e "${BOLD}5. Monitoring Engineer${NC} ${DIM}(src/monitoring/ 전담)${NC}"
    echo -e "${BLUE}───────────────────────────────────────${NC}"
    echo "Read .claude/team/monitor.md for your role. You own src/monitoring/ exclusively. Langfuse tracing, Prometheus metrics, structured logging. Run tests: pytest tests/unit/monitoring/ --cov=src/monitoring. Target 95% coverage. NEVER edit src/api/middleware/."
    echo ""

    echo -e "${BOLD}6. Frontend Developer${NC} ${DIM}(frontend/ 전담)${NC}"
    echo -e "${BLUE}───────────────────────────────────────${NC}"
    echo "Read .claude/team/frontend.md for your role. You own frontend/ entirely and tests/e2e/. React + TypeScript + Tailwind + Vite. Run: cd frontend && npm run dev. Build: npm run build. NEVER edit backend src/ code."
    echo ""

    echo -e "${BOLD}7. QA Guardian${NC} ${DIM}(tests/, CI/CD 전담)${NC}"
    echo -e "${BLUE}───────────────────────────────────────${NC}"
    echo "Read .claude/team/qa.md for your role. You own tests/conftest.py, tests/unit/services/, .github/workflows/. Enforce 95% overall coverage. ONLY write test code and CI config, NEVER source code. Run: pytest --cov=src --cov-fail-under=95 tests/"
    echo ""

    echo -e "${DIM}───────────────────────────────────────${NC}"
    echo -e "${YELLOW}Tip:${NC} 리드(첫 번째 인스턴스)는 별도 프롬프트 없이 cs 시작 시 자동 생성됩니다."
    echo -e "${YELLOW}Tip:${NC} 각 인스턴스의 .claude/team/*.md 파일에 상세 지침이 있습니다."
}

# 빠른 시작 가이드
show_quickstart() {
    echo -e "${BOLD}${CYAN}"
    echo "=========================================="
    echo "  Claude Squad Quick Start"
    echo "=========================================="
    echo -e "${NC}"
    echo ""

    check_cs || exit 1

    echo ""
    echo -e "${BOLD}Step 1:${NC} cs 실행"
    echo "  cs"
    echo ""
    echo -e "${BOLD}Step 2:${NC} 리드 인스턴스가 자동 생성됩니다."
    echo "  리드에게 팀 조율 역할을 지시하세요."
    echo ""
    echo -e "${BOLD}Step 3:${NC} 'N' 키로 teammate 인스턴스 추가"
    echo "  아래 명령으로 각 세션별 프롬프트를 확인하세요:"
    echo "  $0 prompts"
    echo ""
    echo -e "${BOLD}Key Bindings:${NC}"
    echo "  n/N     새 인스턴스 생성"
    echo "  ↑/↓     인스턴스 이동"
    echo "  Enter   인스턴스 접속 (추가 프롬프트)"
    echo "  c       커밋 & 일시정지"
    echo "  s       커밋 & 푸시 (GitHub)"
    echo "  r       일시정지된 인스턴스 재개"
    echo "  D       인스턴스 삭제"
    echo "  Tab     미리보기/diff 전환"
    echo "  q       종료"
    echo ""
    echo -e "${BOLD}Team Sessions (7 teammates):${NC}"
    echo "  1. RAG Engineer       - src/rag/"
    echo "  2. Agent Developer    - src/agents/"
    echo "  3. API Developer      - src/api/"
    echo "  4. MCP/Infra          - src/mcp/, src/services/, node/"
    echo "  5. Monitoring         - src/monitoring/"
    echo "  6. Frontend           - frontend/"
    echo "  7. QA Guardian        - tests/, CI/CD"
    echo ""
    echo -e "${DIM}상세 프롬프트: $0 prompts${NC}"
}

case "${1:-}" in
    check)
        check_cs
        ;;
    prompts)
        show_prompts
        ;;
    help)
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  (default)  Quick start guide + cs 설치 확인"
        echo "  prompts    각 세션별 프롬프트 출력"
        echo "  check      cs 설치 확인"
        echo "  help       이 도움말"
        ;;
    *)
        show_quickstart
        ;;
esac
