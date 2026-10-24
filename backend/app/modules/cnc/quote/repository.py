"""Independent committed transactions for snapshots, runs and mutation intents."""

import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config.path_conf import BASE_DIR
from app.config.setting import settings
from app.modules.cnc.browser.contracts import (
    ConfigurationReceipt,
    Geometry,
    IntentClaim,
    IntentKey,
    IntentRecord,
    IntentState,
    Parameters,
    SubmissionReceipt,
    UploadReceipt,
    item_fingerprint,
)
from app.modules.cnc.browser.errors import BrowserStop, Reason
from app.modules.cnc.browser.files import STEP_SUFFIXES, StepPayload, TrustedStep
from app.modules.cnc.login.providers import resolve_provider
from app.modules.cnc.login.repository import LoginRepository
from app.modules.cnc.login.runtime import masked_username
from app.plugin.module_cnc.cnc_account.model import CncAccountModel
from app.plugin.module_cnc.cnc_part.model import CncPartModel
from app.plugin.module_cnc.cnc_part_config.model import CncPartConfigModel
from app.plugin.module_cnc.cnc_platform.model import CncPlatformModel
from app.plugin.module_cnc.cnc_quote.model import CncQuoteIntentModel, CncQuoteRunModel

from .authorization import ActorAuthorizer
from .contracts import TERMINAL, QuoteAccount, QuoteError, QuoteRunView, QuoteSnapshot

# Local resource ceiling only. A production adapter must ALSO enforce its own
# verified primary-CAD limit before any upload; this is not a provider limit.
SOURCE_FILE_LIMIT = 100 * 1024 * 1024


def _accessible(row, auth) -> bool:
    return row is not None and not row.is_deleted and (auth.user.is_superuser or row.created_id == auth.user.id)


def _configuration_revision(config, part, platform) -> str:
    values = [
        config.id, config.created_id, config.enabled, config.is_deleted, config.part_id, config.site_type,
        config.material, config.quantity, config.surface_finish, config.extra_params,
        part.id, part.created_id, part.is_deleted, part.file_path, part.size_bytes, part.extension,
        part.upload_authorized, part.validation_status, part.declared_unit,
        platform.id, platform.is_deleted, platform.login_url, platform.quote_entry_url,
    ]
    return hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def parameters(config) -> Parameters:
    if not config.material or type(config.quantity) is not int or config.quantity < 1:
        raise QuoteError("QUOTE_PARAMETERS_INVALID")
    values = {"material": config.material, "quantity": str(config.quantity)}
    if config.surface_finish:
        values["surface_finish"] = config.surface_finish
    extras = config.extra_params or {}
    if not isinstance(extras, dict) or len(extras) > 32:
        raise QuoteError("QUOTE_PARAMETERS_INVALID")
    for key, value in extras.items():
        if not isinstance(key, str) or key in {"material", "quantity", "surface_finish"} or type(value) not in {str, int, float, bool}:
            raise QuoteError("QUOTE_PARAMETERS_INVALID")
        if type(value) is float and not math.isfinite(value):
            raise QuoteError("QUOTE_PARAMETERS_INVALID")
        values[key] = ("true" if value else "false") if type(value) is bool else str(value)
    try:
        return Parameters.from_mapping(values)
    except BrowserStop:
        raise QuoteError("QUOTE_PARAMETERS_INVALID") from None


