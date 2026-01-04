#!/usr/bin/env bash
# Claude Code Notification Hook → Slack
# Hook input JSON은 stdin으로 들어옴 (Claude Code hooks reference)
set -euo pipefail

# 프로젝트 루트
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# 환경 변수 로드 (에러 무시)
[[ -f "$PROJECT_ROOT/.env" ]] && source "$PROJECT_ROOT/.env" 2>/dev/null || true
[[ -f "$PROJECT_ROOT/.env.local" ]] && source "$PROJECT_ROOT/.env.local" 2>/dev/null || true

# Webhook URL 체크
if [[ -z "${SLACK_WEBHOOK_URL:-}" ]]; then
    echo "[$(date +%H:%M:%S)] SLACK_WEBHOOK_URL not set, logging locally"
    exit 0
fi

# stdin에서 Hook JSON payload 읽기
payload="$(cat)"

# jq 있으면 파싱, 없으면 기본 메시지
if command -v jq &> /dev/null && [[ -n "$payload" ]]; then
    hook_event=$(echo "$payload" | jq -r '.hook_event_name // "unknown"')
    message=$(echo "$payload" | jq -r '.notification.message // .message // "Check Claude Code session"')
    tool_name=$(echo "$payload" | jq -r '.tool_name // ""')
    session_id=$(echo "$payload" | jq -r '.session_id // ""')
else
    hook_event="notification"
    message="Claude Code needs attention"
    tool_name=""
    session_id=""
fi

# 이벤트별 이모지/색상
case "$hook_event" in
    "Notification")
        emoji="🔔"
        color="#439FE0"
        ;;
    "PermissionRequest")
        emoji="🔐"
        color="warning"
        message="권한 요청: $message"
        ;;
    "Stop")
        emoji="✅"
        color="good"
        message="세션 완료"
        ;;
    "PostToolUse")
        emoji="🔧"
        color="#439FE0"
        message="Tool 실행: ${tool_name:-$message}"
        ;;
    *)
        emoji="💬"
        color="#439FE0"
        ;;
esac

# 알림 텍스트 구성
text="${emoji} *Claude Code* | ${hook_event}\n${message}"
[[ -n "$session_id" ]] && text="${text}\n_Session: ${session_id}_"

# Slack으로 전송
curl -s -X POST "$SLACK_WEBHOOK_URL" \
    -H 'Content-type: application/json' \
    --data "{
        \"channel\": \"${SLACK_CHANNEL:-#dev-notifications}\",
        \"attachments\": [{
            \"color\": \"${color}\",
            \"text\": \"${text}\",
            \"footer\": \"Creator Onboarding Agent\",
            \"ts\": $(date +%s)
        }]
    }" >/dev/null

# 로컬 로그
echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $hook_event: $message" >> "$PROJECT_ROOT/.claude/hooks/notifications.log"
