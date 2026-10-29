from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, BatchSetAvailable, PageResultSchema
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.utils.common_util import search_to_dict
from app.utils.excel_util import ExcelUtil

from .crud import CncPartCRUD
from .schema import (
    CncPartCreateSchema,
    CncPartOutSchema,
    CncPartQueryParam,
    CncPartUpdateSchema,
)


class CncPartService:
    """
    图纸文件模块服务层 (CncPartService)

    【业务职责】
    负责 CNC 零件 3D CAD 图纸（STEP/STP）的核心业务逻辑管理，包括：
    1. 零件图纸的检索与查询（单条详情、条件列表、分页查询）；
    2. 图纸批量 Excel 导入导出。
    """

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        """
        初始化图纸文件服务

        参数:
        - auth (AuthSchema): 当前用户认证与鉴权上下文
        - db (AsyncSession): SQLAlchemy 异步会话
        """
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> CncPartOutSchema:
        """
        获取单张零件图纸详情 (Agent 核心查询接口)

        【Agent 调用指南】:
        - 适用场景:
          1. 报价自动化 Agent 在上传图纸到立创/Xometry 等平台前，调用此方法获取文件的真实磁盘存储路径 `file_path`。
        - 权限与状态: 仅能查到未被软删除 (is_deleted=False) 的有效图纸。

        参数:
        - id (int): 零件图纸主键 ID

        返回值:
        - CncPartOutSchema: 零件图纸详情数据模型（包含 file_name, file_path, extension, size_bytes 等）

        异常:
        - CustomException: 当指定 ID 的图纸不存在或已被删除时抛出
        """
        obj = await CncPartCRUD(self.auth, self.db).get(id=id)
        if not obj:
            raise CustomException(msg="该数据不存在")
        return CncPartOutSchema.model_validate(obj)

    async def get_list(
        self,
        search: CncPartQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> list[CncPartOutSchema]:
        """
        按条件获取零件图纸列表（全量不分页）

        【Agent 调用指南】:
        - 适用场景:
          1. 下拉框选择图纸，或 Agent 根据图纸文件名 (file_name) 搜索定位零件 ID。
        - 查询模式: 自动解析 search 参数，支持模糊匹配（文件名、路径）。

        参数:
        - search (CncPartQueryParam | None): 过滤条件参数
        - order_by (list[dict[str, str]] | None): 排序规则列表，例如 [{"created_time": "desc"}]

        返回值:
        - list[CncPartOutSchema]: 符合条件的图纸模型列表
        """
        obj_list = await CncPartCRUD(self.auth, self.db).get_list(search=search_to_dict(search), order_by=order_by)
        return [CncPartOutSchema.model_validate(obj) for obj in obj_list]

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: CncPartQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[CncPartOutSchema]:
        """
        分页查询零件图纸列表 (Agent 列表查询接口)

        【Agent 调用指南】:
        - 适用场景: 前端表格分页呈现，或 Agent 遍历大批量图纸数据仓库。
        - 默认排序: 若未指定 order_by，默认按 ID 升序 [{"id": "asc"}] 排列。
        - 软删除过滤: 底层自动排除已软删除记录。

        参数:
        - page_no (int): 分页页码，从 1 开始
        - page_size (int): 每页条数
        - search (CncPartQueryParam | None): 条件过滤参数
        - order_by (list[dict[str, str]] | None): 排序字段规则

        返回值:
        - PageResultSchema[CncPartOutSchema]: 分页结果容器，包含 items（当前页数据列表）、total（符合条件总记录数）等
        """
        offset = (page_no - 1) * page_size
        return await CncPartCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=search_to_dict(search, {}),
            out_schema=CncPartOutSchema,
        )

    async def create(self, data: CncPartCreateSchema) -> CncPartOutSchema:
        obj = await CncPartCRUD(self.auth, self.db).create(data=data)
        return CncPartOutSchema.model_validate(obj)

    async def update(self, id: int, data: CncPartUpdateSchema) -> CncPartOutSchema:
        obj = await CncPartCRUD(self.auth, self.db).get(id=id)
        if not obj:
            raise CustomException(msg="更新失败，该数据不存在")

        obj = await CncPartCRUD(self.auth, self.db).update(id=id, data=data)
        return CncPartOutSchema.model_validate(obj)

    async def delete(self, ids: list[int]) -> None:
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        objs = await CncPartCRUD(self.auth, self.db).get_list(search={"id": ("in", ids)})
        obj_map = {o.id: o for o in objs}
        for id_ in ids:
            if id_ not in obj_map:
                raise CustomException(msg="删除失败，该数据不存在")
        await CncPartCRUD(self.auth, self.db).delete(ids=ids)

    async def set_available(self, data: BatchSetAvailable) -> None:
        await CncPartCRUD(self.auth, self.db).set(ids=data.ids, status=data.status)

    @staticmethod
    async def batch_export(obj_list: list[dict[str, Any]]) -> bytes:
        mapping_dict = {
            "id": "业务标识 ID，自增整数；Demo 版不设主键约束",
            "file_name": "文件名称",
            "file_path": "文件存储路径",
            # "extension": "文件扩展名；字典：step=STEP 图纸，stp=STEP 图纸的另一扩展名",
            # "size_bytes": "文件大小，单位：字节，必须大于 0",
            # "declared_unit": "图纸声明单位，例如 mm=毫米；为空表示未知，示例并非完整字典",
            # "created_time": "记录创建时间，带时区",
            # "updated_time": "记录最近更新时间；Demo 版由后端更新，无数据库触发器",
            # "file_type": "文件类型",
        }

        data = obj_list.copy()
        for item in data:
            item["status"] = "启用" if item.get("status") == 0 else "停用"
            creator_info = item.get("created_id")
            if isinstance(creator_info, dict):
                item["created_id"] = creator_info.get("name", "未知")
            else:
                item["created_id"] = "未知"

        return await ExcelUtil.aexport_list2excel(list_data=data, mapping_dict=mapping_dict)

    async def batch_import(self, file: UploadFile, update_support: bool = False) -> str:
        header_dict = {
            "文件名称": "file_name",
            "文件存储路径": "file_path",
            # "文件扩展名；字典：step=STEP 图纸，stp=STEP 图纸的另一扩展名": "extension",
            # "文件大小，单位：字节，必须大于 0": "size_bytes",
            # "图纸声明单位，例如 mm=毫米；为空表示未知，示例并非完整字典": "declared_unit",
            # "文件类型": "file_type",
        }

        try:
            contents = await file.read()
            rows = await ExcelUtil.aread_excel_to_dicts(contents)
            await file.close()

            if not rows:
                raise CustomException(msg="导入文件为空")

            missing_headers = [h for h in header_dict if h not in rows[0]]
            if missing_headers:
                raise CustomException(msg=f"导入文件缺少必要的列: {', '.join(missing_headers)}")

            # 将中文字段名映射为英文字段
            mapped_rows = []
            for row in rows:
                mapped_rows.append({en: row.get(ch) for ch, en in header_dict.items()})

            required_fields = []
            errors = []
            for field in required_fields:
                missing_indices = [i + 1 for i, r in enumerate(mapped_rows) if r.get(field) is None]
                if missing_indices:
                    field_name = next((k for k, v in header_dict.items() if v == field), field)
                    rows_str = "、".join(str(i) for i in missing_indices)
                    errors.append(f"{field_name}不能为空，第{rows_str}行")
            if errors:
                raise CustomException(msg=f"导入失败，以下行缺少必要字段：\n{'; '.join(errors)}")

            error_msgs = []
            success_count = 0

            for i, row in enumerate(mapped_rows, start=1):
                try:
                    create_schema = CncPartCreateSchema.model_validate(row)
                    await CncPartCRUD(self.auth, self.db).create(data=create_schema)
                    success_count += 1
                except Exception as e:
                    error_msgs.append(f"第{i}行: {e!s}")
                    continue

            result = f"成功导入 {success_count} 条数据"
            if error_msgs:
                result += "\n错误信息:\n" + "\n".join(error_msgs)
            return result

        except Exception as e:
            logger.error(f"批量导入失败: {e!s}")
            raise CustomException(msg=f"导入失败: {e!s}")

    @staticmethod
    def import_template_download() -> bytes:
        header_list = [
            "文件名称",
            "文件存储路径",
            # "文件扩展名；字典：step=STEP 图纸，stp=STEP 图纸的另一扩展名",
            # "文件大小，单位：字节，必须大于 0",
            # "图纸声明单位，例如 mm=毫米；为空表示未知，示例并非完整字典",
            # "文件校验状态；字典：PENDING=待校验，HEADER_VALID=文件头基础检查通过，REJECTED=已拒绝；不代表几何或可加工性通过",
            # "第三方上传授权；字典：false=未授权，true=已授权",
            # "文件类型",
        ]
        selector_header_list = []
        option_list = []

        return ExcelUtil.get_excel_template(
            header_list=header_list,
            selector_header_list=selector_header_list,
            option_list=option_list,
        )
