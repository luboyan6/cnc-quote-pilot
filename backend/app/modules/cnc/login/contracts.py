"""Bounded browser commands and public, secret-free session views."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LoginError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    kind: Literal["click", "drag", "scroll", "key", "text"]
    # 坐标空间跟随各流程的真实视口：登录会话是 1280x720，报价运行是 1600x1200
    # （嘉立创 1440x900）。客户端按运行视图回报的 viewport 换算，所以这里只留一个
    # 绝对上限，避免把任意大的数值直接送进 Playwright；具体边界由视口本身保证。
    x: int | None = Field(None, ge=0, lt=4096, strict=True)
    y: int | None = Field(None, ge=0, lt=4096, strict=True)
    x2: int | None = Field(None, ge=0, lt=4096, strict=True)
    y2: int | None = Field(None, ge=0, lt=4096, strict=True)
    delta_x: int | None = Field(None, ge=-1500, le=1500, strict=True)
    delta_y: int | None = Field(None, ge=-1500, le=1500, strict=True)
    key: Literal["Enter", "Tab", "Shift+Tab", "Backspace", "Delete", "Escape", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Space"] | None = None
    text: str | None = Field(None, min_length=1, max_length=256, repr=False)

    @model_validator(mode="after")
    def command_shape(self):
        required = {
            "click": {"x", "y"},
            # Slider challenges only accept a press-move-release sequence, so a
            # human completing one needs both the origin and the release point.
            "drag": {"x", "y", "x2", "y2"},
            "scroll": {"delta_y"},
            "key": {"key"},
            "text": {"text"},
        }[self.kind]
        supplied = {name for name in ("x", "y", "x2", "y2", "delta_x", "delta_y", "key", "text") if getattr(self, name) is not None}
        allowed = required | ({"delta_x"} if self.kind == "scroll" else set())
        if not required <= supplied or not supplied <= allowed:
            raise ValueError("INVALID_INPUT")
        return self


LoginStatus = Literal["STARTING", "AUTHENTICATING", "READY", "WAITING_HUMAN", "FAILED", "CLOSED"]


class LoginView(BaseModel):
    session_id: str
    account_id: int
    platform_name: str
    username: str
    status: LoginStatus
    reason: str
    reused: bool = False
    viewport: dict[str, int] = Field(default_factory=lambda: {"width": 1280, "height": 720})
    expires_at: datetime


@dataclass(frozen=True, repr=False)
class AccountSnapshot:
    id: int
    actor_id: int
    owner_id: int
    platform_id: int
    platform_name: str
    username: str
    password: str = field(repr=False)
    login_method: str
    login_url: str
    quote_url: str
    revision: str
    encrypted_state: str | None = field(repr=False)
    # Platform-side account code bound on the first proven credential submit.
    # Providers whose identity endpoint echoes the login identifier leave it empty.
    identity_code: str | None = None
