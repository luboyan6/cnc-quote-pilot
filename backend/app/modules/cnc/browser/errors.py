"""Fixed public reasons: never include DOM, URLs, credentials, or SDK errors."""

from enum import StrEnum


class Reason(StrEnum):
    INVALID_INPUT = "invalid_input"
    POLICY_BLOCKED = "policy_blocked"
    SESSION_INVALID = "session_invalid"
    SESSION_BUSY = "session_busy"
    CAPACITY = "browser_capacity"
    WRONG_CONSUMER = "wrong_consumer"
    DEPENDENCY_MISSING = "browser_dependency_missing"
    BROWSER_FAILED = "browser_failed"
    CLEANUP_FAILED = "browser_cleanup_failed"
    AUTH_REQUIRED = "authentication_required"
    CHALLENGE = "human_challenge"
    IDENTITY_MISMATCH = "identity_mismatch"
    PAGE_UNKNOWN = "page_unknown"
    READ_TIMEOUT = "read_timeout"
    FILE_INVALID = "file_invalid"
    STATE_UNAVAILABLE = "intent_store_unavailable"
    INTENT_CONFLICT = "intent_conflict"
    MUTATION_UNCERTAIN = "mutation_uncertain"
    PARAMETERS_MISMATCH = "parameters_mismatch"
    GEOMETRY_INVALID = "geometry_invalid"
    QUOTE_INVALID = "quote_invalid"


class BrowserStop(Exception):
    """Safe to project into an exception-agent decision, without raw page data."""

    def __init__(self, reason: Reason) -> None:
        self.reason = Reason(reason)
        super().__init__(self.reason.value)
