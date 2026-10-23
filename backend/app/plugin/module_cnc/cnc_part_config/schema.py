# -*- coding: utf-8 -*-

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from app.core.base_schema import BaseSchema, UserBySchema, BaseQueryParam, UserByQueryParam
from app.core.validator import DateTimeStr
class CncPartConfigCreateSchema(BaseModel):
    """
    图纸参数配置表新增模型
    """
    name: str | None = Field(default=None, description='配置名称，例如：Xometry铝合金标准加工')
    site_type: int | None = Field(default=None, description='报价平台类型；1=Xometry，2=嘉立创')
    material: str | None = Field(default=None, description='加工材料；存储对应报价平台的具体材料选项')
    quantity: int | None = Field(default=None, description='加工数量；正整数，默认1')
    surface_finish: str | None = Field(default=None, description='表面处理方式；存储对应报价平台的具体表面处理选项')
    extra_params: dict | None = Field(default=None, description='平台差异化参数；JSON格式，例如颜色、公差、表面粗糙度等')
    enabled: bool = Field(default=True, description='是否启用；true=启用，false=禁用')
    part_id: int | None = Field(default=None, description='关联图纸ID')


class CncPartConfigUpdateSchema(BaseModel):
    """
    图纸参数配置表更新模型
    """
    name: str | None = Field(default=None, description='配置名称，例如：Xometry铝合金标准加工')
    site_type: int | None = Field(default=None, description='报价平台类型；1=Xometry，2=嘉立创')
    material: str | None = Field(default=None, description='加工材料；存储对应报价平台的具体材料选项')
    quantity: int | None = Field(default=None, description='加工数量；正整数，默认1')
    surface_finish: str | None = Field(default=None, description='表面处理方式；存储对应报价平台的具体表面处理选项')
    extra_params: dict | None = Field(default=None, description='平台差异化参数；JSON格式，例如颜色、公差、表面粗糙度等')
    enabled: bool | None = Field(default=None, description='是否启用；true=启用，false=禁用')
    part_id: int | None = Field(default=None, description='关联图纸ID')


class CncPartConfigOutSchema(CncPartConfigCreateSchema, BaseSchema, UserBySchema):
    """
    图纸参数配置表响应模型
    """
    model_config = ConfigDict(from_attributes=True)


class CncPartConfigQueryParam(BaseQueryParam, UserByQueryParam):
    """图纸参数配置表查询参数"""

    name: str | None = Field(None, description="配置名称，例如：Xometry铝合金标准加工", json_schema_extra={"q": "like"})
    site_type: int | None = Field(None, description="报价平台类型；1=Xometry，2=嘉立创", json_schema_extra={"q": "eq"})
    material: str | None = Field(None, description="加工材料；存储对应报价平台的具体材料选项", json_schema_extra={"q": "like"})
    quantity: int | None = Field(None, description="加工数量；正整数，默认1", json_schema_extra={"q": "eq"})
    surface_finish: str | None = Field(None, description="表面处理方式；存储对应报价平台的具体表面处理选项", json_schema_extra={"q": "like"})
    extra_params: dict | None = Field(None, description="平台差异化参数；JSON格式，例如颜色、公差、表面粗糙度等", json_schema_extra={"q": "eq"})
    enabled: bool | None = Field(None, description="是否启用；true=启用，false=禁用", json_schema_extra={"q": "eq"})
    part_id: int | None = Field(None, description="关联图纸ID", json_schema_extra={"q": "eq"})
