#!/usr/bin/env bash
# PreToolUse Hook: JSON 파일 편집 전 검증
# stdin으로 Hook JSON payload 수신
set -euo pipefail

# stdin에서 payload 읽기
payload="$(cat)"

# JSON 파싱
if command -v jq &> /dev/null && [[ -n "$payload" ]]; then
    FILE_PATH=$(echo "$payload" | jq -r '.tool_input.file_path // ""')
    NEW_CONTENT=$(echo "$payload" | jq -r '.tool_input.new_string // .tool_input.content // ""')
else
    FILE_PATH="${CLAUDE_FILE_PATH:-}"
    NEW_CONTENT=""
fi

# JSON 파일이 아니면 통과
[[ ! "$FILE_PATH" == *.json ]] && exit 0

# new_content가 있으면 JSON 검증 시도
if [[ -n "$NEW_CONTENT" ]]; then
    if ! echo "$NEW_CONTENT" | python3 -m json.tool > /dev/null 2>&1; then
        # 부분 편집일 수 있으므로 경고만 출력
        echo "WARNING: JSON syntax may be invalid in edit" >&2
    fi
fi

# 통과
exit 0
