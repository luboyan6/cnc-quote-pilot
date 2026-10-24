# -*- coding: utf-8 -*-

from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema


class CncPlatformCreateSchema(BaseModel):
    """
    竞价平台新增模型
    """
    name: str = Field(..., min_length=1, max_length=100, description="平台名称")
    login_url: str = Field(..., min_length=1, description="登录地址")
    quote_entry_url: str = Field(..., min_length=1, description="询价地址")


class CncPlatformUpdateSchema(CncPlatformCreateSchema):
    """
    竞价平台更新模型
    """


class CncPlatformOutSchema(BaseSchema, UserBySchema):
    """
    竞价平台响应模型
    """
    model_config = ConfigDict(from_attributes=True)

    name: str | None = Field(default=None, description="平台名称")
    login_url: str | None = Field(default=None, description="登录地址")
    quote_entry_url: str | None = Field(default=None, description="询价地址")


class CncPlatformQueryParam(BaseQueryParam, UserByQueryParam):
    """竞价平台查询参数"""

    name: str | None = Field(None, description="平台名称", json_schema_extra={"q": "like"})
    login_url: str | None = Field(None, description="登录地址", json_schema_extra={"q": "like"})
    quote_entry_url: str | None = Field(None, description="询价地址", json_schema_extra={"q": "like"})
