"""Read-only metadata for the user-selected live-test drawing; never auth data."""

import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

from loguru import logger

logger.remove()

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config.setting import settings


async def main():
    engine = create_async_engine(settings.ASYNC_DB_URI, hide_parameters=True, echo=False)
    try:
        async with asyncio.timeout(12), engine.connect() as connection:
            parts = (await connection.execute(text(
                "SELECT id, file_name, size_bytes, extension, upload_authorized, "
                "validation_status, created_id FROM cnc_part "
                "WHERE lower(file_name) = lower(:name) AND is_deleted = :deleted"
            ), {"name": "L072-1.15-M12.STEP", "deleted": False})).mappings().all()
            result = {"drawing": "L072-1.15-M12.STEP", "parts": []}
            for part in parts:
                item = dict(part)
                configs = (await connection.execute(text(
                    "SELECT id, name, site_type, material, quantity, surface_finish, "
                    "extra_params, enabled, created_id FROM cnc_part_config "
                    "WHERE part_id = :part_id AND is_deleted = :deleted"
                ), {"part_id": part["id"], "deleted": False})).mappings().all()
                item["configurations"] = []
                for config in configs:
                    current = dict(config)
                    platform = (await connection.execute(text(
                        "SELECT id, name, quote_entry_url FROM cnc_platform "
                        "WHERE id = :platform_id AND is_deleted = :deleted"
                    ), {"platform_id": config["site_type"], "deleted": False})).mappings().first()
                    current["platform"] = None if platform is None else {
                        "id": platform["id"], "name": platform["name"],
                        "entry_host": urlsplit(platform["quote_entry_url"] or "").hostname,
                    }
                    accounts = (await connection.execute(text(
                        "SELECT id, created_id, enabled FROM cnc_account "
                        "WHERE platform_id = :platform_id AND is_deleted = :deleted"
                    ), {"platform_id": config["site_type"], "deleted": False})).mappings().all()
                    current["account_metadata"] = [dict(account) for account in accounts]
                    item["configurations"].append(current)
                result["parts"].append(item)
            unresolved = (await connection.execute(text(
                "SELECT r.run_id, r.status, r.frozen, i.state FROM cnc_quote_run r "
                "JOIN cnc_quote_intent i ON i.run_id = r.run_id "
                "WHERE r.account_id = :account_id AND i.operation = :operation "
                "AND i.state IN (:claimed, :uncertain)"
            ), {"account_id": 1, "operation": "upload", "claimed": "claimed", "uncertain": "uncertain"})).mappings().all()
            result["unresolved_upload_metadata"] = []
            for row in unresolved:
                frozen = row["frozen"]
                if isinstance(frozen, str):
                    frozen = json.loads(frozen)
                result["unresolved_upload_metadata"].append({
                    "run_id": row["run_id"], "status": row["status"], "state": row["state"],
                    "sha256": frozen.get("sha256") if isinstance(frozen, dict) else None,
                    "size": frozen.get("size") if isinstance(frozen, dict) else None,
                })
            print(json.dumps(result, ensure_ascii=True, default=str))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        original = getattr(error, "orig", error)
        print(json.dumps({"error": "READ_ONLY_TARGET_PREFLIGHT_FAILED", "type": type(error).__name__, "cause_type": type(original).__name__, "errno": getattr(original, "errno", None)}))
        sys.exit(1)
