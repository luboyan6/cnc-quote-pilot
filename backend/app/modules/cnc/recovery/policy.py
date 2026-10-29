import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.modules.cnc.browser.errors import BrowserStop
from app.modules.cnc.login.contracts import LoginError

from .contracts import (
    ErrorCategory,
    RecoveryAction,
    RecoveryDecision,
    SideEffectState,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


_SENSITIVE_PATTERNS = [
    re.compile(r"Traceback \(most recent call last\):.*", re.DOTALL),
    re.compile(r"[A-Za-z]:\\[^\s'\"]+"),
    re.compile(r"/(?:Users|home|root|app|var|tmp)/[^\s'\"]+"),
    re.compile(r"(?:bearer\s+[A-Za-z0-9_\-\.]+)", re.IGNORECASE),
    re.compile(r"(?:password\s*=\s*['\"][^'\"]*['\"])", re.IGNORECASE),
]


def sanitize_error_message(text: str) -> str:
    cleaned = text
    for pattern in _SENSITIVE_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:1000] if cleaned else "未知错误"


def compute_backoff(attempt_count: int, clock_now: datetime, jitter: float = 0.0) -> datetime:
    """Baseline 30s / 120s plus jitter.
    Attempt 1 -> next attempt after 30s.
    Attempt 2 -> next attempt after 120s.
    """
    if attempt_count <= 1:
        base = 30.0
    else:
        base = 120.0
    delay = max(1.0, base * (1.0 + jitter))
    return clock_now + timedelta(seconds=delay)


