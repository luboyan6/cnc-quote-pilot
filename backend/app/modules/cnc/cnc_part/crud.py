from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema

from .model import CncPartModel
from .schema import CncPartCreateSchema, CncPartUpdateSchema


class CncPartCRUD(CRUDBase[CncPartModel, CncPartCreateSchema, CncPartUpdateSchema]):
    """
    图纸文件数据访问层 (CncPartCRUD)

    【职责说明】
    封装针对 `CncPartModel` 零件图纸表的数据库层交互，依托 SQLAlchemy 2.0 异步会话。
    继承自通用基础数据层 `CRUDBase`。

    【核心查询能力继承自 CRUDBase】:
    - get(id: int, preload: list[str] | None = None) -> CncPartModel | None:
        根据主键 ID 查询单条未被软删除的图纸记录。
    - get_list(search: dict | None = None, order_by: list[dict] | None = None) -> list[CncPartModel]:
        根据多字段条件表达式批量查询图纸记录列表。
    - page(offset: int, limit: int, search: dict | None = None, order_by: list[dict] | None = None, out_schema: type | None = None) -> PageResultSchema:
        对图纸执行分页查询，自动统计匹配总数并支持动态字段排序。
    """

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        """
        初始化图纸文件 CRUD 数据访问层

        参数:
        - auth (AuthSchema): 当前用户认证凭据模型（包含 user_id、角色等上下文）
        - db (AsyncSession): 异步数据库会话
        """
        super().__init__(model=CncPartModel, auth=auth, db=db)
