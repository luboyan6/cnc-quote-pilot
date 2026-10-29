"""Apply only the new revision on an isolated SQLite DB, then compare schema."""

import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Table, UniqueConstraint, create_engine, inspect

from app.modules.cnc.cnc_quote.model import CncQuoteIntentModel, CncQuoteRunModel


class MigrationTests(unittest.TestCase):
    def test_new_revision_round_trip_and_model_columns_constraints(self):
        file = Path(__file__).resolve().parents[3] / "app/alembic/versions/2026_10_23_1600_c9e3a6b72f14.py"
        spec = importlib.util.spec_from_file_location("quote_test_migration", file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.down_revision, "0ce906be2d99")
        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                setattr(module, "op", Operations(MigrationContext.configure(connection)))
                module.upgrade()
                inspector = inspect(connection)
                self.assertEqual(set(inspector.get_table_names()), {"cnc_quote_run", "cnc_quote_intent"})
                for model in [CncQuoteRunModel, CncQuoteIntentModel]:
                    table = model.__table__
                    assert isinstance(table, Table)
                    columns = inspector.get_columns(model.__tablename__)
                    self.assertEqual(
                        {column["name"] for column in columns},
                        set(model.__table__.columns.keys()) - ({"item_id", "attempt_no", "item_claim_owner", "item_claim_token"} if model is CncQuoteRunModel else set()),
                    )
                    expected_unique = {
                        tuple(column.name for column in constraint.columns) for constraint in table.constraints if isinstance(constraint, UniqueConstraint) and constraint.name != "uq_cnc_item_attempt"
                    }
                    self.assertEqual({tuple(constraint["column_names"]) for constraint in inspector.get_unique_constraints(model.__tablename__)}, expected_unique)
                module.downgrade()
                self.assertEqual(inspect(connection).get_table_names(), [])
        finally:
            engine.dispose()
