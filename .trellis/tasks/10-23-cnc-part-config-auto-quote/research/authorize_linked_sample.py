"""Enable ONLY the current linked sample, explicitly approved on 2026-10-23.

Refuse if the observed unique enabled configuration changes. No credentials,
file paths or file contents are printed. This is an operator action, not an
automatic behavior of the quote feature.
"""

import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select

from app.core.base_model import MappedBase
from app.core.database import async_db_session, async_engine
from app.core.logger import logger
from app.plugin.module_cnc.cnc_part.model import CncPartModel
from app.plugin.module_cnc.cnc_part_config.model import CncPartConfigModel
from app.utils.import_util import ImportUtil


async def main():
    logger.remove()
    ImportUtil.find_models(MappedBase)
    try:
        async with async_db_session() as db, db.begin():
            configs = (await db.scalars(select(CncPartConfigModel).where(
                CncPartConfigModel.is_deleted.is_(False),
                CncPartConfigModel.enabled.is_(True),
            ).with_for_update(of=CncPartConfigModel))).unique().all()
            if len(configs) != 1:
                raise ValueError("Observed unique configuration changed")
            config = configs[0]
            part = await db.scalar(select(CncPartModel).where(
                CncPartModel.id == config.part_id,
                CncPartModel.is_deleted.is_(False),
            ).with_for_update(of=CncPartModel))
            if part is None or not config.created_id or config.created_id != part.created_id:
                raise ValueError("Linked sample ownership changed")
            if not part.file_path or not part.size_bytes or part.extension.lower().lstrip(".") not in {"step", "stp"}:
                raise ValueError("Sample metadata invalid")
            previous = part.upload_authorized
            part.upload_authorized = True
            part.updated_id = config.created_id
            await db.flush()
            summary = {"config_id": config.id, "part_id": part.id,
                       "previous_authorization": previous,
                       "upload_authorized": part.upload_authorized,
                       "other_drawings_modified": False}
        print(json.dumps(summary))
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        print("SAMPLE_AUTHORIZATION_NOT_CONFIRMED_NO_PRIVATE_DETAILS", file=sys.stderr)
        sys.exit(1)
