import unittest
from types import SimpleNamespace

from app.config.path_conf import STATIC_DIR
from app.modules.cnc.cnc_quote_result.evidence import (
    ensure_private_evidence_dir,
    resolve_evidence_path,
    store_private_evidence,
)


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
