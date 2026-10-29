from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ErrorCategory(str, Enum):
    TEMPORARY_NETWORK = "TEMPORARY_NETWORK"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    HUMAN_ACTION_REQUIRED = "HUMAN_ACTION_REQUIRED"
    PERMANENT_REJECTED = "PERMANENT_REJECTED"
    RATE_LIMITED = "RATE_LIMITED"
    DOM_CONTRACT_CHANGED = "DOM_CONTRACT_CHANGED"
    UNCERTAIN_MUTATION = "UNCERTAIN_MUTATION"
    LOCAL_PERSISTENCE_FAILED = "LOCAL_PERSISTENCE_FAILED"
    OWNER_LOST_EXPIRED = "OWNER_LOST_EXPIRED"


class SideEffectState(str, Enum):
    NONE = "NONE"
    CLAIMED = "CLAIMED"
    CONFIRMED = "CONFIRMED"
    UNCERTAIN = "UNCERTAIN"


class RecoveryAction(str, Enum):
    RETRY_WAIT = "RETRY_WAIT"
    REAUTHENTICATE = "REAUTHENTICATE"
    WAITING_HUMAN = "WAITING_HUMAN"
    RECONCILING = "RECONCILING"
    RETRY_LOCAL_SAVE = "RETRY_LOCAL_SAVE"
    FAIL_TERMINAL = "FAIL_TERMINAL"
    CANCEL_TERMINAL = "CANCEL_TERMINAL"


class RecoveryDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_code: str = Field(min_length=1, max_length=80)
    category: ErrorCategory
    stage: str
    effect_state: SideEffectState
    action: RecoveryAction
    retryable: bool
    next_attempt_at: datetime | None = None
    user_message: str = Field(min_length=1, max_length=1000)
    cooldown_seconds: int = 0


class RecoveryError(Exception):
    def __init__(self, reason: str, status_code: int = 400):
        super().__init__(reason)
        self.reason = reason
        self.status_code = status_code
