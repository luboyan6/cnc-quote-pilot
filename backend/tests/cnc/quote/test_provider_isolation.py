"""Provider shortcuts use selected account scopes, frozen bytes and durable guards."""

import hashlib
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.cnc.browser.contracts import Parameters, SessionScope
from app.modules.cnc.browser.files import StepPayload, TrustedStep
from app.modules.cnc.login.contracts import AccountSnapshot, LoginError
from app.modules.cnc.quote import instant
from app.modules.cnc.quote import jlc_quote_service as jlc
from app.modules.cnc.quote import xometry_quote_service as xometry
from app.modules.cnc.quote.contracts import QuoteSnapshot

STEP = b"ISO-10303-21;\nEND-ISO-10303-21;"
PAYLOAD = StepPayload(STEP, hashlib.sha256(STEP).hexdigest())
ACCOUNT = AccountSnapshot(91, 7, 7, 83, "JLC", "selected-user", "selected-password", "PASSWORD", "https://www.jlc-cnc.com", "https://www.jlc-cnc.com/cncOrder", "rev", None, "selected-code")


@pytest.fixture
def jlc_isolation_without_activation():
    # These synthetic tests stop before a result and exercise the guarded
    # account/upload internals; they do not activate the production path.
    with patch.object(jlc, "_require_reviewed_parameter_readback"):
        yield


@pytest.mark.asyncio
@pytest.mark.parametrize(("quantity", "material"), [(1, "铝合金-6061"), (5, "不锈钢-304")])
async def test_jlc_unverified_parameters_stop_before_browser_or_upload(quantity, material):
    browser = MagicMock()
    inputs = AsyncMock()
    mutation = AsyncMock()
    with pytest.raises(LoginError, match="JLC_EFFECTIVE_PARAMETERS_UNVERIFIED"):
        await jlc.execute_jlc_quote(
            "part.step",
            account=ACCOUNT,
            payload=PAYLOAD,
            quantity=quantity,
            material=material,
            input_guard=inputs,
            mutation_guard=mutation,
            executor=SimpleNamespace(session=browser),
        )
    browser.assert_not_called()
    inputs.assert_not_awaited()
    mutation.assert_not_awaited()


@pytest.mark.asyncio
async def test_jlc_reuses_only_verified_selected_identity():
    session = SimpleNamespace(goto=AsyncMock())
    provider = SimpleNamespace(verify=AsyncMock(return_value=True), submit=AsyncMock())
    guard = AsyncMock()
    assert await jlc._ensure_jlc_session(session, provider, ACCOUNT, guard) == "selected-code"
    provider.verify.assert_awaited_once_with(session, "selected-user", "selected-code")
    provider.submit.assert_not_awaited()
    guard.assert_awaited_once()


@pytest.mark.asyncio
async def test_jlc_login_uses_selected_credentials_and_rejects_wrong_identity():
    session = SimpleNamespace(goto=AsyncMock())
    provider = SimpleNamespace(verify=AsyncMock(return_value=False), submit=AsyncMock(return_value=True), identify=AsyncMock(return_value="other-code"))
    with pytest.raises(LoginError, match="IDENTITY_MISMATCH"):
        await jlc._ensure_jlc_session(session, provider, ACCOUNT, AsyncMock())
    provider.submit.assert_awaited_once_with(session, ACCOUNT.username, ACCOUNT.password, ACCOUNT.quote_url)


