"""Reviewed adapter activation boundary.

Historical platform-config JSON is intentionally not executable configuration.
An adapter may be registered here only after primary-CAD controls/limit, complete
parameter readback and the no-order quote semantics have current evidence.
"""

from dataclasses import dataclass
from typing import Protocol

from app.modules.cnc.browser.contracts import PlatformAdapter

from .contracts import QuoteError
from .xometry import XometryDOMBinding, XometryQuoteAdapter

# Only a reviewed source binding belongs here. A public uploader, old test-route
# candidates, synthetic fixture, or user setting cannot activate managed quotes.
_REVIEWED_XOMETRY_BINDING: XometryDOMBinding | None = None


@dataclass(frozen=True)
class AdapterBinding:
    adapter: PlatformAdapter
    version: str
    max_size: int


class AdapterFactory(Protocol):
    def __call__(self, snapshot, run_id: str) -> AdapterBinding | None: ...


def resolve_quote_adapter(snapshot, run_id: str) -> AdapterBinding | None:
    if snapshot.provider_code == "xometry_us":
        binding = _REVIEWED_XOMETRY_BINDING
        if binding is None:
            raise QuoteError("XOMETRY_BINDING_UNVERIFIED")
        adapter = XometryQuoteAdapter(snapshot, run_id, binding)
        adapter.validate_parameters(snapshot.requested)
        return AdapterBinding(adapter, binding.version, binding.max_size)
    # Other providers remain explicitly unavailable rather than borrowing the
    # Xometry upload/configuration/result semantics.
    return None
