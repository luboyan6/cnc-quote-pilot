import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt


def utcnow() -> datetime:
    return datetime.now(UTC)


class ScheduleError(Exception):
    def __init__(self, reason: str, status_code: int = 400):
        super().__init__(reason)
        self.reason = reason
        self.status_code = status_code


class ScheduleTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    config_id: int = Field(ge=1, strict=True)
    account_id: int | None = Field(None, ge=1, strict=True)
    quantities: list[Annotated[StrictInt, Field(ge=1, le=100000)]] = Field(min_length=1, max_length=100)


class ScheduleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: str = Field(min_length=1, max_length=120)
    interval_minutes: int = Field(ge=1, le=43200)  # 1 min to 30 days
    timezone: str = Field(default="UTC", min_length=1, max_length=40)
    targets: list[ScheduleTarget] = Field(min_length=1, max_length=100)


class ScheduleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: str | None = Field(None, min_length=1, max_length=120)
    interval_minutes: int | None = Field(None, ge=1, le=43200)
    timezone: str | None = Field(None, min_length=1, max_length=40)
    targets: list[ScheduleTarget] | None = Field(None, min_length=1, max_length=100)


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def compute_next_slot(anchor_time: datetime, interval_minutes: int, now: datetime) -> datetime:
    """Calculates the next future slot starting from anchor_time in increments of interval_minutes."""
    anchor = ensure_utc(anchor_time)
    current = ensure_utc(now)
    if current <= anchor:
        return anchor
    delta_seconds = (current - anchor).total_seconds()
    interval_seconds = interval_minutes * 60
    k = int(delta_seconds // interval_seconds) + 1
    return anchor + timedelta(seconds=k * interval_seconds)


def target_fingerprint(targets: list[ScheduleTarget]) -> str:
    raw = sorted(
        {(t.config_id, t.account_id, q) for t in targets for q in t.quantities},
        key=lambda x: (x[0], x[1] or 0, x[2]),
    )
    return hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
