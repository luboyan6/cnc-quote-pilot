"""Source chat ownership, tombstones and visible projection in isolated SQLite."""

import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.ai.chat.model import SourceChatMessage, SourceChatSession
from app.modules.ai.chat.source_repository import SourceChatRepository, VisibleMessage


@pytest.mark.asyncio
async def test_numeric_ownership_projection_repair_and_deletion_barrier():
    engine = create_async_engine("sqlite+aiosqlite://")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SourceChatSession.__table__.create)
            await conn.run_sync(SourceChatMessage.__table__.create)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        first = VisibleMessage("checkpoint-human-1", "user", "hello", 0)
        second = VisibleMessage("checkpoint-assistant-1", "assistant", "world", 1)

        async with sessions.begin() as db:
            owner = SourceChatRepository(db, 101)
            await owner.create("source-session", "First session")
            await owner.project("source-session", [first, second])
        async with sessions.begin() as db:
            owner = SourceChatRepository(db, 101)
            await owner.project("source-session", [first, second])
            assert [(m.role, m.content) for m in await owner.messages("source-session")] == [("user", "hello"), ("assistant", "world")]
            assert (await owner.page(offset=0, limit=10))[1] == 1
            assert await owner.rename("source-session", "Renamed")
            assert (await owner.page(offset=0, limit=10, title="named"))[1] == 1

            other = SourceChatRepository(db, 202)
            assert await other.get("source-session") is None
            assert (await other.page(offset=0, limit=10))[1] == 0
            assert not await other.rename("source-session", "stolen")
            with pytest.raises(LookupError, match="CHAT_SESSION_UNAVAILABLE"):
                await other.messages("source-session")
            with pytest.raises(LookupError, match="CHAT_SESSION_UNAVAILABLE"):
                await other.project("source-session", [first])
            enriched = VisibleMessage("checkpoint-assistant-1", "assistant", "world", 1, (42,))
            await owner.project("source-session", [first, enriched])
            await owner.project("source-session", [first, enriched])
            assert (await owner.messages("source-session"))[1].evidence_result_ids == [42]
            with pytest.raises(ValueError, match="INVALID_CHAT_PROJECTION"):
                await owner.project("source-session", [VisibleMessage("checkpoint-human-1", "user", "hello", 0, (42,))])
        async with sessions.begin() as db:
            owner = SourceChatRepository(db, 101)
            with pytest.raises(ValueError, match="CHAT_PROJECTION_CONFLICT"):
                await owner.project("source-session", [VisibleMessage("checkpoint-human-1", "user", "changed", 0)])
            assert await owner.delete("source-session")
            assert await owner.get("source-session") is None
            with pytest.raises(LookupError, match="CHAT_SESSION_UNAVAILABLE"):
                await owner.project("source-session", [first])
        async with sessions() as db:
            with pytest.raises(IntegrityError):
                await SourceChatRepository(db, 202).create("source-session", "resurrected")
            await db.rollback()
    finally:
        await engine.dispose()


def test_migration_preserves_unrelated_tables_and_is_reversible():
    path = Path(__file__).resolve().parents[3] / "app/alembic/versions/2026_10_29_1200_3a29b7e61029.py"
    spec = importlib.util.spec_from_file_location("source_chat_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "f6b3e1c91028"
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE TABLE checkpoints (id INTEGER PRIMARY KEY)")
            module.op = Operations(MigrationContext.configure(conn))
            module.upgrade()
            assert {"ai_source_chat_session", "ai_source_chat_message", "checkpoints"}.issubset(inspect(conn).get_table_names())
            assert {"owner_id", "deleted_at"}.issubset({column["name"] for column in inspect(conn).get_columns("ai_source_chat_session")})
            module.downgrade()
            assert inspect(conn).get_table_names() == ["checkpoints"]
    finally:
        engine.dispose()


def test_evidence_projection_migration_preserves_rows_and_blocks_lossy_downgrade():
    path = Path(__file__).resolve().parents[3] / "app/alembic/versions/2026_10_30_1000_a816e3b61030.py"
    spec = importlib.util.spec_from_file_location("source_evidence_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "9c4f72e61029"
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE TABLE ai_source_chat_message (session_id TEXT, source_id TEXT, content TEXT)")
            conn.exec_driver_sql("INSERT INTO ai_source_chat_message VALUES ('s', 'm', 'kept')")
            module.op = Operations(MigrationContext.configure(conn))
            module.upgrade()
            assert conn.exec_driver_sql("SELECT content, evidence_result_ids FROM ai_source_chat_message").one() == ("kept", None)
            conn.exec_driver_sql("UPDATE ai_source_chat_message SET evidence_result_ids = '[42]'")
            with pytest.raises(RuntimeError, match="SOURCE_EVIDENCE_PROJECTION_NOT_EMPTY"):
                module.downgrade()
            assert "evidence_result_ids" in {item["name"] for item in inspect(conn).get_columns("ai_source_chat_message")}
            conn.exec_driver_sql("UPDATE ai_source_chat_message SET evidence_result_ids = NULL")
            module.downgrade()
            assert conn.exec_driver_sql("SELECT content FROM ai_source_chat_message").scalar_one() == "kept"
    finally:
        engine.dispose()


@pytest.mark.skipif(not os.environ.get("CNC_TEST_AGENT_PG_DSN"), reason="Disposable PostgreSQL DSN not supplied")
def test_evidence_projection_migration_on_disposable_postgres():
    dsn = os.environ["CNC_TEST_AGENT_PG_DSN"]
    if not dsn.startswith("postgresql://"):
        raise ValueError("CNC_TEST_AGENT_PG_DSN must use postgresql://")
    schema = "agent_evidence_" + uuid4().hex
    engine = create_engine(dsn.replace("postgresql://", "postgresql+psycopg://", 1), hide_parameters=True)
    path = Path(__file__).resolve().parents[3] / "app/alembic/versions/2026_10_30_1000_a816e3b61030.py"
    spec = importlib.util.spec_from_file_location("source_evidence_postgres_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            conn.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
            conn.exec_driver_sql("CREATE TABLE ai_source_chat_message (session_id TEXT, source_id TEXT, content TEXT)")
            conn.exec_driver_sql("INSERT INTO ai_source_chat_message VALUES ('s', 'm', 'kept')")
            module.op = Operations(MigrationContext.configure(conn))
            module.upgrade()
            assert conn.exec_driver_sql("SELECT content, evidence_result_ids FROM ai_source_chat_message").one() == ("kept", None)
            conn.exec_driver_sql("UPDATE ai_source_chat_message SET evidence_result_ids = '[42]'")
            with pytest.raises(RuntimeError, match="SOURCE_EVIDENCE_PROJECTION_NOT_EMPTY"):
                module.downgrade()
            conn.exec_driver_sql("UPDATE ai_source_chat_message SET evidence_result_ids = NULL")
            module.downgrade()
            assert conn.exec_driver_sql("SELECT content FROM ai_source_chat_message").scalar_one() == "kept"
    finally:
        with engine.begin() as conn:
            conn.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        engine.dispose()
