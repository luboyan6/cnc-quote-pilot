# -*- coding: utf-8 -*-

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from app.core.base_schema import BaseSchema, UserBySchema, BaseQueryParam, UserByQueryParam
from app.core.validator import DateTimeStr
class CncPartCreateSchema(BaseModel):
    """
    图纸文件新增模型
    """
    extension: str | None = Field(default=None, description='文件扩展名；字典：step=STEP 图纸，stp=STEP 图纸的另一扩展名')
    size_bytes: int | None = Field(default=None, description='文件大小，单位：字节，必须大于 0')
    declared_unit: str | None = Field(default=None, description='图纸声明单位，例如 mm=毫米；为空表示未知，示例并非完整字典')
    validation_status: str | None = Field(default=None, description='文件校验状态；字典：PENDING=待校验，HEADER_VALID=文件头基础检查通过，REJECTED=已拒绝；不代表几何或可加工性通过')
    upload_authorized: bool = Field(default=True, description='第三方上传授权；字典：false=未授权，true=已授权')
    file_path: str | None = Field(default=None, description='文件存储路径')
    file_name: str | None = Field(default=None, description='文件名称')
    file_type: int | None = Field(default=None, description='文件类型')


class CncPartUpdateSchema(BaseModel):
    """
    图纸文件更新模型
    """
    extension: str | None = Field(default=None, description='文件扩展名；字典：step=STEP 图纸，stp=STEP 图纸的另一扩展名')
    size_bytes: int | None = Field(default=None, description='文件大小，单位：字节，必须大于 0')
    declared_unit: str | None = Field(default=None, description='图纸声明单位，例如 mm=毫米；为空表示未知，示例并非完整字典')
    validation_status: str | None = Field(default=None, description='文件校验状态；字典：PENDING=待校验，HEADER_VALID=文件头基础检查通过，REJECTED=已拒绝；不代表几何或可加工性通过')
    upload_authorized: bool | None = Field(default=None, description='第三方上传授权；字典：false=未授权，true=已授权')
    file_path: str | None = Field(default=None, description='文件存储路径')
    file_name: str | None = Field(default=None, description='文件名称')
    file_type: int | None = Field(default=None, description='文件类型')


class CncPartOutSchema(CncPartCreateSchema, BaseSchema, UserBySchema):
    """
    图纸文件响应模型
    """
    model_config = ConfigDict(from_attributes=True)


class CncPartQueryParam(BaseQueryParam, UserByQueryParam):
    """图纸文件查询参数"""

    extension: str | None = Field(None, description="文件扩展名；字典：step=STEP 图纸，stp=STEP 图纸的另一扩展名", json_schema_extra={"q": "like"})
    size_bytes: int | None = Field(None, description="文件大小，单位：字节，必须大于 0", json_schema_extra={"q": "eq"})
    declared_unit: str | None = Field(None, description="图纸声明单位，例如 mm=毫米；为空表示未知，示例并非完整字典", json_schema_extra={"q": "like"})
    validation_status: str | None = Field(None, description="文件校验状态；字典：PENDING=待校验，HEADER_VALID=文件头基础检查通过，REJECTED=已拒绝；不代表几何或可加工性通过", json_schema_extra={"q": "like"})
    upload_authorized: bool | None = Field(None, description="第三方上传授权；字典：false=未授权，true=已授权", json_schema_extra={"q": "eq"})
    file_path: str | None = Field(None, description="文件存储路径", json_schema_extra={"q": "like"})
    file_name: str | None = Field(None, description="文件名称", json_schema_extra={"q": "like"})
    file_type: int | None = Field(None, description="文件类型", json_schema_extra={"q": "eq"})
