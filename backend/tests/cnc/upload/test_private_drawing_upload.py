"""Real private STEP storage and idempotency, using only isolated SQLite."""

import asyncio
import hashlib
import importlib.util
import threading
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI, UploadFile
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.staticfiles import StaticFiles

from app.common.enums import RET
from app.config.setting import settings
from app.core.base_model import MappedBase
from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.dependencies import get_current_user
from app.core.exceptions import CustomException, handle_exception
from app.modules.cnc.browser.errors import BrowserStop
from app.modules.cnc.cnc_drawing_upload.controller import DrawingUploadRouter
from app.modules.cnc.cnc_drawing_upload.model import CncDrawingUpload
from app.modules.cnc.cnc_drawing_upload.service import DrawingUploadService
from app.modules.cnc.cnc_drawing_upload.storage import drawing_path
from app.modules.cnc.cnc_part.model import CncPartModel
from app.modules.cnc.quote.contracts import QuoteError
from app.modules.cnc.quote.repository import source_file
from app.modules.system.dept.model import DeptModel
from app.modules.system.menu.model import MenuModel
from app.modules.system.position.model import PositionModel
from app.modules.system.role.model import RoleDeptsModel, RoleMenusModel, RoleModel
from app.modules.system.user.model import UserModel, UserPositionsModel, UserRolesModel

STEP = b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;"


def file(name: str, content: bytes = STEP) -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(content), size=len(content))


@pytest_asyncio.fixture
async def storage(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'isolated.sqlite').as_posix()}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    models = [DeptModel, MenuModel, PositionModel, RoleModel, UserModel, RoleDeptsModel, RoleMenusModel, UserPositionsModel, UserRolesModel, CncPartModel, CncDrawingUpload]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync: MappedBase.metadata.create_all(sync, tables=[model.__table__ for model in models]))
    async with sessions.begin() as db:
        db.add_all([UserModel(id=7, username="owner", password="hash", name="Owner"), UserModel(id=8, username="other", password="hash", name="Other")])
    try:
        yield sessions, tmp_path / "private"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_private_upload_is_owned_idempotent_and_quote_checked(storage):
    sessions, root = storage
    service = DrawingUploadService(AuthSchema(user=CoreUserSchema(id=7)), sessions, root)
    request_id = uuid4()
    first = await service.upload(request_id, file("part.STEP"))
    second = await service.upload(request_id, file("part.STEP"))
    assert first == second
    assert set(first.model_dump()) == {"request_id", "state", "part_id", "sha256", "size_bytes"}
    assert first.sha256 == hashlib.sha256(STEP).hexdigest()
    assert first.size_bytes == len(STEP)
    async with sessions() as db:
        part = await db.get(CncPartModel, first.part_id)
        assert part is not None and part.created_id == 7 and part.upload_authorized is False
        assert part.validation_status == "HEADER_VALID"
        path = drawing_path(root, 7, request_id, ".step")
        assert path.read_bytes() == STEP
        assert not path.is_relative_to(Path(settings.UPLOAD_FILE_PATH).resolve())
        # Existing non-Xometry upload authorization remains in force.
        with pytest.raises(QuoteError, match="THIRD_PARTY_UPLOAD_NOT_AUTHORIZED"):
            source_file(part, root / "public", private_binding=(root, path, first.sha256))
        source, payload = source_file(part, root / "public", require_upload_authorization=False, private_binding=(root, path, first.sha256))
        assert payload.buffer == STEP and source.read_verified().buffer == STEP
        path.write_bytes(STEP.replace(b"HEADER", b"header"))
        with pytest.raises(QuoteError, match="FILE_INVALID"):
            source_file(part, root / "public", require_upload_authorization=False, private_binding=(root, path, first.sha256))
        with pytest.raises(BrowserStop):
            source.read_verified()
    with pytest.raises(CustomException) as modified:
        await service.status(request_id)
    assert modified.value.code == RET.CONFLICT.code


@pytest.mark.asyncio
async def test_cross_user_and_request_body_conflicts_are_separate(storage):
    sessions, root = storage
    first = DrawingUploadService(AuthSchema(user=CoreUserSchema(id=7)), sessions, root)
    second = DrawingUploadService(AuthSchema(user=CoreUserSchema(id=8)), sessions, root)
    request_id = uuid4()
    original = await first.upload(request_id, file("part.stp"))
    with pytest.raises(CustomException) as denied:
        await second.status(request_id)
    assert denied.value.code == RET.NOT_FOUND.code
    other = await second.upload(request_id, file("other.stp"))
    assert original.part_id != other.part_id
    for name, content in [("other.stp", STEP), ("part.stp", STEP.replace(b"HEADER", b"header"))]:
        with pytest.raises(CustomException) as conflict:
            await first.upload(request_id, file(name, content))
        assert conflict.value.code == RET.CONFLICT.code
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(CncPartModel)) == 2


