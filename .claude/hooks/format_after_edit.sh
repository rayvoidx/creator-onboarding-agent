#!/usr/bin/env bash
# PostToolUse Hook: Edit/Write 후 자동 포맷팅
# stdin으로 Hook JSON payload 수신
set -euo pipefail

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# stdin에서 payload 읽기
payload="$(cat)"

# 파일 경로 추출
if command -v jq &> /dev/null && [[ -n "$payload" ]]; then
    file_path=$(echo "$payload" | jq -r '.tool_input.file_path // .file_path // ""')
else
    file_path="${CLAUDE_FILE_PATH:-}"
fi

# 파일 없으면 종료
[[ -z "$file_path" || ! -f "$file_path" ]] && exit 0

# 확장자 추출
ext="${file_path##*.}"

# 확장자별 포맷팅
case "$ext" in
    py)
        # Python: ruff format + isort
        if command -v ruff &> /dev/null; then
            ruff format "$file_path" 2>/dev/null || true
            ruff check "$file_path" --fix --select I 2>/dev/null || true
        elif command -v black &> /dev/null; then
            black -q "$file_path" 2>/dev/null || true
        fi
        ;;
    js|jsx|ts|tsx|json|md|yaml|yml)
        # JavaScript/TypeScript/JSON/Markdown: prettier
        if command -v prettier &> /dev/null; then
            prettier --write "$file_path" 2>/dev/null || true
        elif [[ -f "$PROJECT_ROOT/node_modules/.bin/prettier" ]]; then
            "$PROJECT_ROOT/node_modules/.bin/prettier" --write "$file_path" 2>/dev/null || true
        fi
        ;;
    sh|bash)
        # Shell: shfmt (설치되어 있으면)
        if command -v shfmt &> /dev/null; then
            shfmt -w "$file_path" 2>/dev/null || true
        fi
        ;;
    sql)
        # SQL: sqlfluff (설치되어 있으면)
        if command -v sqlfluff &> /dev/null; then
            sqlfluff fix "$file_path" 2>/dev/null || true
        fi
        ;;
esac

# 로그
echo "[$(date +%H:%M:%S)] Formatted: $file_path" >> "$PROJECT_ROOT/.claude/hooks/format.log" 2>/dev/null || true
