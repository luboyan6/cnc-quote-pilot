"""Private one-shot upload evidence; durable intent, no order/export declaration."""
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).parent))
from managed_provider_inspect import (
    InspectExecutor, LoginManager, LoginRepository, SessionCodec, CryptoUtil,
    async_db_session, async_engine, select, CncAccountModel, CncPartConfigModel,
)
from app.modules.cnc.quote.repository import QuoteRepository, DurableIntentStore
from app.modules.cnc.browser.contracts import IntentKey, Operation, item_fingerprint
from app.modules.cnc.browser.files import upload_step

PROJECTION = """() => ({
 headings: [...document.querySelectorAll('h1,h2,h3')].map(n=>n.textContent.trim()).slice(0,15),
 fileInputs: [...document.querySelectorAll('input[type=file]')].map(n=>({id:n.id,accept:n.accept,multiple:n.multiple})),
 controls: [...document.querySelectorAll('button,input,select,[role=combobox],[role=radio],[role=checkbox]')].map(n=>({tag:n.tagName,id:n.id,type:n.type,role:n.getAttribute('role'),label:n.getAttribute('aria-label'),text:(n.innerText||'').trim().slice(0,180),value: ['radio','checkbox','number'].includes(n.type)?n.value:undefined,checked:n.checked,disabled:n.disabled})).filter(n=>n.type!=='password' && n.type!=='email').slice(0,100),
 dialogs: [...document.querySelectorAll('[role=dialog]')].map(n=>n.innerText.slice(0,9000)),
 labels: [...document.querySelectorAll('label')].map(n=>({for:n.htmlFor,text:n.innerText})).slice(0,50),
 summaries: [...document.querySelectorAll('[data-testid]')].map(n=>({testid:n.getAttribute('data-testid'),text:n.innerText.slice(0,600)})).filter(n=>/part|material|finish|price|lead|quantity|export|itar/i.test(n.testid)).slice(0,40)
})"""

class EvidenceActivity:
    can_input = False
    begun = True
    ready_for_step = True
    poll_interval = .2
    terminal = False

    def __init__(self, auth, snapshot, view, repository):
        self.auth, self.snapshot, self.view, self.repository = auth,snapshot,view,repository
        self.activity_id = view.run_id
        self.step = 0
        self.observations = []
        self.intents = DurableIntentStore(repository.sessions)
        self.key = None
        self.claimed = False

    async def check_inputs(self):
        await self.repository.validate(self.auth,self.snapshot)
        await self.repository.assert_active(self.auth.user.id,self.activity_id)

    async def login_state(self,status,reason):
        if status in {'WAITING_HUMAN','FAILED'}:
            self.observations.append({'login_status':status,'reason':reason})
            self.terminal = True

    async def observe(self,session):
        data = await session.page.evaluate(PROJECTION)
        self.observations.append({'step':self.step,'dom':data})
        print(json.dumps(self.observations[-1],ensure_ascii=False),flush=True)
        return data

    async def advance(self,session,provider):
        await self.check_inputs()
        page = session.page
        if self.step == 0:
            await page.wait_for_timeout(4000)
            launcher = page.locator('#dashboard-get-instant-quote-primary')
            if await page.locator('input[type=file]').count() == 0 and await launcher.count() == 1:
                await launcher.click(timeout=3000)
            await page.locator('input[type=file]').wait_for(state='attached',timeout=7000)
            await self.observe(session)
        elif self.step == 1:
            locator = page.locator('input[type=file]')
            if await locator.count() != 1:
                self.terminal = True
                return
            self.key = IntentKey(session.scope,self.activity_id,'1',Operation.UPLOAD,item_fingerprint(self.snapshot.payload.sha256,self.snapshot.requested))
            claim = await self.intents.claim(self.key)
            if not claim.is_new:
                self.terminal = True
                return
            self.claimed = True
            await upload_step(locator,self.snapshot.payload)
            await self.observe(session)
        elif self.step == 2:
            await page.wait_for_timeout(3500)
            data = await self.observe(session)
            # Start Instant Quote is reviewed quoting only, not an order. Stop
            # whenever an export/ITAR declaration is presented, never select it.
            declaration = any('ITAR' in s or 'export control' in s.lower() for s in data['dialogs'])
            if declaration:
                self.terminal = True
                return
            start = page.locator('#instant-quote-continue')
            if await start.count() == 1 and await start.is_enabled():
                await start.click(timeout=3000)
        elif self.step < 8:
            await page.wait_for_timeout(3500)
            data = await self.observe(session)
            if any('ITAR' in s or 'export control' in s.lower() for s in data['dialogs']):
                self.terminal = True
        else:
            self.terminal = True
        self.step += 1

    async def finish(self,reason):
        if self.claimed:
            await self.intents.mark_uncertain(self.key)
        final = self.view.model_copy(update={'status':'CANCELLED','stage':'parse' if self.claimed else 'login','reason':'RESEARCH_UPLOAD_UNCONFIRMED_NO_RETRY' if self.claimed else reason,'can_input':False})
        await self.repository.save(final,evidence={'kind':'private_upload_research','observed_at':datetime.now(UTC).isoformat(),'observations':self.observations,'upload_attempted':self.claimed})
        target = Path(__file__).with_name('xometry-upload-evidence.json')
        target.write_text(json.dumps({'run_id':self.activity_id,'observations':self.observations,'upload_attempted':self.claimed},ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'status':final.status,'reason':final.reason,'upload_attempted':self.claimed}),flush=True)

async def main():
    manager = LoginManager(repository=LoginRepository(),executor=InspectExecutor(SessionCodec(CryptoUtil)),lifetime_seconds=180)
    try:
        async with async_db_session() as db:
            configs=(await db.scalars(select(CncPartConfigModel).where(CncPartConfigModel.enabled.is_(True),CncPartConfigModel.is_deleted.is_(False)))).all()
        if len(configs)!=1 or configs[0].id!=1:
            print('PREREQUISITE_MISMATCH'); return
        auth=SimpleNamespace(user=SimpleNamespace(id=configs[0].created_id,is_superuser=False))
        repo=QuoteRepository()
        snapshot=await repo.snapshot(auth,1,None)
        if snapshot.payload.sha256!='364dcf18796a0613f7453984faf66c510be980905b4f0991aa9fda06a58c8d6c':
            print('SAMPLE_MISMATCH'); return
        request_id=str(uuid5(NAMESPACE_URL,'cnc-approved-xometry-upload-research-2026-10-23-uploader-wait'))
        prior=await repo.find(auth,1,request_id=request_id)
        if prior:
            print(json.dumps({'status':'RESEARCH_ALREADY_ATTEMPTED_NO_RETRY','reason':prior.reason})); return
        view,created=await repo.create(auth,snapshot,request_id)
        if not created:
            print('EXISTING_RUN_NO_RETRY'); return
        activity=EvidenceActivity(auth,snapshot,view,repo)
        login=await manager.start(snapshot.account,quote_activity=activity)
        await asyncio.wait_for(asyncio.shield(manager.sessions[login.session_id].task),timeout=150)
    finally:
        await manager.close_all()
        await async_engine.dispose()

if __name__=='__main__':
    try: asyncio.run(main())
    except Exception as exc: print(json.dumps({'reason':getattr(exc,'reason',type(exc).__name__)}),flush=True)

