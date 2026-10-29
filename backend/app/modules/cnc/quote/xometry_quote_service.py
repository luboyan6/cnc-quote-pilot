"""Xometry (美国站) 自动化报价服务类与方法实现。

严格对齐 .agents/skills/cnc-xometry-quote/SKILL.md 及 observed-dom-and-evidence.md。
严格遵守「只报价、不下单」合规准则（从不点击 Checkout、Place Order 或付款）。

封装于核心服务类 XometryQuoteService 中，提供两个标准化方法：
1. execute_xometry_quote:
   底层无头浏览器（Playwright）驱动的自动化执行方法。
   支持直接上传 STEP 图纸并等待几何解析（或针对已有报价单零件进行对账复用），
   自动处理出口管制声明（EAR99），配置数量/材质/表面处理/精密公差/粗糙度，
   读取 Fastest / Standard / Least Expensive 三档交期、单价、总价及到货日期，截屏留证。
2. quote_part_config:
   系统业务与 Agent 调用的图纸参数配置自动报价入口方法。
   根据 config_id 从数据库读取 CncPartConfig 与关联 CncPart 图纸，
   校验权限与 upload_authorized 授权，解析本地 STEP 图纸物理路径，
   结合 XometryCncParamCatalog 将通用或中文加工参数映射为 Xometry 官方英文选项，
   拉起 execute_xometry_quote 自动化执行，返回结构化报价结果。
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.config.path_conf import BASE_DIR
from app.core.base_schema import AuthSchema
from app.core.logger import logger
from app.modules.cnc.browser.contracts import Authentication, AuthStatus, SessionScope
from app.modules.cnc.browser.errors import BrowserStop
from app.modules.cnc.browser.files import StepPayload
from app.modules.cnc.browser.session import BrowserExecutor
from app.modules.cnc.browser.state import SessionCodec
from app.modules.cnc.login.contracts import AccountSnapshot, LoginError
from app.modules.cnc.login.providers import resolve_provider
from app.modules.cnc.quote.xometry_cnc_params_loader import XometryCncParamCatalog
from app.utils.crypto_util import CryptoUtil

# --- 实测稳定的 DOM 选择器与规则 ---

DASHBOARD = "https://www.xometry.com/quoting/home/"
NEW_QUOTE_URL = "https://www.xometry.com/quoting/quote/new"
QUOTE_PATH = "/quoting/quote/{quote_id}"
CONFIGURE_SUFFIX = "?initialTab=Configure"

QUOTE_ID_RE = re.compile(r"\bQ\d{2}-\d{4}-\d{4}\b")
PRICE_RE = re.compile(r"\$((?:\d+|\d{1,3}(?:,\d{3})+)\.\d{2})(?![\d.,])")
UNIT_RE = re.compile(r"\$((?:\d+|\d{1,3}(?:,\d{3})+)\.\d{2})\s*ea\.")

# 报价单列表与卡片
PART_CARD_ACTIONS = '[data-testid="part-card-title-actions"]'
EDIT_CONFIGURATION = '[data-testid="navigate-to-configuration-button"]'
TIER_BLOCK = '[data-testid="tierAndLeadTime"]'

# 参数配置页控件
PROCESS_TRIGGER = "#option-select-process"
MATERIAL_TRIGGER = "#material-select-material-select"
FINISH_TRIGGER = "#finish-select-finish-multiselect"
TOLERANCE_TRIGGER = "#option-select-tolerances-radio-metal"
ROUGHNESS_TRIGGER = "#option-select-surface-roughness-select"
QUANTITY_INPUT = "input[role=spinbutton]"
SAVE_AND_VIEW = '[data-testid="Button-configure-part-header-save-and-view-quote"], button:has-text("Save Configuration")'
PRICING_PANEL = '[data-testid="configure-part-pricing-commerce-stack"]'

# 出口管制声明控件 (ITAR / EAR99)
ITAR_NO_BTN = '[data-testid="ItarView-itar-option-confirmed-not-itar"], button:has-text("No, this file is not controlled")'
ITAR_YES_BTN = '[data-testid="ItarView-itar-option-confirmed-itar"], button:has-text("Yes, this file is controlled")'
ITAR_CONTINUE_BTN = '[data-testid="ItarView-itar-continue"], button:has-text("Continue")'

# 交期与到货日期（形如 "Arrives by Nov 10"）
ARRIVES_RE = re.compile(r"Arrives by\s+([A-Z][a-z]{2})\.?\s+(\d{1,2})")
TIER_NAMES = ("Least Expensive", "Standard", "Fastest")
MONTHS = {
    m: i
    for i, m in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
        start=1,
    )
}


@dataclass(frozen=True, slots=True)
class XometryAccount:
    """登录报价所需的账号快照；密码/会话密文仅在内存中安全流转。"""

    id: int
    owner_id: int
    username: str
    password: str
    login_url: str
    quote_url: str
    login_method: str = "PASSWORD"
    encrypted_state: str | None = None


class XometryQuoteError(LoginError, RuntimeError):
    """报价失败，args[0] 为稳定的原因码，便于上层或接口层精确识别。"""


def _fail(code: str) -> XometryQuoteError:
    return XometryQuoteError(code)


def _parse_num(text: str) -> str:
    cleaned = re.sub(r"[^\d.]", "", text.strip())
    return cleaned if cleaned else "0.00"


async def _settle(page, script: str, arg: Any = None, *, tries: int = 12, delay: int = 800):
    """SPA 软导航会销毁执行上下文，读取必须跨上下文重试。"""
    for _ in range(tries):
        try:
            return await page.evaluate(script, arg) if arg is not None else await page.evaluate(script)
        except Exception:
            await page.wait_for_timeout(delay)
    raise _fail("XOMETRY_PAGE_UNREADABLE")


async def _await_ready(page, selector: str, *, timeout_ms: int = 60_000) -> None:
    """等待目标控件挂载且 React 水合完成。"""
    deadline = asyncio.get_running_loop().time() + timeout_ms / 1000
    while asyncio.get_running_loop().time() < deadline:
        ready = await _settle(
            page,
            "() => { const el = document.querySelector('%s'); return !!el && Object.keys(el).some(k => k.startsWith('__reactFiber$')); }".replace("%s", selector),
        )
        if ready:
            return
        await page.wait_for_timeout(1000)
    raise _fail("XOMETRY_PAGE_UNSUPPORTED")


# --- 身份核验与会话维护 ---


async def _verify_settled(session, provider, account: XometryAccount | AccountSnapshot, *, timeout_s: float = 30.0) -> bool:
    """轮询身份校验：Xometry 报价页水合需要时间，避免早读误判。"""
    deadline = asyncio.get_running_loop().time() + timeout_s
    while asyncio.get_running_loop().time() < deadline:
        try:
            if await provider.verify(session, account.username):
                return True
        except LoginError:
            raise
        except Exception:
            pass
        await session.page.wait_for_timeout(1500)
    return False


async def _ensure_signed_in(session, provider, account: XometryAccount | AccountSnapshot, input_guard: Callable[[], Awaitable[None]]) -> str:
    """先验会话，再真实登录。返回身份指纹；未通过则抛出异常拒绝报价。"""
    await input_guard()
    await session.goto(account.quote_url)
    if await _verify_settled(session, provider, account):
        return await provider.identify(session)

    login_method = account.login_method or "PASSWORD"
    if login_method != "PASSWORD" or not account.password:
        raise _fail("MANUAL_LOGIN_REQUIRED")

    await input_guard()
    await session.goto(account.login_url)
    async with asyncio.timeout(30):
        submitted = await provider.submit(session, account.username, account.password, account.quote_url)
    if not submitted:
        raise _fail("PROVIDER_VERIFICATION_REQUIRED")

    await session.goto(account.quote_url)
    if not await _verify_settled(session, provider, account):
        raise _fail("LOGIN_IDENTITY_VERIFICATION_REQUIRED")
    return await provider.identify(session)


# --- 图纸上传与既有报价对账 ---


async def _upload_step_file(
    page,
    step_file: Path,
    export_controlled: bool | None = None,
    *,
    payload: StepPayload,
    input_guard: Callable[[], Awaitable[None]],
    mutation_guard: Callable[[str], Awaitable[None]],
) -> str:
    """自动上传 STEP 图纸到 Xometry，并处理几何解析与出口管制声明。返回生成的报价号。"""
    logger.info(f"正在向 Xometry 上传 STEP 图纸: {step_file.name}")
    if "/quoting/home" not in page.url and "/quoting/quote/" not in page.url:
        await page.goto(DASHBOARD, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

    # 尝试关闭可能存在的 Cookie 提示
    try:
        cookie_btn = page.locator("#onetrust-accept-btn-handler").first
        if await cookie_btn.count() > 0 and await cookie_btn.is_visible():
            await cookie_btn.click()
            await page.wait_for_timeout(500)
    except Exception:
        pass

    # 定位并点击主上传入口按钮（需等待 React 水合完成）
    entry_css = '[data-testid="DashboardGetInstantQuotePrimary-dashboard-get-instant-quote-primary"]'
    file_input = page.locator('input[type="file"]').first
    if await file_input.count() == 0:
        entry_btn = page.locator(f'{entry_css}, #dashboard-get-instant-quote-primary, button:has-text("Get an Instant Quote")').first
        if await entry_btn.count() > 0 and await entry_btn.is_visible():
            try:
                await _await_ready(page, entry_css, timeout_ms=30_000)
            except Exception:
                pass
            await entry_btn.click(timeout=10_000)
            await page.wait_for_timeout(1000)

        file_input = page.locator('[role=dialog] input[type="file"], input[type="file"]').first
        if await file_input.count() == 0:
            try:
                await file_input.wait_for(state="attached", timeout=15_000)
            except Exception:
                pass

    if await file_input.count() == 0:
        raise _fail("XOMETRY_UPLOADER_NOT_FOUND")

    # 注入 STEP 图纸文件
    await input_guard()
    await mutation_guard("upload")
    await file_input.set_input_files(payload.sdk_payload())
    await page.wait_for_timeout(1500)

    # 等待 Start Instant Quote 按钮可用并点击
    continue_btn = page.locator('#instant-quote-continue, button:has-text("Start Instant Quote")').first
    if await continue_btn.count() > 0:
        try:
            await continue_btn.wait_for(state="visible", timeout=45_000)
            for _ in range(30):
                if not await continue_btn.is_disabled():
                    break
                await page.wait_for_timeout(1000)
            await input_guard()
            await mutation_guard("upload")
            await continue_btn.click(timeout=10_000)
        except (LoginError, BrowserStop):
            raise
        except Exception as e:
            logger.warning(f"Clicking instant-quote-continue failed/skipped: {e}")

    # 优先处理出口管制对话框（ITAR / EAR99）
    try:
        await page.locator(f"{ITAR_NO_BTN}, {ITAR_YES_BTN}").first.wait_for(state="visible", timeout=15_000)
        itar_no = page.locator(ITAR_NO_BTN).first
        if await itar_no.count() > 0 and await itar_no.is_visible():
            # Legacy booleans carry neither the current full declaration nor
            # its file/version decision record. Only the managed typed command
            # can authorize this mutation; never click through in the shortcut.
            await input_guard()
            raise _fail("QUOTE_EXPORT_DECLARATION_REQUIRED")
    except (XometryQuoteError, LoginError, BrowserStop):
        raise
    except Exception as e:
        logger.debug(f"ITAR modal check skipped/not present: {e}")

    # 等待到达报价单页面
    for _ in range(25):
        if "/quoting/quote/" in page.url:
            break
        await page.wait_for_timeout(1500)

    # 等待几何解析与配置按钮就绪（最多 90s）
    ready_locator = page.locator(f'{EDIT_CONFIGURATION}, [data-testid="part-card-title-actions"], div:has-text("part ready")').first
    try:
        await ready_locator.wait_for(state="visible", timeout=90_000)
    except Exception:
        pass

    # 从当前 URL 或页面文本提取报价号
    quote_match = QUOTE_ID_RE.search(page.url)
    if quote_match:
        return quote_match.group(0)

    page_text = await _settle(page, "() => document.body.innerText.slice(0, 30000)")
    for match in QUOTE_ID_RE.findall(page_text or ""):
        return match

    return ""


async def _quote_ids(page) -> list[str]:
    """从报价单列表读取候选报价号。"""
    text = await _settle(page, "() => document.body.innerText.slice(0, 40000)")
    seen: list[str] = []
    for match in QUOTE_ID_RE.findall(text or ""):
        if match not in seen:
            seen.append(match)
    return seen


async def _part_index(page, file_name: str) -> int | None:
    """在报价单页找出文件名匹配的零件序号；未命中返回 None。"""
    found = await _settle(
        page,
        (
            """(name) => {
          const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
          const target = norm(name);
          if (target.length < 8) return -1;
          const head = target.slice(0, 12);
          const tail = target.slice(-10);
          const buttons = [...document.querySelectorAll('%s')];
          let best = {index: -1, depth: 1e9};
          for (let i = 0; i < buttons.length; i++) {
            let node = buttons[i];
            for (let up = 1; up <= 8 && node; up++) {
              const extra = [...node.querySelectorAll('[title],[aria-label],[alt]')]
                .map(e => (e.getAttribute('title') || '') + (e.getAttribute('aria-label') || '') + (e.getAttribute('alt') || ''))
                .join(' ');
              const candidate = norm((node.innerText || '') + ' ' + extra);
              if (candidate.includes(head) && candidate.includes(tail)) {
                if (up < best.depth) best = {index: i, depth: up};
                break;
              }
              node = node.parentElement;
            }
          }
          return best.index;
        }"""
        ).replace("%s", EDIT_CONFIGURATION),
        file_name,
    )
    return None if found is None or found < 0 else int(found)


async def _reconcile(page, file_name: str, quote_id: str | None) -> tuple[str, int]:
    """返回 (报价号, 零件序号)。命中既有报价即复用。"""
    if quote_id:
        await page.goto("https://www.xometry.com" + QUOTE_PATH.format(quote_id=quote_id), wait_until="domcontentloaded")
        await _await_ready(page, EDIT_CONFIGURATION)
        index = await _part_index(page, file_name)
        if index is None:
            raise _fail("QUOTE_PART_NOT_FOUND")
        return quote_id, index

    await page.goto(DASHBOARD, wait_until="domcontentloaded")
    deadline = asyncio.get_running_loop().time() + 30
    candidates: list[str] = []
    while asyncio.get_running_loop().time() < deadline:
        candidates = await _quote_ids(page)
        if candidates:
            break
        await page.wait_for_timeout(2000)
    if not candidates:
        raise _fail("QUOTE_RECONCILE_EMPTY")

    for candidate in candidates[:15]:
        await page.goto("https://www.xometry.com" + QUOTE_PATH.format(quote_id=candidate), wait_until="domcontentloaded")
        try:
            await _await_ready(page, EDIT_CONFIGURATION, timeout_ms=20_000)
        except XometryQuoteError:
            continue
        index = await _part_index(page, file_name)
        if index is not None:
            return candidate, index
    raise _fail("QUOTE_PART_NOT_FOUND")


# --- 参数配置与回读 ---


async def _choose_option(page, trigger: str, label: str, *, input_guard: Callable[[], Awaitable[None]], required: bool = True) -> str | None:
    """在 OptionSelect 中按精确文案或搜索选中一项，返回回读到的当前值。"""
    if not label or not label.strip():
        return None

    raw_name = trigger.lstrip("#")
    full_selector = f"{trigger}, [data-testid='{raw_name}'], [data-testid*='{raw_name}']"
    field = page.locator(full_selector).first

    try:
        await field.wait_for(state="visible", timeout=20_000)
    except Exception:
        if required:
            raise _fail("QUOTE_OPTION_UNAVAILABLE")
        return None

    # 1. 如果当前控件的文本已经满足目标，直接返回当前值，避免不必要的弹窗干扰
    current_text = (await _settle(page, f"() => (document.querySelector('{trigger}') || document.querySelector('[data-testid=\"{raw_name}\"]') || {{}}).innerText || ''") or "").strip()
    want = label.strip().lower()
    norm_want = re.sub(r"[^a-z0-9]", "", want)
    norm_current = re.sub(r"[^a-z0-9]", "", current_text.lower())
    if norm_want and norm_want in norm_current:
        logger.info(f"配置项 {trigger} 当前值已满足: {current_text}")
        return current_text.splitlines()[0].strip() if current_text else label

    # 2. 点击触发器展开下拉列表
    await input_guard()
    await field.click(timeout=15_000)
    await page.wait_for_timeout(1000)

    # 尝试在材质等搜索框中输入过滤关键词
    search_input = page.locator('input[role="combobox"]#search-material-select, input[placeholder*="Search"]').first
    if await search_input.count() > 0 and await search_input.is_visible():
        search_kw = label.split("-")[0].split("(")[0].strip()
        await input_guard()
        await search_input.fill(search_kw)
        await page.wait_for_timeout(600)

    await input_guard()
    # An uncertain option click must not be replayed by the read-only retry helper.
    picked = await page.evaluate(
        page,
        """([label]) => {
          const want = label.trim().toLowerCase();
          const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
          const normWant = norm(want);

          const options = [...document.querySelectorAll('[role=option], [role=listitem], .option, [data-testid*="option"]')];
          let hit = options.find(o => (o.innerText || '').trim().toLowerCase() === want)
                 || options.find(o => norm(o.innerText || '').includes(normWant));

          if (!hit) {
              hit = options.find(o => {
                  const firstLine = (o.innerText || '').split('\\n')[0].trim().toLowerCase();
                  return firstLine.includes(want) || norm(firstLine).includes(normWant);
              });
          }

          if (!hit) {
              return {absent: true, available: options.map(o => (o.innerText || '').split('\\n')[0].trim()).slice(0, 30)};
          }
          hit.click();
          return {clicked: true};
        }""",
        [label],
    )
    if picked.get("missing") or picked.get("absent"):
        await input_guard()
        await page.keyboard.press("Escape")
        if current_text:
            logger.warning(f"无法精确匹配选项 {label}，降级保持当前值: {current_text}")
            return current_text.splitlines()[0].strip()
        if required:
            raise _fail("QUOTE_OPTION_UNAVAILABLE")
        return None

    await page.wait_for_timeout(1500)
    raw = await _settle(page, f"() => (document.querySelector('{trigger}') || document.querySelector('[data-testid=\"{raw_name}\"]') || {{}}).innerText || ''") or ""
    return raw.strip().splitlines()[0].strip() if raw.strip() else label


async def _set_quantity(page, quantity: int, *, input_guard: Callable[[], Awaitable[None]]) -> str:
    field = page.locator(QUANTITY_INPUT).first
    try:
        await field.wait_for(state="visible", timeout=20_000)
    except Exception:
        raise _fail("QUOTE_PAGE_UNSUPPORTED")
    await input_guard()
    await field.fill(str(quantity))
    await input_guard()
    await field.press("Enter")
    await page.wait_for_timeout(2000)
    return (await field.input_value()) or ""


def _read_price(text: str) -> dict[str, Any]:
    """从配置页价格面板解析总价与单价。"""
    amounts = [float(v.replace(",", "")) for v in PRICE_RE.findall(text or "")]
    if not amounts:
        return {"total": None, "unit": None}
    total = amounts[0]
    unit = next((v for v in amounts[1:] if v < total), total)
    return {"total": total, "unit": unit}


async def _configure(page, requested: dict[str, Any], *, input_guard: Callable[[], Awaitable[None]]) -> dict[str, Any]:
    await _await_ready(page, PROCESS_TRIGGER)
    effective: dict[str, Any] = {}
    if requested.get("material"):
        effective["material"] = await _choose_option(page, MATERIAL_TRIGGER, requested["material"], input_guard=input_guard)
    if requested.get("surface_finish"):
        effective["surface_finish"] = await _choose_option(page, FINISH_TRIGGER, requested["surface_finish"], input_guard=input_guard)
    if requested.get("tolerance"):
        effective["tolerance"] = await _choose_option(page, TOLERANCE_TRIGGER, requested["tolerance"], input_guard=input_guard, required=False)
    if requested.get("roughness"):
        effective["roughness"] = await _choose_option(page, ROUGHNESS_TRIGGER, requested["roughness"], input_guard=input_guard, required=False)
    if requested.get("quantity"):
        effective["quantity"] = await _set_quantity(page, int(requested["quantity"]), input_guard=input_guard)

    await page.wait_for_timeout(2000)
    panel = await _settle(
        page,
        "() => { const p = document.querySelector('%s'); return p ? p.innerText : document.body.innerText; }".replace("%s", PRICING_PANEL),
    )
    effective["price"] = _read_price(panel or "")
    return effective


# --- 读价与阶梯提取 ---


def _arrival(month: str, day: str, now: datetime) -> str | None:
    number = MONTHS.get(month[:3])
    if not number:
        return None
    year = now.year + (1 if number < now.month else 0)
    return f"{year:04d}-{number:02d}-{int(day):02d}"


async def _read_tiers(page, now: datetime) -> list[dict[str, Any]]:
    """读取报价单三档价格、单价、到货日期。"""
    blocks = await _settle(
        page,
        (
            """() => [...document.querySelectorAll('%s')].slice(0, 3).map(b => {
             let node = b;
             for (let up = 0; up < 6 && node; up++) {
               if (/\\$[\\d,]+\\.\\d{2}/.test(node.innerText || '')) return node.innerText;
               node = node.parentElement;
             }
             return b.innerText;
           })"""
        ).replace("%s", TIER_BLOCK),
    )
    tiers: list[dict[str, Any]] = []
    for block in blocks or []:
        text = " ".join(line.strip() for line in (block or "").splitlines() if line.strip())
        arrival = ARRIVES_RE.search(text)
        unit = UNIT_RE.search(text)
        unit_amount = str(Decimal(unit.group(1).replace(",", ""))) if unit else None
        if unit is not None:
            totals = [match.group(1) for match in PRICE_RE.finditer(text) if match.start() != unit.start()]
            total = str(Decimal(totals[0].replace(",", ""))) if len(totals) == 1 else None
        else:
            amounts = [str(Decimal(v.replace(",", ""))) for v in PRICE_RE.findall(text)]
            total = amounts[0] if amounts else None

        tier_name = next((name for name in TIER_NAMES if re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE)), None)
        tiers.append(
            {
                "tier": tier_name,
                "amount": total,
                "unit_amount": unit_amount,
                "arrives_by": _arrival(arrival.group(1), arrival.group(2), now) if arrival else None,
                "raw": text[:200],
            }
        )
    return tiers


def _quote_status(preferred: dict[str, Any] | None) -> str:
    if preferred and (preferred.get("amount") is not None or preferred.get("unit_amount") is not None):
        return "QUOTED"
    if preferred and re.search(r"\b(?:pending review|manual quote required|under review|manual review required)\b", preferred.get("raw", ""), re.IGNORECASE):
        return "PENDING_REVIEW"
    raise _fail("XOMETRY_CURRENT_PRICE_UNCONFIRMED")


def _select_tier(tiers: list[dict[str, Any]], label: str) -> dict[str, Any]:
    matches = [tier for tier in tiers if tier.get("tier") == label]
    if len(matches) != 1:
        raise _fail("XOMETRY_LEAD_TIME_UNCONFIRMED")
    return matches[0]


def map_to_xometry_parameters(
    material: str | None = None,
    surface_finish: str | None = None,
    tolerance: str | None = None,
    roughness: str | None = None,
) -> dict[str, str]:
    """将通用或中文加工参数映射为 Xometry 平台的标准参数选项。"""
    catalog = XometryCncParamCatalog()
    mat_clean = (material or "").strip()
    surf_clean = (surface_finish or "").strip()
    tol_clean = (tolerance or "").strip()
    rough_clean = (roughness or "").strip()

    # 1. 材质映射
    target_mat = "Aluminum 6061-T6x (Best Available)"
    if any(k in mat_clean for k in ["6061", "AL6061", "铝合金"]):
        if "7075" in mat_clean:
            target_mat = "Aluminum 7075-T6"
        else:
            target_mat = "Aluminum 6061-T6x (Best Available)"
    elif "7075" in mat_clean:
        target_mat = "Aluminum 7075-T6"
    elif any(k in mat_clean for k in ["45#", "45号", "碳钢", "1045"]):
        target_mat = "Steel 1018"
    elif any(k in mat_clean for k in ["4140", "合金钢"]):
        target_mat = "Steel 4140"
    elif any(k in mat_clean for k in ["316", "316L"]):
        target_mat = "Stainless Steel 316/316L"
    elif any(k in mat_clean for k in ["304", "不锈钢"]):
        target_mat = "Stainless Steel 304/304L"
    elif any(k in mat_clean for k in ["POM", "赛钢", "聚甲醛", "Acetal", "Delrin"]):
        target_mat = "Acetal (POM)"
    elif any(k in mat_clean for k in ["黄铜", "铜", "Brass"]):
        target_mat = "Copper C360 (Brass)"
    elif mat_clean:
        exact = next((m["name"] for m in catalog.get_all_materials() if m["name"].lower() == mat_clean.lower()), None)
        if exact:
            target_mat = exact

    # 2. 表面处理映射
    target_surf = "Standard"
    if any(k in surf_clean for k in ["硬质", "Hard"]):
        target_surf = "Black Hardcoat Anodize" if any(k in surf_clean for k in ["黑", "Black"]) else "Clear Hardcoat Anodize"
    elif any(k in surf_clean for k in ["阳极", "Anodize"]):
        target_surf = "Black Anodize" if any(k in surf_clean for k in ["黑", "Black"]) else "Clear Anodize"
    elif any(k in surf_clean for k in ["发黑", "发蓝", "Black Oxide"]):
        target_surf = "Black Oxide"
    elif any(k in surf_clean for k in ["喷砂", "Blast"]):
        target_surf = "Bead Blast"
    elif any(k in surf_clean for k in ["钝化", "Passivate"]):
        target_surf = "Passivate"
    elif any(k in surf_clean for k in ["导电", "Chem Film", "阿洛丁"]):
        target_surf = "Chem Film Clear"
    elif any(k in surf_clean for k in ["镍", "Nickel"]):
        target_surf = "Electroless Nickel Plating"
    elif any(k in surf_clean for k in ["锌", "Zinc"]):
        target_surf = "Zinc Plating"
    elif surf_clean:
        exact = next((f["name"] for f in catalog.get_all_finishes() if f["name"].lower() == surf_clean.lower()), None)
        if exact:
            target_surf = exact

    # 3. 精密公差映射
    target_tol = "±.005″ (±0.13mm)"
    if any(k in tol_clean for k in ["精密", "f级", "0.05", "0.02"]):
        target_tol = "This part requires tolerances tighter than ±.005″ (±0.13mm)"
    elif any(k in tol_clean for k in ["宽松", "c级", "0.25", "0.5"]):
        target_tol = "±.010″ (±0.25mm)"

    # 4. 表面粗糙度映射
    target_rough = "125uin/3.2um Ra"
    if any(k in rough_clean for k in ["1.6", "严格"]):
        target_rough = "63uin/1.6um Ra"
    elif any(k in rough_clean for k in ["0.8", "极致"]):
        target_rough = "32uin/0.8um Ra"
    elif any(k in rough_clean for k in ["0.4", "镜面"]):
        target_rough = "16uin/0.4um Ra"

    return {
        "material": target_mat,
        "surface_finish": target_surf,
        "tolerance": target_tol,
        "roughness": target_rough,
    }


# ==============================================================================
# XometryQuoteService: 适配 Xometry 平台的完整报价服务类
# ==============================================================================


class XometryQuoteService:
    """Xometry (美国站) 自动化报价服务类。

    提供两个核心方法：
    1. execute_xometry_quote: 底层基于 Playwright 的无头浏览器报价执行方法
    2. quote_part_config: 面向业务与 Agent 调用的图纸参数配置自动报价方法
    """

    @classmethod
    async def execute_xometry_quote(
        cls,
        target: str | Path | XometryAccount | AccountSnapshot | None = None,
        *,
        step_file_path: str | Path | None = None,
        account: XometryAccount | AccountSnapshot | None = None,
        input_guard: Callable[[], Awaitable[None]] | None = None,
        mutation_guard: Callable[[str], Awaitable[None]] | None = None,
        authenticated_guard: Callable[[str | None, str], Awaitable[None]] | None = None,
        payload: StepPayload | None = None,
        file_name: str | None = None,
        quantity: int = 1,
        material: str = "Aluminum 6061-T6x (Best Available)",
        surface_finish: str = "Standard",
        tolerance: str | None = None,
        roughness: str | None = None,
        lead_time_pref: str = "Standard",
        quote_id: str | None = None,
        export_controlled: bool | None = None,
        executor: BrowserExecutor | None = None,
    ) -> dict[str, Any]:
        """对 STEP 文件或既有零件执行一次完整的 Xometry 自动报价流程。

        支持直接上传本地 STEP 图纸，或复用已有报价单号进行对账；
        自动配置加工参数、提取三档阶梯价格及交期，并保存截图留证。
        """
        # 兼容 target 传参为 XometryAccount 或文件路径
        resolved_step_path: Path | None = None
        if isinstance(target, (XometryAccount, AccountSnapshot)):
            account = target
        elif isinstance(target, (str, Path)):
            resolved_step_path = Path(target)
        elif step_file_path is not None:
            resolved_step_path = Path(step_file_path)

        if resolved_step_path and not resolved_step_path.is_absolute():
            resolved_step_path = (BASE_DIR / resolved_step_path).resolve()

        resolved_file_name = file_name or (resolved_step_path.name if resolved_step_path else None)
        if not resolved_file_name:
            raise _fail("QUOTE_INPUT_INVALID")
        if quantity < 1:
            raise _fail("QUOTE_INPUT_INVALID")
        if not account:
            raise _fail("ACCOUNT_REQUIRED")
        if input_guard is None or mutation_guard is None:
            raise _fail("QUOTE_EXECUTION_GUARD_REQUIRED")

        provider = resolve_provider(account.login_url, account.quote_url)
        if provider.code != "xometry_us":
            raise _fail("PLATFORM_UNSUPPORTED_OR_UNTRUSTED")

        codec = SessionCodec(CryptoUtil)
        executor = executor or BrowserExecutor(codec, capacity=1)
        scope = SessionScope(str(account.owner_id), provider.code, str(account.id))

        encrypted_state = account.encrypted_state
        if encrypted_state:
            try:
                codec.open(scope, encrypted_state, provider.policy)
            except BrowserStop:
                encrypted_state = None

        now = datetime.now(UTC)
        outcome: dict[str, Any] = {
            "platform": "Xometry US",
            "provider": provider.code,
            "file_name": resolved_file_name,
            "export_controlled": export_controlled,
            "quoted_at": now.isoformat(),
        }

        failure: Exception | None = None
        try:
            async with executor.session(scope, provider.policy, encrypted_state=encrypted_state) as session:
                try:
                    page = session.page
                    await page.set_viewport_size({"width": 1600, "height": 1200})
                    page.on("popup", lambda popup: asyncio.create_task(popup.close()))

                    # 1. 登录态验证与自愈
                    identity = await _ensure_signed_in(session, provider, account, input_guard)
                    if authenticated_guard is not None:
                        await input_guard()
                        session.confirm_authentication(Authentication(AuthStatus.AUTHENTICATED, scope))
                        await authenticated_guard(identity or None, await session.export_encrypted_state())
                    outcome["identity_code"] = identity
                    outcome["login"] = "LOGIN_VERIFIED"

                    resolved_quote: str = quote_id or ""
                    part_idx: int = 0

                    # 2. 图纸输入处理（STEP 上传 vs 既有报价单对账）
                    if resolved_step_path and not quote_id:
                        if payload is None:
                            raise _fail("QUOTE_INPUT_INVALID")
                        uploaded_qid = await _upload_step_file(
                            page,
                            resolved_step_path,
                            export_controlled=export_controlled,
                            payload=payload,
                            input_guard=input_guard,
                            mutation_guard=mutation_guard,
                        )
                        if uploaded_qid:
                            resolved_quote = uploaded_qid
                        # 等待配置按钮就绪并定位到零件
                        await _await_ready(page, EDIT_CONFIGURATION, timeout_ms=45_000)
                        found_idx = await _part_index(page, payload.sdk_payload()["name"])
                        if found_idx is None:
                            raise _fail("XOMETRY_UPLOADED_PART_UNCONFIRMED")
                        part_idx = found_idx
                    else:
                        resolved_quote, part_idx = await _reconcile(page, resolved_file_name, quote_id)

                    outcome["quote_id"] = resolved_quote
                    outcome["part_index"] = part_idx

                    # 3. 进入参数配置页
                    await page.locator(EDIT_CONFIGURATION).nth(part_idx).click(timeout=20_000)
                    await _await_ready(page, PROCESS_TRIGGER, timeout_ms=90_000)

                    # 4. 写入参数并回读有效值
                    requested = {
                        "material": material,
                        "surface_finish": surface_finish,
                        "quantity": quantity,
                        "tolerance": tolerance,
                        "roughness": roughness,
                    }
                    outcome["requested"] = requested
                    await input_guard()
                    await mutation_guard("configure")
                    outcome["effective"] = await _configure(page, requested, input_guard=input_guard)
                    outcome["currency"] = "USD"

                    # 5. 保存配置并返回报价结果
                    await input_guard()
                    await mutation_guard("submit")
                    await page.locator(SAVE_AND_VIEW).first.click(timeout=20_000)
                    await _await_ready(page, TIER_BLOCK, timeout_ms=90_000)
                    await page.wait_for_timeout(3000)
                    outcome["tiers"] = await _read_tiers(page, now)

                    # 6. 首选交期匹配
                    pref_label = "Standard"
                    if lead_time_pref in ("加急", "UD", "Fastest", "Urgent"):
                        pref_label = "Fastest"
                    elif lead_time_pref in ("经济", "ED", "Least Expensive", "Economy"):
                        pref_label = "Least Expensive"

                    preferred = _select_tier(outcome["tiers"], pref_label)
                    outcome["selected"] = preferred
                    outcome["unit_price"] = preferred["unit_amount"] if preferred else None
                    outcome["total_amount"] = preferred["amount"] if preferred else None
                    outcome["quote_status"] = _quote_status(preferred)
                    outcome["url"] = page.url

                    # 7. 截图留存（合规与证据归档）
                    screenshot_dir = BASE_DIR / "static" / "upload"
                    screenshot_dir.mkdir(parents=True, exist_ok=True)
                    stem_name = Path(resolved_file_name).stem
                    screenshot_name = f"xometry_quote_{stem_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    screenshot_path = screenshot_dir / screenshot_name
                    await page.screenshot(path=str(screenshot_path))
                    outcome["evidence_screenshot"] = f"static/upload/{screenshot_name}"
                    outcome["note"] = "Xometry 自动报价遵循只报价、不下单安全准则。"

                except (XometryQuoteError, LoginError, BrowserStop) as exc:
                    failure = exc
        except BrowserStop as exc:
            if failure is None:
                failure = exc

        if failure is not None:
            reason = getattr(failure, "reason", None) or str(failure)
            raise _fail(str(reason)) from None

        logger.info(
            "Xometry 自动报价完成 quote=%s/part=%s status=%s total=%s",
            outcome.get("quote_id"),
            outcome.get("part_index"),
            outcome.get("quote_status"),
            outcome.get("total_amount"),
        )
        return outcome

    @classmethod
    async def quote_part_config(
        cls,
        auth: AuthSchema,
        db: Any,
        config_id: int,
        *,
        lead_time_pref: str = "Standard",
        quantity_override: int | None = None,
        account_id: int | None = None,
        export_controlled: bool | None = None,
        quote_id: str | None = None,
    ) -> dict[str, Any]:
        """面向业务层与 Agent 调用的图纸参数配置自动报价方法。

        加载 CncPartConfig 与 CncPart，核查 upload_authorized 上传授权，
        利用 Xometry 参数知识库进行中英文参数转换与约束校验，
        调度 execute_xometry_quote 运行自动化报价，返回结构化完整结果。
        """
        from .instant import quote_config

        return await quote_config(
            auth,
            db,
            config_id,
            account_id=account_id,
            quantity_override=quantity_override,
            lead_time_pref=lead_time_pref,
            export_controlled=export_controlled,
            quote_id=quote_id,
            expected_provider="xometry_us",
        )


# --- 保持模块级别别名导出，确保历史引用与调用兼容 ---

execute_xometry_quote = XometryQuoteService.execute_xometry_quote
quote_part_config = XometryQuoteService.quote_part_config


def load_step_name(file_path: str | Path) -> str:
    """保留原始图纸名称供对账识别。"""
    return Path(file_path).name