@pytest.mark.asyncio
async def test_failed_write_is_recoverable_without_duplicate_and_cleans_staging(storage):
    sessions, root = storage
    service = DrawingUploadService(AuthSchema(user=CoreUserSchema(id=7)), sessions, root)
    request_id = uuid4()
    with patch("app.modules.cnc.cnc_drawing_upload.service.store_drawing", side_effect=OSError("private path")):
        with pytest.raises(CustomException) as failed:
            await service.upload(request_id, file("part.setp"))
        assert failed.value.code == RET.INTERNAL_SERVER_ERROR.code
    pending = await service.status(request_id)
    assert pending.state == "PENDING" and pending.part_id is None
    ready = await service.upload(request_id, file("part.setp"))
    assert ready.state == "READY"
    assert not list(root.rglob("*.tmp"))
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(CncPartModel)) == 1


@pytest.mark.asyncio
async def test_cancelled_request_waits_for_writer_and_can_recover_by_same_key(storage):
    from app.modules.cnc.cnc_drawing_upload.storage import store_drawing

    sessions, root = storage
    service = DrawingUploadService(AuthSchema(user=CoreUserSchema(id=7)), sessions, root)
    request_id = uuid4()
    entered = threading.Event()
    release = threading.Event()

    def slow_store(path, data, digest):
        entered.set()
        if not release.wait(5):
            raise OSError("controlled timeout")
        store_drawing(path, data, digest)

    with patch("app.modules.cnc.cnc_drawing_upload.service.store_drawing", side_effect=slow_store):
        task = asyncio.create_task(service.upload(request_id, file("part.step")))
        assert await asyncio.to_thread(entered.wait, 5)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert (await service.status(request_id)).state == "PENDING"
    result = await service.upload(request_id, file("part.step"))
    assert result.state == "READY" and not list(root.rglob("*.tmp"))
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(CncPartModel)) == 1


@pytest.mark.asyncio
async def test_same_key_concurrent_uploads_create_only_one_drawing(storage):
    sessions, root = storage
    service = DrawingUploadService(AuthSchema(user=CoreUserSchema(id=7)), sessions, root)
    request_id = uuid4()
    results = await asyncio.gather(*(service.upload(request_id, file("part.step")) for _ in range(3)))
    assert len({result.part_id for result in results}) == 1
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(CncPartModel)) == 1


@pytest.mark.asyncio
async def test_invalid_or_oversize_content_never_creates_part(storage):
    sessions, root = storage
    service = DrawingUploadService(AuthSchema(user=CoreUserSchema(id=7)), sessions, root)
    for name, content in [("../part.step", STEP), ("part.exe", STEP), ("part.step", b"bad"), ("part.stp", b"")]:
        with pytest.raises(CustomException):
            await service.upload(uuid4(), file(name, content))
    with patch.object(settings, "MAX_FILE_SIZE", len(STEP) - 1), pytest.raises(CustomException):
        await service.upload(uuid4(), file("part.step"))
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(CncPartModel)) == 0
    assert not root.exists()


@pytest.mark.asyncio
async def test_http_permissions_static_boundary_and_response(storage, tmp_path):
    sessions, root = storage
    permissions = ["module_ai:chat:query", "module_common:file:upload", "module_cnc:cnc_part:create", "module_cnc:cnc_part:detail"]
    app = FastAPI()
    app.include_router(DrawingUploadRouter, prefix="/cnc")
    static = tmp_path / "static"
    static.mkdir()
    app.mount("/static", StaticFiles(directory=static), name="static")
    handle_exception(app)

    async def actor():
        return AuthSchema(user=CoreUserSchema(id=7), permissions=permissions)

    app.dependency_overrides[get_current_user] = actor
    key = uuid4()
    with patch("app.modules.cnc.cnc_drawing_upload.controller.DrawingUploadService", side_effect=lambda auth: DrawingUploadService(auth, sessions, root)), patch("app.core.router_class._write_operation_log_async", new=AsyncMock()):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://local.test") as client:
            for missing in permissions[:3]:
                permissions.remove(missing)
                response = await client.post("/cnc/drawing-upload/step", data={"request_id": str(key)}, files={"file": ("part.step", STEP)})
                assert response.status_code == 403
                permissions.append(missing)
            response = await client.post("/cnc/drawing-upload/step", data={"request_id": str(key)}, files={"file": ("part.step", STEP)})
            assert response.status_code == 200, response.text
            data = response.json()["data"]
            assert set(data) == {"request_id", "state", "part_id", "sha256", "size_bytes"}
            assert (await client.get(f"/cnc/drawing-upload/status/{key}")).json()["data"] == data
            assert (await client.get(f"/static/{key}.step")).status_code == 404


