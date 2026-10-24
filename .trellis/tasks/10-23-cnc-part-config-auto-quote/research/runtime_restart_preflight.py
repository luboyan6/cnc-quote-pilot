"""Read-only schema/activity preflight for the existing local development server."""

import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

from alembic.autogenerate import produce_migrations
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.core.base_model import MappedBase
from app.core.database import async_engine
from app.core.logger import logger
from app.utils.import_util import ImportUtil
from app.utils.migration_util import preserve_postgresql_identity


async def main():
    logger.remove()
    ImportUtil.find_models(MappedBase)
    metadata = MappedBase.metadata
    heads = ScriptDirectory.from_config(Config(str(ROOT / "backend/alembic.ini"))).get_heads()

    def compare(connection):
        def include_name(name, type_, parent_names):
            return type_ != "table" or parent_names["schema_qualified_table_name"] in metadata.tables

        context = MigrationContext.configure(connection, opts={
            "target_metadata": metadata,
            "compare_server_default": True,
            "render_as_batch": True,
            "include_name": include_name,
        })
        script = produce_migrations(context, metadata)
        if script is None:
            raise RuntimeError("Missing comparison result")
        preserve_postgresql_identity(context, script, metadata)
        return sum(len(ops.ops) for ops in script.upgrade_ops_list)

    try:
        async with async_engine.connect() as connection:
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            revisions = list((await connection.execute(text("SELECT version_num FROM alembic_version"))).scalars())
            changes = await connection.run_sync(compare)
            activity = (await connection.execute(text(
                "SELECT (SELECT COUNT(*) FROM cnc_quote_run WHERE status NOT IN "
                "('QUOTED','REFERENCE_ESTIMATE','PENDING_REVIEW','FAILED','CANCELLED')) AS nonterminal_quote_runs, "
                "(SELECT COUNT(*) FROM cnc_account WHERE lease_owner IS NOT NULL "
                "AND lease_until > (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')) AS live_account_leases"
            ))).mappings().one()
        result = {
            "read_only": True,
            "migration_heads": heads,
            "database_revisions": revisions,
            "pending_model_operations": changes,
            **dict(activity),
        }
        result["ready_for_restart"] = (
            set(heads) == set(revisions) and changes == 0
            and not result["nonterminal_quote_runs"] and not result["live_account_leases"]
        )
        Path(__file__).with_name("runtime-restart-preflight-2026-10-23.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        print(json.dumps(result))
        if not result["ready_for_restart"]:
            sys.exit(2)
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"READ_ONLY_RESTART_PREFLIGHT_FAILED: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
