"""Offline negative checks; synthetic STEP declarations never modify source CAD."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from validate_inputs import Sample, check_config, check_sample


def draft_config() -> dict:
    return {
        "platform_code": "xometry_us",
        "provider_group": "xometry",
        "schema_version": "future-local-version",
        "config_version": "future-config-version",
        "lifecycle": "draft",
        "automation_enabled": False,
        "policy": {
            "forbidden_actions": ["purchase", "checkout", "place_order", "payment", "change_account_security"],
            "unknown_option": "reject",
            "missing_required": "stop_and_report",
            "silent_substitution": False,
        },
        "quote_extraction": {"raw_material_price_is_quote": False},
        "readiness": {"live_quote": "verified"},
    }


class InputChecksTest(unittest.TestCase):
    def test_same_size_tampering_fails_identity_check(self):
        original = b"#1=(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.));\nA"
        sample = Sample("A", "synthetic.step", len(original), hashlib.sha256(original).hexdigest())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / sample.filename
            path.write_bytes(original[:-1] + b"B")
            checks = {check.name: check.status for check in check_sample(sample, path)}
        self.assertEqual(checks["sample.A.size"], "PASS")
        self.assertEqual(checks["sample.A.sha256"], "FAIL")

    def test_non_mm_declaration_fails_even_when_identity_matches(self):
        content = b"#1=(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT($,.METRE.));"
        sample = Sample("A", "synthetic.step", len(content), hashlib.sha256(content).hexdigest())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / sample.filename
            path.write_bytes(content)
            checks = {check.name: check.status for check in check_sample(sample, path)}
        self.assertEqual(checks["sample.A.sha256"], "PASS")
        self.assertEqual(checks["sample.A.unit"], "FAIL")

    def test_cross_platform_identity_is_rejected(self):
        for field, value in (("platform_code", "rapiddirect"), ("provider_group", "rapiddirect")):
            with self.subTest(field=field):
                config = draft_config()
                config[field] = value
                checks = {check.name: check.status for check in check_config("xometry_us", config, "future-local-version")}
                self.assertEqual(checks["xometry_us.identity"], "FAIL")

    def test_jlc_cannot_reuse_another_provider_group(self):
        config = draft_config()
        config["platform_code"] = "jlc_cnc_cn"
        config["provider_group"] = "jlc"
        matching = {check.name: check.status for check in check_config("jlc_cnc_cn", config, "future-local-version")}
        self.assertEqual(matching["jlc_cnc_cn.identity"], "PASS")
        for group in ("xometry", "rapiddirect"):
            with self.subTest(provider_group=group):
                config["provider_group"] = group
                checks = {check.name: check.status for check in check_config("jlc_cnc_cn", config, "future-local-version")}
                self.assertEqual(checks["jlc_cnc_cn.identity"], "FAIL")

    def test_draft_cannot_enable_automation_or_drop_payment_guard(self):
        config = draft_config()
        config["automation_enabled"] = True
        config["policy"]["forbidden_actions"].remove("payment")
        checks = {check.name: check.status for check in check_config("xometry_us", config, "future-local-version")}
        self.assertEqual(checks["xometry_us.draft"], "FAIL")
        self.assertEqual(checks["xometry_us.forbidden_actions"], "FAIL")

    def test_draft_and_claimed_live_quote_never_establish_live_readiness(self):
        checks = {check.name: check.status for check in check_config("xometry_us", draft_config(), "future-local-version")}
        self.assertEqual(checks["xometry_us.schema_version"], "PASS")
        self.assertEqual(checks["xometry_us.draft"], "PASS")
        self.assertEqual(checks["xometry_us.live_readiness"], "NOT_ASSESSED")


if __name__ == "__main__":
    unittest.main()
