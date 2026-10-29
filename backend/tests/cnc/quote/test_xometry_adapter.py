"""Real local Chromium DOM/SDK checks; no provider traffic or live acceptance."""

import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from _quote_support import ACCOUNT, STEP
from playwright.async_api import async_playwright

from app.modules.cnc.browser.contracts import ConfigurationReceipt, DeclarationReceipt, IntentKey, Operation, Parameters, ProvisionalQuote, SessionScope, item_fingerprint
from app.modules.cnc.browser.errors import BrowserStop, Reason
from app.modules.cnc.browser.files import StepPayload, TrustedStep
from app.modules.cnc.quote import xometry
from app.modules.cnc.quote.contracts import QuoteError, QuoteSnapshot
from app.modules.cnc.quote.providers import resolve_quote_adapter
from app.modules.cnc.quote.xometry import DOMValue, ParameterControl, XometryDOMBinding, XometryQuoteAdapter

HTML = """<!doctype html><html><body>
<input id="cad" type="file" multiple accept=".step,.stp">
<div id="parts"></div><div id="process">CNC</div>
<button id="material" type="button">Material</button>
<div id="options" hidden>
  <div role="option"><span class="title">Aluminum 6061</span><span>description $$ Popular</span></div>
  <div role="option"><span class="title">Aluminum 6061-T651, Plate</span><span>different product form $$$</span></div>
</div>
<input id="quantity" type="number" value="1">
<select id="finish"><option>Standard</option><option>Anodized</option></select>
<span id="saved-material">Old material</span><span id="saved-quantity">1</span><span id="saved-finish">Standard</span>
<button id="save">Save Configuration</button>
<div id="declaration" hidden><p id="statement">This exact file declaration covers export-controlled data.</p>
<button id="no">No, this file is not controlled (including EAR99).</button>
<button id="yes">Yes, this file is controlled.</button><button id="continue">Continue</button></div>
<div id="quote"><span class="qid">Q-synthetic</span><span class="pid">P-synthetic</span>
<span class="rev">0</span><span class="priced">2020-01-01T00:00:00Z</span>
<span class="qty">1</span><span class="status">Auto-Quoted</span><span class="amount">12.30</span>
<span class="currency">USD</span><span class="scope">Each</span><span class="lead">3 business days</span></div>
<script>
window.uploads=0; window.saves=0; window.continues=0; window.currentMaterial='Old material';
const $=s=>document.querySelector(s);
$('#cad').addEventListener('change',()=>{
  window.uploads++; const f=$('#cad').files[0];
  $('#parts').innerHTML='<div class="part"><span class="pid">P-synthetic</span><span class="fid">F-synthetic</span>'+
    '<span class="name"></span><span class="bytes"></span><span class="x">1</span><span class="y">2</span>'+
    '<span class="z">3</span><span class="volume">6</span></div>';
  $('.part .name').textContent=f.name; $('.part .bytes').textContent=f.size;
  if(window.needsDeclaration) $('#declaration').hidden=false;
});
$('#material').onclick=()=>{$('#options').hidden=false;};
$('#options').onclick=e=>{const o=e.target.closest('[role=option]'); if(o){window.currentMaterial=o.querySelector('.title').textContent; $('#options').hidden=true;}};
window.finishSave=()=>{
  if(!window.ignoreMaterial) $('#saved-material').textContent=window.currentMaterial;
  $('#saved-quantity').textContent=$('#quantity').value; $('#saved-finish').textContent=$('#finish').value;
  $('#quote .rev').textContent=String(Number($('#quote .rev').textContent)+1);
  $('#quote .priced').textContent=new Date().toISOString(); $('#quote .qty').textContent=$('#quantity').value;
};
$('#save').onclick=()=>{window.saves++; if(!window.delaySave) window.finishSave();};
$('#no').onclick=()=>{window.declarationChoice='not_controlled';};
$('#yes').onclick=()=>{window.declarationChoice='controlled';};
$('#continue').onclick=()=>{window.continues++; $('#declaration').hidden=true;};
</script></body></html>"""


