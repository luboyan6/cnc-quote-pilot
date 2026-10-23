# -*- coding: utf-8 -*-

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema
from .model import CncPartModel
from .schema import CncPartCreateSchema, CncPartUpdateSchema


class CncPartCRUD(CRUDBase[CncPartModel, CncPartCreateSchema, CncPartUpdateSchema]):
    """图纸文件数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        """
        初始化CRUD数据层

        参数:
        - auth (AuthSchema): 认证信息模型
        - db (AsyncSession): 数据库会话
        """
        super().__init__(model=CncPartModel, auth=auth, db=db)
