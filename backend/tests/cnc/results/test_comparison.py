import unittest
from decimal import Decimal

from app.modules.cnc.cnc_quote_result.comparison import (
    build_comparison_key,
    compute_price_diff_and_rate,
)


class TestComparison(unittest.TestCase):
    def test_build_comparison_key_deterministic_and_canonical(self):
        k1 = build_comparison_key(
            platform_code="jlc_cnc_cn",
            account_condition=10,
            file_sha256="abc123def456",
            quantity=2,
            currency="CNY",
            price_scope="unit",
            quote_kind="QUOTED",
            material="AL6061",
            surface_finish="Sandblasting",
            extra_params={"tolerance": "ISO 2768-m", "_internal": "skip"},
        )
        k2 = build_comparison_key(
            platform_code="JLC_CNC_CN ",
            account_condition=10,
            file_sha256="ABC123DEF456",
            quantity=2,
            currency="cny",
            price_scope="UNIT",
            quote_kind="quoted",
            material="al6061",
            surface_finish="sandblasting",
            extra_params={"tolerance": "ISO 2768-m"},
        )
        self.assertIsNotNone(k1)
        self.assertEqual(k1, k2)

    def test_build_comparison_key_rejects_missing_or_invalid_dimensions(self):
        # Missing currency
        self.assertIsNone(
            build_comparison_key(
                platform_code="jlc_cnc_cn",
                account_condition=10,
                file_sha256="abc",
                quantity=1,
                currency=None,
                price_scope="unit",
                quote_kind="QUOTED",
                material="AL6061",
            )
        )
        # FAILED or CANCELLED status cannot form comparable series
        self.assertIsNone(
            build_comparison_key(
                platform_code="jlc_cnc_cn",
                account_condition=10,
                file_sha256="abc",
                quantity=1,
                currency="CNY",
                price_scope="unit",
                quote_kind="FAILED",
                material="AL6061",
            )
        )

    def test_distinct_conditions_produce_distinct_keys(self):
        base = dict(
            platform_code="jlc_cnc_cn",
            account_condition=10,
            file_sha256="abc",
            quantity=1,
            currency="CNY",
            price_scope="unit",
            quote_kind="QUOTED",
            material="AL6061",
        )
        k_qty1 = build_comparison_key(**base)
        k_qty2 = build_comparison_key(**{**base, "quantity": 5})
        k_currency_usd = build_comparison_key(**{**base, "currency": "USD"})
        k_ref_estimate = build_comparison_key(**{**base, "quote_kind": "REFERENCE_ESTIMATE"})

        self.assertNotEqual(k_qty1, k_qty2)
        self.assertNotEqual(k_qty1, k_currency_usd)
        self.assertNotEqual(k_qty1, k_ref_estimate)

    def test_compute_price_diff_and_rate(self):
        # 1. Normal increase: 100 -> 120 (+20, +0.2000)
        diff, rate = compute_price_diff_and_rate(Decimal("120.00"), Decimal("100.00"))
        self.assertEqual(diff, "+20.0000")
        self.assertEqual(rate, "+0.2000")

        # 2. Normal decrease: 100 -> 85.50 (-14.50, -0.1450)
        diff, rate = compute_price_diff_and_rate("85.50", "100.00")
        self.assertEqual(diff, "-14.5000")
        self.assertEqual(rate, "-0.1450")

        # 3. Same price: 100 -> 100 (0.0000, 0.0000)
        diff, rate = compute_price_diff_and_rate(100, 100)
        self.assertEqual(diff, "+0.0000")
        self.assertEqual(rate, "+0.0000")

        # 4. Previous is 0: rate must be None to prevent division by zero
        diff, rate = compute_price_diff_and_rate("50.00", "0")
        self.assertEqual(diff, "+50.0000")
        self.assertIsNone(rate)

        # 5. Missing values
        diff, rate = compute_price_diff_and_rate(None, "100")
        self.assertIsNone(diff)
        self.assertIsNone(rate)
