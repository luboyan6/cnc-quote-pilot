"""Save an owned STEP drawing once, with a recoverable request identity."""

import asyncio
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.common.enums import RET
from app.config.setting import settings
from app.core.base_schema import AuthSchema
from app.core.database import async_db_session
from app.core.exceptions import CustomException
from app.modules.cnc.browser.files import STEP_SUFFIXES
from app.modules.cnc.cnc_part.model import CncPartModel
from app.utils.upload_util import UploadUtil

from .model import CncDrawingUpload
from .schema import DrawingUploadResult
from .storage import PRIVATE_DRAWING_ROOT, drawing_path, store_drawing, verify_drawing


def _unavailable() -> CustomException:
    return CustomException(msg="图纸上传记录不存在或不可用", code=RET.NOT_FOUND.code)


def _conflict() -> CustomException:
    return CustomException(msg="该请求标识已绑定其他图纸或文件已变更", code=RET.CONFLICT.code)


async def _store_before_cancellation(path: Path, content: bytes, digest: str) -> None:
    """Never abandon an active filesystem writer when the request is cancelled."""
    task = asyncio.create_task(asyncio.to_thread(store_drawing, path, content, digest))
    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if task.done() and not task.cancelled():
            task.exception()  # Retrieve any storage error before propagating cancellation.
        raise


class DrawingUploadService:
    def __init__(
        self,
        auth: AuthSchema,
        sessions: async_sessionmaker[AsyncSession] = async_db_session,
        root: Path = PRIVATE_DRAWING_ROOT,
    ) -> None:
        actor_id = auth.user.id
        if type(actor_id) is not int or actor_id <= 0:
            raise _unavailable()
        self.actor_id = actor_id
        self.sessions = sessions
        self.root = root

    def _path(self, request_id: UUID, extension: str) -> Path:
        try:
            return drawing_path(self.root, self.actor_id, request_id, extension)
        except ValueError:
            raise CustomException(msg="私有图纸存储配置不可用", code=RET.INTERNAL_SERVER_ERROR.code) from None

    @staticmethod
    def _validate_upload(name: str | None, data: bytes) -> tuple[str, str]:
        if not name or not UploadUtil.check_path_traversal(name) or len(name) > 255:
            raise CustomException(msg="图纸文件名无效")
        extension = Path(name).suffix.lower()
        if extension not in STEP_SUFFIXES:
            raise CustomException(msg="仅支持 STEP、STP 或 SETP 图纸")
        if not data or len(data) > settings.MAX_FILE_SIZE:
            raise CustomException(msg="图纸为空或超过允许的大小")
        if not data.lstrip().startswith(b"ISO-10303-21;") or not data.rstrip().endswith(b"END-ISO-10303-21;"):
            raise CustomException(msg="图纸不是有效的 STEP 文件（缺少文件头或结束标记）")
        return name, extension

    async def _register(self, request_id: UUID, name: str, extension: str, data: bytes, digest: str) -> None:
        path = self._path(request_id, extension)
        try:
            async with self.sessions.begin() as db:
                current = await db.get(CncDrawingUpload, (self.actor_id, str(request_id)))
                if current is not None:
                    return
                part = CncPartModel(
                    created_id=self.actor_id,
                    file_name=name,
                    file_path=path.as_posix(),
                    extension=extension.removeprefix("."),
                    size_bytes=len(data),
                    validation_status="PENDING",
                    upload_authorized=False,
                )
                db.add(part)
                await db.flush()
                db.add(CncDrawingUpload(
                    owner_id=self.actor_id,
                    request_id=str(request_id),
                    part_id=part.id,
                    sha256=digest,
                    size_bytes=len(data),
                    file_name=name,
                    extension=extension,
                    state="PENDING",
                ))
                await db.flush()
        except IntegrityError:
            # A concurrent request may have committed the same owner/key.
            # Re-read after rollback; any unrelated integrity failure propagates.
            async with self.sessions() as db:
                if await db.get(CncDrawingUpload, (self.actor_id, str(request_id))) is None:
                    raise

    async def _bound_rows(self, db: AsyncSession, request_id: UUID, *, lock: bool = False) -> tuple[CncDrawingUpload, CncPartModel]:
        stmt = (
            select(CncDrawingUpload, CncPartModel)
            .join(CncPartModel, CncPartModel.id == CncDrawingUpload.part_id)
            .where(CncDrawingUpload.owner_id == self.actor_id, CncDrawingUpload.request_id == str(request_id))
        )
        if lock:
            stmt = stmt.with_for_update()
        found = (await db.execute(stmt)).one_or_none()
        if found is None:
            raise _unavailable()
        record, part = found
        expected_path = self._path(request_id, record.extension)
        if (
            part.is_deleted
            or part.created_id != self.actor_id
            or part.file_name != record.file_name
            or part.file_path != expected_path.as_posix()
            or part.size_bytes != record.size_bytes
            or part.extension != record.extension.removeprefix(".")
            or record.state not in {"PENDING", "READY"}
            or (record.state == "READY" and part.validation_status != "HEADER_VALID")
        ):
            raise _unavailable()
        return record, part

    async def upload(self, request_id: UUID, upload: UploadFile) -> DrawingUploadResult:
        data = await upload.read(settings.MAX_FILE_SIZE + 1)
        name, extension = self._validate_upload(upload.filename, data)
        digest = hashlib.sha256(data).hexdigest()
        await self._register(request_id, name, extension, data, digest)

        async with self.sessions.begin() as db:
            record, part = await self._bound_rows(db, request_id, lock=True)
            if (record.sha256, record.size_bytes, record.file_name, record.extension) != (digest, len(data), name, extension):
                raise _conflict()
            path = self._path(request_id, extension)
            try:
                await _store_before_cancellation(path, data, digest)
            except ValueError:
                raise _conflict() from None
            except OSError:
                raise CustomException(msg="保存图纸失败，请使用同一请求标识重试", code=RET.INTERNAL_SERVER_ERROR.code) from None
            record.state = "READY"
            record.updated_at = datetime.now(UTC)
            part.validation_status = "HEADER_VALID"
            await db.flush()
            result = DrawingUploadResult(request_id=str(request_id), state="READY", part_id=part.id, sha256=digest, size_bytes=len(data))
        return result

    async def status(self, request_id: UUID) -> DrawingUploadResult:
        async with self.sessions() as db:
            record, part = await self._bound_rows(db, request_id)
            if record.state == "READY" and not await asyncio.to_thread(
                verify_drawing, self._path(request_id, record.extension), record.sha256, record.size_bytes
            ):
                raise _conflict()
            return DrawingUploadResult(
                request_id=record.request_id,
                state="READY" if record.state == "READY" else "PENDING",
                part_id=part.id if record.state == "READY" else None,
                sha256=record.sha256,
                size_bytes=record.size_bytes,
            )
