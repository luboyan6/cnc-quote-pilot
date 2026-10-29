"""JlcQuoteService: Standalone and agent-invocable JLC CNC China quoting service.

Adheres strictly to .agents/skills/cnc-jlc-quote/SKILL.md and observed-dom-and-evidence.md.
Provides:
  - execute_jlc_quote(step_file_path, quantity, material, surface_finish, tolerance, lead_time_pref):
      Direct headless browser automation against JLC CNC quoting portal.
  - quote_part_config(auth, db, config_id, lead_time_pref, quantity_override):
      Loads CncPartConfig and CncPart, validates permissions and upload authorization,
      invokes execute_jlc_quote, and returns full structured quote result for agents/UI.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.config.path_conf import BASE_DIR
from app.core.base_schema import AuthSchema
from app.core.logger import logger
from app.modules.cnc.browser.contracts import Authentication, AuthStatus, SessionScope
from app.modules.cnc.browser.files import STEP_SUFFIXES, StepPayload
from app.modules.cnc.browser.session import BrowserExecutor
from app.modules.cnc.browser.state import SessionCodec
from app.modules.cnc.login.contracts import AccountSnapshot, LoginError
from app.modules.cnc.login.providers import resolve_provider
from app.utils.crypto_util import CryptoUtil


def _parse_num(text: str) -> str | None:
    """Unknown/invalid money remains unknown; a visible zero remains zero."""
    value = text.strip()
    currency = re.search(r"[¥￥]\s*([^\s元/（()）]+)", value)
    raw = currency.group(1) if currency else value
    if not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", raw):
        return None
    try:
        amount = Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None
    return str(amount) if amount.is_finite() and amount >= 0 else None


def _unit_price(text: str) -> str:
    amount = _parse_num(text.split("（", 1)[0])
    if amount is None:
        raise LoginError("JLC_CURRENT_PRICE_UNCONFIRMED")
    return amount


def _lead_days(text: str, title: str) -> str | None:
    match = re.search(rf"{re.escape(title)}[:：]\s*(\d+\s*个工作日)", text)
    return re.sub(r"\s+", "", match.group(1)) if match else None


async def _dismiss_jlc_tour(page) -> None:
    """Clear driver.js onboarding tour and full-page overlays."""
    try:
        skip_btn = page.locator("button:has-text('跳过'), button:has-text('不用了')")
        if await skip_btn.count() > 0 and await skip_btn.first.is_visible():
            await skip_btn.first.click(timeout=1500)
    except Exception:
        pass
    try:
        await page.evaluate("""() => {
            for (const node of document.querySelectorAll('[id^="driver-"], .driver-popover, .driver-overlay, #driver-page-overlay')) node.remove();
            for (const node of document.querySelectorAll('.driver-fix-stacking')) node.classList.remove('driver-fix-stacking');
        }""")
    except Exception:
        pass


async def _configure_jlc_parameters(
    page,
    *,
    material: str | None = None,
    surface_finish: str | None = None,
    tolerance: str | None = None,
    input_guard: Callable[[], Awaitable[None]],
) -> None:
    """Optionally opens the JLC CNC parameter modal and updates material, surface finish, and tolerance."""
    target_mat = material.strip() if material else ""
    target_surf = surface_finish.strip() if surface_finish else ""
    target_tol = tolerance.strip() if tolerance else ""

    # Normalize default material & surface finish checks
    is_default_mat = not target_mat or target_mat in {"铝合金", "铝合金-6061", "6061", "AL6061"}
    is_default_surf = not target_surf or "本色" in target_surf and "哑光" in target_surf and "阳极氧化" in target_surf
    is_default_tol = not target_tol or "GB/T 1804-2000" in target_tol or "m级" in target_tol

    if is_default_mat and is_default_surf and is_default_tol:
        return

    logger.info(f"更新嘉立创加工参数: material={target_mat}, surface={target_surf}, tol={target_tol}")
    await _dismiss_jlc_tour(page)
    btn = page.locator(".change-info, button:has-text('修改参数')").first
    if await btn.count() == 0 or not await btn.is_visible():
        await input_guard()
        await page.evaluate("() => document.querySelector('.change-info')?.click()")
    else:
        await input_guard()
        await btn.click(force=True)
    await page.wait_for_timeout(1000)

    dialog = page.locator(".material-dialog:visible, .el-dialog:has-text('选择加工参数'):visible").first
    try:
        await dialog.wait_for(state="visible", timeout=6000)
    except Exception:
        await _dismiss_jlc_tour(page)
        await input_guard()
        await page.evaluate("() => document.querySelector('.change-info')?.click()")
        await page.wait_for_timeout(1500)

    # 1. Update Material if not default
    if not is_default_mat:
        cat = None
        if "铝" in target_mat:
            cat = "铝合金"
        elif "不锈钢" in target_mat or "钢" in target_mat:
            cat = "不锈钢"
        elif "铜" in target_mat:
            cat = "铜合金"
        elif any(p in target_mat for p in ["POM", "尼龙", "ABS", "PC", "亚克力", "PEEK"]):
            cat = "塑料"

        if cat:
            cat_btn = page.locator(f".material-dialog .classification span.hand:has-text('{cat}')").first
            if await cat_btn.count() > 0 and await cat_btn.is_visible():
                await input_guard()
                await cat_btn.click(force=True)
                await page.wait_for_timeout(400)

        mat_item = page.locator(f".material-dialog .material-content span.hand:has-text('{target_mat}')").first
        if await mat_item.count() > 0 and await mat_item.is_visible():
            await input_guard()
            await mat_item.click(force=True)
            await page.wait_for_timeout(400)
        else:
            short_name = target_mat.split("-")[-1]
            fuzzy_item = page.locator(f".material-dialog .material-content span.hand:has-text('{short_name}')").first
            if await fuzzy_item.count() > 0 and await fuzzy_item.is_visible():
                await input_guard()
                await fuzzy_item.click(force=True)
                await page.wait_for_timeout(400)

    # 2. Update Surface Finish if specified
    if not is_default_surf:
        if "不做处理" in target_surf or "不处理" in target_surf or "无处理" in target_surf:
            no_finish = page.locator(".material-dialog .surface-item:has-text('表面不做处理')").first
            if await no_finish.count() > 0 and await no_finish.is_visible():
                await input_guard()
                await no_finish.click(force=True)
                await page.wait_for_timeout(400)
        else:
            for color in ["黑色", "深空灰", "红色", "粉红色", "天蓝色", "深绿色", "沙金", "宝蓝色"]:
                if color in target_surf:
                    color_btn = page.locator(f".material-dialog .surface-config span:has-text('{color}')").first
                    if await color_btn.count() > 0 and await color_btn.is_visible():
                        await input_guard()
                        await color_btn.click(force=True)
                        await page.wait_for_timeout(300)
                    break
            if "亮光" in target_surf:
                gloss_btn = page.locator(".material-dialog label.el-radio:has-text('亮光')").first
                if await gloss_btn.count() > 0 and await gloss_btn.is_visible():
                    await input_guard()
                    await gloss_btn.click(force=True)
                    await page.wait_for_timeout(300)

    # 3. Update Tolerance if not default
    if not is_default_tol:
        for tol_val in ["±0.02mm", "±0.05mm", "±0.10mm"]:
            if tol_val in target_tol:
                tol_btn = page.locator(f".material-dialog .el-radio:has-text('{tol_val}')").first
                if await tol_btn.count() > 0 and await tol_btn.is_visible():
                    await input_guard()
                    await tol_btn.click(force=True)
                    await page.wait_for_timeout(300)
                break

    # 4. Confirm submission via JS
    await input_guard()
    await page.evaluate("""() => {
        const btns = Array.from(document.querySelectorAll('.material-dialog .el-dialog__footer button, .el-dialog .el-dialog__footer button'));
        const target = btns.find(b => b.textContent.includes('确认提交') || b.textContent.includes('确'));
        if (target) target.click();
    }""")
    await page.wait_for_timeout(2500)
    await _dismiss_jlc_tour(page)


async def _ensure_jlc_session(session, provider, account: AccountSnapshot, input_guard: Callable[[], Awaitable[None]]) -> str:
    """Reuse only the selected account's verified session; otherwise submit it once."""
    await input_guard()
    await session.goto(account.quote_url)
    if account.identity_code and await provider.verify(session, account.username, account.identity_code):
        return account.identity_code
    if account.login_method != "PASSWORD" or not account.password:
        raise LoginError("MANUAL_LOGIN_REQUIRED")
    await input_guard()
    await session.goto(account.login_url)
    async with asyncio.timeout(30):
        submitted = await provider.submit(session, account.username, account.password, account.quote_url)
    if not submitted:
        raise LoginError("PROVIDER_VERIFICATION_REQUIRED")
    await session.goto(account.quote_url)
    identity = await provider.identify(session)
    if not identity or (account.identity_code and identity != account.identity_code):
        raise LoginError("IDENTITY_MISMATCH")
    if not await provider.verify(session, account.username, identity):
        raise LoginError("LOGIN_IDENTITY_VERIFICATION_REQUIRED")
    return identity


