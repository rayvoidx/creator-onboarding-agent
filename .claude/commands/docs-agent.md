---
description: OpenAPI/Swagger 문서 자동 생성
argument-hint: "[action] [target]"
allowed-tools: Read, Edit, Write, Grep, Glob, Bash
---

# Docs Agent

API 문서를 자동 생성하고 업데이트합니다.

## Instructions

1. OpenAPI 스펙 생성:
   ```bash
   python scripts/export_openapi.py > openapi.json
   ```

2. 엔드포인트 문서화:
   - Request/Response 스키마
   - 에러 응답 (4xx, 5xx)
   - 인증 요구사항

3. 예시 추가 및 설명 보강

## Arguments
- `$ARGUMENTS` - 문서화 대상 또는 액션

## Documentation Standards
- 모든 엔드포인트에 summary, description 필수
- Request/Response 예시 포함
- Error response 문서화

## Key Files
- `src/api/v1/routes/`
- `src/api/schemas/`
- `scripts/export_openapi.py`
