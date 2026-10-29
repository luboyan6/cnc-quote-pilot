"""Actual local DB concurrency and privacy; not live platform acceptance."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from _quote_support import ACCOUNT, STEP, Account, CncQuoteIntentModel, CncQuoteRunModel, Config, Menu, Part, Platform, QuoteDatabase, Role, User
from sqlalchemy import func, select, update

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.modules.cnc.browser.contracts import Geometry, IntentKey, IntentState, Operation, SessionScope, UploadReceipt, item_fingerprint
from app.modules.cnc.browser.errors import BrowserStop
from app.modules.cnc.quote.contracts import QuoteError
from app.modules.cnc.quote.repository import DurableIntentStore, QuoteRepository, parameters, source_file


class RepositoryTests(QuoteDatabase):
    async def new_run(self):
        snapshot = await self.repo.snapshot(self.auth, 5, None)
        view, _ = await self.repo.create(self.auth, snapshot, str(uuid4()))
        self.snapshot, self.view = snapshot, view
        self.key = IntentKey(SessionScope("7", "xometry_us", "31"), view.run_id, "1", Operation.UPLOAD, item_fingerprint(snapshot.payload.sha256, snapshot.requested))
        return view

    async def test_real_platform_primary_key_and_optional_finish(self):
        snapshot = await self.repo.snapshot(self.auth, 5, None)
        self.assertEqual(snapshot.account.platform_id, 48)
        self.assertEqual(snapshot.provider_code, "xometry_us")
        self.assertEqual(dict(snapshot.requested.values), {"material": "Aluminum 6061", "quantity": "2"})
        self.assertEqual(snapshot.payload.buffer, STEP)
        self.assertNotIn(ACCOUNT.password, str(snapshot.frozen))

    async def test_account_zero_one_multiple_and_actor_filter(self):
        self.assertEqual([item.id for item in await self.repo.accounts(self.auth, 5)], [31])
        async with self.sessions() as db, db.begin():
            db.add_all([Account(id=32), Account(id=33, platform_id=99), Account(id=34, created_id=99)])
        self.assertEqual([item.id for item in await self.repo.accounts(self.auth, 5)], [31, 32])
        with self.assertRaisesRegex(QuoteError, "ACCOUNT_SELECTION_REQUIRED"):
            await self.repo.snapshot(self.auth, 5, None)
        for invalid in [33, 34, 999]:
            with self.assertRaisesRegex(QuoteError, "ACCOUNT_UNAVAILABLE"):
                await self.repo.snapshot(self.auth, 5, invalid)
        async with self.sessions() as db, db.begin():
            await db.execute(update(Account).values(enabled=False))
        with self.assertRaisesRegex(QuoteError, "NO_AVAILABLE_ACCOUNT"):
            await self.repo.snapshot(self.auth, 5, None)

    async def test_snapshot_rejects_config_part_acl_disabled_and_cross_platform(self):
        other = AuthSchema(user=CoreUserSchema(id=99))
        with self.assertRaisesRegex(QuoteError, "CONFIGURATION_UNAVAILABLE"):
            await self.repo.snapshot(other, 5, 31)
        self.login.load.return_value = replace(ACCOUNT, platform_id=12)
        with self.assertRaisesRegex(QuoteError, "ACCOUNT_PLATFORM_MISMATCH"):
            await self.repo.snapshot(self.auth, 5, 31)
        self.login.load.return_value = ACCOUNT
        async with self.sessions() as db, db.begin():
            await db.execute(update(Part).values(created_id=99))
        with self.assertRaisesRegex(QuoteError, "PART_UNAVAILABLE"):
            await self.repo.snapshot(self.auth, 5, 31)

    async def test_xometry_test_column_does_not_block_or_invalidate_but_file_changes_stop(self):
        snapshot = await self.repo.snapshot(self.auth, 5, 31)
        async with self.sessions() as db, db.begin():
            await db.execute(update(Part).values(upload_authorized=False))
        await self.repo.validate(self.auth, snapshot)
        current = await self.repo.snapshot(self.auth, 5, 31)
        self.assertEqual(current.config_revision, snapshot.config_revision)
        self.assertEqual(current.payload.buffer, STEP)
        async with self.sessions() as db:
            self.assertFalse((await db.get(Part, 9)).upload_authorized)
        self.file.write_bytes(STEP.replace(b"HEADER", b"CHANGED"))
        with self.assertRaises(BrowserStop):
            await self.repo.validate(self.auth, snapshot)
        with self.assertRaisesRegex(QuoteError, "FILE_INVALID"):
            await self.repo.snapshot(self.auth, 5, 31)

    async def test_other_provider_retains_upload_column_policy_and_revision(self):
        login_url = "https://www.jlc-cnc.com/"
        quote_url = "https://www.jlc-cnc.com/cncOrder/#/placeOrder"
        async with self.sessions() as db, db.begin():
            await db.execute(update(Platform).values(login_url=login_url, quote_entry_url=quote_url))
        self.login.load.return_value = replace(ACCOUNT, login_url=login_url, quote_url=quote_url)
        snapshot = await self.repo.snapshot(self.auth, 5, 31)
        self.assertEqual(snapshot.provider_code, "jlc_cnc_cn")
        async with self.sessions() as db, db.begin():
            await db.execute(update(Part).values(upload_authorized=False))
        with self.assertRaisesRegex(QuoteError, "QUOTE_INPUT_CHANGED"):
            await self.repo.validate(self.auth, snapshot)
        with self.assertRaisesRegex(QuoteError, "THIRD_PARTY_UPLOAD_NOT_AUTHORIZED"):
            await self.repo.snapshot(self.auth, 5, 31)

    async def test_config_change_stops_frozen_run(self):
        snapshot = await self.repo.snapshot(self.auth, 5, 31)
        async with self.sessions() as db, db.begin():
            await db.execute(update(Config).values(quantity=3))
        with self.assertRaisesRegex(QuoteError, "QUOTE_INPUT_CHANGED"):
            await self.repo.validate(self.auth, snapshot)

    async def test_concurrent_run_creation_has_one_winner_and_same_click_reuses(self):
        snapshot = await self.repo.snapshot(self.auth, 5, 31)
        request = str(uuid4())
        values = await asyncio.gather(*(self.repo.create(self.auth, snapshot, request) for _ in range(5)))
        self.assertEqual(sum(created for _, created in values), 1)
        self.assertEqual(len({view.run_id for view, _ in values}), 1)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(CncQuoteRunModel)), 1)
        fresh_repo = QuoteRepository(self.sessions, self.login, self.root)
        persisted = await fresh_repo.find(self.auth, 5, request_id=request)
        self.assertEqual(persisted.run_id, values[0][0].run_id)
        self.assertNotIn(ACCOUNT.password, persisted.model_dump_json())

    async def test_intent_concurrent_claim_restart_and_confirm_roundtrip(self):
        await self.new_run()
        store = DurableIntentStore(self.sessions)
        results = await asyncio.gather(*(store.claim(self.key) for _ in range(5)))
        self.assertEqual(sum(result.is_new for result in results), 1)
        fresh_store = DurableIntentStore(self.sessions)
        result = await fresh_store.claim(self.key)
        self.assertFalse(result.is_new)
        self.assertEqual(result.record.state, IntentState.CLAIMED)
        receipt = UploadReceipt("private-reference", self.snapshot.payload.sha256, Geometry(*(Decimal("1") for _ in range(4))))
        await fresh_store.confirm(self.key, receipt)
        await fresh_store.mark_uncertain(self.key)
        confirmed = await store.claim(self.key)
        self.assertEqual(confirmed.record.state, IntentState.CONFIRMED)
        self.assertEqual(confirmed.record.receipt, receipt)
        with self.assertRaises(BrowserStop):
            await store.confirm(self.key, replace(receipt, reference="different-reference"))

    async def test_intent_fingerprint_scope_and_generation_cannot_change_frozen_item(self):
        await self.new_run()
        store = DurableIntentStore(self.sessions)
        await store.claim(self.key)
        invalid = [replace(self.key, fingerprint="a" * 64), replace(self.key, scope=SessionScope("99", "xometry_us", "31")), replace(self.key, execution_generation="2", fingerprint="b" * 64)]
        for key in invalid:
            with self.assertRaises(BrowserStop):
                await store.claim(key)

    async def test_cancel_orphan_preserves_uncertain_and_fences_live_worker(self):
        view = await self.new_run()
        store = DurableIntentStore(self.sessions)
        await store.claim(self.key)
        async with self.sessions() as db, db.begin():
            await db.execute(update(Account).values(lease_owner="other-worker", lease_until=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=60)))
        with self.assertRaisesRegex(QuoteError, "QUOTE_WORKER_ACTIVE_CANNOT_CANCEL"):
            await self.repo.cancel_orphan(self.auth, 5, view.run_id)
        async with self.sessions() as db, db.begin():
            await db.execute(update(Account).values(lease_until=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)))
        cancelled = await self.repo.cancel_orphan(self.auth, 5, view.run_id)
        self.assertEqual(cancelled.status, "CANCELLED")
        async with self.sessions() as db:
            run = await db.get(CncQuoteRunModel, view.run_id)
            intent = await db.scalar(select(CncQuoteIntentModel))
            self.assertIsNone(run.active_config_id)
            self.assertEqual(intent.state, IntentState.UNCERTAIN.value)
        self.assertFalse((await store.claim(self.key)).is_new)
        self.assertEqual((await self.repo.cancel_orphan(self.auth, 5, view.run_id)).status, "CANCELLED")

    async def test_stored_run_is_actor_scoped_even_for_superuser(self):
        view = await self.new_run()
        async with self.sessions() as db, db.begin():
            await db.execute(update(User).where(User.id == 99).values(is_superuser=True))
        other = AuthSchema(user=CoreUserSchema(id=99, is_superuser=True))
        self.assertIsNone(await self.repo.find(other, 5, run_id=view.run_id))
        with self.assertRaisesRegex(QuoteError, "CONFIGURATION_BUSY"):
            await self.repo.create(other, self.snapshot, str(uuid4()))

    async def test_file_path_and_header_and_untrusted_parameters(self):
        part = SimpleNamespace(upload_authorized=True, validation_status="HEADER_VALID", extension="step", file_path="https://example.test/p.step", size_bytes=1)
        for path in ["https://example.test/p.step", str(self.root.parent / "outside.step"), str(self.root / ".." / "outside.step")]:
            part.file_path = path
            with self.assertRaisesRegex(QuoteError, "FILE_INVALID"):
                source_file(part, self.root)
        for extra in [{"quantity": 8}, {"surface_finish": "implicit"}, {"tolerance": {"unknown": True}}, {"": "empty-key"}, {"roughness": float("nan")}]:
            with self.assertRaisesRegex(QuoteError, "QUOTE_PARAMETERS_INVALID"):
                parameters(SimpleNamespace(material="Al", quantity=1, surface_finish=None, extra_params=extra))
        requested = parameters(SimpleNamespace(material="Al", quantity=1, surface_finish=None, extra_params={"threads": False, "inserts": True, "roughness": 1.6}))
        self.assertEqual(dict(requested.values), {"material": "Al", "quantity": "1", "threads": "false", "inserts": "true", "roughness": "1.6"})

    async def test_fresh_actor_disable_delete_and_role_menu_revocation(self):
        snapshot = await self.repo.snapshot(self.auth, 5, 31)
        for model, field, value, reason in [
            (User, "status", 1, "QUOTE_ACTOR_UNAVAILABLE"),
            (User, "is_deleted", True, "QUOTE_ACTOR_UNAVAILABLE"),
            (Role, "status", 1, "QUOTE_PERMISSION_REVOKED"),
            (Role, "is_deleted", True, "QUOTE_PERMISSION_REVOKED"),
            (Menu, "status", 1, "QUOTE_PERMISSION_REVOKED"),
            (Menu, "is_deleted", True, "QUOTE_PERMISSION_REVOKED"),
        ]:
            async with self.sessions() as db, db.begin():
                await db.execute(update(model).values(**{field: value}))
            with self.assertRaisesRegex(QuoteError, reason):
                await self.repo.validate(self.auth, snapshot)
            async with self.sessions() as db, db.begin():
                await db.execute(update(model).values(**{field: 0 if field == "status" else False}))
        async with self.sessions() as db, db.begin():
            await db.execute(update(Menu).where(Menu.permission == "module_cnc:cnc_account:update").values(permission="revoked"))
        with self.assertRaisesRegex(QuoteError, "QUOTE_PERMISSION_REVOKED"):
            await self.repo.validate(self.auth, snapshot)

    async def test_cached_superuser_flag_cannot_survive_demotion(self):
        async with self.sessions() as db, db.begin():
            await db.execute(update(User).where(User.id == 7).values(is_superuser=True))
            await db.execute(update(Config).values(created_id=99))
        stale_superuser = AuthSchema(user=CoreUserSchema(id=7, is_superuser=True))
        snapshot = await self.repo.snapshot(stale_superuser, 5, 31)
        async with self.sessions() as db, db.begin():
            await db.execute(update(User).where(User.id == 7).values(is_superuser=False))
        with self.assertRaisesRegex(QuoteError, "CONFIGURATION_UNAVAILABLE"):
            await self.repo.validate(stale_superuser, snapshot)

    async def test_admin_can_settle_only_stale_expired_other_actor_without_old_view(self):
        old = await self.new_run()
        await DurableIntentStore(self.sessions).claim(self.key)
        async with self.sessions() as db, db.begin():
            await db.execute(update(User).where(User.id == 99).values(is_superuser=True))
        admin = AuthSchema(user=CoreUserSchema(id=99, is_superuser=True))
        admin_snapshot = replace(self.snapshot, account=replace(self.snapshot.account, actor_id=99))
        with self.assertRaisesRegex(QuoteError, "CONFIGURATION_BUSY"):
            await self.repo.create(admin, admin_snapshot, str(uuid4()))
        async with self.sessions() as db, db.begin():
            await db.execute(update(CncQuoteRunModel).where(CncQuoteRunModel.run_id == old.run_id).values(updated_at=datetime.now(UTC) - timedelta(seconds=120)))
            await db.execute(update(Account).values(lease_owner="old-worker", lease_until=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=60)))
        with self.assertRaisesRegex(QuoteError, "CONFIGURATION_BUSY"):
            await self.repo.create(admin, admin_snapshot, str(uuid4()))
        async with self.sessions() as db, db.begin():
            await db.execute(update(Account).values(lease_until=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)))
        fresh, created = await self.repo.create(admin, admin_snapshot, str(uuid4()))
        self.assertTrue(created)
        self.assertNotEqual(fresh.run_id, old.run_id)
        self.assertIsNone(await self.repo.find(admin, 5, run_id=old.run_id))
        async with self.sessions() as db:
            old_row = await db.get(CncQuoteRunModel, old.run_id)
            self.assertEqual(old_row.status, "CANCELLED")
            self.assertEqual((await db.scalar(select(CncQuoteIntentModel))).state, IntentState.UNCERTAIN.value)

    async def test_normal_other_actor_cannot_settle_stale_run(self):
        await self.new_run()
        async with self.sessions() as db, db.begin():
            await db.execute(update(Config).values(created_id=99))
            await db.execute(update(Part).values(created_id=99))
            await db.execute(update(CncQuoteRunModel).values(updated_at=datetime.now(UTC) - timedelta(seconds=120)))
        other = AuthSchema(user=CoreUserSchema(id=99))
        other_snapshot = replace(self.snapshot, account=replace(self.snapshot.account, actor_id=99))
        with self.assertRaisesRegex(QuoteError, "CONFIGURATION_BUSY"):
            await self.repo.create(other, other_snapshot, str(uuid4()))
