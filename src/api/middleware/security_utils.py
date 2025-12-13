"""보안 유틸리티: RBAC 데코레이터, PII 로그 필터"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Callable, List, Any
import re


class PIILogFilter(logging.Filter):
    """간단한 PII 마스킹 로그 필터"""

    def __init__(self, patterns: List[str] | None = None) -> None:
        super().__init__()
        self.patterns = patterns or ["resident_reg_no", "phone", "email"]

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        msg = str(record.getMessage())
        for key in self.patterns:
            if key in msg:
                msg = msg.replace(key, f"{key}[*masked*]")
        record.msg = msg
        return True


def require_roles(*allowed_roles: str) -> Callable:
    """엔드포인트 접근을 허용할 역할 지정 데코레이터
    사용 예:
        @require_roles("admin", "manager")
        async def handler(...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request") or (
                len(args) > 0 and getattr(args[0], "request", None)
            )
            user_role = None
            try:
                if (
                    request
                    and hasattr(request, "state")
                    and getattr(request.state, "user", None)
                ):
                    user_role = getattr(request.state.user, "role", None)
            except Exception:
                user_role = None

            if allowed_roles and user_role not in allowed_roles:
                from fastapi import HTTPException  # type: ignore[import-not-found]

                raise HTTPException(
                    status_code=403, detail="Forbidden: insufficient role"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def sanitize_prompt(prompt: str, max_len: int = 8000) -> str:
    """간단한 안전 프롬프트 가드.

    - 시스템/메타 지시 제거 시도
    - 지시 무력화 패턴 차단
    - 잠재적 키/토큰 패턴 마스킹
    - 길이 제한 적용
    """
    try:
        p = prompt or ""
        # Normalize whitespace
        p = re.sub(r"\s+", " ", p).strip()
        # Block common jailbreak patterns
        block_patterns = [
            r"ignore (all )?previous instructions",
            r"disregard (the )?system( prompt)?",
            r"you are now (my|no longer) (assistant|chatgpt)",
            r"act as (.*)",
            r"/prompt_injection",
        ]
        for bp in block_patterns:
            p = re.sub(bp, "[blocked]", p, flags=re.IGNORECASE)
        # Mask obvious secrets
        p = re.sub(r"sk-[A-Za-z0-9]{16,}", "sk-***", p)
        p = re.sub(
            r"(api[_-]?key)\s*[:=]\s*([A-Za-z0-9-_]{10,})",
            r"\1: ***",
            p,
            flags=re.IGNORECASE,
        )
        # Truncate
        if len(p) > max_len:
            p = p[:max_len] + "..."
        return p
    except Exception:
        return prompt


_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?82[- ]?)?0?1[0-9][- ]?\d{3,4}[- ]?\d{4}")
_RRN_RE = re.compile(r"\b\d{6}-\d{7}\b")


def _mask_text(text: str) -> str:
    try:
        s = text
        s = _EMAIL_RE.sub("[email masked]", s)
        s = _PHONE_RE.sub("[phone masked]", s)
        s = _RRN_RE.sub("[rrn masked]", s)
        return s
    except Exception:
        return text


def sanitize_output(obj: Any, max_str_len: int = 20000) -> Any:
    """출력 마스킹/정제(재귀). 문자열은 PII 패턴 마스킹 및 길이 제한 적용."""
    try:
        if obj is None:
            return None
        if isinstance(obj, str):
            s = _mask_text(obj)
            if len(s) > max_str_len:
                s = s[:max_str_len] + "..."
            return s
        if isinstance(obj, list):
            return [sanitize_output(x, max_str_len) for x in obj]
        if isinstance(obj, dict):
            return {k: sanitize_output(v, max_str_len) for k, v in obj.items()}
        return obj
    except Exception:
        return obj
