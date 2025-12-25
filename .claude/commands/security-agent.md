---
description: API rate-limit 및 MCP 보안 감사
argument-hint: "[audit-type] [target]"
allowed-tools: Read, Grep, Glob
---

# Security Agent

보안 설정을 감사하고 개선안을 제시합니다.

## Instructions

1. Rate limiting 설정 검토:
   - `src/api/middleware/rate_limit.py`
   - Redis 기반 vs 메모리 기반

2. 인증/인가 검증:
   - JWT 토큰 검증
   - API 키 관리

3. 입력 검증:
   - SQL Injection
   - XSS
   - Command Injection

4. CORS 정책 검토

## Arguments
- `$ARGUMENTS` - 감사 유형 및 대상

## Security Checklist
- [ ] Rate limiting per endpoint
- [ ] JWT validation
- [ ] Input sanitization
- [ ] CORS whitelist
- [ ] Secret rotation

## Key Files
- `src/api/middleware/rate_limit.py`
- `src/api/middleware/auth.py`
- `src/api/middleware/security_utils.py`
