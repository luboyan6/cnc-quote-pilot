import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from app.modules.cnc.cnc_quote.model import CncQuoteRunModel
from app.modules.cnc.cnc_quote_batch.model import CncQuoteBatchModel, CncQuoteCapacityModel
from app.modules.cnc.cnc_quote_batch_item.model import CncQuoteBatchItemModel


def migration(file):
    spec = importlib.util.spec_from_file_location("isolated_migration_" + file.stem, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_batch_migration_roundtrip_and_historical_duplicates_stop_without_deletion():
    root = Path(__file__).resolve().parents[3] / "app/alembic/versions"
    original = migration(root / "2026_10_23_1600_c9e3a6b72f14.py")
    new = migration(root / "2026_10_28_1400_d4b9a2f61028.py")
    assert new.down_revision == "b76d50ea5d8f"
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            operations = Operations(MigrationContext.configure(connection))
            setattr(original, "op", operations)
            setattr(new, "op", operations)
            original.upgrade()
            connection.execute(text("CREATE TABLE cnc_quote_result (id INTEGER PRIMARY KEY, run_id VARCHAR(64), currency VARCHAR(10))"))
            connection.execute(text("INSERT INTO cnc_quote_result(run_id) VALUES ('old-run'), ('old-run')"))
            with pytest.raises(RuntimeError, match="old-run"):
                new.upgrade()
            assert connection.scalar(text("SELECT COUNT(*) FROM cnc_quote_result")) == 2
            assert "cnc_quote_batch" not in inspect(connection).get_table_names()
            # Fix only this synthetic test input; production migration never deletes.
            connection.execute(text("DELETE FROM cnc_quote_result"))
            new.upgrade()
            inspector = inspect(connection)
            for model in [CncQuoteBatchModel, CncQuoteCapacityModel, CncQuoteBatchItemModel, CncQuoteRunModel]:
                assert {c["name"] for c in inspector.get_columns(model.__tablename__)} == set(model.__table__.columns.keys())
                expected = {tuple(c.name for c in constraint.columns) for constraint in model.__table__.constraints if constraint.__class__.__name__ == "UniqueConstraint"}
                assert {tuple(c["column_names"]) for c in inspector.get_unique_constraints(model.__tablename__)} == expected
            assert connection.scalar(text("SELECT version FROM cnc_quote_capacity WHERE id=1")) == 0
            new.downgrade()
            assert set(inspect(connection).get_table_names()) == {"cnc_quote_run", "cnc_quote_intent", "cnc_quote_result"}
    finally:
        engine.dispose()
