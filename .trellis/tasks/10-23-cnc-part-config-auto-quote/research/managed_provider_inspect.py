"""Private managed login/current DOM research. No upload/order action.

Outputs allowlisted metadata only; never prints exceptions or credential values.
Uses existing LoginRepository + LoginManager for official fenced ownership.
"""

import asyncio
import json
import os
import re
import sys
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".trellis/.runtime/playwright-browsers"))

from sqlalchemy import select

from app.core.base_model import MappedBase
from app.core.database import async_db_session, async_engine
from app.core.logger import logger
from app.modules.cnc.login.providers import resolve_provider
from app.modules.cnc.login.repository import LoginRepository
from app.modules.cnc.login.runtime import LoginManager
from app.modules.cnc.quote.repository import QuoteRepository
from app.modules.cnc.browser.session import BrowserExecutor
from app.modules.cnc.browser.state import SessionCodec
from app.utils.crypto_util import CryptoUtil
from app.plugin.module_cnc.cnc_account.model import CncAccountModel
from app.plugin.module_cnc.cnc_part.model import CncPartModel
from app.plugin.module_cnc.cnc_part_config.model import CncPartConfigModel
from app.utils.import_util import ImportUtil

logger.remove()
ImportUtil.find_models(MappedBase)

PROJECTION = """() => ({
  headings: Array.from(document.querySelectorAll('h1,h2,h3')).map(n=>n.textContent.trim()).slice(0,8),
  fileInputs: Array.from(document.querySelectorAll('input[type=file]')).map(n=>({id:n.id,accept:n.accept,multiple:n.multiple})),
  quoteControls: Array.from(document.querySelectorAll('button,a')).map(n=>({id:n.id,text:(n.innerText||'').trim(),label:n.getAttribute('aria-label')})).filter(n=>/Upload|Start Instant|Get an Instant Quote|Create.*Quote|Edit Configuration|Save Configuration|提交询价|上传|修改参数|登录|Continue|Log In/.test(n.text)).slice(0,20),
  usernameControl: document.querySelectorAll('input#username[name=username]').length,
  passwordControl: document.querySelectorAll('input#password[name=password]').length,
  jlcLoginFrame: document.querySelectorAll('iframe#jlc-cas-login-window').length,
  shadowHosts: Array.from(document.querySelectorAll('*')).filter(n=>n.shadowRoot).map(n=>n.tagName)
})"""


class InspectExecutor(BrowserExecutor):
    @asynccontextmanager
    async def session(self, scope, policy, **kwargs):
        hosts = set()
        failed = set()
        file_evidence = set()
        response_tasks = set()
        async with super().session(scope, policy, **kwargs) as session:
            def observed(request):
                host = urlsplit(request.url).hostname
                if host and host not in policy.allowed_hosts and not policy.blocks_optional_resource(request):
                    hosts.add((host, request.resource_type, request.is_navigation_request()))
                if host == "us-files.xometry.com":
                    path = urlsplit(request.url).path.lower()
                    file_evidence.add(("resource",request.resource_type,"thumbnail" if "thumb" in path else "image" if path.endswith((".png",".jpg",".jpeg",".webp")) else "file"))
            def failure(request):
                host = urlsplit(request.url).hostname
                if host in policy.allowed_hosts:
                    code = re.search(r"net::[A-Z_]+",request.failure or "")
                    failed.add((host,code.group() if code else "request_failed"))
            async def response_metadata(response):
                if urlsplit(response.url).hostname != "api.xometry.com" or "json" not in response.headers.get("content-type", ""):
                    return
                try:
                    data = await response.json()
                    def visit(value, keys=()):
                        if isinstance(value,dict):
                            for key, child in value.items():
                                visit(child,keys+(str(key) if re.fullmatch(r"[A-Za-z_]+",str(key)) else "*",))
                        elif isinstance(value,list):
                            for child in value: visit(child,keys+("[]",))
                        elif isinstance(value,str) and urlsplit(value).hostname == "us-files.xometry.com":
                            file_evidence.add(("official_api_field",".".join(keys),"file_delivery"))
                    visit(data)
                except Exception:
                    return
            def response_observed(response):
                task=asyncio.create_task(response_metadata(response))
                response_tasks.add(task)
                task.add_done_callback(response_tasks.discard)
            session.page.context.on("request", observed)
            session.page.context.on("requestfailed", failure)
            session.page.context.on("response", response_observed)
            try:
                yield session
            except BaseException as error:
                print(json.dumps({"inspection_failure_type":type(error).__name__,"frames":[{"file":Path(frame.filename).name,"function":frame.name,"line":frame.lineno} for frame in traceback.extract_tb(error.__traceback__)]}),flush=True)
                raise
            finally:
                if response_tasks: await asyncio.gather(*response_tasks,return_exceptions=True)
                print(json.dumps({"platform":scope.platform_code,"unknown_requests":[{"host":h,"type":t,"navigation":n} for h,t,n in sorted(hosts)],"failed_allowed_hosts":sorted(failed),"file_delivery_evidence":sorted(file_evidence)}),flush=True)


