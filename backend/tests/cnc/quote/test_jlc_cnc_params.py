import unittest

from app.modules.cnc.quote.jlc_cnc_params_loader import JlcCncParamCatalog


class TestJlcCncParams(unittest.TestCase):
    def setUp(self):
        self.catalog = JlcCncParamCatalog()

    def test_materials_count(self):
        materials = self.catalog.get_all_materials()
        self.assertEqual(len(materials), 17)
        cats = self.catalog.get_categories()
        self.assertEqual(len(cats), 5)
        self.assertIn("铝合金", cats)
        self.assertIn("塑料", cats)
        self.assertIn("铜合金", cats)
        self.assertIn("合金钢", cats)
        self.assertIn("不锈钢", cats)

    def test_crafts_count(self):
        crafts = self.catalog.get_all_crafts()
        self.assertEqual(len(crafts), 18)

    def test_aluminum_6061_support(self):
        crafts = self.catalog.get_supported_crafts_for_material("铝合金-6061")
        craft_names = [c["name"] for c in crafts]
        self.assertIn("喷砂+普通阳极氧化", craft_names)
        self.assertIn("激光打标", craft_names)
        tols = self.catalog.get_supported_tolerances_for_material("铝合金-6061")
        self.assertIn("±0.02mm", tols)
        self.assertIn("GB/T 1804-2000 m级", tols)

    def test_steel_tolerances(self):
        tols = self.catalog.get_supported_tolerances_for_material("45#钢")
        self.assertNotIn("±0.02mm", tols)
        self.assertIn("±0.05mm", tols)

    def test_mutual_exclusion(self):
        valid, conflicts = self.catalog.check_craft_mutual_exclusion(["仅喷砂", "钝化"])
        self.assertFalse(valid)
        self.assertTrue(len(conflicts) > 0)

        valid, conflicts = self.catalog.check_craft_mutual_exclusion(["喷砂+普通阳极氧化", "激光打标"])
        self.assertTrue(valid)
        self.assertEqual(len(conflicts), 0)

    def test_validation_valid_config(self):
        res = self.catalog.validate_quote_config(
            material="铝合金-6061",
            surface_mode=2,
            surface_treatments=["喷砂+普通阳极氧化", "激光打标"],
            tolerance="±0.05mm",
            roughness="严格外观",
            has_thread=True,
            has_assembly=False,
            quantity=10,
            delivery_code="BD",
        )
        self.assertTrue(res["valid"])
        self.assertEqual(res["errors"], [])
        self.assertTrue(res["requires_2d_drawing"])

    def test_validation_invalid_config(self):
        res = self.catalog.validate_quote_config(
            material="工程塑料-ABS（白色）",
            surface_mode=2,
            surface_treatments=["喷砂+普通阳极氧化"],
            tolerance="±0.02mm",
            roughness="极致外观",
        )
        self.assertFalse(res["valid"])
        self.assertTrue(any("不支持表面处理工艺" in err for err in res["errors"]))
        self.assertTrue(any("不支持最严公差" in err for err in res["errors"]))
        self.assertTrue(any("不支持外观要求" in err for err in res["errors"]))


if __name__ == "__main__":
    unittest.main()
