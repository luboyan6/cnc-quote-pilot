"""Apply only the exact sample specification the user explicitly selected."""

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
from app.plugin.module_cnc.cnc_part_config.model import CncPartConfigModel
from app.utils.import_util import ImportUtil

MATERIAL = "Aluminum 6061-T6x (Best Available)"
FINISH = "Standard"


async def main():
    logger.remove()
    ImportUtil.find_models(MappedBase)
    try:
        async with async_db_session() as db, db.begin():
            configs = (await db.scalars(select(CncPartConfigModel).where(
                CncPartConfigModel.is_deleted.is_(False),
                CncPartConfigModel.enabled.is_(True),
            ).with_for_update(of=CncPartConfigModel))).unique().all()
            if len(configs) != 1 or configs[0].id != 1 or configs[0].part_id != 2:
                raise ValueError("Previously reviewed sample configuration changed")
            config = configs[0]
            if config.material not in {"铝合金", MATERIAL} or config.surface_finish not in {None, "", FINISH}:
                raise ValueError("Do not overwrite an independently changed specification")
            config.material, config.surface_finish = MATERIAL, FINISH
            config.updated_id = config.created_id
            await db.flush()
            summary = {"config_id": config.id, "part_id": config.part_id,
                       "material": config.material, "surface_finish": config.surface_finish,
                       "quantity": config.quantity, "other_configurations_modified": False}
        print(json.dumps(summary, ensure_ascii=False))
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        print("SAMPLE_CONFIGURATION_NOT_CONFIRMED_NO_PRIVATE_DETAILS", file=sys.stderr)
        sys.exit(1)
