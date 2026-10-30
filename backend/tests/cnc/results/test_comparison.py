import unittest
from decimal import Decimal

from app.modules.cnc.cnc_quote_result.comparison import (
    COMPARISON_RULE_VERSION,
    build_comparison_key,
    compute_price_diff_and_rate,
)


def complete_conditions() -> dict:
    return {
        "platform_code": "jlc_cnc_cn",
        "account_condition": 10,
        "file_sha256": "ab" * 32,
        "quantity": 2,
        "currency": "CNY",
        "price_scope": "unit",
        "quote_kind": "QUOTED",
        "material": "AL6061",
        "surface_finish": "Sandblasting",
        "extra_params": {"tolerance": "ISO 2768-m"},
        "lead_time_tier": "5 days",
        "tax_included": True,
        "shipping_included": False,
        "discount_amount": Decimal("0.00"),
    }


class TestComparison(unittest.TestCase):
    def test_build_comparison_key_deterministic_and_canonical(self):
        conditions = complete_conditions()
        first = build_comparison_key(**conditions)
        canonical_variant = {
            **conditions,
            "platform_code": "JLC_CNC_CN ",
            "file_sha256": "AB" * 32,
            "currency": "cny",
            "price_scope": "UNIT",
            "quote_kind": "quoted",
            "material": "al6061",
            "surface_finish": "sandblasting",
            "extra_params": {"tolerance": "ISO 2768-m", "_internal": "ignored"},
            "discount_amount": Decimal("0"),
        }
        self.assertIsNotNone(first)
        self.assertEqual(first, build_comparison_key(**canonical_variant))

    def test_missing_or_invalid_conditions_cannot_form_a_key(self):
        conditions = complete_conditions()
        missing = {
            "platform_code": [None, "unknown", "   "],
            "account_condition": [None, "  ", 0, True],
            "file_sha256": [None, "abc", "g" * 64],
            "quantity": [None, 0, -1, True, 1.5],
            "currency": [None, "  ", "UNKNOWN", "UNK", "XXX"],
            "price_scope": [None, "", "unknown"],
            "quote_kind": [None, "FAILED"],
            "material": [None, "   "],
            "extra_params": [None, {"tolerance": None}, {"tolerance": "  "}, {"tolerance": {"unclear": True}}, {"roughness": float("nan")}],
            "lead_time_tier": [None, "   "],
            "tax_included": [None],
            "shipping_included": [None],
            "discount_amount": [None, "NaN", "-1"],
            "version": [COMPARISON_RULE_VERSION - 1],
        }
        for field, values in missing.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    self.assertIsNone(build_comparison_key(**{**conditions, field: value}))

    def test_distinct_technical_and_commercial_conditions_produce_distinct_keys(self):
        conditions = complete_conditions()
        base_key = build_comparison_key(**conditions)
        self.assertIsNotNone(base_key)
        variants = {
            "file_sha256": "cd" * 32,
            "material": "AL7075",
            "quantity": 5,
            "currency": "USD",
            "price_scope": "line",
            "quote_kind": "REFERENCE_ESTIMATE",
            "lead_time_tier": "10 days",
            "tax_included": False,
            "shipping_included": True,
            "discount_amount": Decimal("2.50"),
        }
        for field, value in variants.items():
            with self.subTest(field=field):
                self.assertNotEqual(base_key, build_comparison_key(**{**conditions, field: value}))

    def test_compute_price_diff_and_rate(self):
        self.assertEqual(compute_price_diff_and_rate(Decimal("120.00"), Decimal("100.00")), ("+20.0000", "+0.2000"))
        self.assertEqual(compute_price_diff_and_rate("85.50", "100.00"), ("-14.5000", "-0.1450"))
        self.assertEqual(compute_price_diff_and_rate(100, 100), ("+0.0000", "+0.0000"))
        self.assertEqual(compute_price_diff_and_rate("50.00", "0"), ("+50.0000", None))
        self.assertEqual(compute_price_diff_and_rate(None, "100"), (None, None))
