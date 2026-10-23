"""Separate credential writes from public account responses."""

from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema
from app.core.validator import DateTimeStr


class CncAccountCreateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    platform_id: int | None = Field(None, ge=1)
    alias: str | None = Field(None, max_length=100)
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., max_length=255, repr=False)
    login_url: str | None = None
    login_method: str | None = Field("PASSWORD", max_length=24)
    enabled: bool = True
    authorization_note: str | None = Field(None, max_length=2000)


class CncAccountUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    platform_id: int | None = Field(None, ge=1)
    alias: str | None = Field(None, max_length=100)
    username: str | None = Field(None, min_length=1, max_length=64)
    password: str | None = Field(None, max_length=255, repr=False)
    login_url: str | None = None
    login_method: str | None = Field(None, max_length=24)
    enabled: bool | None = None
    authorization_note: str | None = Field(None, max_length=2000)


class CncAccountOutSchema(BaseSchema, UserBySchema):
    model_config = ConfigDict(from_attributes=True)
    platform_id: int | None = None
    platform_name: str | None = None
    alias: str | None = None
    username: str
    login_url: str | None = None
    login_method: str | None = None
    enabled: bool | None = True
    authorization_note: str | None = None
    session_status: str | None = None
    last_verified_at: DateTimeStr | None = None
    auth_expires_at: DateTimeStr | None = None
    has_credentials: bool = False


class CncAccountQueryParam(BaseQueryParam, UserByQueryParam):
    platform_id: int | None = Field(None, json_schema_extra={"q": "eq"})
    alias: str | None = Field(None, json_schema_extra={"q": "like"})
    username: str | None = Field(None, json_schema_extra={"q": "like"})
    login_url: str | None = Field(None, json_schema_extra={"q": "like"})
    login_method: str | None = Field(None, json_schema_extra={"q": "like"})
    session_status: str | None = Field(None, json_schema_extra={"q": "eq"})
    enabled: bool | None = Field(None, json_schema_extra={"q": "eq"})