def source_file(part, root: Path) -> tuple[TrustedStep, StepPayload]:
    if part.upload_authorized is not True:
        raise QuoteError("THIRD_PARTY_UPLOAD_NOT_AUTHORIZED")
    if part.validation_status == "REJECTED" or not part.file_path or "." + str(part.extension).lower().lstrip(".") not in STEP_SUFFIXES:
        raise QuoteError("FILE_INVALID")
    try:
        stored = str(part.file_path).replace("\\", "/")
        if "://" in stored or "\x00" in stored or ".." in Path(stored).parts:
            raise ValueError
        if stored.startswith(settings.STATIC_URL.rstrip("/") + "/"):
            path = BASE_DIR / stored.lstrip("/")
        else:
            candidate = Path(stored)
            path = candidate if candidate.is_absolute() else BASE_DIR / candidate
        path = path.resolve(strict=True)
        root = root.resolve(strict=True)
        if not path.is_relative_to(root) or path.suffix.lower() not in STEP_SUFFIXES:
            raise ValueError
        if type(part.size_bytes) is not int or not 0 < part.size_bytes <= SOURCE_FILE_LIMIT:
            raise ValueError
        with path.open("rb") as stream:
            contents = stream.read(SOURCE_FILE_LIMIT + 1)
        if len(contents) != part.size_bytes:
            raise ValueError
        if not contents.lstrip().startswith(b"ISO-10303-21;") or not contents.rstrip().endswith(b"END-ISO-10303-21;"):
            raise ValueError
        digest = hashlib.sha256(contents).hexdigest()
        step = TrustedStep(root, path, digest, len(contents), SOURCE_FILE_LIMIT)
        return step, StepPayload(contents, digest)
    except (OSError, ValueError, TypeError, RuntimeError):
        raise QuoteError("FILE_INVALID") from None