@pytest.mark.asyncio
@pytest.mark.usefixtures("jlc_isolation_without_activation")
async def test_jlc_upload_uses_account_scope_and_frozen_bytes_after_guards():
    operations = []
    upload = AsyncMock(side_effect=RuntimeError("stop-after-upload"))
    page = SimpleNamespace(set_viewport_size=AsyncMock(), on=MagicMock(), locator=MagicMock(return_value=SimpleNamespace(set_input_files=upload)))
    session = SimpleNamespace(page=page, goto=AsyncMock())
    observed = {}

    @asynccontextmanager
    async def browser(scope, policy, *, encrypted_state):
        observed.update(scope=scope, state=encrypted_state)
        yield session

    async def inputs():
        operations.append("inputs")

    async def mutation(operation):
        operations.append(operation)

    with patch.object(jlc, "_ensure_jlc_session", AsyncMock(return_value="selected-code")), patch.object(jlc, "_dismiss_jlc_tour", AsyncMock()):
        with pytest.raises(RuntimeError, match="stop-after-upload"):
            await jlc.execute_jlc_quote(
                "private-file.setp",
                account=ACCOUNT,
                payload=PAYLOAD,
                input_guard=inputs,
                mutation_guard=mutation,
                executor=SimpleNamespace(session=browser),
            )
    assert observed["scope"] == SessionScope("7", "jlc_cnc_cn", "91")
    assert observed["state"] is None
    upload.assert_awaited_once_with(PAYLOAD.sdk_payload())
    assert operations[-2:] == ["inputs", "upload"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("jlc_isolation_without_activation")
async def test_jlc_persists_only_encrypted_verified_account_state_through_guard():
    session = SimpleNamespace(
        page=SimpleNamespace(set_viewport_size=AsyncMock(), on=MagicMock()),
        goto=AsyncMock(side_effect=RuntimeError("stop-before-upload")),
        confirm_authentication=MagicMock(),
        export_encrypted_state=AsyncMock(return_value="encrypted-account-state"),
    )

    @asynccontextmanager
    async def browser(*args, **kwargs):
        assert kwargs["encrypted_state"] == "selected-encrypted-state"
        yield session

    save_state = AsyncMock()
    with patch.object(jlc, "_ensure_jlc_session", AsyncMock(return_value="selected-code")):
        with pytest.raises(RuntimeError, match="stop-before-upload"):
            await jlc.execute_jlc_quote(
                "part.step",
                account=replace(ACCOUNT, encrypted_state="selected-encrypted-state"),
                payload=PAYLOAD,
                input_guard=AsyncMock(),
                mutation_guard=AsyncMock(),
                authenticated_guard=save_state,
                executor=SimpleNamespace(session=browser),
            )
    save_state.assert_awaited_once_with("selected-code", "encrypted-account-state")
    assert session.confirm_authentication.call_args.args[0].scope == SessionScope("7", "jlc_cnc_cn", "91")


@pytest.mark.asyncio
@pytest.mark.usefixtures("jlc_isolation_without_activation")
async def test_jlc_lost_lease_guard_prevents_upload():
    upload = AsyncMock()
    page = SimpleNamespace(set_viewport_size=AsyncMock(), on=MagicMock(), locator=MagicMock(return_value=SimpleNamespace(set_input_files=upload)))
    session = SimpleNamespace(page=page, goto=AsyncMock())

    @asynccontextmanager
    async def browser(*args, **kwargs):
        yield session

    with patch.object(jlc, "_ensure_jlc_session", AsyncMock(return_value="selected-code")), patch.object(jlc, "_dismiss_jlc_tour", AsyncMock()):
        with pytest.raises(LoginError, match="LEASE_LOST"):
            await jlc.execute_jlc_quote(
                "part.step",
                account=ACCOUNT,
                payload=PAYLOAD,
                input_guard=AsyncMock(),
                mutation_guard=AsyncMock(side_effect=LoginError("LEASE_LOST")),
                executor=SimpleNamespace(session=browser),
            )
    upload.assert_not_awaited()


def declaration_page():
    absent = SimpleNamespace(count=AsyncMock(return_value=0))
    declaration = SimpleNamespace(wait_for=AsyncMock(), count=AsyncMock(return_value=1), is_visible=AsyncMock(return_value=True), click=AsyncMock())
    uploader = SimpleNamespace(count=AsyncMock(return_value=1), set_input_files=AsyncMock())

    def locator(selector):
        element = uploader if selector == 'input[type="file"]' else declaration if "ItarView" in selector else absent
        return SimpleNamespace(first=element)

    return SimpleNamespace(url=xometry.DASHBOARD, locator=locator, wait_for_timeout=AsyncMock()), declaration, uploader


@pytest.mark.asyncio
async def test_xometry_omitted_declaration_stops_before_choice_or_continue():
    page, declaration, uploader = declaration_page()
    mutation = AsyncMock()
    with pytest.raises(xometry.XometryQuoteError, match="QUOTE_EXPORT_DECLARATION_REQUIRED"):
        await xometry._upload_step_file(page, Path("private.step"), payload=PAYLOAD, input_guard=AsyncMock(), mutation_guard=mutation)
    uploader.set_input_files.assert_awaited_once_with(PAYLOAD.sdk_payload())
    declaration.click.assert_not_awaited()
    mutation.assert_awaited_once_with("upload")


@pytest.mark.asyncio
async def test_xometry_declaration_guard_failure_is_not_swallowed():
    page, declaration, _ = declaration_page()
    with pytest.raises(LoginError, match="QUOTE_PERMISSION_REVOKED"):
        await xometry._upload_step_file(
            page,
            Path("private.step"),
            False,
            payload=PAYLOAD,
            input_guard=AsyncMock(side_effect=[None, LoginError("QUOTE_PERMISSION_REVOKED")]),
            mutation_guard=AsyncMock(),
        )
    declaration.click.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy_choice", [False, True])
async def test_xometry_boolean_cannot_replace_file_version_declaration(legacy_choice):
    page, declaration, _ = declaration_page()
    with pytest.raises(xometry.XometryQuoteError, match="QUOTE_EXPORT_DECLARATION_REQUIRED"):
        await xometry._upload_step_file(page, Path("private.step"), legacy_choice, payload=PAYLOAD, input_guard=AsyncMock(), mutation_guard=AsyncMock())
    declaration.click.assert_not_awaited()


@pytest.mark.parametrize("text", ["", "系统预估价 暂无", "审核中", "¥12.3.4", "¥-1.00", "NaN", "Infinity", "2件"])
def test_jlc_missing_or_invalid_price_never_becomes_zero(text):
    with pytest.raises(LoginError, match="JLC_CURRENT_PRICE_UNCONFIRMED"):
        jlc._unit_price(text)


def test_jlc_visible_zero_and_unknown_lead_time_remain_distinct():
    assert jlc._unit_price("系统预估价 ¥0.00（参考）") == "0.00"
    assert jlc._unit_price("¥1,234.50") == "1234.50"
    assert jlc._lead_days("标准交期：6 个工作日", "标准交期") == "6个工作日"
    assert jlc._lead_days("标准交期：¥20.00", "标准交期") is None
    assert jlc._lead_days("预计到货 2026-12-01", "标准交期") is None


@pytest.mark.asyncio
@pytest.mark.usefixtures("jlc_isolation_without_activation")
async def test_jlc_missing_price_cannot_return_completed_estimate():
    locator = MagicMock()
    locator.first = locator
    locator.filter.return_value = locator
    locator.get_by_text.return_value = locator
    locator.count = AsyncMock(return_value=0)
    locator.text_content = AsyncMock(return_value="")
    locator.set_input_files = AsyncMock()
    locator.wait_for = AsyncMock()
    page = SimpleNamespace(set_viewport_size=AsyncMock(), on=MagicMock(), locator=MagicMock(return_value=locator), wait_for_timeout=AsyncMock(), screenshot=AsyncMock())
    session = SimpleNamespace(page=page, goto=AsyncMock())

    @asynccontextmanager
    async def browser(*args, **kwargs):
        yield session

    with (
        patch.object(jlc, "_ensure_jlc_session", AsyncMock(return_value="selected-code")),
        patch.object(jlc, "_dismiss_jlc_tour", AsyncMock()),
        patch.object(jlc, "_configure_jlc_parameters", AsyncMock()),
    ):
        with pytest.raises(LoginError, match="JLC_CURRENT_PRICE_UNCONFIRMED"):
            await jlc.execute_jlc_quote("part.step", account=ACCOUNT, payload=PAYLOAD, input_guard=AsyncMock(), mutation_guard=AsyncMock(), executor=SimpleNamespace(session=browser))
    page.screenshot.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "effective",
    [
        None,
        {"material": "铝合金-6061", "quantity": "1", "surface_finish": "喷砂", "tolerance": "标准"},
        {"material": "不锈钢-304", "quantity": "5", "surface_finish": "喷砂", "tolerance": "标准"},
        {"material": "铝合金-6061", "quantity": "5"},
    ],
)
async def test_jlc_run_does_not_publish_requested_values_as_effective(effective):
    from app.modules.cnc.quote.service import QuoteService

    snapshot = QuoteSnapshot(
        8,
        9,
        ACCOUNT,
        "config-rev",
        "part.step",
        TrustedStep(Path("."), Path("part.step"), PAYLOAD.sha256, len(STEP), 1000),
        PAYLOAD,
        Parameters.from_mapping({"material": "铝合金-6061", "quantity": "5", "surface_finish": "喷砂", "tolerance": "标准"}),
        "jlc_cnc_cn",
    )
    repository = SimpleNamespace(stage_shortcut_result=AsyncMock(), save=AsyncMock())
    activity = SimpleNamespace(
        snapshot=snapshot,
        change=AsyncMock(),
        finish=AsyncMock(),
        input_guard=AsyncMock(),
        mutation_guard=AsyncMock(),
        authenticated_guard=AsyncMock(),
        repository=repository,
        pending_result=False,
    )
    service = QuoteService(repository=object(), manager=object())
    with patch.object(jlc, "execute_jlc_quote", AsyncMock(return_value={"effective": effective, "unit_price": "12.34"})):
        await service._run_jlc(activity)
    activity.finish.assert_awaited_once_with("JLC_EFFECTIVE_PARAMETERS_UNVERIFIED")
    repository.stage_shortcut_result.assert_not_awaited()
    repository.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_xometry_tier_zero_missing_and_unit_only_do_not_invent_amounts():
    blocks = ["Least Expensive $0.00 ea. $0.00 Arrives by Nov 10", "Standard $10.00 ea.", "Fastest Pending Review"]
    with patch.object(xometry, "_settle", AsyncMock(return_value=blocks)):
        from datetime import UTC, datetime

        tiers = await xometry._read_tiers(object(), datetime(2026, 10, 28, tzinfo=UTC))
    assert tiers[0]["amount"] == "0.00"
    assert tiers[0]["unit_amount"] == "0.00"
    assert xometry._quote_status(tiers[0]) == "QUOTED"
    assert tiers[1]["amount"] is None
    assert tiers[1]["unit_amount"] == "10.00"
    assert tiers[1]["arrives_by"] is None
    assert tiers[2]["amount"] is None
    assert xometry._quote_status(tiers[2]) == "PENDING_REVIEW"
    with pytest.raises(xometry.XometryQuoteError, match="XOMETRY_CURRENT_PRICE_UNCONFIRMED"):
        xometry._quote_status({"amount": None, "raw": "Standard"})


