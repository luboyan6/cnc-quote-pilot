from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema
from app.core.logger import logger

from .model import CncAccountModel
from .schema import CncAccountCreateSchema, CncAccountUpdateSchema


class CncAccountCRUD(CRUDBase[CncAccountModel, CncAccountCreateSchema, CncAccountUpdateSchema]):
    """网站账号数据层"""

    def _log_error(self, message: str) -> None:
        # Dev Loguru diagnostics expand traceback locals, including encrypted
        # credentials. Preserve the failure marker without exception/parameters.
        logger.error(message)

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        """
        初始化CRUD数据层

        参数:
        - auth (AuthSchema): 认证信息模型
        - db (AsyncSession): 数据库会话
        """
        super().__init__(model=CncAccountModel, auth=auth, db=db)
