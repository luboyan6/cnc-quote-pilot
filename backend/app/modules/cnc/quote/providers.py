"""Reviewed adapter activation boundary.

Historical platform-config JSON is intentionally not executable configuration.
An adapter may be registered here only after primary-CAD controls/limit, complete
parameter readback and the no-order quote semantics have current evidence.
"""

from dataclasses import dataclass
from typing import Protocol

from app.modules.cnc.browser.contracts import PlatformAdapter


@dataclass(frozen=True)
class AdapterBinding:
    adapter: PlatformAdapter
    version: str
    max_size: int


class AdapterFactory(Protocol):
    def __call__(self, snapshot, run_id: str) -> AdapterBinding | None: ...


def resolve_quote_adapter(snapshot, run_id: str) -> AdapterBinding | None:
    # Current evidence: neither platform has a verified production upload +
    # full configure + current quote extraction contract. Login remains usable.
    # Fail explicitly before claiming or sending a remote upload, never infer
    # selectors or enable the draft research registry.
    return None