def classify_error(
    error: Exception | str,
    stage: str = "UNKNOWN",
    effect_state: SideEffectState = SideEffectState.NONE,
    attempt_count: int = 1,
    max_attempts: int = 3,
    reauth_count: int = 0,
    max_reauth: int = 1,
    clock: Callable[[], datetime] | None = None,
    cooldown_seconds: int = 0,
    jitter: float = 0.0,
) -> RecoveryDecision:
    now_fn = clock or utcnow
    now = now_fn()

    if isinstance(error, (LoginError, BrowserStop)):
        reason = str(error.reason)
    elif isinstance(error, Exception):
        reason = f"{type(error).__name__}: {str(error)}"
    else:
        reason = str(error)

    reason_clean = sanitize_error_message(reason)
    reason_upper = reason.upper()

    # Rule 1: Uncertain Side Effect — NEVER blindly replay mutation.
    if effect_state in (SideEffectState.CLAIMED, SideEffectState.UNCERTAIN) or "UNCERTAIN" in reason_upper or "RECONCIL" in reason_upper:
        return RecoveryDecision(
            error_code="RECONCILIATION_REQUIRED",
            category=ErrorCategory.UNCERTAIN_MUTATION,
            stage=stage,
            effect_state=SideEffectState.UNCERTAIN,
            action=RecoveryAction.RECONCILING,
            retryable=False,
            next_attempt_at=None,
            user_message="远端操作状态未决，为防止重复报价已暂停自动重试，请进行只读核对或人工处理。",
            cooldown_seconds=0,
        )

    # Rule 2: Local Persistence Failure — only retry local save, do not re-upload.
    if "LOCAL_PERSISTENCE" in reason_upper or "RESULT_STORAGE" in reason_upper or "DB_COMMIT" in reason_upper:
        return RecoveryDecision(
            error_code="LOCAL_PERSISTENCE_FAILED",
            category=ErrorCategory.LOCAL_PERSISTENCE_FAILED,
            stage=stage,
            effect_state=effect_state,
            action=RecoveryAction.RETRY_LOCAL_SAVE,
            retryable=True,
            next_attempt_at=now + timedelta(seconds=2),
            user_message="远端报价已获取，但本地数据存储异常，将重试本地持久化。",
            cooldown_seconds=0,
        )

    # Rule 3: Human action required (Captcha, MFA, Export declaration).
    if (
        reason in {"WAITING_HUMAN", "CAPTCHA_REQUIRED", "MFA_REQUIRED", "SMS_CODE_REQUIRED", "DECLARATION_REQUIRED", "XOMETRY_DECLARATION_REQUIRED"}
        or "CAPTCHA" in reason_upper
        or "DECLARATION" in reason_upper
    ):
        return RecoveryDecision(
            error_code="WAITING_HUMAN_REQUIRED",
            category=ErrorCategory.HUMAN_ACTION_REQUIRED,
            stage=stage,
            effect_state=effect_state,
            action=RecoveryAction.WAITING_HUMAN,
            retryable=False,
            next_attempt_at=None,
            user_message="需要人工介入（如验证码、安全认证或出口管制声明），已暂停等待处理。",
            cooldown_seconds=0,
        )

    # Rule 4: Session expired — single re-auth allowed.
    if reason in {"SESSION_EXPIRED", "UNAUTHORIZED", "LOGIN_REQUIRED", "TOKEN_EXPIRED"} or "401" in reason_upper or "SESSION_INVALID" in reason_upper:
        if reauth_count < max_reauth and attempt_count < max_attempts:
            return RecoveryDecision(
                error_code="SESSION_EXPIRED_REAUTHENTICATING",
                category=ErrorCategory.SESSION_EXPIRED,
                stage=stage,
                effect_state=effect_state,
                action=RecoveryAction.REAUTHENTICATE,
                retryable=True,
                next_attempt_at=now + timedelta(seconds=2),
                user_message="登录会话失效，正在进行一次自动重新认证。",
                cooldown_seconds=0,
            )
        return RecoveryDecision(
            error_code="SESSION_EXPIRED_REAUTH_EXHAUSTED",
            category=ErrorCategory.SESSION_EXPIRED,
            stage=stage,
            effect_state=effect_state,
            action=RecoveryAction.FAIL_TERMINAL,
            retryable=False,
            next_attempt_at=None,
            user_message="登录会话失效且已达重认证上限，请检查账号密码或登录状态。",
            cooldown_seconds=0,
        )

    # Rule 5: Rate limit / 429 cooldown.
    if reason in {"RATE_LIMITED", "TOO_MANY_REQUESTS", "COOLDOWN_ACTIVE"} or "429" in reason_upper or "LIMIT" in reason_upper:
        cd = max(cooldown_seconds, 60)
        if attempt_count < max_attempts:
            return RecoveryDecision(
                error_code="RATE_LIMITED_COOLING_DOWN",
                category=ErrorCategory.RATE_LIMITED,
                stage=stage,
                effect_state=effect_state,
                action=RecoveryAction.RETRY_WAIT,
                retryable=True,
                next_attempt_at=now + timedelta(seconds=cd),
                user_message=f"平台触发限流，进入冷却等待（{cd}秒）后重试。",
                cooldown_seconds=cd,
            )
        return RecoveryDecision(
            error_code="RATE_LIMITED_EXHAUSTED",
            category=ErrorCategory.RATE_LIMITED,
            stage=stage,
            effect_state=effect_state,
            action=RecoveryAction.FAIL_TERMINAL,
            retryable=False,
            next_attempt_at=None,
            user_message="平台持续触发限流，已达到最大尝试次数。",
            cooldown_seconds=cd,
        )

    # Rule 6: Temporary network errors / timeouts.
    if reason in {"NETWORK_TIMEOUT", "GATEWAY_TIMEOUT", "CONNECTION_RESET", "TIMEOUT"} or "TIMEOUT" in reason_upper or "CONNECTERROR" in reason_upper:
        if attempt_count < max_attempts:
            next_at = compute_backoff(attempt_count, now, jitter)
            return RecoveryDecision(
                error_code="TEMPORARY_NETWORK_ERROR",
                category=ErrorCategory.TEMPORARY_NETWORK,
                stage=stage,
                effect_state=effect_state,
                action=RecoveryAction.RETRY_WAIT,
                retryable=True,
                next_attempt_at=next_at,
                user_message="遇到临时网络超时，已排队等待下一次自动重试。",
                cooldown_seconds=0,
            )
        return RecoveryDecision(
            error_code="MAX_ATTEMPTS_EXCEEDED",
            category=ErrorCategory.TEMPORARY_NETWORK,
            stage=stage,
            effect_state=effect_state,
            action=RecoveryAction.FAIL_TERMINAL,
            retryable=False,
            next_attempt_at=None,
            user_message=f"网络超时且已达到最大尝试次数（{max_attempts}次），任务已停止。",
            cooldown_seconds=0,
        )

    # Rule 7: DOM or selector changed.
    if reason in {"DOM_CHANGED", "SELECTOR_NOT_FOUND", "PAGE_CONTRACT_MISMATCH"} or "SELECTOR" in reason_upper:
        return RecoveryDecision(
            error_code="DOM_CONTRACT_CHANGED",
            category=ErrorCategory.DOM_CONTRACT_CHANGED,
            stage=stage,
            effect_state=effect_state,
            action=RecoveryAction.FAIL_TERMINAL,
            retryable=False,
            next_attempt_at=None,
            user_message="第三方平台页面结构可能发生变更，已保留凭据并安全停止，请排查适配器。",
            cooldown_seconds=0,
        )

    # Rule 8: Process crash / lease expiry.
    if reason in {"BATCH_OWNER_LOST_NO_RETRY", "LEASE_EXPIRED", "OWNER_LOST"}:
        return RecoveryDecision(
            error_code="OWNER_LOST_RECONCILING",
            category=ErrorCategory.OWNER_LOST_EXPIRED,
            stage=stage,
            effect_state=effect_state,
            action=RecoveryAction.RECONCILING,
            retryable=False,
            next_attempt_at=None,
            user_message="任务执行者失联或租约超时，已保留状态进入待核对。",
            cooldown_seconds=0,
        )

    # Rule 9: Default — Permanent rejection (unsupported parameters, verified stop, validation errors).
    err_code = reason if (len(reason) <= 60 and reason.replace("_", "").isalnum() and reason.isupper()) else "PERMANENT_REJECTED"
    return RecoveryDecision(
        error_code=err_code,
        category=ErrorCategory.PERMANENT_REJECTED,
        stage=stage,
        effect_state=effect_state,
        action=RecoveryAction.FAIL_TERMINAL,
        retryable=False,
        next_attempt_at=None,
        user_message=f"不可重试的业务校验失败或平台限制：{reason_clean}",
        cooldown_seconds=0,
    )
