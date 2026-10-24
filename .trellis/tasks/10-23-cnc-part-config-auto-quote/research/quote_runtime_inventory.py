"""Read-only, allowlisted quote inventory; no credentials, paths or receipts."""

import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import text

from app.core.database import async_engine
from app.core.logger import logger


async def main():
    logger.remove()
    try:
        async with async_engine.connect() as connection:
            # Enforced by the database as well as by this script's SELECT-only queries.
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            configs = (await connection.execute(text(
                "SELECT c.id AS config_id, c.part_id, c.site_type AS platform_id, "
                "c.enabled, c.material, c.quantity, c.surface_finish, "
                "p.extension, p.upload_authorized, p.validation_status, "
                "(SELECT COUNT(*) FROM cnc_account a WHERE a.platform_id = c.site_type "
                "AND a.enabled = true AND a.is_deleted = false) AS enabled_accounts "
                "FROM cnc_part_config c LEFT JOIN cnc_part p ON p.id = c.part_id "
                "WHERE c.is_deleted = false ORDER BY c.id"
            ))).mappings().all()
            runs = (await connection.execute(text(
                "SELECT run_id, config_id, part_id, platform_id, account_id, status, "
                "stage, reason, active_config_id FROM cnc_quote_run "
                "ORDER BY created_at DESC LIMIT 20"
            ))).mappings().all()
            intents = (await connection.execute(text(
                "SELECT run_id, operation, state, COUNT(*) AS count "
                "FROM cnc_quote_intent GROUP BY run_id, operation, state "
                "ORDER BY run_id, operation, state"
            ))).mappings().all()
            versions = list((await connection.execute(text(
                "SELECT version_num FROM alembic_version"
            ))).scalars())
            platforms = (await connection.execute(text(
                "SELECT p.id AS platform_id, p.name AS platform_name, "
                "(SELECT COUNT(*) FROM cnc_account a WHERE a.platform_id = p.id "
                "AND a.enabled = true AND a.is_deleted = false) AS enabled_accounts "
                "FROM cnc_platform p WHERE p.is_deleted = false ORDER BY p.id"
            ))).mappings().all()
            activity = (await connection.execute(text(
                "SELECT (SELECT COUNT(*) FROM cnc_quote_run "
                "WHERE status NOT IN ('QUOTED','REFERENCE_ESTIMATE','PENDING_REVIEW','FAILED','CANCELLED')) "
                "AS nonterminal_quote_runs, "
                "(SELECT COUNT(*) FROM cnc_account WHERE lease_owner IS NOT NULL "
                "AND lease_until > (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')) AS live_account_leases"
            ))).mappings().one()
            result = {
                "read_only": True,
                "database_revisions": versions,
                "configurations": [dict(row) for row in configs],
                "runs": [dict(row) for row in runs],
                "intent_counts": [dict(row) for row in intents],
                "platform_account_counts": [dict(row) for row in platforms],
                "runtime_activity": dict(activity),
            }
            contents = json.dumps(result, ensure_ascii=False, indent=2)
            Path(__file__).with_name("quote-runtime-inventory-2026-10-23.json").write_text(contents, encoding="utf-8")
            print(contents)
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"READ_ONLY_INVENTORY_FAILED: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