def test_upload_migration_preserves_existing_tables_and_downgrades():
    path = Path(__file__).resolve().parents[3] / "app/alembic/versions/2026_10_29_1300_9c4f72e61029.py"
    spec = importlib.util.spec_from_file_location("drawing_upload_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "3a29b7e61029"
    engine = create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE TABLE cnc_part (id INTEGER PRIMARY KEY)")
            conn.exec_driver_sql("CREATE TABLE checkpoints (id INTEGER PRIMARY KEY)")
            module.op = Operations(MigrationContext.configure(conn))
            module.upgrade()
            assert "cnc_drawing_upload" in inspect(conn).get_table_names()
            module.downgrade()
            assert set(inspect(conn).get_table_names()) == {"cnc_part", "checkpoints"}
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_chat_references_verify_upload_owner_bytes_and_current_permission(storage, monkeypatch):
    """A chat turn receives only a ready, owned, unchanged drawing reference."""
    from contextlib import asynccontextmanager

    pytest.importorskip("langchain_core")
    pytest.importorskip("langgraph")
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    from langgraph.checkpoint.memory import InMemorySaver

    from app.modules.ai.agent.service import AgentService
    from app.modules.ai.chat import source_service
    from app.modules.ai.chat.model import SourceChatMessage, SourceChatSession
    from app.modules.ai.chat.source_repository import SourceChatRepository
    from app.modules.ai.chat.source_service import DrawingReferenceUnavailable, SourceChatService

    sessions, root = storage
    async with sessions.begin() as db:
        connection = await db.connection()
        await connection.run_sync(SourceChatSession.__table__.create)
        await connection.run_sync(SourceChatMessage.__table__.create)
        for actor_id in (7, 8):
            owner = await db.get(UserModel, actor_id)
            owner.is_superuser = True
            await SourceChatRepository(db, actor_id).create(f"session-{actor_id}", "test")

    owner_auth = AuthSchema(user=CoreUserSchema(id=7))
    other_auth = AuthSchema(user=CoreUserSchema(id=8))
    request_id = uuid4()
    uploaded = await DrawingUploadService(owner_auth, sessions, root).upload(request_id, file("part.step"))

    async def no_tools(_actor, _refresh, _sessions):
        return []

    @asynccontextmanager
    async def factory(_config):
        yield FakeListChatModel(responses=["answer"])

    async def refresh_owner():
        return owner_auth

    async def refresh_other():
        return other_auth

    monkeypatch.setattr(source_service, "build_read_tools", no_tools)
    monkeypatch.setattr(source_service, "DrawingUploadService", lambda auth, db: DrawingUploadService(auth, db, root))
    agent = AgentService(InMemorySaver(), model_factory=factory)
    owner = SourceChatService(owner_auth, agent, refresh_owner, sessions)
    other = SourceChatService(other_auth, agent, refresh_other, sessions)

    async def run(chat, session, turn):
        return [event async for event in chat.stream(
            session_id=session, turn_id=turn, message="", skills=[], model_config={}, drawing_uploads=[request_id]
        )]

    try:
        assert (await run(owner, "session-7", "first"))[-1].type == "turn.completed"
        async with sessions() as db:
            visible = await SourceChatRepository(db, 7).messages("session-7")
            assert f"图纸 ID: {uploaded.part_id}" in visible[0].content
            assert uploaded.sha256 in visible[0].content
            assert "不代表授权" in visible[0].content
            assert str(root) not in visible[0].content

        with pytest.raises(DrawingReferenceUnavailable):
            await run(other, "session-8", "foreign")

        drawing_path(root, 7, request_id, ".step").write_bytes(STEP.replace(b"HEADER", b"header"))
        with pytest.raises(DrawingReferenceUnavailable):
            await run(owner, "session-7", "tampered")

        async with sessions.begin() as db:
            current = await db.get(UserModel, 7)
            current.is_superuser = False
        with pytest.raises(PermissionError, match="PERMISSION_DENIED"):
            await run(owner, "session-7", "revoked")
    finally:
        await agent.close()
