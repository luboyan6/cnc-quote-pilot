import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config.path_conf import STATIC_DIR
from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.dependencies import db_getter, get_current_user
from app.core.exceptions import CustomException, handle_exception
from app.modules.cnc.cnc_quote_result import evidence
from app.modules.cnc.cnc_quote_result.controller import CncQuoteResultRouter, get_screenshot_controller
from app.modules.cnc.cnc_quote_result.evidence import (
    ensure_private_evidence_dir,
    resolve_evidence_path,
    store_private_evidence,
)
from app.modules.cnc.cnc_quote_result.model import CncQuoteResultModel


class TestEvidence(unittest.TestCase):
    def setUp(self):
        ensure_private_evidence_dir()

    def test_store_and_resolve_private_evidence(self):
        ev_id = "test-ev-12345"
        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        path = store_private_evidence(ev_id, dummy_png)
        self.assertTrue(path.exists())

        row = SimpleNamespace(
            evidence_id=ev_id,
            evidence_screenshot=None,
        )
        resolved = resolve_evidence_path(row)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved, path)

        # Cleanup
        if path.exists():
            path.unlink()

    def test_resolve_evidence_path_prevents_path_traversal(self):
        # 1. Traversal via evidence_id
        row_traversal_id = SimpleNamespace(
            evidence_id="../../secret",
            evidence_screenshot=None,
        )
        # Even with ../, Path.name strips to "secret" and remains strictly inside PRIVATE_EVIDENCE_DIR
        resolved_id = resolve_evidence_path(row_traversal_id)
        # Should not resolve to an out-of-boundary file
        self.assertIsNone(resolved_id)

        # 2. Traversal via evidence_screenshot
        row_traversal_rel = SimpleNamespace(
            evidence_id=None,
            evidence_screenshot="../../etc/passwd",
        )
        resolved_rel = resolve_evidence_path(row_traversal_rel)
        self.assertIsNone(resolved_rel)

    def test_legacy_screenshot_fallback_within_static_allowed(self):
        # Create temporary file inside static
        static_test = STATIC_DIR / "temp_evidence_test.png"
        STATIC_DIR.mkdir(parents=True, exist_ok=True)
        static_test.write_bytes(b"LEGACY_SCREENSHOT")

        try:
            row = SimpleNamespace(
                evidence_id=None,
                evidence_screenshot="static/temp_evidence_test.png",
            )
            resolved = resolve_evidence_path(row)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved, static_test.resolve())
        finally:
            if static_test.exists():
                static_test.unlink()


@pytest.mark.asyncio
async def test_private_only_screenshot_never_falls_back_to_legacy_path(tmp_path, monkeypatch):
    private = tmp_path / "private"
    public = tmp_path / "static"
    private.mkdir()
    public.mkdir()
    (private / "proof.png").write_bytes(b"private-image")
    (public / "old.png").write_bytes(b"legacy-image")
    monkeypatch.setattr(evidence, "PRIVATE_EVIDENCE_DIR", private)
    monkeypatch.setattr(evidence, "STATIC_DIR", public)
    monkeypatch.setattr(evidence, "BASE_DIR", tmp_path)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(CncQuoteResultModel.__table__.create)
        async with sessions.begin() as db:
            db.add(CncQuoteResultModel(id=1, created_id=7, evidence_id="proof", evidence_state="available", evidence_screenshot="static/old.png"))
        owner = AuthSchema(user=CoreUserSchema(id=7))
        other = AuthSchema(user=CoreUserSchema(id=8))
        async with sessions() as db:
            response = await get_screenshot_controller(owner, 1, db, private_only=True)
            assert response.path == private / "proof.png"
            with pytest.raises(CustomException) as denied:
                await get_screenshot_controller(other, 1, db, private_only=True)
            assert denied.value.code == 403
            (private / "proof.png").unlink()
            with pytest.raises(CustomException) as missing:
                await get_screenshot_controller(owner, 1, db, private_only=True)
            assert missing.value.code == 404
            legacy = await get_screenshot_controller(owner, 1, db, private_only=False)
            assert legacy.path == public / "old.png"
        (private / "proof.png").write_bytes(b"private-image")
        app = FastAPI()
        app.include_router(CncQuoteResultRouter)
        handle_exception(app)

        async def current():
            return AuthSchema(user=CoreUserSchema(id=7), permissions=["module_cnc:cnc_quote_result:query"])

        async def database():
            async with sessions() as db:
                yield db

        app.dependency_overrides[get_current_user] = current
        app.dependency_overrides[db_getter] = database
        with patch("app.core.router_class._write_operation_log_async", new=AsyncMock()):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/cnc_quote_result/screenshot/1", params={"private_only": True})
                assert response.status_code == 200 and response.content == b"private-image"
                assert "no-store" in response.headers["cache-control"]
                (private / "proof.png").unlink()
                missing = await client.get("/cnc_quote_result/screenshot/1", params={"private_only": True})
                assert missing.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_history_endpoint_accepts_no_filters():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(CncQuoteResultModel.__table__.create)
        async with sessions.begin() as db:
            db.add(CncQuoteResultModel(id=1, created_id=7, part_id=42, quote_status="QUOTED", unit_price=Decimal("12.34")))
        app = FastAPI()
        app.include_router(CncQuoteResultRouter)
        handle_exception(app)

        async def current():
            return AuthSchema(user=CoreUserSchema(id=7), permissions=["module_cnc:cnc_quote_result:query"])

        async def database():
            async with sessions() as db:
                yield db

        app.dependency_overrides[get_current_user] = current
        app.dependency_overrides[db_getter] = database
        with patch("app.core.router_class._write_operation_log_async", new=AsyncMock()):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/cnc_quote_result/history-prices")
                assert response.status_code == 200
                assert [item["id"] for item in response.json()["data"]] == [1]
                assert (await client.get("/cnc_quote_result/history-prices", params={"part_id": 43})).json()["data"] == []
                assert (await client.get("/cnc_quote_result/list")).json()["data"]["total"] == 1
                assert (await client.get("/cnc_quote_result/stats")).json()["data"]["total_quotes"] == 1
    finally:
        await engine.dispose()