def _require_reviewed_parameter_readback() -> None:
    # The recorded JLC evidence describes the editor and an old screenshot,
    # but does not identify a reliable same-part, post-save readback for all
    # requested parameters. Do not upload or manufacture an effective result.
    raise LoginError("JLC_EFFECTIVE_PARAMETERS_UNVERIFIED")


async def execute_jlc_quote(
    step_file_path: str | Path,
    *,
    account: AccountSnapshot,
    input_guard: Callable[[], Awaitable[None]],
    mutation_guard: Callable[[str], Awaitable[None]],
    authenticated_guard: Callable[[str | None, str], Awaitable[None]] | None = None,
    payload: StepPayload | None = None,
    executor: BrowserExecutor | None = None,
    quantity: int = 1,
    material: str = "铝合金-6061",
    surface_finish: str = "喷砂+普通阳极氧化 - 本色 - 哑光",
    tolerance: str = "GB/T 1804-2000 m级",
    lead_time_pref: str = "标准",
) -> dict[str, Any]:
    """Execute live quoting automation against JLC CNC China portal.

    Strictly complies with the 'quote-only, no-order' boundary:
    never clicks '加入购物车' (addCarCNC) or checkout.
    """
    step_file = Path(step_file_path)
    if step_file.suffix.lower() not in STEP_SUFFIXES or payload is None or type(quantity) is not int or quantity < 1:
        raise LoginError("QUOTE_INPUT_INVALID")
    provider = resolve_provider(account.login_url, account.quote_url)
    if provider.code != "jlc_cnc_cn":
        raise LoginError("PLATFORM_UNSUPPORTED_OR_UNTRUSTED")
    _require_reviewed_parameter_readback()
    codec = SessionCodec(CryptoUtil)
    scope = SessionScope(str(account.owner_id), provider.code, str(account.id))
    # BrowserExecutor decrypts the account-bound scope and enforces provider egress.
    executor = executor or BrowserExecutor(codec, capacity=1)
    await input_guard()
    async with executor.session(scope, provider.policy, encrypted_state=account.encrypted_state) as session:
        page = session.page
        await page.set_viewport_size({"width": 1440, "height": 900})
        page.on("popup", lambda popup: asyncio.create_task(popup.close()))

        # 1. Verify session authentication (auto re-login if expired)
        customer_code = await _ensure_jlc_session(session, provider, account, input_guard)
        if authenticated_guard is not None:
            await input_guard()
            session.confirm_authentication(Authentication(AuthStatus.AUTHENTICATED, scope))
            await authenticated_guard(customer_code, await session.export_encrypted_state())

        # 2. Navigate to quote placeOrder page
        await input_guard()
        await session.goto(account.quote_url.split("#", 1)[0].rstrip("/") + "/#/placeOrder")
        await _dismiss_jlc_tour(page)

        # 3. Upload STEP drawing file
        upload_input = page.locator('input[type="file"].el-upload__input[name="file"]')
        await input_guard()
        await mutation_guard("upload")
        await upload_input.set_input_files(payload.sdk_payload())

        # 4. Wait for server-side geometry parsing
        dim_locator = page.locator("div, p, span").filter(has_text=re.compile(r"尺寸:\s*[\d.]+")).first
        await dim_locator.wait_for(state="visible", timeout=60000)
        await page.wait_for_timeout(1500)
        await _dismiss_jlc_tour(page)

        # Extract geometric information
        dim_text = await page.locator('p:has-text("尺寸:")').first.text_content() or ""
        vol_text = await page.locator('p:has-text("体积:")').first.text_content() or ""
        area_text = await page.locator('p:has-text("表面积:")').first.text_content() or ""

        def _clean(val: str) -> str:
            return re.sub(r"\s+", " ", val).strip()

        geometry = {
            "dimensions": _clean(dim_text.replace("尺寸:", "")),
            "volume": _clean(vol_text.replace("体积:", "")),
            "surface_area": _clean(area_text.replace("表面积:", "")),
        }

        # 5. Quantity configuration if quantity > 1
        if quantity > 1:
            await input_guard()
            await mutation_guard("configure")
            spinbutton = page.locator('input[role="spinbutton"], input.el-input__inner').first
            if await spinbutton.count() > 0 and await spinbutton.is_visible():
                await spinbutton.fill(str(quantity))
                await spinbutton.press("Enter")
                await page.wait_for_timeout(1500)

        # 6. Apply material, surface finish and tolerance configuration
        await input_guard()
        await mutation_guard("configure")
        await _configure_jlc_parameters(
            page,
            material=material,
            surface_finish=surface_finish,
            tolerance=tolerance,
            input_guard=input_guard,
        )

        # 7. Ensure row checkbox is selected
        await _dismiss_jlc_tour(page)
        checkbox = page.locator("tbody .el-checkbox").first
        if await checkbox.count() > 0:
            is_checked = await checkbox.locator('input[type="checkbox"]').is_checked()
            if not is_checked:
                await input_guard()
                await mutation_guard("configure")
                await checkbox.click(force=True)
                await page.wait_for_timeout(1000)

        # 8. Extract lead-time options and price breakdown
        tiers = []
        tier_names = [("加急", "加急交期"), ("标准", "标准交期"), ("经济", "经济交期")]

        for short_name, full_name in tier_names:
            await _dismiss_jlc_tour(page)
            radio = page.locator("div.delivery-box").get_by_text(short_name).first
            if await radio.count() > 0:
                await input_guard()
                await mutation_guard("configure")
                await radio.click(force=True)
                await page.wait_for_timeout(800)

                # Extract card text
                card_text = await page.locator("div.delivery-box").text_content() or ""
                days = _lead_days(card_text, full_name)

                # Read breakdown from summary box (.w300)
                summary_text = await page.locator(".w300 > .flex.flex-col.pt20 > div.mb20").text_content() or ""
                tax_match = re.search(r"税费[:：]\s*¥?\s*([\d.]+)", summary_text)
                total_match = re.search(r"总计[（(]含税[)）][:：]\s*¥?\s*([\d.]+)", summary_text)
                discount_match = re.search(r"券后约?\s*¥?\s*([\d.]+)", summary_text)

                # Read part price from radio or card
                price_match = re.search(rf"{full_name}[:：][^¥]*¥\s*([\d.]+)", card_text)
                part_amount = _parse_num(price_match.group(1)) if price_match else None
                tax_amount = _parse_num(tax_match.group(1)) if tax_match else None
                total_amount = _parse_num(total_match.group(1)) if total_match else None
                discount_amount = _parse_num(discount_match.group(1)) if discount_match else None

                # Estimate shipping time
                estimate_text = await page.locator("div.delivery-box .alert, div.delivery-box .el-alert__title").first.text_content() or ""

                tiers.append(
                    {
                        "tier": full_name,
                        "days": days,
                        "part_amount": part_amount,
                        "tax_amount": tax_amount,
                        "total_amount": total_amount,
                        "discount_amount": discount_amount,
                        "estimated_ship_date": estimate_text.strip(),
                    }
                )

        # 8. Re-select preferred lead time
        pref_tier = next((t for t in tiers if lead_time_pref in t["tier"]), None)
        if tiers and pref_tier is None:
            raise LoginError("JLC_LEAD_TIME_UNAVAILABLE")
        if pref_tier:
            pref_radio = page.locator("div.delivery-box").get_by_text(lead_time_pref).first
            if await pref_radio.count() > 0:
                await input_guard()
                await mutation_guard("configure")
                await _dismiss_jlc_tour(page)
                await pref_radio.click(force=True)
                await page.wait_for_timeout(500)

        # Re-read active summary breakdown for selected tier
        final_summary = await page.locator(".w300 > .flex.flex-col.pt20 > div.mb20").text_content() or ""
        cur_tax = re.search(r"税费[:：]\s*¥?\s*([\d.]+)", final_summary)
        cur_total = re.search(r"总计[（(]含税[)）][:：]\s*¥?\s*([\d.]+)", final_summary)
        cur_discount = re.search(r"券后约?\s*¥?\s*([\d.]+)", final_summary)
        active_tax = _parse_num(cur_tax.group(1)) if cur_tax else (pref_tier.get("tax_amount") if pref_tier else None)
        active_total = _parse_num(cur_total.group(1)) if cur_total else (pref_tier.get("total_amount") if pref_tier else None)
        active_discount = _parse_num(cur_discount.group(1)) if cur_discount else (pref_tier.get("discount_amount") if pref_tier else None)

        # Read unit price from table
        unit_price_text = await page.locator("td:has-text('系统预估价'), .price-info").first.text_content() or ""
        unit_price = _unit_price(unit_price_text)

        # 9. Save verified snapshot screenshot to static/upload
        screenshot_dir = BASE_DIR / "static" / "upload"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_name = f"jlc_quote_{step_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        screenshot_path = screenshot_dir / screenshot_name
        await page.screenshot(path=str(screenshot_path))

        now_iso = datetime.now(UTC).isoformat()
        return {
            "platform": "嘉立创中国",
            "customer_code": customer_code,
            "file_name": step_file.name,
            "geometry": geometry,
            "parameters": {
                "material": material,
                "quantity": quantity,
                "surface_finish": surface_finish,
                "tolerance": tolerance,
            },
            "quote_status": "REFERENCE_ESTIMATE",
            "currency": "CNY",
            "unit_price": unit_price,
            "tax_amount": active_tax,
            "total_amount": active_total,
            "discount_amount": active_discount,
            "selected_lead_time": pref_tier,
            "all_lead_time_tiers": tiers,
            "verified_at": now_iso,
            "evidence_screenshot": f"static/upload/{screenshot_name}",
            "note": "系统自动报价仅做参考，最终以人工审核报价为准。严格遵循只报价、不下单合规准则。",
        }


async def quote_part_config(
    auth: AuthSchema,
    db: Any,
    config_id: int,
    *,
    lead_time_pref: str = "标准",
    quantity_override: int | None = None,
    account_id: int | None = None,
) -> dict[str, Any]:
    """Agent tool entrypoint: Quote a CncPartConfig by ID.

    Reads drawing and parameter settings from cnc_part_config and cnc_part,
    verifies permissions, executes JLC quoting automation, and returns results.
    """
    from .instant import quote_config

    return await quote_config(
        auth,
        db,
        config_id,
        account_id=account_id,
        quantity_override=quantity_override,
        lead_time_pref=lead_time_pref,
        expected_provider="jlc_cnc_cn",
    )
