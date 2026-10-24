"""Read-only migration preflight; no SQL parameters or application rows printed."""

import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import inspect, text

from app.core.database import async_engine
from app.core.logger import logger


async def main():
    logger.remove()
    try:
        async with async_engine.connect() as connection:
            revisions = list((await connection.execute(text("SELECT version_num FROM alembic_version"))).scalars())
            tables = await connection.run_sync(lambda sync: inspect(sync).get_table_names())
            print(json.dumps({"database_revisions": revisions, "quote_tables": [name for name in tables if name in {"cnc_quote_run", "cnc_quote_intent"}]}))
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        print("READ_ONLY_MIGRATION_PREFLIGHT_FAILED", file=sys.stderr)
        sys.exit(1)
