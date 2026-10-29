# -*- coding: utf-8 -*-

from pydantic import BaseModel, ConfigDict, Field
from app.core.base_schema import BaseSchema, UserBySchema, BaseQueryParam, UserByQueryParam


class CncPartConfigCreateSchema(BaseModel):
    """
    图纸参数配置表新增模型
    """
    name: str | None = Field(default=None, description='配置名称，例如：Xometry铝合金标准加工')
    site_type: int | None = Field(default=None, description='报价平台类型；1=Xometry，2=嘉立创')
    material: str | None = Field(default=None, description='加工材料；存储对应报价平台的具体材料选项')
    quantity: int | None = Field(default=1, description='加工数量；正整数，默认1')
    surface_finish: str | None = Field(default=None, description='表面处理方式；存储对应报价平台的具体表面处理选项')
    extra_params: dict | None = Field(default=None, description='平台差异化参数；JSON格式，例如颜色、公差、表面粗糙度等')
    enabled: bool = Field(default=True, description='是否启用；true=启用，false=禁用')
    part_id: int | None = Field(default=None, description='关联图纸ID')

    # 详细参数扩展
    material_category: str | None = Field(default=None, description='材料分类')
    material_code: str | None = Field(default=None, description='材料代码')
    subprocess_code: str | None = Field(default=None, description='加工方式/子工艺')
    surface_finish_code: str | None = Field(default=None, description='表面处理代码')
    surface_finish_options_json: dict | None = Field(default_factory=dict, description='表面处理二级细项配置')
    tolerance: str | None = Field(default=None, description='选用精度公差')
    roughness: str | None = Field(default=None, description='外观/表面粗糙度')
    has_threads: bool = Field(default=False, description='是否含螺纹攻牙')
    thread_count: int = Field(default=0, description='螺纹攻牙孔数')
    has_inserts: bool = Field(default=False, description='是否含压铆螺母/镶件')
    insert_count: int = Field(default=0, description='镶件安装数量')
    inspection_code: str | None = Field(default=None, description='出货检验要求代码')
    certification_code: str | None = Field(default=None, description='材质证明/质量认证标准')
    marking_code: str | None = Field(default=None, description='零件打标/丝印方式代码')
    marking_text: str | None = Field(default=None, description='打标文本内容')
    delivery_code: str | None = Field(default=None, description='交付周期偏好')
    requires_2d_drawing: bool = Field(default=False, description='是否强制需要2D工程图纸')
    drawing_2d_file_id: int | None = Field(default=None, description='配套2D图纸文件ID')
    technical_notes: str | None = Field(default=None, description='加工技术注意事项说明')


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

    # 详细参数扩展
    material_category: str | None = Field(default=None, description='材料分类')
    material_code: str | None = Field(default=None, description='材料代码')
    subprocess_code: str | None = Field(default=None, description='加工方式/子工艺')
    surface_finish_code: str | None = Field(default=None, description='表面处理代码')
    surface_finish_options_json: dict | None = Field(default=None, description='表面处理二级细项配置')
    tolerance: str | None = Field(default=None, description='选用精度公差')
    roughness: str | None = Field(default=None, description='外观/表面粗糙度')
    has_threads: bool | None = Field(default=None, description='是否含螺纹攻牙')
    thread_count: int | None = Field(default=None, description='螺纹攻牙孔数')
    has_inserts: bool | None = Field(default=None, description='是否含压铆螺母/镶件')
    insert_count: int | None = Field(default=None, description='镶件安装数量')
    inspection_code: str | None = Field(default=None, description='出货检验要求代码')
    certification_code: str | None = Field(default=None, description='材质证明/质量认证标准')
    marking_code: str | None = Field(default=None, description='零件打标/丝印方式代码')
    marking_text: str | None = Field(default=None, description='打标文本内容')
    delivery_code: str | None = Field(default=None, description='交付周期偏好')
    requires_2d_drawing: bool | None = Field(default=None, description='是否强制需要2D工程图纸')
    drawing_2d_file_id: int | None = Field(default=None, description='配套2D图纸文件ID')
    technical_notes: str | None = Field(default=None, description='加工技术注意事项说明')


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
    tolerance: str | None = Field(None, description="选用精度公差", json_schema_extra={"q": "like"})
    requires_2d_drawing: bool | None = Field(None, description="是否强制需要2D图纸", json_schema_extra={"q": "eq"})
