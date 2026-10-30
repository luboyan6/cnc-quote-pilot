"""Read only the known configuration owner's ID and connectivity for smoke setup.

No credentials, rows, connection URLs or exception text are printed. No migration
or model request is performed. Run from backend with its virtualenv interpreter.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("ENVIRONMENT", "dev")
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "backend"))


async def main():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.config.setting import settings

    engine = create_async_engine(settings.ASYNC_DB_URI, echo=False, hide_parameters=True)
    try:
        async with asyncio.timeout(12):
            async with engine.connect() as connection:
                async with connection.begin():
                    if settings.DATABASE_TYPE == "postgres":
                        await connection.execute(text("SET TRANSACTION READ ONLY"))
                    row = (
                        await connection.execute(
                            text("SELECT id, created_id FROM cnc_part_config WHERE id = :config_id AND is_deleted = false"),
                            {"config_id": 1},
                        )
                    ).first()
                    print(json.dumps({"read_only": True, "database_reachable": True, "known_config_id": row[0] if row else None, "owner_actor_id": row[1] if row else None}))
    except Exception as exc:
        print(json.dumps({"read_only": True, "database_reachable": False, "error_type": type(exc).__name__}))
        return 1
    finally:
        await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
