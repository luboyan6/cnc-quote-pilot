"""Public skill metadata; no filesystem paths or executable endpoints."""

from pydantic import BaseModel, Field


class SkillInfoSchema(BaseModel):
    name: str = Field(description="技能标识")
    description: str = Field(description="技能简介")
    allowed_tools: list[str] = Field(default_factory=list, description="已交付且当前可用的工具")


class SkillDetailSchema(SkillInfoSchema):
    content: str = Field(description="发布的只读技能内容")
