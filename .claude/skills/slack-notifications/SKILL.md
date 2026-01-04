# Slack Notifications Skill

Slack을 통한 개발 진행 상황 알림 및 모니터링을 위한 스킬입니다.

## Triggers

- progress, 진행, 알림, notify, notification
- slack, 슬랙
- report, 리포트, 보고

## Instructions

### 진행 상황 알림

마일스톤 완료 시 자동으로 Slack 알림을 전송합니다:

```bash
# 일반 알림
./.claude/hooks/slack-notify.sh "기능 구현 50% 완료" "#dev-notifications" "info"

# 성공 알림
./.claude/hooks/slack-notify.sh "모든 테스트 통과 (95% 커버리지)" "#dev-notifications" "success"

# 에러 알림
./.claude/hooks/slack-notify.sh "빌드 실패: TypeScript 에러 3건" "#dev-notifications" "error"
```

### 알림 유형

| Type | 용도 | 색상 |
|------|------|------|
| `info` | 일반 진행 상황 | 파랑 |
| `success` | 작업 완료, 테스트 통과 | 초록 |
| `warning` | 주의 필요 | 노랑 |
| `error` | 에러, 실패 | 빨강 |

### 자동 알림 트리거

다음 이벤트에서 자동 알림:
1. 주요 기능 구현 완료
2. 테스트 스위트 실행 결과
3. PR 생성/머지
4. 빌드 성공/실패
5. 30분 이상 블록 시

### 환경 변수 설정

`.env.local`에 추가:
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_TEAM_ID=T0123456789
```

## Related Files

- `.mcp.json` - MCP 서버 설정
- `.claude/hooks/slack-notify.sh` - 알림 스크립트
- `.claude/hooks/notifications.log` - 알림 로그