class QuoteRepository:
    def __init__(self, session_factory=None, login_repository=None, storage_root: Path | None = None, authorizer=None):
        if session_factory is None:
            from app.core.database import async_db_session

            session_factory = async_db_session
        self.sessions = session_factory
        self.login = login_repository or LoginRepository(session_factory)
        self.authorizer = authorizer or ActorAuthorizer(session_factory)
        upload_root = settings.UPLOAD_FILE_PATH
        self.root = storage_root or (upload_root if upload_root.is_absolute() else BASE_DIR / upload_root)

    async def _objects(self, db, auth, config_id, *, lock=False):
        statement = select(CncPartConfigModel).where(CncPartConfigModel.id == config_id)
        if lock:
            statement = statement.with_for_update()
        config = await db.scalar(statement)
        if not _accessible(config, auth):
            raise QuoteError("CONFIGURATION_UNAVAILABLE")
        if not config.enabled:
            raise QuoteError("CONFIGURATION_DISABLED")
        part = await db.scalar(select(CncPartModel).where(CncPartModel.id == config.part_id))
        if not _accessible(part, auth):
            raise QuoteError("PART_UNAVAILABLE")
        platform = await db.scalar(select(CncPlatformModel).where(CncPlatformModel.id == config.site_type))
        if platform is None or platform.is_deleted:
            raise QuoteError("PLATFORM_CONFIGURATION_INVALID")
        provider = resolve_provider(platform.login_url, platform.quote_entry_url)
        return config, part, platform, provider

    async def accounts(self, auth, config_id: int) -> list[QuoteAccount]:
        auth = await self.authorizer.load(auth.user.id, for_run=False)
        async with self.sessions() as db:
            _, _, platform, _ = await self._objects(db, auth, config_id)
            statement = select(CncAccountModel).where(CncAccountModel.platform_id == platform.id, CncAccountModel.is_deleted.is_(False), CncAccountModel.enabled.is_(True))
            if not auth.user.is_superuser:
                statement = statement.where(CncAccountModel.created_id == auth.user.id)
            rows = (await db.scalars(statement.order_by(CncAccountModel.id))).unique().all()
            return [QuoteAccount(id=row.id, alias=row.alias or "", masked_username=masked_username(row.username)) for row in rows]

    async def snapshot(self, auth, config_id: int, account_id: int | None) -> QuoteSnapshot:
        auth = await self.authorizer.load(auth.user.id)
        accounts = await self.accounts(auth, config_id)
        if not accounts:
            raise QuoteError("NO_AVAILABLE_ACCOUNT")
        if account_id is None:
            if len(accounts) != 1:
                raise QuoteError("ACCOUNT_SELECTION_REQUIRED")
            account_id = accounts[0].id
        if account_id not in {item.id for item in accounts}:
            raise QuoteError("ACCOUNT_UNAVAILABLE")
        account = await self.login.load(auth, account_id)
        async with self.sessions() as db:
            config, part, platform, provider = await self._objects(db, auth, config_id)
            if account.platform_id != platform.id:
                raise QuoteError("ACCOUNT_PLATFORM_MISMATCH")
            requested = parameters(config)
            step, payload = source_file(part, self.root)
            name = Path((part.file_name or "part.step").replace("\\", "/")).name
            return QuoteSnapshot(config.id, part.id, account, _configuration_revision(config, part, platform), name, step, payload, requested, provider.code)

    async def validate(self, auth, snapshot: QuoteSnapshot) -> None:
        auth = await self.authorizer.load(auth.user.id)
        account = await self.login.load(auth, snapshot.account.id)
        async with self.sessions() as db:
            config, part, platform, _ = await self._objects(db, auth, snapshot.config_id)
            if account.revision != snapshot.account.revision or _configuration_revision(config, part, platform) != snapshot.config_revision:
                raise QuoteError("QUOTE_INPUT_CHANGED")
        # Revalidate disk identity before mutations, but always upload the buffer
        # frozen above, never reopen a path from Playwright.
        snapshot.step.read_verified()

    async def find(self, auth, config_id: int, run_id: str | None = None, request_id: str | None = None):
        auth = await self.authorizer.load(auth.user.id)
        async with self.sessions() as db:
            config = await db.scalar(select(CncPartConfigModel).where(CncPartConfigModel.id == config_id))
            if not _accessible(config, auth):
                raise QuoteError("CONFIGURATION_UNAVAILABLE")
            statement = select(CncQuoteRunModel).where(CncQuoteRunModel.config_id == config_id, CncQuoteRunModel.actor_id == auth.user.id)
            if run_id is not None:
                statement = statement.where(CncQuoteRunModel.run_id == run_id)
            elif request_id is not None:
                statement = statement.where(CncQuoteRunModel.request_id == request_id)
            else:
                statement = statement.where(CncQuoteRunModel.active_config_id == config_id)
            row = await db.scalar(statement)
            if row is None:
                return None
            return QuoteRunView.model_validate(row.public_view)

    async def create(self, auth, snapshot: QuoteSnapshot, request_id: str) -> tuple[QuoteRunView, bool]:
        auth = await self.authorizer.load(auth.user.id)
        now = datetime.now(UTC)
        view = QuoteRunView(
            run_id=str(uuid4()), config_id=snapshot.config_id, account_id=snapshot.account.id,
            platform_name=snapshot.account.platform_name, masked_username=masked_username(snapshot.account.username),
            file_name=snapshot.file_name, status="STARTING", stage="prepare", reason="QUOTE_STARTING",
            requested=dict(snapshot.requested.values), expires_at=now + timedelta(minutes=30),
        )
        try:
            async with self.sessions() as db, db.begin():
                await self._objects(db, auth, snapshot.config_id, lock=True)
                existing = await db.scalar(select(CncQuoteRunModel).where(CncQuoteRunModel.active_config_id == snapshot.config_id).with_for_update())
                if existing:
                    if existing.actor_id != auth.user.id:
                        if not auth.user.is_superuser:
                            raise QuoteError("CONFIGURATION_BUSY")
                        # A freshly committed run may still be claiming its
                        # account. Do not mistake that admission gap for a crash.
                        if existing.updated_at.replace(tzinfo=None) > now.replace(tzinfo=None) - timedelta(seconds=60):
                            raise QuoteError("CONFIGURATION_BUSY")
                        try:
                            await self._settle_expired(db, existing)
                        except QuoteError:
                            raise QuoteError("CONFIGURATION_BUSY") from None
                        await db.flush()
                    else:
                        return QuoteRunView.model_validate(existing.public_view), False
                db.add(CncQuoteRunModel(
                    run_id=view.run_id, actor_id=auth.user.id, owner_id=snapshot.account.owner_id,
                    config_id=snapshot.config_id, active_config_id=snapshot.config_id, part_id=snapshot.part_id,
                    platform_id=snapshot.account.platform_id, account_id=snapshot.account.id, request_id=request_id,
                    frozen=snapshot.frozen, public_view=view.model_dump(mode="json"),
                    status=view.status, stage=view.stage, reason=view.reason, created_at=now, updated_at=now,
                ))
            return view, True
        except IntegrityError:
            # Another HTTP request committed the same click or active config.
            prior = await self.find(auth, snapshot.config_id, request_id=request_id) or await self.find(auth, snapshot.config_id)
            if prior:
                return prior, False
            raise QuoteError("CONFIGURATION_BUSY") from None

    async def save(self, view: QuoteRunView, *, evidence: dict | None = None) -> None:
        async with self.sessions() as db, db.begin():
            row = await db.scalar(select(CncQuoteRunModel).where(CncQuoteRunModel.run_id == view.run_id).with_for_update())
            if row is None:
                raise QuoteError("QUOTE_RUN_UNAVAILABLE")
            if row.status in TERMINAL:
                if row.public_view != view.model_dump(mode="json"):
                    raise QuoteError("QUOTE_RUN_ALREADY_TERMINAL")
                return
            row.status, row.stage, row.reason = view.status, view.stage, view.reason
            row.public_view = view.model_dump(mode="json")
            if evidence is not None:
                # Core frozen input keys remain immutable; private same-run
                # verification evidence is archived alongside the snapshot and
                # never returned through QuoteRunView or the public result.
                row.frozen = {**row.frozen, "execution_evidence": evidence}
            row.updated_at = datetime.now(UTC)
            if view.status in TERMINAL:
                row.active_config_id = None

    async def cancel_orphan(self, auth, config_id, run_id):
        """Settle only after the durable browser lease is absent/expired.

        A live remote worker cannot be cancelled locally. No intent is removed
        or granted again, even after a restart or an uncertain remote receipt.
        """
        auth = await self.authorizer.load(auth.user.id)
        async with self.sessions() as db, db.begin():
            run = await db.scalar(select(CncQuoteRunModel).where(CncQuoteRunModel.run_id == run_id, CncQuoteRunModel.config_id == config_id, CncQuoteRunModel.actor_id == auth.user.id).with_for_update())
            if run is None:
                raise QuoteError("QUOTE_RUN_UNAVAILABLE")
            view = QuoteRunView.model_validate(run.public_view)
            if run.status in TERMINAL:
                return view
            return await self._settle_expired(db, run)

    async def _settle_expired(self, db, run):
        account = await db.scalar(select(CncAccountModel).where(CncAccountModel.id == run.account_id).with_for_update(of=CncAccountModel))
        now = datetime.now(UTC).replace(tzinfo=None)
        if account is not None and account.lease_owner and account.lease_until and account.lease_until.replace(tzinfo=None) > now:
            raise QuoteError("QUOTE_WORKER_ACTIVE_CANNOT_CANCEL")
        intents = (await db.scalars(select(CncQuoteIntentModel).where(CncQuoteIntentModel.run_id == run.run_id))).all()
        for intent in intents:
            if intent.state == IntentState.CLAIMED.value:
                intent.state = IntentState.UNCERTAIN.value
        view = QuoteRunView.model_validate(run.public_view)
        candidate = view.model_copy(update={"status": "CANCELLED", "reason": "QUOTE_CANCELLED_AFTER_LEASE_EXPIRY", "can_input": False})
        run.status, run.reason, run.public_view = candidate.status, candidate.reason, candidate.model_dump(mode="json")
        run.active_config_id, run.updated_at = None, datetime.now(UTC)
        return candidate

    async def assert_active(self, actor_id: int, run_id: str):
        async with self.sessions() as db:
            state = await db.scalar(select(CncQuoteRunModel.status).where(CncQuoteRunModel.run_id == run_id, CncQuoteRunModel.actor_id == actor_id))
            if state is None or state in TERMINAL:
                raise QuoteError("QUOTE_RUN_CLOSED")


