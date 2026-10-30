"""Independent committed transactions for snapshots, runs and mutation intents."""

import hashlib
import json
import math
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.config.path_conf import BASE_DIR
from app.config.setting import settings
from app.modules.cnc.browser.contracts import (
    ConfigurationReceipt,
    DeclarationReceipt,
    Geometry,
    IntentClaim,
    IntentKey,
    IntentRecord,
    IntentState,
    Operation,
    Parameters,
    SessionScope,
    SubmissionReceipt,
    UploadReceipt,
    item_fingerprint,
)
from app.modules.cnc.browser.errors import BrowserStop, Reason
from app.modules.cnc.browser.files import STEP_SUFFIXES, StepPayload, TrustedStep
from app.modules.cnc.cnc_account.model import CncAccountModel
from app.modules.cnc.cnc_drawing_upload.model import CncDrawingUpload
from app.modules.cnc.cnc_drawing_upload.storage import PRIVATE_DRAWING_ROOT, drawing_path
from app.modules.cnc.cnc_part.model import CncPartModel
from app.modules.cnc.cnc_part_config.model import CncPartConfigModel
from app.modules.cnc.cnc_platform.model import CncPlatformModel
from app.modules.cnc.cnc_quote.model import CncQuoteIntentModel, CncQuoteRunModel
from app.modules.cnc.cnc_quote_result.model import CncQuoteResultModel
from app.modules.cnc.login.providers import resolve_provider
from app.modules.cnc.login.repository import LoginRepository
from app.modules.cnc.login.runtime import masked_username

from .authorization import ActorAuthorizer
from .contracts import TERMINAL, QuoteAccount, QuoteError, QuoteRunView, QuoteSnapshot

# Local resource ceiling only. A production adapter must ALSO enforce its own
# verified primary-CAD limit before any upload; this is not a provider limit.
SOURCE_FILE_LIMIT = 100 * 1024 * 1024


def _accessible(row, auth) -> bool:
    return row is not None and not row.is_deleted and (auth.user.is_superuser or row.created_id == auth.user.id)


