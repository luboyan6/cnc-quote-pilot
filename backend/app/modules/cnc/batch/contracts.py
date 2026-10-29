import hashlib
import json
from collections import Counter
from typing import Annotated
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from app.modules.cnc.quote.contracts import QuoteError

TERMINAL_ITEMS = frozenset({"COMPLETED", "FAILED", "CANCELLED"})
SUCCESS_QUOTES = frozenset({"QUOTED", "REFERENCE_ESTIMATE", "PENDING_REVIEW"})


class BatchError(QuoteError):
    def __init__(self, reason: str, status_code: int = 400):
        super().__init__(reason)
        self.status_code = status_code


class BatchTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    config_id: int = Field(ge=1, strict=True)
    account_id: int | None = Field(None, ge=1, strict=True)
    quantities: list[Annotated[StrictInt, Field(ge=1, le=100000)]] = Field(min_length=1, max_length=100)


class BatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    request_id: UUID
    targets: list[BatchTarget] = Field(min_length=1, max_length=100)


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def normalized_targets(data: BatchRequest):
    return sorted({(t.config_id, t.account_id, q) for t in data.targets for q in t.quantities}, key=lambda t: (t[0], t[1] or 0, t[2]))


def attempt_request_id(item_id: str, attempt_no: int) -> str:
    return str(uuid5(UUID(item_id), str(attempt_no)))


def aggregate(states: list[str]) -> tuple[str, dict[str, int]]:
    counts = dict(Counter(states))
    if any(s not in TERMINAL_ITEMS for s in states):
        status = next((s for s in ("CANCELLING", "RUNNING", "RECONCILING", "WAITING_HUMAN") if s in counts), "PENDING")
        # RECONCILING remains active but is a separately visible count.
        return ("RUNNING" if status == "RECONCILING" else status), counts
    if counts.get("CANCELLED"):
        return "CANCELLED", counts
    if counts.get("FAILED"):
        return ("PARTIAL_FAILED" if counts.get("COMPLETED") else "FAILED"), counts
    return "COMPLETED", counts
