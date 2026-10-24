"""STEP upload regressions; isolated HTTP/storage tests, no app DB or browser."""

import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import httpx
from fastapi import FastAPI, UploadFile

from app.common.enums import RET
from app.config.setting import settings
from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.dependencies import get_current_user
from app.core.exceptions import CustomException, handle_exception
from app.modules.common.file.controller import FileRouter
from app.modules.common.file.service import FileService
from app.utils.upload_util import UploadUtil

# Framing fixture only, intentionally no BREP/geometry claim.
STEP = b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;"


class StepUploadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "upload"
        root_patch = patch.object(settings, "UPLOAD_FILE_PATH", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    async def upload(self, name, content, **kwargs):
        file = UploadFile(filename=name, file=BytesIO(content), size=len(content))
        try:
            return await FileService.upload_service("https://app.example/", file, **kwargs)
        finally:
            await file.close()

    async def test_step_extensions_metadata_and_exact_storage(self):
        for extension in ("step", "stp", "STEP", "STP", "setp"):
            with self.subTest(extension=extension):
                result = await self.upload(f"零件.{extension}", STEP)
                path = Path(result.file_path)
                self.assertEqual(result.origin_name, f"零件.{extension}")
                self.assertEqual(path.suffix, "." + extension.lower())
                self.assertTrue(path.resolve().is_relative_to(self.root.resolve()))
                self.assertEqual(path.read_bytes(), STEP)
                self.assertNotIn("\\", result.file_path)
                self.assertNotIn("\\", result.file_url)
                # Upload API returns storage metadata, never extracted dimensions/units.
                self.assertNotIn("declared_unit", result.model_dump())

    async def test_reject_fake_empty_and_truncated_step_before_writing(self):
        for content in (b"", b"not a STEP", b"%PDF-1.7", STEP[:-1], b"END-ISO-10303-21;"):
            with self.subTest(content=content):
                with self.assertRaises(CustomException):
                    await self.upload("part.step", content)
        self.assertFalse(self.root.exists())

    async def test_allow_surrounding_whitespace_without_claiming_geometry(self):
        content = b" \n" + STEP + b"\r\n"
        result = await self.upload("part.stp", content)
        self.assertEqual(Path(result.file_path).read_bytes(), content)

    async def test_actual_bytes_enforce_limit_without_size_metadata(self):
        for declared_size in (None, 1):
            with self.subTest(declared_size=declared_size), patch.object(settings, "MAX_FILE_SIZE", len(STEP) - 1):
                file = UploadFile(filename="part.step", file=BytesIO(STEP), size=declared_size)
                try:
                    with self.assertRaises(CustomException):
                        await UploadUtil.upload_file(file, "https://app.example/")
                finally:
                    await file.close()
        self.assertFalse(self.root.exists())

    async def test_exact_limit_is_allowed_and_metadata_over_limit_rejected(self):
        with patch.object(settings, "MAX_FILE_SIZE", len(STEP)):
            result = await self.upload("exact.step", STEP)
            self.assertEqual(Path(result.file_path).read_bytes(), STEP)
            with self.assertRaises(CustomException):
                await self.upload("large.step", STEP + b" ")

    async def test_existing_non_cad_types_and_upload_directories(self):
        for name, content, upload_type, target in (
            ("avatar.png", b"\x89PNG\r\n\x1a\nimage", "avatar", None),
            ("photo.jpeg", b"\xff\xd8\xffimage", "file", None),
            ("animation.gif", b"GIF89aimage", "file", None),
            ("favicon.ico", b"\x00\x00\x01\x00image", "resource", None),
            ("legacy.xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1sheet", "file", None),
            ("param.jpg", b"\xff\xd8\xffimage", "param", None),
            ("book.xlsx", b"PK\x03\x04[Content_Types].xml", "file", None),
            ("icon.svg", b"<svg></svg>", "resource", "images/icons"),
        ):
            with self.subTest(name=name):
                result = await self.upload(name, content, upload_type=upload_type, target_path=target)
                path = Path(result.file_path)
                self.assertEqual(path.read_bytes(), content)
                self.assertIn(upload_type, path.parts)
                if target:
                    self.assertEqual(path.parent, self.root / "resource" / target)

    async def test_dangerous_extensions_and_paths_still_rejected(self):
        for name in ("run.py", "run.exe", "../part.step", "..\\part.stp"):
            with self.subTest(name=name), self.assertRaises(CustomException):
                await self.upload(name, STEP)
        with self.assertRaises(CustomException):
            await self.upload("part.step", STEP, upload_type="resource", target_path="../private")

    async def test_download_rejects_sibling_prefix_and_traversal(self):
        outside = Path(self.temp.name) / "upload_private"
        outside.mkdir()
        path = outside / "part.step"
        path.write_bytes(STEP)
        for value in (str(path), "../part.step"):
            with self.subTest(value=value), self.assertRaises(CustomException):
                await FileService.download_service(value)


class StepUploadPermissionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "upload"
        self.permissions = ["module_common:file:upload", "module_common:file:download"]
        self.authenticated = True
        app = FastAPI()
        app.include_router(FileRouter, prefix="/common")
        handle_exception(app)

        async def actor():
            if not self.authenticated:
                raise CustomException(msg="认证已失效", code=RET.UNAUTHORIZED.code)
            return AuthSchema(user=CoreUserSchema(id=7), permissions=self.permissions)

        # Synthetic actor only; real route dependencies and AuthPermission remain active.
        app.dependency_overrides[get_current_user] = actor
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://app.example")
        self.addAsyncCleanup(self.client.aclose)
        for item in (patch.object(settings, "UPLOAD_FILE_PATH", self.root), patch("app.core.router_class._write_operation_log_async", new=AsyncMock())):
            item.start()
            self.addCleanup(item.stop)

    async def test_authorized_route_round_trip_and_download_preserves_file(self):
        response = await self.client.post("/common/file/upload?upload_type=file", files={"file": ("part.STEP", STEP, "application/step")})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["origin_name"], "part.STEP")
        path = Path(data["file_path"])
        response = await self.client.post("/common/file/download", json={"file_path": str(path), "delete": False})
        self.assertEqual(response.content, STEP)
        self.assertTrue(path.exists())

    async def test_invalid_step_rejected_by_route_without_storing_file(self):
        response = await self.client.post("/common/file/upload", files={"file": ("part.stp", b"not STEP")})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.root.exists())

    async def test_missing_upload_and_download_permissions_deny_real_routes(self):
        for missing, operation in (("module_common:file:upload", "upload"), ("module_common:file:download", "download")):
            self.permissions = [p for p in ("module_common:file:upload", "module_common:file:download") if p != missing]
            if operation == "upload":
                response = await self.client.post("/common/file/upload", files={"file": ("part.step", STEP)})
            else:
                response = await self.client.post("/common/file/download", json={"file_path": "private.step", "delete": False})
            self.assertEqual(response.status_code, 403, response.text)
        self.assertFalse(self.root.exists())

    async def test_unauthenticated_actor_does_not_store_upload(self):
        self.authenticated = False
        response = await self.client.post("/common/file/upload", files={"file": ("part.step", STEP)})
        self.assertEqual(response.status_code, 401)
        self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()
