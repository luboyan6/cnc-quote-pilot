# -*- coding: utf-8 -*-

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class CncPlatformModel(ModelMixin, UserMixin):
    """
    竞价平台表
    """
    __tablename__: str = 'cnc_platform'
    __table_args__: dict[str, str] = {'comment': '竞价平台'}
    name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment='平台名称')
    login_url: Mapped[str | None] = mapped_column(Text, nullable=True, comment='登录地址')
    quote_entry_url: Mapped[str | None] = mapped_column(Text, nullable=True, comment='询价地址')

