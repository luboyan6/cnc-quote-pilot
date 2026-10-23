"""Verify once, upload those bytes through the official Playwright file API."""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import BrowserStop, Reason


@dataclass(frozen=True)
class StepPayload:
    buffer: bytes = field(repr=False)
    sha256: str

    def sdk_payload(self) -> dict:
        # Do not expose the source path/name to the browser or any model.
        return {"name": "part.step", "mimeType": "application/step", "buffer": self.buffer}


@dataclass(frozen=True)
class TrustedStep:
    root: Path = field(repr=False)
    path: Path = field(repr=False)
    expected_sha256: str
    expected_size: int
    max_size: int  # Required verified platform limit, e.g. research RD 15_000_000.

    def read_verified(self) -> StepPayload:
        """A trusted root/identity comes from storage ACL, never from a page/model."""
        try:
            if not re.fullmatch(r"[0-9a-f]{64}", self.expected_sha256):
                raise ValueError
            if type(self.expected_size) is not int or type(self.max_size) is not int or not 0 < self.expected_size <= self.max_size:
                raise ValueError
            root = self.root.resolve(strict=True)
            path = self.path.resolve(strict=True)
            if not root.is_dir() or not path.is_relative_to(root) or path.suffix.lower() not in {".step", ".stp"}:
                raise ValueError
            with path.open("rb") as stream:
                contents = stream.read(self.max_size + 1)
            if len(contents) != self.expected_size or len(contents) > self.max_size:
                raise ValueError
            if hashlib.sha256(contents).hexdigest() != self.expected_sha256:
                raise ValueError
            if not contents.lstrip().startswith(b"ISO-10303-21;") or not contents.rstrip().endswith(b"END-ISO-10303-21;"):
                raise ValueError
            return StepPayload(contents, self.expected_sha256)
        except (OSError, ValueError, TypeError, RuntimeError):
            raise BrowserStop(Reason.FILE_INVALID) from None


async def upload_step(locator: Any, payload: StepPayload) -> None:
    """Strict Locator auto-waits are provided by the official SDK. No retries."""
    await locator.set_input_files(payload.sdk_payload())


async def upload_step_with_chooser(page: Any, trigger: Any, payload: StepPayload) -> None:
    """For a verified dynamic picker; never automate an OS file dialog."""
    async with page.expect_file_chooser() as chooser:
        await trigger.click()
    await (await chooser.value).set_files(payload.sdk_payload())
