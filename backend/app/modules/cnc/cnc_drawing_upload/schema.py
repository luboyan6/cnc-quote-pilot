"""Public upload results never include a server storage path."""

from typing import Literal

from pydantic import BaseModel


class DrawingUploadResult(BaseModel):
    request_id: str
    state: Literal["PENDING", "READY"]
    part_id: int | None = None
    sha256: str
    size_bytes: int