class InspectActivity:
    terminal = False
    can_input = False
    begun = False
    ready_for_step = True
    poll_interval = 0.1

    def __init__(self, code):
        self.code = code
        self.result = None

    async def check_inputs(self):
        # This activity is read-only inspection, not a quote. The production
        # runner revalidates its frozen file/configuration through this port.
        return None

    async def login_state(self, status, reason):
        if status in {"WAITING_HUMAN", "FAILED"}:
            self.result = {"platform": self.code, "status": status, "reason": reason}
            self.terminal = True

    async def advance(self, session, provider):
        session.check_active()
        # Identity can succeed while the quote SPA is still hydrating. The
        # authenticated home may show navigation before opening its uploader.
        await session.page.wait_for_timeout(5000)
        session.check_active()
        launcher = session.page.locator("#dashboard-get-instant-quote-primary")
        if await session.page.locator('input[type="file"]').count() == 0 and await launcher.count() == 1:
            await launcher.click(timeout=3000)
            await session.page.wait_for_timeout(3000)
            session.check_active()
        self.result = {"platform": self.code, "status": "AUTHENTICATED_CURRENT_DOM", "host": urlsplit(session.page.url).hostname,
                       "path": urlsplit(session.page.url).path, "dom": await session.page.evaluate(PROJECTION)}
        self.terminal = True

    async def finish(self, reason):
        if self.result is None:
            self.result = {"platform": self.code, "status": "FAILED", "reason": reason}


async def main():
    repository = LoginRepository()
    manager = LoginManager(repository=repository, executor=InspectExecutor(SessionCodec(CryptoUtil)), lifetime_seconds=180)
    try:
        async with async_db_session() as db:
            accounts = (await db.scalars(select(CncAccountModel).where(CncAccountModel.is_deleted.is_(False), CncAccountModel.enabled.is_(True)))).unique().all()
            configs = (await db.scalars(select(CncPartConfigModel).where(CncPartConfigModel.is_deleted.is_(False), CncPartConfigModel.enabled.is_(True)))).all()
            parts = {part.id:part for part in (await db.scalars(select(CncPartModel).where(CncPartModel.is_deleted.is_(False)))).all()}
        print(json.dumps({"inventory": {"enabled_accounts":len(accounts), "enabled_configs":len(configs),
                         "linked_authorized_configs":sum(bool(parts.get(c.part_id) and parts[c.part_id].upload_authorized is True) for c in configs)}}),flush=True)
        print(json.dumps({"config_inventory":[{"linked_part_exists":c.part_id in parts,
                           "part_upload_authorized":parts[c.part_id].upload_authorized if c.part_id in parts else None,
                           "part_owner_matches_config":parts[c.part_id].created_id==c.created_id if c.part_id in parts else None,
                           "configured_material_present":bool(c.material),"configured_finish_present":bool(c.surface_finish),
                           "configured_material":c.material,"configured_quantity":c.quantity,
                           "extra_parameter_keys":sorted((c.extra_params or {}).keys()),
                           "enabled_matching_account_count":sum(a.platform_id==c.site_type and a.created_id==c.created_id for a in accounts)} for c in configs]}),flush=True)
        if "--inventory-only" in sys.argv:
            return
        seen = set()
        for row in accounts:
            if not row.platform or not row.created_id:
                continue
            try:
                provider = resolve_provider(row.platform.login_url, row.platform.quote_entry_url)
                if provider.code in seen:
                    continue
                seen.add(provider.code)
                linked = [c for c in configs if c.site_type == row.platform_id and c.created_id == row.created_id and c.part_id in parts and parts[c.part_id].created_id == row.created_id and parts[c.part_id].upload_authorized is True]
                print(json.dumps({"platform":provider.code,"owned_authorized_linked_config_count":len(linked),
                                  "encrypted_state_available":bool(row.session_ciphertext),"credentials_available":row.has_credentials}),flush=True)
                auth = SimpleNamespace(user=SimpleNamespace(id=row.created_id, is_superuser=False))
                if linked:
                    frozen = await QuoteRepository().snapshot(auth, linked[0].id, row.id)
                    approved = {"364dcf18796a0613f7453984faf66c510be980905b4f0991aa9fda06a58c8d6c", "d3884475c50c336e3f13e5ca1665605104dc1ccc4113e962c62bff46b21e25e6", "038fe7d3d464c57bfc0cb0856954f1f6bbf78b152f6db9a67ede92dbd8ea7cc7"}
                    print(json.dumps({"linked_file_identity":{"sha256":frozen.payload.sha256,"size":len(frozen.payload.buffer),"matches_D16_recorded_sample":frozen.payload.sha256 in approved}}),flush=True)
                snapshot = await repository.load(auth, row.id)
                activity = InspectActivity(provider.code)
                view = await manager.start(snapshot, quote_activity=activity)
                owned = manager.sessions[view.session_id]
                await asyncio.wait_for(asyncio.shield(owned.task), timeout=140)
                print(json.dumps(activity.result,ensure_ascii=False),flush=True)
            except Exception as exc:
                print(json.dumps({"platform":getattr(locals().get("provider"),"code","unknown"),"result":getattr(exc,"reason",type(exc).__name__)}),flush=True)
            finally:
                await manager.close_all()
    finally:
        await manager.close_all()
        await async_engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(json.dumps({"result":getattr(exc,"reason",type(exc).__name__)}),flush=True)