def _configuration_revision(config, part, platform) -> str:
    provider_code = resolve_provider(platform.login_url, platform.quote_entry_url).code
    values = [
        config.id,
        config.created_id,
        config.enabled,
        config.is_deleted,
        config.part_id,
        config.site_type,
        config.material,
        config.quantity,
        config.surface_finish,
        config.extra_params,
        part.id,
        part.created_id,
        part.is_deleted,
        part.file_path,
        part.size_bytes,
        part.extension,
        getattr(part, "upload_authorized", None) if provider_code != "xometry_us" else None,
        getattr(part, "validation_status", None),
        part.declared_unit,
        platform.id,
        platform.is_deleted,
        platform.login_url,
        platform.quote_entry_url,
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


def source_file(part, root: Path, *, require_upload_authorization: bool = True, private_binding: tuple[Path, Path, str] | None = None) -> tuple[TrustedStep, StepPayload]:
    if require_upload_authorization and getattr(part, "upload_authorized", True) is not True:
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
        root = root.resolve()
        expected_hash = None
        if private_binding is not None:
            if part.validation_status != "HEADER_VALID":
                raise ValueError
            private_root, expected_path, expected_hash = private_binding
            root = private_root.resolve(strict=True)
            if path != expected_path or not path.is_relative_to(root):
                raise ValueError
        elif not path.is_relative_to(root):
            raise ValueError
        if not root.is_dir() or path.suffix.lower() not in STEP_SUFFIXES:
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
        if expected_hash is not None and digest != expected_hash:
            raise ValueError
        step = TrustedStep(root, path, digest, len(contents), SOURCE_FILE_LIMIT)
        return step, StepPayload(contents, digest)
    except (OSError, ValueError, TypeError, RuntimeError):
        raise QuoteError("FILE_INVALID") from None


class QuoteRepository:
    def __init__(self, session_factory=None, login_repository=None, storage_root: Path | None = None, authorizer=None, private_storage_root: Path | None = None):
        if session_factory is None:
            from app.core.database import async_db_session

            session_factory = async_db_session
        self.sessions = session_factory
        self.login = login_repository or LoginRepository(session_factory)
        self.authorizer = authorizer or ActorAuthorizer(session_factory)
        upload_root = settings.UPLOAD_FILE_PATH
        self.root = storage_root or (upload_root if upload_root.is_absolute() else BASE_DIR / upload_root)
        self.private_root = private_storage_root or PRIVATE_DRAWING_ROOT

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

    async def snapshot(self, auth, config_id: int, account_id: int | None, *, quantity: int | None = None) -> QuoteSnapshot:
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
            if quantity is not None:
                if type(quantity) is not int or not 1 <= quantity <= 100000:
                    raise QuoteError("QUOTE_PARAMETERS_INVALID")
                requested = Parameters.from_mapping(dict(requested.values) | {"quantity": str(quantity)})
            require_auth = provider.code != "xometry_us"
            private_binding = None
            if part.file_path:
                try:
                    stored = Path(str(part.file_path).replace("\\", "/"))
                    candidate = (stored if stored.is_absolute() else BASE_DIR / stored).resolve()
                except (OSError, ValueError, RuntimeError):
                    raise QuoteError("FILE_INVALID") from None
                if candidate.is_relative_to(self.private_root.resolve()):
                    record = await db.scalar(select(CncDrawingUpload).where(CncDrawingUpload.part_id == part.id))
                    if (
                        record is None
                        or record.state != "READY"
                        or record.owner_id != part.created_id
                        or record.size_bytes != part.size_bytes
                        or record.file_name != part.file_name
                        or record.extension.removeprefix(".") != part.extension
                    ):
                        raise QuoteError("FILE_INVALID")
                    try:
                        expected = drawing_path(self.private_root, record.owner_id, UUID(record.request_id), record.extension)
                    except (ValueError, TypeError):
                        raise QuoteError("FILE_INVALID") from None
                    private_binding = (self.private_root, expected, record.sha256)
            step, payload = source_file(part, self.root, require_upload_authorization=require_auth, private_binding=private_binding)
            name = Path((part.file_name or "part.step").replace("\\", "/")).name
            return QuoteSnapshot(config.id, part.id, account, _configuration_revision(config, part, platform), name, step, payload, requested, provider.code)

    async def from_frozen(self, auth, frozen: dict) -> QuoteSnapshot:
        try:
            quantity = int(frozen["requested"]["quantity"])
            snapshot = await self.snapshot(auth, frozen["config_id"], frozen["account_id"], quantity=quantity)
            actual = snapshot.frozen
            if any(actual[key] != frozen[key] for key in ("config_revision", "account_revision", "sha256", "size", "requested", "provider_code", "contract_version")):
                raise QuoteError("QUOTE_INPUT_CHANGED")
            return snapshot
        except (KeyError, TypeError, ValueError):
            raise QuoteError("QUOTE_INPUT_CHANGED") from None

    async def assert_upload_available(self, snapshot: QuoteSnapshot, *, run_id: str | None = None) -> None:
        async with self.sessions() as db:
            statement = (
                select(CncQuoteRunModel, CncQuoteIntentModel.operation)
                .join(CncQuoteIntentModel, CncQuoteIntentModel.run_id == CncQuoteRunModel.run_id)
                .where(
                    CncQuoteRunModel.account_id == snapshot.account.id,
                    CncQuoteIntentModel.operation.in_([Operation.UPLOAD.value, Operation.CONFIGURE.value, Operation.SUBMIT.value, Operation.DECLARATION.value]),
                    CncQuoteIntentModel.state.in_([IntentState.CLAIMED.value, IntentState.UNCERTAIN.value]),
                )
            )
            if run_id is not None:
                statement = statement.where(CncQuoteRunModel.run_id != run_id)
            rows = (await db.execute(statement)).all()
            for row, operation in rows:
                prior_hash = (row.frozen or {}).get("sha256")
                valid_hash = isinstance(prior_hash, str) and re.fullmatch(r"[0-9a-f]{64}", prior_hash) is not None
                if not valid_hash or prior_hash == snapshot.payload.sha256:
                    reason = "QUOTE_PRIOR_UPLOAD_UNCONFIRMED_NO_RETRY" if operation == Operation.UPLOAD.value else "QUOTE_PRIOR_MUTATION_UNCONFIRMED_NO_RETRY"
                    raise QuoteError(reason)

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

    async def create(self, auth, snapshot: QuoteSnapshot, request_id: str, *, batch_claim: dict | None = None) -> tuple[QuoteRunView, bool]:
        auth = await self.authorizer.load(auth.user.id)
        now = datetime.now(UTC)
        view = QuoteRunView(
            run_id=str(uuid4()),
            config_id=snapshot.config_id,
            account_id=snapshot.account.id,
            platform_name=snapshot.account.platform_name,
            masked_username=masked_username(snapshot.account.username),
            file_name=snapshot.file_name,
            status="STARTING",
            stage="prepare",
            reason="QUOTE_STARTING",
            requested=dict(snapshot.requested.values),
            expires_at=now + timedelta(minutes=30),
        )
        try:
            async with self.sessions() as db, db.begin():
                item = None
                if batch_claim:
                    from app.modules.cnc.cnc_quote_batch_item.model import CncQuoteBatchItemModel

                    item = await db.scalar(select(CncQuoteBatchItemModel).where(CncQuoteBatchItemModel.id == batch_claim["id"]).with_for_update())
                    if (
                        item is None
                        or item.claim_owner != batch_claim["owner"]
                        or item.claim_token != batch_claim["token"]
                        or item.claim_until is None
                        or item.claim_until.replace(tzinfo=UTC) <= datetime.now(UTC)
                        or item.cancel_requested_at is not None
                        or item.run_id is not None
                        or item.config_id != snapshot.config_id
                        or item.account_id != snapshot.account.id
                        or item.batch_id != batch_claim["batch_id"]
                        or batch_claim["actor_id"] != auth.user.id
                    ):
                        raise QuoteError("BATCH_CLAIM_LOST")
                await self._objects(db, auth, snapshot.config_id, lock=True)
                existing = await db.scalar(select(CncQuoteRunModel).where(CncQuoteRunModel.active_config_id == snapshot.config_id).with_for_update())
                if existing:
                    if batch_claim:
                        raise QuoteError("CONFIGURATION_BUSY")
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
                db.add(
                    CncQuoteRunModel(
                        run_id=view.run_id,
                        actor_id=auth.user.id,
                        owner_id=snapshot.account.owner_id,
                        config_id=snapshot.config_id,
                        active_config_id=snapshot.config_id,
                        part_id=snapshot.part_id,
                        platform_id=snapshot.account.platform_id,
                        account_id=snapshot.account.id,
                        request_id=request_id,
                        item_id=item.id if item else None,
                        attempt_no=batch_claim["attempt_no"] if batch_claim else None,
                        item_claim_owner=batch_claim["owner"] if batch_claim else None,
                        item_claim_token=batch_claim["token"] if batch_claim else None,
                        frozen=snapshot.frozen,
                        public_view=view.model_dump(mode="json"),
                        status=view.status,
                        stage=view.stage,
                        reason=view.reason,
                        created_at=now,
                        updated_at=now,
                    )
                )
                if item and batch_claim:
                    item.run_id, item.attempt_count = view.run_id, batch_claim["attempt_no"]
                    item.exec_status, item.started_at, item.updated_at = "RUNNING", now, now
                    item.row_version += 1
                    from app.modules.cnc.batch.repository import BatchRepository

                    await BatchRepository.aggregate(db, item.batch_id)
            return view, True
        except IntegrityError:
            # Another HTTP request committed the same click or active config.
            prior = await self.find(auth, snapshot.config_id, request_id=request_id) or await self.find(auth, snapshot.config_id)
            if prior and (not batch_claim or prior.run_id == view.run_id):
                return prior, False
            raise QuoteError("CONFIGURATION_BUSY") from None

    async def _locked_run_item(self, db, run_id: str):
        from app.modules.cnc.cnc_quote_batch_item.model import CncQuoteBatchItemModel

        item_id = await db.scalar(select(CncQuoteRunModel.item_id).where(CncQuoteRunModel.run_id == run_id))
        item = await db.scalar(select(CncQuoteBatchItemModel).where(CncQuoteBatchItemModel.id == item_id).with_for_update()) if item_id else None
        row = await db.scalar(select(CncQuoteRunModel).where(CncQuoteRunModel.run_id == run_id).with_for_update())
        if row is None:
            raise QuoteError("QUOTE_RUN_UNAVAILABLE")
        return row, item

    @staticmethod
    def _check_claim(row, item, *, allow_cancel=False, allow_staged=False):
        if row.item_id is None:
            return
        if item is None or item.run_id != row.run_id or item.claim_owner != row.item_claim_owner or item.claim_token != row.item_claim_token:
            raise QuoteError("BATCH_CLAIM_LOST")
        if not allow_staged and (item.claim_until is None or item.claim_until.replace(tzinfo=UTC) <= datetime.now(UTC)):
            raise QuoteError("BATCH_CLAIM_LOST")
        if item.cancel_requested_at and not (allow_cancel or allow_staged):
            raise QuoteError("BATCH_CANCELLED")

    async def validate_claim(self, run_id: str) -> None:
        async with self.sessions() as db, db.begin():
            row, item = await self._locked_run_item(db, run_id)
            self._check_claim(row, item)

    async def claim_shortcut(self, run_id: str, operation: str) -> None:
        async with self.sessions() as db, db.begin():
            row, item = await self._locked_run_item(db, run_id)
            self._check_claim(row, item)
            if row.status in TERMINAL:
                raise QuoteError("QUOTE_RUN_CLOSED")
            try:
                op = Operation(operation)
            except ValueError:
                raise QuoteError("QUOTE_EXECUTION_UNAVAILABLE") from None
            existing = await db.scalar(select(CncQuoteIntentModel).where(CncQuoteIntentModel.run_id == run_id, CncQuoteIntentModel.generation == "shortcut", CncQuoteIntentModel.operation == op.value))
            if existing:
                raise QuoteError("QUOTE_MUTATION_UNCONFIRMED_NO_RETRY")
            frozen = row.frozen
            scope = SessionScope(str(row.owner_id), frozen["provider_code"], str(row.account_id))
            db.add(
                CncQuoteIntentModel(
                    id=str(uuid4()),
                    run_id=run_id,
                    generation="shortcut",
                    operation=op.value,
                    fingerprint=item_fingerprint(frozen["sha256"], Parameters.from_mapping(frozen["requested"])),
                    scope=scope.as_dict(),
                    state=IntentState.CLAIMED.value,
                )
            )

    async def stage_shortcut_result(self, view: QuoteRunView, evidence: dict) -> None:
        async with self.sessions() as db, db.begin():
            row, item = await self._locked_run_item(db, view.run_id)
            self._check_claim(row, item)
            if row.status in TERMINAL or view.status not in {"QUOTED", "REFERENCE_ESTIMATE", "PENDING_REVIEW"}:
                raise QuoteError("QUOTE_RUN_CLOSED")
            row.frozen = {**row.frozen, "pending_result_view": view.model_dump(mode="json"), "pending_result_evidence": evidence}

    async def persist_pending_result(self, run_id: str) -> QuoteRunView | None:
        async with self.sessions() as db:
            row = await db.get(CncQuoteRunModel, run_id)
            if row is None or not row.frozen.get("pending_result_view"):
                return None
            candidate = QuoteRunView.model_validate(row.frozen["pending_result_view"])
            evidence = row.frozen.get("pending_result_evidence")
        await self.save(candidate, evidence=evidence, _staged=True)
        return candidate

    async def record_declaration(self, auth, snapshot: QuoteSnapshot, run_id: str, declaration, choice: str) -> None:
        await self.authorizer.load(auth.user.id)
        async with self.sessions() as db, db.begin():
            row, item = await self._locked_run_item(db, run_id)
            self._check_claim(row, item)
            current = QuoteRunView.model_validate(row.public_view)
            if (
                row.actor_id != auth.user.id
                or row.config_id != snapshot.config_id
                or row.account_id != snapshot.account.id
                or row.frozen.get("sha256") != snapshot.payload.sha256
                or current.status != "WAITING_HUMAN"
                or current.export_declaration != declaration
                or choice not in {option.value for option in declaration.options}
            ):
                raise QuoteError("QUOTE_EXPORT_DECLARATION_STALE")
            prior = row.frozen.get("export_declaration_decision")
            if prior:
                if prior.get("declaration_id") != declaration.declaration_id or prior.get("choice") != choice:
                    raise QuoteError("QUOTE_EXPORT_DECLARATION_STALE")
                return
            decision = {
                "run_id": run_id,
                "actor_id": auth.user.id,
                "sha256": snapshot.payload.sha256,
                "declaration_id": declaration.declaration_id,
                "statement": declaration.statement,
                "options": [option.model_dump() for option in declaration.options],
                "choice": choice,
                "scope": "xometry_quote_only",
                "decided_at": datetime.now(UTC).isoformat(),
            }
            row.frozen = {**row.frozen, "export_declaration_decision": decision}

    async def save(self, view: QuoteRunView, *, evidence: dict | None = None, _staged: bool = False) -> None:
        async with self.sessions() as db, db.begin():
            row, item = await self._locked_run_item(db, view.run_id)
            if row.status in TERMINAL:
                if row.public_view != view.model_dump(mode="json"):
                    raise QuoteError("QUOTE_RUN_ALREADY_TERMINAL")
                return
            if _staged and row.frozen.get("pending_result_view") != view.model_dump(mode="json"):
                raise QuoteError("QUOTE_RESULT_UNAVAILABLE")
            if row.frozen.get("pending_result_view") and view.status in {"FAILED", "CANCELLED"}:
                raise QuoteError("QUOTE_RESULT_PENDING")
            self._check_claim(row, item, allow_cancel=view.status == "CANCELLED", allow_staged=_staged)
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
                if item:
                    item.exec_status = "COMPLETED" if view.status in {"QUOTED", "REFERENCE_ESTIMATE", "PENDING_REVIEW"} else view.status
                    item.quote_kind = view.status if item.exec_status == "COMPLETED" else None
                    item.error_code = None if item.exec_status == "COMPLETED" else view.reason
                    item.finished_at, item.updated_at = row.updated_at, row.updated_at
                    item.claim_owner, item.claim_until = None, None
                    if view.status == "FAILED" and item.cancel_requested_at is None:
                        from app.modules.cnc.recovery.contracts import RecoveryAction, SideEffectState
                        from app.modules.cnc.recovery.policy import classify_error

                        intents = (await db.scalars(select(CncQuoteIntentModel).where(CncQuoteIntentModel.run_id == row.run_id))).all()
                        uncertain = any(intent.state in {IntentState.CLAIMED.value, IntentState.UNCERTAIN.value} for intent in intents)
                        previous_reauth = await db.scalar(
                            select(func.count())
                            .select_from(CncQuoteRunModel)
                            .where(
                                CncQuoteRunModel.item_id == item.id,
                                CncQuoteRunModel.run_id != row.run_id,
                                CncQuoteRunModel.reason.in_(["SESSION_EXPIRED", "UNAUTHORIZED", "LOGIN_REQUIRED", "TOKEN_EXPIRED", "SESSION_INVALID"]),
                            )
                        )
                        decision = classify_error(
                            view.reason,
                            stage=view.stage,
                            effect_state=SideEffectState.CLAIMED if uncertain else SideEffectState.NONE,
                            attempt_count=item.attempt_count,
                            max_attempts=item.max_attempts,
                            reauth_count=previous_reauth or 0,
                        )
                        if decision.action in {RecoveryAction.RETRY_WAIT, RecoveryAction.REAUTHENTICATE}:
                            item.exec_status, item.next_attempt_at, item.run_id, item.finished_at = "RETRY_WAIT", decision.next_attempt_at, None, None
                            item.error_code = decision.error_code
                        elif decision.action == RecoveryAction.RECONCILING:
                            item.exec_status, item.finished_at = "RECONCILING", None
                            item.error_code = decision.error_code
                    item.row_version += 1
                await self._persist_result(db, row, view, evidence)
                if _staged or "pending_result_view" in row.frozen:
                    row.frozen = {k: v for k, v in row.frozen.items() if k not in {"pending_result_view", "pending_result_evidence"}}
                    intents = (
                        await db.scalars(
                            select(CncQuoteIntentModel).where(
                                CncQuoteIntentModel.run_id == row.run_id, CncQuoteIntentModel.generation == "shortcut", CncQuoteIntentModel.state == IntentState.CLAIMED.value
                            )
                        )
                    ).all()
                    for intent in intents:
                        intent.state = IntentState.CONFIRMED.value
                if item:
                    from app.modules.cnc.batch.repository import BatchRepository

                    await BatchRepository.aggregate(db, item.batch_id)
            elif item:
                item.exec_status = "WAITING_HUMAN" if view.status == "WAITING_HUMAN" else "RUNNING"
                item.updated_at = row.updated_at
                item.row_version += 1

    async def _persist_result(self, db, row, view: QuoteRunView, evidence: dict | None = None) -> None:
        existing = await db.scalar(select(CncQuoteResultModel).where(CncQuoteResultModel.run_id == row.run_id))
        if existing is not None:
            return
        frozen = row.frozen or {}
        requested = frozen.get("requested") or view.requested
        result = view.result
        evidence = evidence or frozen.get("execution_evidence") or {}
        duration = max(0, (row.updated_at.replace(tzinfo=UTC) - row.created_at.replace(tzinfo=UTC)).total_seconds()) if row.updated_at and row.created_at else 0.0
        batch_id = None
        round_id = None
        queue_ms = 0
        active_execution_ms = int(duration * 1000)
        human_wait_ms = 0
        reconcile_ms = 0
        total_wall_ms = int(duration * 1000)
        error_code = None

        item_id = getattr(row, "item_id", None)
        if item_id:
            from app.modules.cnc.cnc_quote_batch_item.model import CncQuoteBatchItemModel
            from app.modules.cnc.cnc_quote_schedule_round.model import CncQuoteScheduleRoundModel

            item = await db.get(CncQuoteBatchItemModel, item_id)
            if item:
                batch_id = item.batch_id
                error_code = item.error_code
                if item.started_at and item.created_at:
                    queue_ms = max(0, int((item.started_at.replace(tzinfo=UTC) - item.created_at.replace(tzinfo=UTC)).total_seconds() * 1000))
                if item.finished_at and item.started_at:
                    active_execution_ms = max(0, int((item.finished_at.replace(tzinfo=UTC) - item.started_at.replace(tzinfo=UTC)).total_seconds() * 1000))
                if item.finished_at and item.created_at:
                    total_wall_ms = max(0, int((item.finished_at.replace(tzinfo=UTC) - item.created_at.replace(tzinfo=UTC)).total_seconds() * 1000))
                if batch_id:
                    from app.modules.cnc.cnc_quote_batch.model import CncQuoteBatchModel

                    source = await db.scalar(select(CncQuoteBatchModel.source).where(CncQuoteBatchModel.id == batch_id))
                    if source == "schedule":
                        round_row = await db.scalar(select(CncQuoteScheduleRoundModel).where(CncQuoteScheduleRoundModel.batch_id == batch_id))
                        if round_row:
                            round_id = round_row.id

        file_sha256 = frozen.get("sha256")
        platform_code = frozen.get("provider_code", "unknown")
        quantity_val = int(requested["quantity"]) if requested and "quantity" in requested and str(requested["quantity"]).isdigit() else 1
        quote_currency = result.currency if result else None
        quote_scope = result.price_scope if result else None
        lead_time_text = (result.lead_time or {}).get("text") if result else None
        tax_included = None

        from app.modules.cnc.cnc_quote_result.comparison import (
            COMPARISON_RULE_VERSION,
            build_comparison_key,
        )

        comparison_key = build_comparison_key(
            platform_code=platform_code,
            account_condition=row.account_id,
            file_sha256=file_sha256,
            quantity=quantity_val,
            currency=quote_currency,
            price_scope=quote_scope,
            quote_kind=view.status,
            material=requested.get("material") if requested else None,
            surface_finish=requested.get("surface_finish") if requested else None,
            tolerance=requested.get("tolerance") if requested else None,
            roughness=requested.get("roughness") if requested else None,
            extra_params=requested,
            lead_time_tier=lead_time_text,
            tax_included=tax_included,
            version=COMPARISON_RULE_VERSION,
        )

        effective_snapshot = {
            "requested": requested,
            "provider_code": platform_code,
            "account_id": row.account_id,
            "file_sha256": file_sha256,
            "quote_kind": view.status,
            "currency": quote_currency,
            "price_scope": quote_scope,
            "tax_included": tax_included,
        }

        evidence_id = evidence.get("evidence_id")
        evidence_screenshot = evidence.get("evidence_screenshot")
        evidence_state = "available" if (evidence_id or evidence_screenshot) else None

        def money(value):
            if value is None:
                return None
            try:
                val = Decimal(str(value))
                if not val.is_finite():
                    return None
                return val
            except Exception:
                return None

        db.add(
            CncQuoteResultModel(
                uuid=str(uuid4()),
                run_id=row.run_id,
                item_id=item_id,
                batch_id=batch_id,
                round_id=round_id,
                config_id=row.config_id,
                config_name=f"配置#{row.config_id}",
                part_id=row.part_id,
                part_name=view.file_name,
                platform_id=row.platform_id,
                platform_code=platform_code,
                platform_name=view.platform_name,
                account_id=row.account_id,
                account_alias=view.masked_username,
                quote_status=view.status,
                success=view.status in {"QUOTED", "REFERENCE_ESTIMATE", "PENDING_REVIEW"},
                unit_price=money(result.amount) if result and result.price_scope == "unit" else None,
                total_amount=money(result.total_amount if result.total_amount is not None else result.amount if result.price_scope == "line" else None) if result else None,
                tax_amount=money(result.tax_amount) if result else None,
                discount_amount=money(result.discount_amount) if result else None,
                shipping_amount=None,
                tax_included=tax_included,
                currency=quote_currency,
                price_scope=quote_scope,
                lead_time_raw=lead_time_text,
                lead_time_json=result.lead_time if result else None,
                material=requested.get("material") if requested else None,
                surface_finish=requested.get("surface_finish") if requested else None,
                quantity=quantity_val,
                tolerance=requested.get("tolerance") if requested else None,
                roughness=requested.get("roughness") if requested else None,
                extra_params=requested,
                file_sha256=file_sha256,
                comparison_key=comparison_key,
                comparison_version=COMPARISON_RULE_VERSION if comparison_key else None,
                effective_snapshot=effective_snapshot,
                queue_ms=queue_ms,
                active_execution_ms=active_execution_ms,
                human_wait_ms=human_wait_ms,
                reconcile_ms=reconcile_ms,
                total_wall_ms=total_wall_ms,
                elapsed_ms=int(duration * 1000),
                duration_seconds=Decimal(str(round(duration, 2))),
                evidence_id=evidence_id,
                evidence_state=evidence_state,
                evidence_screenshot=evidence_screenshot,
                quoted_at=result.priced_at if result else None,
                observed_at=result.observed_at if result else None,
                error_code=error_code,
                error_message=None if result else view.reason,
                created_id=row.actor_id,
                updated_id=row.actor_id,
                created_time=row.created_at,
                updated_time=row.updated_at,
            )
        )

    async def cancel_orphan(self, auth, config_id, run_id):
        """Settle only after the durable browser lease is absent/expired.

        A live remote worker cannot be cancelled locally. No intent is removed
        or granted again, even after a restart or an uncertain remote receipt.
        """
        auth = await self.authorizer.load(auth.user.id)
        async with self.sessions() as db, db.begin():
            run = await db.scalar(
                select(CncQuoteRunModel).where(CncQuoteRunModel.run_id == run_id, CncQuoteRunModel.config_id == config_id, CncQuoteRunModel.actor_id == auth.user.id).with_for_update()
            )
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
    if isinstance(receipt, DeclarationReceipt):
        return {"kind": "declaration", "declaration_id": receipt.declaration_id, "choice": receipt.choice, "sha256": receipt.sha256, "upload_reference": receipt.upload_reference}
    if isinstance(receipt, SubmissionReceipt):
        return {"kind": "submit", "reference": receipt.reference, "upload_reference": receipt.upload_reference, "effective": dict(receipt.effective.values)}
    raise BrowserStop(Reason.INTENT_CONFLICT)


def _decode_receipt(value):
    if value is None:
        return None
    if value["kind"] == "upload":
        return UploadReceipt(value["reference"], value["sha256"], Geometry(*(Decimal(number) for number in value["geometry"])))
    if value["kind"] == "declaration":
        return DeclarationReceipt(value["declaration_id"], value["choice"], value["sha256"], value["upload_reference"])
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
        row = await db.scalar(
            select(CncQuoteIntentModel).where(
                CncQuoteIntentModel.run_id == key.item_id, CncQuoteIntentModel.generation == key.execution_generation, CncQuoteIntentModel.operation == key.operation.value
            )
        )
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
                db.add(
                    CncQuoteIntentModel(
                        id=str(uuid4()),
                        run_id=key.item_id,
                        generation=key.execution_generation,
                        operation=key.operation.value,
                        fingerprint=key.fingerprint,
                        scope=key.scope.as_dict(),
                        state=IntentState.CLAIMED.value,
                    )
                )
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
