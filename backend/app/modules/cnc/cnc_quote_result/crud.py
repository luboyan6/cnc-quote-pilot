# -*- coding: utf-8 -*-
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema
from .model import CncQuoteResultModel
from .schema import CncQuoteResultOutSchema


class CncQuoteResultCRUD(CRUDBase[CncQuoteResultModel, Any, Any]):
    """CNC 报价结果展示数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=CncQuoteResultModel, auth=auth, db=db)
