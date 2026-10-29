"""Compatibility entrypoint through the durable, account-fenced quote service."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any
from uuid import uuid4

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.modules.cnc.browser.contracts import Parameters
from app.modules.cnc.browser.errors import BrowserStop
from app.modules.cnc.login.contracts import LoginError

from .contracts import TERMINAL
from .service import get_quote_service


async def quote_config(
    auth: AuthSchema,
    db: Any,
    config_id: int,
    *,
    account_id: int | None = None,
    quantity_override: int | None = None,
    export_controlled: bool | None = None,
    quote_id: str | None = None,
    tolerance: str | None = None,
    roughness: str | None = None,
    lead_time_pref: str | None = None,
    expected_provider: str | None = None,
) -> dict[str, Any]:
    """Use one frozen Run; never retain the caller's HTTP DB session.

    Omitted legacy declaration booleans remain unknown. Managed declaration
    decisions use the existing explicit file/version/choice API.
    """
    service = get_quote_service()
    try:
        snapshot = await service.repository.snapshot(auth, config_id, account_id, quantity=quantity_override)
        if expected_provider is not None and snapshot.provider_code != expected_provider:
            raise LoginError("PLATFORM_UNSUPPORTED_OR_UNTRUSTED")
        if quote_id is not None:
            raise LoginError("QUOTE_EXISTING_REMOTE_INPUT_UNVERIFIED")
        requested = dict(snapshot.requested.values)
        for name, value in (("tolerance", tolerance), ("roughness", roughness), ("lead_time_pref", lead_time_pref)):
            if value is not None:
                requested[name] = value
        snapshot = replace(snapshot, requested=Parameters.from_mapping(requested))
        view = await service.start_snapshot(auth, snapshot, str(uuid4()), export_controlled=export_controlled)
        deadline = asyncio.get_running_loop().time() + 300
        while view.status not in TERMINAL and view.status != "WAITING_HUMAN":
            if asyncio.get_running_loop().time() >= deadline:
                break
            await asyncio.sleep(0.5)
            view = await service.status(auth, config_id, view.run_id)
        if view.status in {"FAILED", "CANCELLED"}:
            raise LoginError(view.reason)
        result = view.result
        return {
            "config_id": config_id,
            "run_id": view.run_id,
            "provider": snapshot.provider_code,
            "platform": snapshot.account.platform_name,
            "file_name": snapshot.file_name,
            "quote_status": view.status,
            "reason": view.reason,
            "parameters": dict(snapshot.requested.values),
            "unit_price": result.amount if result and result.price_scope == "unit" else None,
            "total_amount": result.total_amount if result else None,
            "tax_amount": result.tax_amount if result else None,
            "discount_amount": result.discount_amount if result else None,
            "currency": result.currency if result else None,
            "selected_lead_time": result.lead_time if result else None,
            "all_lead_time_tiers": result.lead_time_tiers if result else None,
            "verified_at": result.observed_at.isoformat() if result else None,
        }
    except (LoginError, BrowserStop) as exc:
        raise CustomException(msg=str(exc.reason)) from None
