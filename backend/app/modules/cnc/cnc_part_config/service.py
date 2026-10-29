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
        extra = dict(data.extra_params or {})
        if data.tolerance and "tolerance" not in extra:
            extra["tolerance"] = data.tolerance
        if data.roughness and "roughness" not in extra:
            extra["roughness"] = data.roughness
        if data.subprocess_code and "subprocess" not in extra:
            extra["subprocess"] = data.subprocess_code
        if data.has_threads:
            extra["has_thread"] = "true"
            extra["threads_count"] = str(data.thread_count)
        if data.has_inserts:
            extra["has_insert"] = "true"
            extra["inserts_count"] = str(data.insert_count)
        if data.requires_2d_drawing:
            extra["requires_2d_drawing"] = "true"
        data.extra_params = extra

        obj = await CncPartConfigCRUD(self.auth, self.db).create(data=data)
        return CncPartConfigOutSchema.model_validate(obj)

    async def update(self, id: int, data: CncPartConfigUpdateSchema) -> CncPartConfigOutSchema:
        obj = await CncPartConfigCRUD(self.auth, self.db).get(id=id)
        if not obj:
            raise CustomException(msg="更新失败，该数据不存在")

        extra = dict(data.extra_params if data.extra_params is not None else (obj.extra_params or {}))
        if data.tolerance:
            extra["tolerance"] = data.tolerance
        if data.roughness:
            extra["roughness"] = data.roughness
        if data.subprocess_code:
            extra["subprocess"] = data.subprocess_code
        if data.has_threads is not None:
            extra["has_thread"] = "true" if data.has_threads else "false"
            if data.thread_count is not None:
                extra["threads_count"] = str(data.thread_count)
        if data.has_inserts is not None:
            extra["has_insert"] = "true" if data.has_inserts else "false"
            if data.insert_count is not None:
                extra["inserts_count"] = str(data.insert_count)
        if data.requires_2d_drawing is not None:
            extra["requires_2d_drawing"] = "true" if data.requires_2d_drawing else "false"
        data.extra_params = extra

        obj = await CncPartConfigCRUD(self.auth, self.db).update(id=id, data=data)
        return CncPartConfigOutSchema.model_validate(obj)

    async def get_params_catalog(self, site_type: int | None = None) -> dict:
        """从数据库读取平台参数元数据字典与关联规则"""
        from sqlalchemy import text
        p_code = "jlc_cnc_cn" if site_type == 2 else ("xometry_us" if site_type == 1 else None)
        
        sql_dict = "SELECT platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description FROM cnc_param_dict WHERE is_deleted = false"
        params = {}
        if p_code:
            sql_dict += " AND platform_code = :p_code"
            params["p_code"] = p_code
        sql_dict += " ORDER BY platform_code, param_type, sort_order, id"
        
        dict_rows = (await self.db.execute(text(sql_dict), params)).mappings().all()

        sql_rel = "SELECT platform_code, relation_type, source_code, target_code, is_allowed, condition_json FROM cnc_param_relation WHERE is_deleted = false"
        if p_code:
            sql_rel += " AND platform_code = :p_code"
        sql_rel += " ORDER BY platform_code, id"
        rel_rows = (await self.db.execute(text(sql_rel), params)).mappings().all()

        mat_rel = {}
        for r in rel_rows:
            key = (r["platform_code"], r["source_code"])
            if key not in mat_rel:
                mat_rel[key] = {"finishes": [], "tolerances": [], "roughnesses": []}
            if r["relation_type"] == "MATERIAL_SUPPORT_FINISH" and r["is_allowed"]:
                mat_rel[key]["finishes"].append(r["target_code"])
            elif r["relation_type"] == "MATERIAL_SUPPORT_TOLERANCE" and r["is_allowed"]:
                mat_rel[key]["tolerances"].append(r["target_code"])
            elif r["relation_type"] == "MATERIAL_SUPPORT_ROUGHNESS" and r["is_allowed"]:
                mat_rel[key]["roughnesses"].append(r["target_code"])

        by_platform = {}
        for d in dict_rows:
            plat = d["platform_code"]
            if plat not in by_platform:
                by_platform[plat] = {
                    "platform_code": plat,
                    "material_categories": [],
                    "materials": [],
                    "surface_finishes": [],
                    "tolerances": [],
                    "roughnesses": [],
                    "subprocesses": [],
                    "inspections": [],
                    "certifications": [],
                    "markings": [],
                    "delivery_tiers": [],
                }
            ptype = d["param_type"]
            cat = d["category"]
            item = {
                "code": d["code"],
                "name": d["name"],
                "category": cat,
                "is_default": d["is_default"],
                "requires_2d_drawing": d["requires_2d_drawing"],
                "options_schema": d["options_schema_json"] or {},
                "properties": d["properties_json"] or {},
                "description": d["description"] or "",
            }
            if ptype == "MATERIAL":
                if cat and cat not in by_platform[plat]["material_categories"]:
                    by_platform[plat]["material_categories"].append(cat)
                rel_info = mat_rel.get((plat, d["name"]), {"finishes": [], "tolerances": [], "roughnesses": []})
                item["supported_finishes"] = rel_info["finishes"]
                item["supported_tolerances"] = rel_info["tolerances"]
                item["supported_roughnesses"] = rel_info["roughnesses"]
                by_platform[plat]["materials"].append(item)
            elif ptype == "SURFACE_FINISH":
                by_platform[plat]["surface_finishes"].append(item)
            elif ptype == "TOLERANCE":
                by_platform[plat]["tolerances"].append(item)
            elif ptype == "ROUGHNESS":
                by_platform[plat]["roughnesses"].append(item)
            elif ptype == "SUBPROCESS":
                by_platform[plat]["subprocesses"].append(item)
            elif ptype == "INSPECTION":
                by_platform[plat]["inspections"].append(item)
            elif ptype == "CERTIFICATION":
                by_platform[plat]["certifications"].append(item)
            elif ptype == "MARKING":
                by_platform[plat]["markings"].append(item)
            elif ptype == "DELIVERY":
                by_platform[plat]["delivery_tiers"].append(item)

        if p_code:
            return by_platform.get(p_code, {})
        return by_platform

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

    async def quote(
        self,
        id: int,
        *,
        lead_time_pref: str = "标准",
        quantity_override: int | None = None,
    ) -> dict[str, Any]:
        """对指定零件配置执行在线自动报价（支持嘉立创 JLC CNC 平台）"""
        from app.modules.cnc.quote.jlc_quote_service import quote_part_config

        return await quote_part_config(
            auth=self.auth,
            db=self.db,
            config_id=id,
            lead_time_pref=lead_time_pref,
            quantity_override=quantity_override,
        )

