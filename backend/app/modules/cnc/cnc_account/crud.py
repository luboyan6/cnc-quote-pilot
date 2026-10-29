from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema
from app.core.logger import logger

from .model import CncAccountModel
from .schema import CncAccountCreateSchema, CncAccountUpdateSchema


class CncAccountCRUD(CRUDBase[CncAccountModel, CncAccountCreateSchema, CncAccountUpdateSchema]):
    """
    网站账号数据访问层 (CncAccountCRUD)

    【职责说明】
    负责 `CncAccountModel` 实体在数据库层面的直接 CRUD 操作。
    继承自框架通用 `CRUDBase`，提供基于 SQLAlchemy 2.0 AsyncSession 的异步数据库操作。

    【核心查询能力继承自 CRUDBase】:
    - get(id: int, preload: list[str] | None = None) -> CncAccountModel | None:
        根据主键 ID 查询单条未被软删除的账号实体。
        支持通过 `preload=["platform"]` 联表预加载所属平台信息，避免 N+1 查询。
    - get_list(search: dict | None = None, order_by: list[dict] | None = None, preload: list[str] | None = None) -> list[CncAccountModel]:
        根据字典条件表达式进行多条件复合查询，返回符合条件的账号实体列表。
    - page(offset: int, limit: int, search: dict | None = None, order_by: list[dict] | None = None, out_schema: type | None = None, preload: list[str] | None = None) -> PageResultSchema:
        执行支持总数统计、动态排序与关联预加载的分页查询。

    【安全设计说明】:
    - 重写了 `_log_error`：避免 Loguru 在开发模式下展开 traceback locals 导致加密凭据或明文片段被打印到日志。
    - 数据权限隔离：根据系统架构原则，CRUD 层不自动做用户级过滤（只做审计字段填充），所有基于用户归属的数据权限隔离由 `CncAccountService` 负责传入过滤条件。
    """

    def _log_error(self, message: str) -> None:
        # Dev Loguru diagnostics expand traceback locals, including encrypted
        # credentials. Preserve the failure marker without exception/parameters.
        logger.error(message)

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        """
        初始化网站账号 CRUD 数据层

        参数:
        - auth (AuthSchema): 当前操作用户的认证上下文（包含当前登录用户 user_id, 角色与超管标记）
        - db (AsyncSession): SQLAlchemy 异步数据库会话
        """
        super().__init__(model=CncAccountModel, auth=auth, db=db)
