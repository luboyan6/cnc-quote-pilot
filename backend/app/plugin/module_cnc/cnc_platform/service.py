# -*- coding: utf-8 -*-

from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, BatchSetAvailable, PageResultSchema
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.utils.common_util import search_to_dict
from app.utils.excel_util import ExcelUtil

from .crud import CncPlatformCRUD
from .schema import (
    CncPlatformCreateSchema,
    CncPlatformOutSchema,
    CncPlatformQueryParam,
    CncPlatformUpdateSchema,
)


class CncPlatformService:
    """竞价平台模块服务层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> CncPlatformOutSchema:
        obj = await CncPlatformCRUD(self.auth, self.db).get(id=id)
        if not obj:
            raise CustomException(msg="该数据不存在")
        return CncPlatformOutSchema.model_validate(obj)

    async def get_list(
        self,
        search: CncPlatformQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> list[CncPlatformOutSchema]:
        obj_list = await CncPlatformCRUD(self.auth, self.db).get_list(search=search_to_dict(search), order_by=order_by)
        return [CncPlatformOutSchema.model_validate(obj) for obj in obj_list]

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: CncPlatformQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[CncPlatformOutSchema]:
        offset = (page_no - 1) * page_size
        return await CncPlatformCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=search_to_dict(search, {}),
            out_schema=CncPlatformOutSchema,
        )

    async def create(self, data: CncPlatformCreateSchema) -> CncPlatformOutSchema:
        obj = await CncPlatformCRUD(self.auth, self.db).create(data=data)
        return CncPlatformOutSchema.model_validate(obj)

    async def update(self, id: int, data: CncPlatformUpdateSchema) -> CncPlatformOutSchema:
        obj = await CncPlatformCRUD(self.auth, self.db).get(id=id)
        if not obj:
            raise CustomException(msg="更新失败，该数据不存在")


        obj = await CncPlatformCRUD(self.auth, self.db).update(id=id, data=data)
        return CncPlatformOutSchema.model_validate(obj)

    async def delete(self, ids: list[int]) -> None:
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        objs = await CncPlatformCRUD(self.auth, self.db).get_list(search={"id": ("in", ids)})
        obj_map = {o.id: o for o in objs}
        for id_ in ids:
            if id_ not in obj_map:
                raise CustomException(msg="删除失败，该数据不存在")
        await CncPlatformCRUD(self.auth, self.db).delete(ids=ids)

    async def set_available(self, data: BatchSetAvailable) -> None:
        await CncPlatformCRUD(self.auth, self.db).set(ids=data.ids, status=data.status)

    @staticmethod
    async def batch_export(obj_list: list[dict[str, Any]]) -> bytes:
        mapping_dict = {
            'id': '主键ID',
            'name': '平台名称',
            'created_time': '创建时间',
            'updated_time': '更新时间',
            'created_id': '创建人ID',
            'login_url': '登录地址',
            'quote_entry_url': '询价地址',
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
            '平台名称': 'name',
            '登录地址': 'login_url',
            '询价地址': 'quote_entry_url',
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

            required_fields = [
                'name',
                'login_url',
                'quote_entry_url',
            ]
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
                    create_schema = CncPlatformCreateSchema.model_validate(row)


                    await CncPlatformCRUD(self.auth, self.db).create(data=create_schema)
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
            '平台名称',
            '登录地址',
            '询价地址',
        ]
        selector_header_list = []
        option_list = []


        return ExcelUtil.get_excel_template(
            header_list=header_list,
            selector_header_list=selector_header_list,
            option_list=option_list,
        )
