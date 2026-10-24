"""Actual upload-to-quote file boundary; isolated storage/DB, no provider I/O."""

import hashlib
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from _quote_support import Part, QuoteDatabase
from fastapi import UploadFile
from sqlalchemy import update

from app.config.setting import settings
from app.core.exceptions import CustomException
from app.modules.cnc.browser.errors import BrowserStop, Reason
from app.modules.cnc.browser.files import upload_step
from app.modules.cnc.quote.contracts import QuoteError
from app.modules.cnc.quote.repository import SOURCE_FILE_LIMIT, source_file
from app.modules.common.file.service import FileService

# Part 21 physical-file syntax only; no solid geometry/manufacturability claim.
STEP = (
    b"ISO-10303-21;\nHEADER;\n"
    b"FILE_DESCRIPTION(('Boundary fixture'),'2;1');\n"
    b"FILE_NAME('fixture.setp','2026-10-23T00:00:00',('fixture'),('fixture'),'test','test','');\n"
    b"FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));\nENDSEC;\nDATA;\n"
    b"#1=CARTESIAN_POINT('boundary',(0.,0.,0.));\nENDSEC;\nEND-ISO-10303-21;"
)


class StepFileBoundaryTests(QuoteDatabase):
    async def upload(self, name, content):
        file = UploadFile(filename=name, file=BytesIO(content), size=len(content))
        try:
            with patch.object(settings, "UPLOAD_FILE_PATH", self.root / "upload"):
                return await FileService.upload_service("https://app.example/", file)
        finally:
            await file.close()

    async def test_uploaded_step_aliases_freeze_reverify_and_send_exact_bytes(self):
        for extension in ("step", "STP", "setp", "SETP"):
            with self.subTest(extension=extension):
                original_name = f"fixture.{extension}"
                uploaded = await self.upload(original_name, STEP)
                stored = Path(uploaded.file_path)
                self.assertEqual(uploaded.origin_name, original_name)
                self.assertEqual(stored.suffix, "." + extension.lower())
                # The UI stores the original extension; old callers can include a dot.
                metadata_extension = extension if extension != "SETP" else ".SETP"
                async with self.sessions() as db, db.begin():
                    await db.execute(update(Part).values(file_path=uploaded.file_path, file_name=original_name, extension=metadata_extension, size_bytes=len(STEP)))
                snapshot = await self.repo.snapshot(self.auth, 5, 31)
                self.assertEqual(snapshot.file_name, original_name)
                self.assertEqual(snapshot.step.path, stored.resolve())
                self.assertEqual(snapshot.payload.buffer, STEP)
                self.assertEqual(snapshot.payload.sha256, hashlib.sha256(STEP).hexdigest())
                await self.repo.validate(self.auth, snapshot)
                self.assertEqual(snapshot.step.read_verified(), snapshot.payload)
                self.assertTrue(stored.exists())

                # Same-size disk tampering cannot pass the frozen identity check.
                stored.write_bytes(STEP.replace(b"HEADER", b"FOOTER"))
                with self.assertRaises(BrowserStop) as error:
                    await self.repo.validate(self.auth, snapshot)
                self.assertEqual(error.exception.reason, Reason.FILE_INVALID)
                locator = AsyncMock()
                await upload_step(locator, snapshot.payload)
                locator.set_input_files.assert_awaited_once_with({"name": "part.step", "mimeType": "application/step", "buffer": STEP})
                self.assertNotIn(str(self.root), repr(locator.set_input_files.call_args))

    async def test_invalid_setp_uploads_fail_before_storage(self):
        for extension in ("setp", "SETP"):
            for content in (b"", b"not STEP", b"%PDF-1.7", STEP[:-1], b"END-ISO-10303-21;"):
                with self.subTest(extension=extension, content=content), self.assertRaises(CustomException):
                    await self.upload(f"fixture.{extension}", content)
        self.assertFalse((self.root / "upload").exists())

    async def test_quote_rejects_non_step_suffix_or_metadata_even_with_valid_bytes(self):
        path = self.root / "fixture.setp"
        path.write_bytes(STEP)
        part = SimpleNamespace(upload_authorized=True, validation_status="HEADER_VALID", extension="setp", file_path=str(path), size_bytes=len(STEP))
        for extension in ("pdf", "txt", "setp.exe", None):
            with self.subTest(metadata=extension), self.assertRaisesRegex(QuoteError, "FILE_INVALID"):
                source_file(SimpleNamespace(**{**vars(part), "extension": extension}), self.root)
        for suffix in (".txt", ".setp.txt", ".exe"):
            invalid = path.with_suffix(suffix)
            invalid.write_bytes(STEP)
            with self.subTest(suffix=suffix), self.assertRaisesRegex(QuoteError, "FILE_INVALID"):
                source_file(SimpleNamespace(**{**vars(part), "file_path": str(invalid)}), self.root)

    async def test_setp_preserves_authorization_root_framing_size_and_hash_guards(self):
        path = self.root / "fixture.setp"
        path.write_bytes(STEP)
        part = SimpleNamespace(upload_authorized=True, validation_status="HEADER_VALID", extension="setp", file_path=str(path), size_bytes=len(STEP))
        with self.assertRaisesRegex(QuoteError, "THIRD_PARTY_UPLOAD_NOT_AUTHORIZED"):
            source_file(SimpleNamespace(**{**vars(part), "upload_authorized": False}), self.root)
        for changed in ({"validation_status": "REJECTED"}, {"size_bytes": 0}, {"size_bytes": len(STEP) - 1}, {"size_bytes": SOURCE_FILE_LIMIT + 1}):
            with self.subTest(changed=changed), self.assertRaisesRegex(QuoteError, "FILE_INVALID"):
                source_file(SimpleNamespace(**{**vars(part), **changed}), self.root)
        sibling = self.root / "other-root"
        sibling.mkdir()
        with self.assertRaisesRegex(QuoteError, "FILE_INVALID"):
            source_file(part, sibling)
        step, _ = source_file(part, self.root)
        for changed in ({"expected_sha256": "0" * 64}, {"expected_size": len(STEP) - 1}, {"max_size": len(STEP) - 1}, {"root": sibling}):
            with self.subTest(changed=changed), self.assertRaises(BrowserStop) as error:
                replace(step, **changed).read_verified()
            self.assertEqual(error.exception.reason, Reason.FILE_INVALID)
        for content in (b"not STEP", b"%PDF-1.7", STEP[:-1], b"END-ISO-10303-21;"):
            path.write_bytes(content)
            invalid = SimpleNamespace(**{**vars(part), "size_bytes": len(content)})
            with self.subTest(content=content), self.assertRaisesRegex(QuoteError, "FILE_INVALID"):
                source_file(invalid, self.root)
            with self.subTest(content=content), self.assertRaises(BrowserStop) as error:
                replace(step, expected_size=len(content), expected_sha256=hashlib.sha256(content).hexdigest()).read_verified()
            self.assertEqual(error.exception.reason, Reason.FILE_INVALID)
