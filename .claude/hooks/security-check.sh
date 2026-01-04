#!/usr/bin/env bash
# PreToolUse Hook: Bash 명령 보안 검사
# stdin으로 Hook JSON payload 수신
set -euo pipefail

# stdin에서 payload 읽기
payload="$(cat)"

# JSON 파싱
if command -v jq &> /dev/null && [[ -n "$payload" ]]; then
    TOOL_NAME=$(echo "$payload" | jq -r '.tool_name // ""')
    COMMAND=$(echo "$payload" | jq -r '.tool_input.command // .tool_input // ""')
else
    TOOL_NAME="${CLAUDE_TOOL_NAME:-}"
    COMMAND="${CLAUDE_TOOL_INPUT:-}"
fi

# Bash 명령이 아니면 통과
[[ "$TOOL_NAME" != "Bash" ]] && exit 0

# 위험한 명령 패턴 차단
DANGEROUS_PATTERNS=(
    "rm -rf /"
    "rm -rf ~"
    "rm -rf \$HOME"
    ":(){ :|:& };:"
    "> /dev/sda"
    "mkfs."
    "dd if=/dev"
    "chmod -R 777 /"
    "chown -R"
    "> /dev/null 2>&1 &"
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
    if [[ "$COMMAND" == *"$pattern"* ]]; then
        echo "BLOCKED: Dangerous command pattern detected: $pattern" >&2
        exit 2  # exit 2 = block the operation
    fi
done

# 민감한 파일 접근 차단
SENSITIVE_PATTERNS=(
    "cat.*\.env"
    "cat.*/etc/passwd"
    "cat.*/etc/shadow"
    "cat.*id_rsa"
    "cat.*\.pem"
    "cat.*credential"
    "cat.*secret"
)

for pattern in "${SENSITIVE_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        echo "BLOCKED: Access to sensitive file pattern: $pattern" >&2
        exit 2
    fi
done

# 통과
exit 0
