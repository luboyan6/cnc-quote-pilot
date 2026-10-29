"""Unit tests for XometryQuoteService."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.cnc.quote.xometry_quote_service import (
    XometryAccount,
    XometryQuoteError,
    XometryQuoteService,
    execute_xometry_quote,
    map_to_xometry_parameters,
    quote_part_config,
)


class TestXometryQuoteService(unittest.IsolatedAsyncioTestCase):
    def test_class_structure_and_method_exports(self):
        """验证 XometryQuoteService 类结构与两个方法命名。"""
        self.assertTrue(hasattr(XometryQuoteService, "execute_xometry_quote"))
        self.assertTrue(hasattr(XometryQuoteService, "quote_part_config"))
        self.assertTrue(callable(XometryQuoteService.execute_xometry_quote))
        self.assertTrue(callable(XometryQuoteService.quote_part_config))
        # 验证模块级别名导出一致性
        self.assertEqual(execute_xometry_quote, XometryQuoteService.execute_xometry_quote)
        self.assertEqual(quote_part_config, XometryQuoteService.quote_part_config)

    def test_map_to_xometry_parameters(self):
        """验证中文与标准图纸参数到 Xometry 英文选项的映射能力。"""
        # 1. 铝合金-6061
        res1 = map_to_xometry_parameters(
            material="铝合金-6061",
            surface_finish="本色阳极氧化",
            tolerance="GB/T 1804-2000 m级",
            roughness="125uin/3.2um Ra",
        )
        self.assertEqual(res1["material"], "Aluminum 6061-T6x (Best Available)")
        self.assertEqual(res1["surface_finish"], "Clear Anodize")
        self.assertIn("0.13mm", res1["tolerance"])
        self.assertEqual(res1["roughness"], "125uin/3.2um Ra")

        # 2. 45#钢 + 钝化 + 严格外观
        res2 = map_to_xometry_parameters(
            material="45#钢",
            surface_finish="钝化",
            tolerance="精密",
            roughness="严格外观",
        )
        self.assertEqual(res2["material"], "Steel 1018")
        self.assertEqual(res2["surface_finish"], "Passivate")
        self.assertIn("tighter than", res2["tolerance"])
        self.assertEqual(res2["roughness"], "63uin/1.6um Ra")

        # 3. 304不锈钢 + 发黑
        res3 = map_to_xometry_parameters(
            material="304不锈钢",
            surface_finish="发黑",
        )
        self.assertEqual(res3["material"], "Stainless Steel 304/304L")
        self.assertEqual(res3["surface_finish"], "Black Oxide")

    async def test_execute_xometry_quote_validation(self):
        """验证 execute_xometry_quote 输入校验与异常抛出。"""
        account = XometryAccount(
            id=1,
            owner_id=1,
            username="test@example.com",
            password="pwd",
            login_url="https://xometry.com/login",
            quote_url="https://www.xometry.com/quoting/home/",
        )
        # 数量非法
        with self.assertRaises(XometryQuoteError) as cm:
            await XometryQuoteService.execute_xometry_quote(
                account,
                file_name="part.step",
                quantity=0,
            )
        self.assertEqual(str(cm.exception), "QUOTE_INPUT_INVALID")

        # 缺少账号
        with self.assertRaises(XometryQuoteError) as cm:
            await XometryQuoteService.execute_xometry_quote(
                file_name="part.step",
                quantity=1,
                account=None,
            )
        self.assertEqual(str(cm.exception), "ACCOUNT_REQUIRED")

    async def test_quote_part_config_uses_shared_account_fenced_service(self):
        """Legacy calls must retain the selected account and frozen override."""
        auth = MagicMock()
        db = MagicMock()
        with patch("app.modules.cnc.quote.instant.quote_config", new_callable=AsyncMock) as shared:
            shared.return_value = {"config_id": 10, "run_id": "durable-run", "quote_status": "QUOTED"}
            result = await XometryQuoteService.quote_part_config(auth, db, config_id=10, account_id=91, quantity_override=5, lead_time_pref="Fastest")
            self.assertEqual(result["run_id"], "durable-run")
            shared.assert_awaited_once_with(
                auth,
                db,
                10,
                account_id=91,
                quantity_override=5,
                lead_time_pref="Fastest",
                export_controlled=None,
                quote_id=None,
                expected_provider="xometry_us",
            )


if __name__ == "__main__":
    unittest.main()
