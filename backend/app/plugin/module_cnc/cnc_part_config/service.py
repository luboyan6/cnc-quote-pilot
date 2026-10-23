# -*- coding: utf-8 -*-

from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, BatchSetAvailable, PageResultSchema
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.utils.common_util import search_to_dict
from app.utils.excel_util import ExcelUtil

from .crud import CncPartConfigCRUD
from .schema import (
    CncPartConfigCreateSchema,
    CncPartConfigOutSchema,
    CncPartConfigQueryParam,
    CncPartConfigUpdateSchema,
)


class CncPartConfigService:
    """图纸参数配置表模块服务层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> CncPartConfigOutSchema:
        obj = await CncPartConfigCRUD(self.auth, self.db).get(id=id)
        if not obj:
            raise CustomException(msg="该数据不存在")
        return CncPartConfigOutSchema.model_validate(obj)

    async def get_list(
        self,
        search: CncPartConfigQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> list[CncPartConfigOutSchema]:
        obj_list = await CncPartConfigCRUD(self.auth, self.db).get_list(search=search_to_dict(search), order_by=order_by)
        return [CncPartConfigOutSchema.model_validate(obj) for obj in obj_list]

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: CncPartConfigQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[CncPartConfigOutSchema]:
        offset = (page_no - 1) * page_size
        return await CncPartConfigCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=search_to_dict(search, {}),
            out_schema=CncPartConfigOutSchema,
        )

    async def create(self, data: CncPartConfigCreateSchema) -> CncPartConfigOutSchema:
        obj = await CncPartConfigCRUD(self.auth, self.db).create(data=data)
        return CncPartConfigOutSchema.model_validate(obj)

    async def update(self, id: int, data: CncPartConfigUpdateSchema) -> CncPartConfigOutSchema:
        obj = await CncPartConfigCRUD(self.auth, self.db).get(id=id)
        if not obj:
            raise CustomException(msg="更新失败，该数据不存在")


        obj = await CncPartConfigCRUD(self.auth, self.db).update(id=id, data=data)
        return CncPartConfigOutSchema.model_validate(obj)

    async def delete(self, ids: list[int]) -> None:
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        objs = await CncPartConfigCRUD(self.auth, self.db).get_list(search={"id": ("in", ids)})
        obj_map = {o.id: o for o in objs}
        for id_ in ids:
            if id_ not in obj_map:
                raise CustomException(msg="删除失败，该数据不存在")
        await CncPartConfigCRUD(self.auth, self.db).delete(ids=ids)

    async def set_available(self, data: BatchSetAvailable) -> None:
        await CncPartConfigCRUD(self.auth, self.db).set(ids=data.ids, status=data.status)

    @staticmethod
    async def batch_export(obj_list: list[dict[str, Any]]) -> bytes:
        mapping_dict = {
            'id': '配置ID，自增主键',
            'name': '配置名称，例如：Xometry铝合金标准加工',
            'site_type': '报价平台类型；1=Xometry，2=嘉立创',
            'material': '加工材料；存储对应报价平台的具体材料选项',
            'quantity': '加工数量；正整数，默认1',
            'surface_finish': '表面处理方式；存储对应报价平台的具体表面处理选项',
            'extra_params': '平台差异化参数；JSON格式，例如颜色、公差、表面粗糙度等',
            'enabled': '是否启用；true=启用，false=禁用',
            'part_id': '关联图纸ID',
            'created_time': '记录创建时间，带时区',
            'updated_time': '记录最近更新时间；由后端更新',
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
            '配置名称，例如：Xometry铝合金标准加工': 'name',
            '报价平台类型；1=Xometry，2=嘉立创': 'site_type',
            '加工材料；存储对应报价平台的具体材料选项': 'material',
            '加工数量；正整数，默认1': 'quantity',
            '表面处理方式；存储对应报价平台的具体表面处理选项': 'surface_finish',
            '平台差异化参数；JSON格式，例如颜色、公差、表面粗糙度等': 'extra_params',
            '是否启用；true=启用，false=禁用': 'enabled',
            '关联图纸ID': 'part_id',
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
                    create_schema = CncPartConfigCreateSchema.model_validate(row)


                    await CncPartConfigCRUD(self.auth, self.db).create(data=create_schema)
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
            '配置名称，例如：Xometry铝合金标准加工',
            '报价平台类型；1=Xometry，2=嘉立创',
            '加工材料；存储对应报价平台的具体材料选项',
            '加工数量；正整数，默认1',
            '表面处理方式；存储对应报价平台的具体表面处理选项',
            '平台差异化参数；JSON格式，例如颜色、公差、表面粗糙度等',
            '是否启用；true=启用，false=禁用',
            '关联图纸ID',
        ]
        selector_header_list = []
        option_list = []


        return ExcelUtil.get_excel_template(
            header_list=header_list,
            selector_header_list=selector_header_list,
            option_list=option_list,
        )