def _encode_receipt(receipt) -> dict[str, Any]:
    if isinstance(receipt, UploadReceipt):
        geometry = receipt.geometry
        return {"kind": "upload", "reference": receipt.reference, "sha256": receipt.sha256, "geometry": [str(geometry.x_mm), str(geometry.y_mm), str(geometry.z_mm), str(geometry.volume_mm3)]}
    if isinstance(receipt, ConfigurationReceipt):
        return {"kind": "configure", "effective": dict(receipt.effective.values)}
    if isinstance(receipt, SubmissionReceipt):
        return {"kind": "submit", "reference": receipt.reference, "upload_reference": receipt.upload_reference, "effective": dict(receipt.effective.values)}
    raise BrowserStop(Reason.INTENT_CONFLICT)


def _decode_receipt(value):
    if value is None:
        return None
    if value["kind"] == "upload":
        return UploadReceipt(value["reference"], value["sha256"], Geometry(*(Decimal(number) for number in value["geometry"])))
    effective = Parameters.from_mapping(value["effective"])
    if value["kind"] == "configure":
        return ConfigurationReceipt(effective)
    if value["kind"] == "submit":
        return SubmissionReceipt(value["reference"], value["upload_reference"], effective)
    raise BrowserStop(Reason.INTENT_CONFLICT)


