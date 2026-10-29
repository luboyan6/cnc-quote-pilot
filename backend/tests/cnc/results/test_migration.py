"""Test T4 Alembic migration f6b3e1c91028 upgrade and downgrade round-trip."""

import importlib.util
import unittest
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect


class TestResultMigration(unittest.TestCase):
    def test_migration_round_trip(self):
        file = Path(__file__).resolve().parents[3] / "app/alembic/versions/2026_10_28_1900_f6b3e1c91028.py"
        spec = importlib.util.spec_from_file_location("results_test_migration", file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertEqual(module.revision, "f6b3e1c91028")
        self.assertEqual(module.down_revision, "e5a2c3d81028")

        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                # Pre-create base table as it was before f6b3e1c91028
                meta = MetaData()
                base_table = Table(
                    "cnc_quote_result",
                    meta,
                    Column("id", Integer, primary_key=True),
                    Column("run_id", String(64)),
                    Column("batch_id", String(36)),
                    Column("item_id", String(36)),
                    Column("unit_price", String(32)),
                    Column("quote_status", String(32)),
                )
                meta.create_all(connection)

                setattr(module, "op", Operations(MigrationContext.configure(connection)))
                # 1. Upgrade
                module.upgrade()
                inspector = inspect(connection)
                cols = {c["name"] for c in inspector.get_columns("cnc_quote_result")}

                expected_new_cols = {
                    "round_id",
                    "file_sha256",
                    "comparison_key",
                    "comparison_version",
                    "effective_snapshot",
                    "tax_included",
                    "shipping_amount",
                    "evidence_id",
                    "evidence_state",
                    "queue_ms",
                    "active_execution_ms",
                    "human_wait_ms",
                    "reconcile_ms",
                    "total_wall_ms",
                    "error_code",
                }
                self.assertTrue(expected_new_cols.issubset(cols))

                # 2. Downgrade
                module.downgrade()
                cols_after = {c["name"] for c in inspect(connection).get_columns("cnc_quote_result")}
                self.assertFalse(any(c in cols_after for c in expected_new_cols))
        finally:
            engine.dispose()