@pytest.mark.asyncio
async def test_xometry_missing_tiers_cannot_be_named_by_position_or_fallback():
    from datetime import UTC, datetime

    with patch.object(xometry, "_settle", AsyncMock(return_value=["Standard $10.00", "$15.00"])):
        tiers = await xometry._read_tiers(object(), datetime(2026, 10, 28, tzinfo=UTC))
    assert tiers[0]["tier"] == "Standard"
    assert tiers[1]["tier"] is None
    assert xometry._select_tier(tiers, "Standard")["amount"] == "10.00"
    with pytest.raises(xometry.XometryQuoteError, match="XOMETRY_LEAD_TIME_UNCONFIRMED"):
        xometry._select_tier(tiers, "Fastest")


@pytest.mark.asyncio
async def test_xometry_revocation_after_quantity_fill_stops_before_enter():
    field = SimpleNamespace(wait_for=AsyncMock(), fill=AsyncMock(), press=AsyncMock())
    page = SimpleNamespace(locator=MagicMock(return_value=SimpleNamespace(first=field)))
    guard = AsyncMock(side_effect=[None, LoginError("QUOTE_PERMISSION_REVOKED")])
    with pytest.raises(LoginError, match="QUOTE_PERMISSION_REVOKED"):
        await xometry._set_quantity(page, 5, input_guard=guard)
    field.fill.assert_awaited_once_with("5")
    field.press.assert_not_awaited()


