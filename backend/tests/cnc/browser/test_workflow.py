import asyncio
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

from _support import GEOMETRY, PARAMS, SCOPE, FakeAdapter, MemoryIntents, fixture_session, fixture_step

from app.modules.cnc.browser.contracts import Authentication, AuthStatus, DayBasis, Geometry, IntentState, LeadTime, LeadTimeDate, LeadTimeKind, Operation, QuoteFreshness
from app.modules.cnc.browser.errors import BrowserStop, Reason
from app.modules.cnc.browser.workflow import QuoteRequest, QuoteWorkflow, read_with_retry


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.step = fixture_step(Path(self.directory.name))
        self.request = QuoteRequest("synthetic-item", "run-1", self.step, PARAMS)
        self.store = MemoryIntents()
        self.adapter = FakeAdapter(self.step)
        self.adapter.request = self.request
        self.workflow = QuoteWorkflow(self.store)
        self.session = None

    async def execute(self):
        if self.session is None:
            self.session = fixture_session()
        return await self.workflow.execute(self.session, self.adapter, self.request)

    async def assert_stop(self, reason):
        with self.assertRaises(BrowserStop) as failure:
            await self.execute()
        self.assertEqual(failure.exception.reason, reason)

    async def test_workflow_complete_decimal_serialization_and_reentry_no_mutations(self):
        result = await self.execute()
        self.assertEqual(result.as_dict()["status"], "QUOTED")
        self.assertEqual(result.as_dict()["amount"], "123.4500")
        self.assertEqual(result.as_dict()["freshness"], "RECALCULATED")
        self.assertEqual(result.as_dict()["lead_time"]["kind"], "duration")
        self.assertEqual(result.as_dict()["lead_time"]["schema_version"], 2)
        self.assertEqual(dict(PARAMS.values), result.as_dict()["effective"])
        self.assertEqual(self.adapter.calls[:5], ["authenticate", "upload", "configure", "read_effective", "read_effective"])
        self.assertEqual({record.state for record in self.store.records.values()}, {IntentState.CONFIRMED})
        self.workflow = QuoteWorkflow(self.store)  # Browser/workflow rebuild keeps durable intents.
        await self.execute()
        self.assertEqual(self.adapter.calls.count("upload"), 1)
        self.assertEqual(self.adapter.calls.count("configure"), 1)
        self.assertEqual(self.adapter.calls.count("submit"), 1)
        self.assertEqual(self.adapter.calls.count("extract_quote"), 2)

    async def test_explicit_production_duration_requires_evidence_and_retains_its_kind(self):
        lead = LeadTime("Synthetic verified production: 5-7 business days", 5, 7, DayBasis.BUSINESS, kind=LeadTimeKind.PRODUCTION_DURATION)
        self.adapter.quote_changes = {"lead_time": lead}
        await self.assert_stop(Reason.QUOTE_INVALID)
        verified = replace(lead, source="synthetic same-request production evidence")
        self.adapter.quote_changes = {"lead_time": verified}
        snapshot = (await self.execute()).as_dict()["lead_time"]
        self.assertEqual(snapshot["kind"], "production_duration")
        self.assertEqual(snapshot["source"], "synthetic same-request production evidence")
        self.assertIsNone(snapshot["start_point"])
        self.assertIsNone(snapshot["date"])
        self.assertEqual(LeadTime.from_dict(snapshot), verified)

    async def test_explicit_arrival_and_ship_dates_preserve_raw_source_and_unknown_year(self):
        for kind in (LeadTimeKind.ARRIVAL_DATE, LeadTimeKind.SHIP_DATE):
            with self.subTest(kind=kind):
                lead = LeadTime("Nov 9", kind=kind, source="synthetic same-request date evidence", date=LeadTimeDate(11, 9))
                self.adapter.quote_changes = {"lead_time": lead}
                result = await self.execute()
                snapshot = result.as_dict()["lead_time"]
                self.assertEqual(snapshot["kind"], kind.value)
                self.assertEqual(snapshot["text"], "Nov 9")
                self.assertEqual(snapshot["source"], "synthetic same-request date evidence")
                self.assertEqual(snapshot["date"], {"month": 11, "day": 9, "year": None})
                self.assertTrue(all(snapshot[field] is None for field in ("minimum_days", "maximum_days", "basis", "start_point")))
                self.assertEqual(LeadTime.from_dict(snapshot), lead)

    async def test_unknown_date_missing_source_and_mixed_semantics_never_become_quoted(self):
        for lead in (
            LeadTime("TBD"),
            LeadTime("8 business days"),
            LeadTime("6 个工作日"),
            LeadTime("TBD", kind=LeadTimeKind.ARRIVAL_DATE, source="synthetic evidence"),
            LeadTime("Nov 9", kind=LeadTimeKind.ARRIVAL_DATE, date=LeadTimeDate(11, 9)),
            LeadTime("Nov 9", kind=LeadTimeKind.SHIP_DATE, source="synthetic evidence", date=LeadTimeDate(11, 9), minimum_days=5),
            LeadTime("Feb 30", kind=LeadTimeKind.ARRIVAL_DATE, source="synthetic evidence", date=LeadTimeDate(2, 30)),
            {"text": "Nov 9", "kind": "arrival_date"},
        ):
            with self.subTest(lead=lead):
                self.adapter.quote_changes = {"lead_time": lead}
                await self.assert_stop(Reason.QUOTE_INVALID)

    async def test_date_lead_time_cannot_bypass_money_identity_geometry_parameters_or_freshness(self):
        lead = LeadTime("Nov 9", kind=LeadTimeKind.ARRIVAL_DATE, source="synthetic evidence", date=LeadTimeDate(11, 9))
        for changes, reason in (
            ({"amount": None}, Reason.QUOTE_INVALID),
            ({"amount": 123.45}, Reason.QUOTE_INVALID),
            ({"currency": "ZZZ"}, Reason.QUOTE_INVALID),
            ({"price_scope": None}, Reason.QUOTE_INVALID),
            ({"scope": replace(SCOPE, account_id="other")}, Reason.QUOTE_INVALID),
            ({"upload_reference": "other-part"}, Reason.QUOTE_INVALID),
            ({"geometry": replace(GEOMETRY, volume_mm3=Decimal("0"))}, Reason.GEOMETRY_INVALID),
            ({"effective": type(PARAMS).from_mapping({"quantity": "2"})}, Reason.PARAMETERS_MISMATCH),
            ({"freshness": QuoteFreshness.CACHE_UNVERIFIED}, Reason.QUOTE_INVALID),
            ({"priced_at": datetime.now(UTC) - timedelta(minutes=10)}, Reason.QUOTE_INVALID),
        ):
            with self.subTest(changes=changes):
                self.adapter.quote_changes = {"lead_time": lead, **changes}
                await self.assert_stop(reason)

    async def test_auth_challenge_expiry_unknown_and_identity_stop_before_upload(self):
        for auth, reason in (
            (Authentication(AuthStatus.CHALLENGE), Reason.CHALLENGE),
            (Authentication(AuthStatus.EXPIRED), Reason.AUTH_REQUIRED),
            (Authentication(AuthStatus.UNKNOWN), Reason.AUTH_REQUIRED),
            (Authentication(AuthStatus.AUTHENTICATED, replace(SCOPE, account_id="other")), Reason.IDENTITY_MISMATCH),
        ):
            with self.subTest(auth=auth):
                self.adapter.auth = auth
                await self.assert_stop(reason)
        self.assertFalse(self.store.records)
        self.assertNotIn("upload", self.adapter.calls)

    async def test_tampered_input_stops_before_intent_and_upload(self):
        self.step.path.write_bytes(b"x" * self.step.expected_size)
        await self.assert_stop(Reason.FILE_INVALID)
        self.assertFalse(self.store.records)
        self.assertNotIn("upload", self.adapter.calls)

    async def test_upload_timeout_stays_uncertain_and_rebuild_never_replays(self):
        self.adapter.upload_error = TimeoutError("token=must-not-leak")
        await self.assert_stop(Reason.MUTATION_UNCERTAIN)
        record = next(iter(self.store.records.values()))
        self.assertEqual(record.state, IntentState.UNCERTAIN)
        self.workflow = QuoteWorkflow(self.store)
        self.session = fixture_session()
        await self.assert_stop(Reason.MUTATION_UNCERTAIN)
        self.assertEqual(self.adapter.calls.count("upload"), 1)
        self.assertIn("reconcile_upload", self.adapter.calls)
        self.assertNotIn("configure", self.adapter.calls)

    async def test_readonly_reconciliation_can_confirm_remote_upload_without_reupload(self):
        self.adapter.upload_error = TimeoutError()
        await self.assert_stop(Reason.MUTATION_UNCERTAIN)
        self.adapter.reconciled[Operation.UPLOAD] = self.adapter.upload_receipt
        self.adapter.upload_error = None
        result = await self.execute()
        self.assertEqual(result.as_dict()["status"], "QUOTED")
        self.assertEqual(self.adapter.calls.count("upload"), 1)

    async def test_submit_timeout_does_not_repeat_submit_or_upload(self):
        self.adapter.submit_error = TimeoutError("secret raw SDK failure")
        await self.assert_stop(Reason.MUTATION_UNCERTAIN)
        self.adapter.submit_error = None
        self.workflow = QuoteWorkflow(self.store)
        await self.assert_stop(Reason.MUTATION_UNCERTAIN)
        self.assertEqual(self.adapter.calls.count("submit"), 1)
        self.assertEqual(self.adapter.calls.count("upload"), 1)
        self.assertIn("reconcile_submit", self.adapter.calls)

    async def test_configure_timeout_does_not_repeat_apply_or_upload(self):
        self.adapter.configure_error = TimeoutError("secret Apply failure")
        await self.assert_stop(Reason.MUTATION_UNCERTAIN)
        record = next(record for record in self.store.records.values() if record.key.operation == Operation.CONFIGURE)
        self.assertEqual(record.state, IntentState.UNCERTAIN)
        self.adapter.configure_error = None
        self.workflow = QuoteWorkflow(self.store)
        await self.assert_stop(Reason.MUTATION_UNCERTAIN)
        self.assertEqual(self.adapter.calls.count("upload"), 1)
        self.assertEqual(self.adapter.calls.count("configure"), 1)
        self.assertNotIn("submit", self.adapter.calls)
        self.assertIn("reconcile_configure", self.adapter.calls)

    async def test_readback_timeout_after_apply_does_not_repeat_configuration(self):
        with patch.object(self.adapter, "read_effective", new_callable=AsyncMock, side_effect=TimeoutError()) as read:
            await self.assert_stop(Reason.READ_TIMEOUT)
            self.assertEqual(read.await_count, 3)
        self.workflow = QuoteWorkflow(self.store)
        await self.assert_stop(Reason.MUTATION_UNCERTAIN)
        self.assertEqual(self.adapter.calls.count("configure"), 1)
        self.assertNotIn("submit", self.adapter.calls)

    async def test_cancellation_of_mutations_preserves_unknown_and_no_replay(self):
        for operation in ("upload", "configure", "submit"):
            with self.subTest(operation=operation):
                adapter = FakeAdapter(self.step)
                adapter.request = self.request
                setattr(adapter, f"{operation}_wait", asyncio.Event())
                store = MemoryIntents()

                async def run(store=store, adapter=adapter):
                    await QuoteWorkflow(store).execute(fixture_session(), adapter, self.request)

                task = asyncio.create_task(run())
                async with asyncio.timeout(2):
                    while operation not in adapter.calls:
                        await asyncio.sleep(0)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                record = next(record for record in store.records.values() if record.key.operation == operation)
                self.assertEqual(record.state, IntentState.UNCERTAIN)
                with self.assertRaises(BrowserStop) as failure:
                    await QuoteWorkflow(store).execute(fixture_session(), adapter, self.request)
                self.assertEqual(failure.exception.reason, Reason.MUTATION_UNCERTAIN)
                self.assertEqual(adapter.calls.count(operation), 1)

    async def test_store_unavailable_before_action_and_confirmation_failure_after_action(self):
        self.store.claim = AsyncMock(side_effect=OSError("db password=secret"))
        await self.assert_stop(Reason.STATE_UNAVAILABLE)
        self.assertNotIn("upload", self.adapter.calls)
        self.store = MemoryIntents()
        self.store.confirm = AsyncMock(side_effect=OSError("db password=secret"))
        self.workflow = QuoteWorkflow(self.store)
        await self.assert_stop(Reason.MUTATION_UNCERTAIN)
        await self.assert_stop(Reason.MUTATION_UNCERTAIN)
        self.assertEqual(self.adapter.calls.count("upload"), 1)

    async def test_apply_mismatch_missing_extra_fields_and_saved_snapshot_difference(self):
        for values in (
            {**dict(PARAMS.values), "quantity": "1"},
            {key: value for key, value in PARAMS.values if key != "material"},
            {**dict(PARAMS.values), "inspection": "required"},
        ):
            with self.subTest(values=values):
                self.store = MemoryIntents()
                self.workflow = QuoteWorkflow(self.store)
                self.adapter.effective = type(PARAMS).from_mapping(values)
                await self.assert_stop(Reason.PARAMETERS_MISMATCH)
        self.assertNotIn("submit", self.adapter.calls)

    async def test_confirmed_configuration_is_re_read_and_never_silently_overwritten(self):
        await self.execute()
        self.adapter.effective = type(PARAMS).from_mapping({**dict(PARAMS.values), "quantity": "3"})
        await self.assert_stop(Reason.PARAMETERS_MISMATCH)
        self.assertEqual(self.adapter.calls.count("configure"), 1)
        self.assertEqual(self.adapter.calls.count("submit"), 1)

    async def test_same_item_changed_parameters_or_new_generation_cannot_bypass_freeze(self):
        await self.execute()
        for generation in ("run-1", "run-2"):
            self.request = replace(self.request, execution_generation=generation, requested=type(PARAMS).from_mapping({**dict(PARAMS.values), "quantity": "4"}))
            self.adapter.request = self.request
            await self.assert_stop(Reason.INTENT_CONFLICT)
        self.assertEqual(self.adapter.calls.count("upload"), 1)

    async def test_zero_geometry_and_unknown_quote_never_become_quoted(self):
        self.adapter.upload_receipt = replace(self.adapter.upload_receipt, geometry=replace(GEOMETRY, volume_mm3=Decimal("0")))
        await self.assert_stop(Reason.GEOMETRY_INVALID)
        self.assertNotIn("submit", self.adapter.calls)

    async def test_quote_requires_exact_money_currency_scope_leadtime_geometry_and_identity(self):
        bad_changes = (
            {"amount": None},
            {"amount": 123.45},
            {"amount": Decimal("NaN")},
            {"amount": Decimal("0")},
            {"currency": None},
            {"currency": "$"},
            {"currency": "ZZZ"},
            {"price_scope": None},
            {"lead_time": None},
            {"lead_time": LeadTime("TBD", 0, 0, DayBasis.BUSINESS)},
            {"lead_time": LeadTime("5 days", 5, 4, DayBasis.BUSINESS)},
            {"geometry": Geometry(Decimal("0"), Decimal("20"), Decimal("30"), Decimal("6000"))},
            {"upload_reference": "other-part"},
            {"submission_reference": "other-quote"},
            {"scope": replace(SCOPE, owner_id="other")},
            {"item_id": "other"},
            {"execution_generation": "other"},
            {"sha256": "f" * 64},
            {"effective": type(PARAMS).from_mapping({"quantity": "2"})},
        )
        for changes in bad_changes:
            with self.subTest(changes=changes):
                self.adapter.quote_changes = changes
                with self.assertRaises(BrowserStop):
                    await self.execute()

    async def test_cache_unknown_stale_future_and_pre_run_recalculation_rejected(self):
        now = datetime.now(UTC)
        for changes in (
            {"freshness": QuoteFreshness.CACHE_UNVERIFIED},
            {"freshness": "RECALCULATED"},
            {"priced_at": now - timedelta(minutes=10)},
            {"priced_at": now + timedelta(minutes=1)},
            {"priced_at": now - timedelta(seconds=1), "freshness": QuoteFreshness.RECALCULATED},
            {"observed_at": now - timedelta(seconds=1)},
            {"observed_at": now.replace(tzinfo=None)},
        ):
            with self.subTest(changes=changes):
                self.adapter.quote_changes = changes
                await self.assert_stop(Reason.QUOTE_INVALID)
        self.adapter.quote_changes = {"priced_at": now - timedelta(seconds=1), "freshness": QuoteFreshness.CURRENT_CONFIRMED}
        result = await self.execute()
        self.assertEqual(result.as_dict()["freshness"], "CURRENT_CONFIRMED")


class ReadRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_timeouts_retry_with_max_three_attempts(self):
        read = AsyncMock(side_effect=[TimeoutError("secret"), TimeoutError("secret"), "read result"])
        self.assertEqual(await read_with_retry(read), "read result")
        self.assertEqual(read.await_count, 3)
        read = AsyncMock(side_effect=TimeoutError("secret"))
        with self.assertRaises(BrowserStop) as failure:
            await read_with_retry(read)
        self.assertEqual(failure.exception.reason, Reason.READ_TIMEOUT)
        self.assertNotIn("secret", str(failure.exception))
        self.assertEqual(read.await_count, 3)
        unknown = AsyncMock(side_effect=ValueError("token=secret"))
        with self.assertRaises(BrowserStop) as failure:
            await read_with_retry(unknown)
        self.assertEqual(failure.exception.reason, Reason.PAGE_UNKNOWN)
        self.assertEqual(unknown.await_count, 1)

    async def test_attempt_deadline_and_cancellation_are_bounded(self):
        async def never():
            await asyncio.Event().wait()

        with self.assertRaises(BrowserStop) as failure:
            await read_with_retry(never, retries=0, timeout_seconds=0.01)
        self.assertEqual(failure.exception.reason, Reason.READ_TIMEOUT)
        task = asyncio.create_task(read_with_retry(never))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        with self.assertRaises(BrowserStop):
            await read_with_retry(never, retries=3)
