"""Safe, ordered event envelope for one local generation turn."""

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal[
    "turn.started", "text.delta", "skill.activated", "tool.started", "tool.completed", "tool.failed",
    "domain.progress", "evidence.available", "turn.completed", "turn.stopped", "turn.failed",
]


class AgentEvent(BaseModel):
    session_id: str
    turn_id: str
    seq: int
    type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)


def evidence_reference(tool_name: str | None, content: Any) -> dict[str, int] | None:
    """Extract only an authorized tool's bounded, private result reference."""
    if tool_name != "cnc_quote_result_detail" or not isinstance(content, str) or len(content) > 65536:
        return None
    try:
        value = json.loads(content)
    except (ValueError, TypeError):
        return None
    if not isinstance(value, dict) or value.get("evidence_available") is not True:
        return None
    result_id = value.get("id")
    if type(result_id) is not int or result_id <= 0:
        return None
    return {"result_id": result_id}