@pytest.mark.asyncio
async def test_jlc_revocation_after_dialog_open_stops_before_parameter_write():
    button = SimpleNamespace(count=AsyncMock(return_value=1), is_visible=AsyncMock(return_value=True), click=AsyncMock(), wait_for=AsyncMock())
    page = SimpleNamespace(locator=MagicMock(return_value=SimpleNamespace(first=button)), wait_for_timeout=AsyncMock())
    guard = AsyncMock(side_effect=[None, LoginError("QUOTE_PERMISSION_REVOKED")])
    with patch.object(jlc, "_dismiss_jlc_tour", AsyncMock()):
        with pytest.raises(LoginError, match="QUOTE_PERMISSION_REVOKED"):
            await jlc._configure_jlc_parameters(page, material="不锈钢-304", input_guard=guard)
    button.click.assert_awaited_once()


@pytest.mark.asyncio
async def test_instant_uses_shared_snapshot_and_does_not_mutate_source_parameters():
    snapshot = QuoteSnapshot(
        8,
        9,
        ACCOUNT,
        "config-rev",
        "part.step",
        TrustedStep(Path("."), Path("part.step"), PAYLOAD.sha256, len(STEP), 1000),
        PAYLOAD,
        Parameters.from_mapping({"material": "6061", "quantity": "5"}),
        "jlc_cnc_cn",
    )
    view = SimpleNamespace(run_id="durable-run", status="WAITING_HUMAN", reason="MANUAL_LOGIN_REQUIRED", result=None)
    service = SimpleNamespace(repository=SimpleNamespace(snapshot=AsyncMock(return_value=snapshot)), start_snapshot=AsyncMock(return_value=view), status=AsyncMock())
    with patch.object(instant, "get_quote_service", return_value=service):
        result = await instant.quote_config(object(), object(), 8, account_id=91, quantity_override=5, tolerance="exact-tolerance")
    assert result["run_id"] == "durable-run"
    assert result["quote_status"] == "WAITING_HUMAN"
    passed = service.start_snapshot.call_args.args[1]
    assert passed.account.id == 91
    assert dict(passed.requested.values)["tolerance"] == "exact-tolerance"
    assert "tolerance" not in dict(snapshot.requested.values)
    assert service.start_snapshot.call_args.kwargs["export_controlled"] is None
    service.status.assert_not_awaited()


@pytest.mark.asyncio
async def test_jlc_legacy_wrapper_preserves_selected_account():
    with patch.object(instant, "quote_config", AsyncMock(return_value={"run_id": "durable"})) as shared:
        await jlc.quote_part_config("auth", "unused-db", 8, account_id=91, quantity_override=5)
    assert shared.call_args.kwargs["account_id"] == 91
    assert shared.call_args.kwargs["expected_provider"] == "jlc_cnc_cn"
