import unittest

from app.modules.cnc.quote.xometry_cnc_params_loader import XometryCncParamCatalog


class TestXometryCncParams(unittest.TestCase):
    def setUp(self):
        self.catalog = XometryCncParamCatalog()

    def test_materials_count_and_categories(self):
        materials = self.catalog.get_all_materials()
        self.assertEqual(len(materials), 62)
        cats = self.catalog.get_material_categories()
        self.assertEqual(len(cats), 8)
        self.assertIn("Aluminum", cats)
        self.assertIn("Plastic", cats)
        self.assertIn("Stainless Steel", cats)
        self.assertIn("Steel", cats)
        self.assertIn("Brass, Bronze, or Copper", cats)
        self.assertIn("Titanium", cats)
        self.assertIn("Composite", cats)
        self.assertIn("Other", cats)

    def test_subprocesses_count(self):
        subs = self.catalog.get_subprocesses()
        self.assertEqual(len(subs), 8)
        sub_names = [s["name"] for s in subs]
        self.assertIn("No Preference", sub_names)
        self.assertIn("CNC Milling", sub_names)
        self.assertIn("Swiss-Type Turning", sub_names)

    def test_aluminum_6061_finishes_and_tolerances(self):
        finishes = self.catalog.get_supported_finishes_for_material("Aluminum 6061-T6x (Best Available)")
        self.assertIn("Standard", finishes)
        self.assertIn("Black Anodize", finishes)
        self.assertIn("Chem Film Clear", finishes)
        self.assertIn("Bead Blast", finishes)
        # Stainless steel finish like Passivate or Black Oxide shouldn't be for Aluminum
        self.assertNotIn("Passivate", finishes)

        tols = self.catalog.get_supported_tolerances_for_material("Aluminum 6061-T6x (Best Available)")
        self.assertIn("±.005″ (±0.13mm)", tols)
        self.assertIn("±.010″ (±0.25mm)", tols)
        self.assertNotIn("±.020″ (±0.5mm)", tols)

    def test_plastic_finishes_and_tolerances(self):
        finishes = self.catalog.get_supported_finishes_for_material("Acetal (POM)")
        self.assertIn("Standard", finishes)
        self.assertIn("Bead Blast", finishes)
        self.assertIn("Request finish", finishes)
        self.assertNotIn("Black Anodize", finishes)
        self.assertNotIn("Gold Plating", finishes)

        tols = self.catalog.get_supported_tolerances_for_material("Acetal (POM)")
        self.assertIn("±.010″ (±0.25mm)", tols)
        self.assertIn("±.020″ (±0.5mm)", tols)
        self.assertNotIn("±.005″ (±0.13mm)", tols)

    def test_validation_valid_metal_config(self):
        res = self.catalog.validate_quote_config(
            material="Aluminum 6061-T6x (Best Available)",
            subprocess="CNC Milling",
            finish="Black Anodize",
            tolerance="±.005″ (±0.13mm)",
            roughness="125uin/3.2um Ra",
            inspection="Standard Inspection",
            threads_count=0,
            inserts_count=0,
            quantity=5,
        )
        self.assertTrue(res["valid"])
        self.assertEqual(res["errors"], [])
        self.assertFalse(res["requires_2d_drawing"])

    def test_validation_threads_trigger_drawing(self):
        res = self.catalog.validate_quote_config(
            material="Aluminum 6061-T6x (Best Available)",
            finish="Standard",
            threads_count=4,
        )
        self.assertTrue(res["valid"])
        self.assertTrue(res["requires_2d_drawing"])
        self.assertTrue(any("螺纹" in r for r in res["drawing_reasons"]))

    def test_validation_inserts_trigger_drawing(self):
        res = self.catalog.validate_quote_config(
            material="Stainless Steel 304/304L",
            finish="Passivate",
            inserts_count=2,
        )
        self.assertTrue(res["valid"])
        self.assertTrue(res["requires_2d_drawing"])
        self.assertTrue(any("镶件" in r for r in res["drawing_reasons"]))

    def test_validation_loose_tolerance_inspection_conflict(self):
        # Loose tolerance on metal is ±.010″ (±0.25mm), which restricts inspection to Standard Inspection
        res = self.catalog.validate_quote_config(
            material="Aluminum 6061-T6x (Best Available)",
            tolerance="±.010″ (±0.25mm)",
            inspection="Formal Inspection with Dimensional Report",
        )
        self.assertFalse(res["valid"])
        self.assertTrue(any("质检仅支持 'Standard Inspection'" in err for err in res["errors"]))

    def test_validation_incompatible_finish(self):
        # Plastic cannot have Anodize
        res = self.catalog.validate_quote_config(
            material="Acetal (POM)",
            finish="Black Anodize",
        )
        self.assertFalse(res["valid"])
        self.assertTrue(any("不支持表面处理" in err for err in res["errors"]))

    def test_validation_tight_tolerance_requires_drawing(self):
        res = self.catalog.validate_quote_config(
            material="Aluminum 6061-T6x (Best Available)",
            tolerance="This part requires tolerances tighter than ±.005″ (±0.13mm)",
        )
        self.assertTrue(res["valid"])
        self.assertTrue(res["requires_2d_drawing"])
        self.assertTrue(any("精密公差" in r for r in res["drawing_reasons"]))


if __name__ == "__main__":
    unittest.main()