def synthetic_binding():
    return XometryDOMBinding(
        version="synthetic-dom-v1",
        evidence="synthetic-only-not-production",
        max_size=1000,
        entry_paths=("/quoting/",),
        primary_input="#cad",
        part_rows="#parts .part",
        part_id=DOMValue(".pid"),
        file_id=DOMValue(".fid"),
        file_name=DOMValue(".name"),
        file_size=DOMValue(".bytes"),
        geometry=(DOMValue(".x"), DOMValue(".y"), DOMValue(".z"), DOMValue(".volume")),
        process=DOMValue("#process"),
        parameters=(
            ParameterControl("material", "#material", DOMValue("#saved-material"), "options", "#options [role=option]", ".title"),
            ParameterControl("quantity", "#quantity", DOMValue("#saved-quantity"), "input"),
            ParameterControl("surface_finish", "#finish", DOMValue("#saved-finish"), "select"),
        ),
        save_button="#save",
        declaration_root="#declaration",
        declaration_statement=DOMValue("#statement"),
        declaration_no="#no",
        declaration_yes="#yes",
        declaration_continue="#continue",
        quote_root="#quote",
        quote_id=DOMValue(".qid"),
        quote_part_id=DOMValue(".pid"),
        quote_revision=DOMValue(".rev"),
        quote_priced_at=DOMValue(".priced"),
        quote_quantity=DOMValue(".qty"),
        quote_status=DOMValue(".status"),
        quote_amount=DOMValue(".amount"),
        quote_currency=DOMValue(".currency"),
        quote_scope=DOMValue(".scope"),
        quote_lead=DOMValue(".lead"),
        statuses=(("Auto-Quoted", "QUOTED"), ("Reference estimate", "REFERENCE_ESTIMATE"), ("Manual review", "PENDING_REVIEW")),
        scopes=(("Each", "unit"), ("Subtotal", "line")),
    )


class XometryDOMTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cnc-xometry-dom-")
        root = Path(self.temp.name)
        source = root / "source.step"
        source.write_bytes(STEP)
        payload = StepPayload(STEP, hashlib.sha256(STEP).hexdigest())
        self.requested = Parameters.from_mapping({"material": "Aluminum 6061", "quantity": "2", "surface_finish": "Standard"})
        self.snapshot = QuoteSnapshot(5, 9, ACCOUNT, "config-rev", "source.step", TrustedStep(root, source, payload.sha256, len(STEP), 1000), payload, self.requested, "xometry_us")
        self.run_id = str(uuid4())
        self.sdk = await async_playwright().start()
        self.browser = await self.sdk.chromium.launch(headless=True)
        self.page = await self.browser.new_page()

        async def local_document(route):
            # All routes are fulfilled in process; the official host is only a
            # synthetic origin used to exercise production route checks.
            await route.fulfill(status=200, content_type="text/html", body=HTML)

        await self.page.route("**/*", local_document)
        await self.page.goto("https://www.xometry.com/quoting/home/")
        self.scope = SessionScope("7", "xometry_us", "31")
        self.session = SimpleNamespace(page=self.page, scope=self.scope, check_active=lambda: None)
        self.adapter = XometryQuoteAdapter(self.snapshot, self.run_id, synthetic_binding())
        self.input_guard = AsyncMock()
        self.adapter.set_input_guard(self.input_guard)

    async def asyncTearDown(self):
        await self.browser.close()
        await self.sdk.stop()
        self.temp.cleanup()

    def key(self, operation):
        return IntentKey(self.scope, self.run_id, "1", operation, item_fingerprint(self.snapshot.payload.sha256, self.requested))

    async def configured(self):
        upload = await self.adapter.upload(self.session, self.snapshot.payload)
        await self.adapter.configure(self.session, upload, self.requested)
        submitted = await self.adapter.submit(self.session, upload, self.requested)
        return upload, submitted

    async def test_real_sdk_exact_buffer_and_saved_full_parameter_readback(self):
        upload, submitted = await self.configured()
        self.assertEqual(upload.sha256, self.snapshot.payload.sha256)
        self.assertEqual(await self.page.locator("#cad").evaluate("el => el.files[0].size"), len(STEP))
        self.assertEqual(await self.page.locator("#cad").evaluate("async el => Array.from(new Uint8Array(await el.files[0].arrayBuffer()))"), list(STEP))
        result = await self.adapter.extract_quote(self.session, upload, submitted)
        self.assertEqual(str(result.amount), "12.30")
        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.effective, self.requested)
        self.assertEqual(result.lead_time.text, "3 business days")
        self.assertEqual(await self.page.evaluate("[window.uploads,window.saves]"), [1, 1])
        # submit uses the save-triggered recalculation, not a second button click.
        await self.adapter.submit(self.session, upload, self.requested)
        self.assertEqual(await self.page.evaluate("window.saves"), 1)

    async def test_unknown_extras_and_ambiguous_material_stop_without_save(self):
        invalid = replace(self.snapshot, requested=Parameters.from_mapping({"material": "Aluminum 6061", "quantity": "2", "unknown": "x"}))
        adapter = XometryQuoteAdapter(invalid, self.run_id, synthetic_binding())
        with self.assertRaisesRegex(QuoteError, "XOMETRY_PARAMETER_UNSUPPORTED"):
            await adapter.upload(self.session, invalid.payload)
        self.assertEqual(await self.page.evaluate("window.uploads"), 0)
        upload = await self.adapter.upload(self.session, self.snapshot.payload)
        await self.page.evaluate("document.querySelector('#options').append(document.querySelector('[role=option]').cloneNode(true))")
        with self.assertRaisesRegex(QuoteError, "XOMETRY_PARAMETER_AMBIGUOUS"):
            await self.adapter.configure(self.session, upload, self.requested)
        self.assertEqual(await self.page.evaluate("window.saves"), 0)

    async def test_declaration_has_no_default_and_continue_is_once_only(self):
        await self.page.evaluate("window.needsDeclaration=true")
        with self.assertRaises(TimeoutError):
            await self.adapter.upload(self.session, self.snapshot.payload)
        declaration = self.adapter.export_declaration
        self.assertIsNotNone(declaration)
        self.assertIsNone(await self.page.evaluate("window.declarationChoice"))
        self.assertEqual(await self.page.evaluate("window.continues"), 0)
        receipt = await self.adapter.continue_declaration(self.session, declaration, "not_controlled")
        self.assertIsInstance(receipt, DeclarationReceipt)
        self.assertEqual(receipt.sha256, self.snapshot.payload.sha256)
        with self.assertRaisesRegex(QuoteError, "UNCONFIRMED_NO_RETRY"):
            await self.adapter.continue_declaration(self.session, declaration, "not_controlled")
        self.assertEqual(await self.page.evaluate("[window.uploads,window.continues]"), [1, 1])

    async def test_changed_declaration_is_not_accepted(self):
        await self.page.evaluate("window.needsDeclaration=true")
        with self.assertRaises(TimeoutError):
            await self.adapter.upload(self.session, self.snapshot.payload)
        previous = self.adapter.export_declaration
        await self.page.locator("#statement").evaluate("el=>el.textContent='A changed file declaration'")
        with self.assertRaisesRegex(QuoteError, "QUOTE_EXPORT_DECLARATION_STALE"):
            await self.adapter.continue_declaration(self.session, previous, "not_controlled")
        self.assertEqual(await self.page.evaluate("window.continues"), 0)

    async def test_pending_save_reconciles_without_a_second_save(self):
        upload = await self.adapter.upload(self.session, self.snapshot.payload)
        await self.page.evaluate("window.delaySave=true")
        with self.assertRaisesRegex(QuoteError, "XOMETRY_RECEIPT_UNCONFIRMED"):
            await self.adapter.configure(self.session, upload, self.requested)
        self.assertIsNone(await self.adapter.reconcile(self.session, self.key(Operation.CONFIGURE)))
        await self.page.evaluate("window.finishSave()")
        receipt = await self.adapter.reconcile(self.session, self.key(Operation.CONFIGURE))
        self.assertIsInstance(receipt, ConfigurationReceipt)
        self.assertEqual(receipt.effective, self.requested)
        self.assertEqual(await self.page.evaluate("[window.uploads,window.saves]"), [1, 1])

    async def test_unsaved_or_mismatching_effective_values_fail(self):
        upload = await self.adapter.upload(self.session, self.snapshot.payload)
        await self.page.evaluate("window.ignoreMaterial=true")
        with self.assertRaises(BrowserStop) as caught:
            await self.adapter.configure(self.session, upload, self.requested)
        self.assertEqual(caught.exception.reason, Reason.PARAMETERS_MISMATCH)

    async def test_input_revoked_after_local_selection_stops_before_save(self):
        upload = await self.adapter.upload(self.session, self.snapshot.payload)
        self.input_guard.side_effect = QuoteError("QUOTE_PERMISSION_REVOKED")
        with self.assertRaisesRegex(QuoteError, "QUOTE_PERMISSION_REVOKED"):
            await self.adapter.configure(self.session, upload, self.requested)
        self.assertEqual(await self.page.evaluate("window.saves"), 0)

    async def test_wrong_quote_id_or_currency_symbol_are_not_accepted(self):
        upload, submitted = await self.configured()
        await self.page.locator("#quote .qid").evaluate("el=>el.textContent='Q-unrelated'")
        with self.assertRaisesRegex(QuoteError, "XOMETRY_QUOTE_EVIDENCE_MISSING"):
            await self.adapter.extract_quote(self.session, upload, submitted)
        await self.page.locator("#quote .qid").evaluate("el=>el.textContent='Q-synthetic'")
        await self.page.locator("#quote .currency").evaluate("el=>el.textContent='$'")
        with self.assertRaisesRegex(QuoteError, "XOMETRY_QUOTE_EVIDENCE_MISSING"):
            await self.adapter.extract_quote(self.session, upload, submitted)

    async def test_revision_change_during_extraction_rejects_mixed_values(self):
        upload, submitted = await self.configured()
        original = xometry._value

        async def changing_page(root, field):
            value = await original(root, field)
            if field == self.adapter.binding.quote_amount:
                await self.page.locator("#quote .rev").evaluate("el=>el.textContent='changed'")
            return value

        with patch.object(xometry, "_value", side_effect=changing_page), self.assertRaisesRegex(QuoteError, "XOMETRY_RECEIPT_UNCONFIRMED"):
            await self.adapter.extract_quote(self.session, upload, submitted)

    async def test_explicit_estimate_and_manual_review_remain_provisional(self):
        upload, submitted = await self.configured()
        for status, expected in [("Reference estimate", "REFERENCE_ESTIMATE"), ("Manual review", "PENDING_REVIEW")]:
            await self.page.locator("#quote .status").evaluate("(el,value)=>el.textContent=value", status)
            result = await self.adapter.extract_quote(self.session, upload, submitted)
            self.assertIsInstance(result, ProvisionalQuote)
            self.assertEqual(result.status, expected)
            if expected == "PENDING_REVIEW":
                self.assertIsNone(result.observation.amount)

    async def test_v2_variant_requires_explicit_binding_and_one_exact_query_value(self):
        v2 = XometryQuoteAdapter(self.snapshot, self.run_id, replace(synthetic_binding(), part_config_variant="v2"))
        # Upload starts on the ordinary home before entering the V2 editor.
        self.assertIs(v2.inspect_page(self.session), self.page)
        for query in [
            "vercel_part_config=test",
            "initialTab=Configure&vercel_part_config=test",
            "vercel_part_config",
            "vercel_part_config=",
            "vercel_part_config=control",
            "vercel_part_config=TEST",
            "vercel_part_config=test&vercel_part_config=test",
            "vercel_part_config=test&vercel_part_config=",
            "vercel_part_config=&vercel_part_config=test",
        ]:
            with self.subTest(query=query):
                await self.page.goto(f"https://www.xometry.com/quoting/quote/Q-local/P-local/?{query}")
                with self.assertRaisesRegex(QuoteError, "XOMETRY_PAGE_UNSUPPORTED"):
                    self.adapter.inspect_page(self.session)
                if query in {"vercel_part_config=test", "initialTab=Configure&vercel_part_config=test"}:
                    self.assertIs(v2.inspect_page(self.session), self.page)
                else:
                    with self.assertRaisesRegex(QuoteError, "XOMETRY_PAGE_UNSUPPORTED"):
                        v2.inspect_page(self.session)

        for url in [
            "https://www.xometry.com/testdrive/?vercel_part_config=test",
            "https://www.xometry.com/quoting/testdrive/?vercel_part_config=test",
            "https://untrusted.example/quoting/quote/Q-local/P-local/?vercel_part_config=test",
        ]:
            with self.subTest(url=url):
                await self.page.goto(url)
                with self.assertRaisesRegex(QuoteError, "XOMETRY_PAGE_UNSUPPORTED"):
                    v2.inspect_page(self.session)
        with self.assertRaisesRegex(QuoteError, "XOMETRY_BINDING_UNVERIFIED"):
            resolve_quote_adapter(self.snapshot, self.run_id)

    async def test_v2_variant_preserves_saved_receipt_and_currency_checks(self):
        self.adapter = XometryQuoteAdapter(self.snapshot, self.run_id, replace(synthetic_binding(), part_config_variant="v2"))
        self.adapter.set_input_guard(self.input_guard)
        await self.page.goto("https://www.xometry.com/quoting/quote/Q-local/P-local/?vercel_part_config=test")
        upload, submitted = await self.configured()
        result = await self.adapter.extract_quote(self.session, upload, submitted)
        self.assertEqual(result.effective, self.requested)
        self.assertEqual(await self.page.evaluate("[window.uploads,window.saves]"), [1, 1])
        await self.page.locator("#quote .currency").evaluate("el=>el.textContent='$'")
        with self.assertRaisesRegex(QuoteError, "XOMETRY_QUOTE_EVIDENCE_MISSING"):
            await self.adapter.extract_quote(self.session, upload, submitted)

    async def test_history_testdrive_and_preexisting_part_are_rejected(self):
        with self.assertRaisesRegex(QuoteError, "XOMETRY_BINDING_UNVERIFIED"):
            resolve_quote_adapter(self.snapshot, self.run_id)
        for url in ["https://www.xometry.com/testdrive/", "https://www.xometry.com/quoting/home/?vercel_part_config=test"]:
            await self.page.goto(url)
            with self.assertRaisesRegex(QuoteError, "XOMETRY_PAGE_UNSUPPORTED"):
                self.adapter.inspect_page(self.session)
        await self.page.goto("https://www.xometry.com/quoting/home/")
        await self.page.locator("#parts").evaluate("el=>el.innerHTML='<div class=part>prior uncertain part</div>'")
        with self.assertRaisesRegex(QuoteError, "XOMETRY_RECEIPT_UNCONFIRMED"):
            await self.adapter.upload(self.session, self.snapshot.payload)
        self.assertEqual(await self.page.evaluate("window.uploads"), 0)