class DurableIntentStore:
    def __init__(self, sessions):
        self.sessions = sessions

    async def _run(self, db, key: IntentKey):
        row = await db.scalar(select(CncQuoteRunModel).where(CncQuoteRunModel.run_id == key.item_id).with_for_update())
        if row is None or str(row.owner_id) != key.scope.owner_id or str(row.account_id) != key.scope.account_id or row.frozen["provider_code"] != key.scope.platform_code:
            raise BrowserStop(Reason.INTENT_CONFLICT)
        frozen = row.frozen
        fingerprint = item_fingerprint(frozen["sha256"], Parameters.from_mapping(frozen["requested"]))
        if fingerprint != key.fingerprint:
            raise BrowserStop(Reason.INTENT_CONFLICT)
        return row

    async def _row(self, db, key):
        row = await db.scalar(select(CncQuoteIntentModel).where(CncQuoteIntentModel.run_id == key.item_id, CncQuoteIntentModel.generation == key.execution_generation, CncQuoteIntentModel.operation == key.operation.value))
        if row is not None and (row.fingerprint != key.fingerprint or row.scope != key.scope.as_dict()):
            raise BrowserStop(Reason.INTENT_CONFLICT)
        return row

    async def claim(self, key: IntentKey) -> IntentClaim:
        try:
            async with self.sessions() as db, db.begin():
                run = await self._run(db, key)
                row = await self._row(db, key)
                if row is not None:
                    return IntentClaim(False, IntentRecord(key, IntentState(row.state), _decode_receipt(row.receipt)))
                if run.status in TERMINAL:
                    raise BrowserStop(Reason.INTENT_CONFLICT)
                db.add(CncQuoteIntentModel(id=str(uuid4()), run_id=key.item_id, generation=key.execution_generation, operation=key.operation.value, fingerprint=key.fingerprint, scope=key.scope.as_dict(), state=IntentState.CLAIMED.value))
            return IntentClaim(True, IntentRecord(key, IntentState.CLAIMED))
        except IntegrityError:
            # Retry only the local uniqueness read, never the remote mutation.
            async with self.sessions() as db:
                await self._run(db, key)
                row = await self._row(db, key)
                if row is None:
                    raise BrowserStop(Reason.STATE_UNAVAILABLE) from None
                return IntentClaim(False, IntentRecord(key, IntentState(row.state), _decode_receipt(row.receipt)))

    async def confirm(self, key: IntentKey, receipt) -> None:
        encoded = _encode_receipt(receipt)
        if encoded["kind"] != key.operation.value:
            raise BrowserStop(Reason.INTENT_CONFLICT)
        async with self.sessions() as db, db.begin():
            await self._run(db, key)
            row = await self._row(db, key)
            if row is None or (row.state == IntentState.CONFIRMED.value and row.receipt != encoded):
                raise BrowserStop(Reason.INTENT_CONFLICT)
            row.state, row.receipt = IntentState.CONFIRMED.value, encoded

    async def mark_uncertain(self, key: IntentKey) -> None:
        async with self.sessions() as db, db.begin():
            await self._run(db, key)
            row = await self._row(db, key)
            if row is None:
                raise BrowserStop(Reason.INTENT_CONFLICT)
            if row.state != IntentState.CONFIRMED.value:
                row.state = IntentState.UNCERTAIN.value
