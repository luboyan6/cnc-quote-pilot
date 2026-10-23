# -*- coding: utf-8 -*-

from sqlalchemy import Boolean, Integer, SmallInteger, BigInteger, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class CncPartConfigModel(ModelMixin, UserMixin):
    """
    图纸参数配置表表
    """
    __tablename__: str = 'cnc_part_config'
    __table_args__: dict[str, str] = {'comment': '图纸参数配置表'}
    # 表主键类型与基类 ModelMixin.id(Integer) 不一致，显式覆盖以保持模型与库结构一致
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True, nullable=False, comment='配置ID，自增主键')
    name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment='配置名称，例如：Xometry铝合金标准加工')
    site_type: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment='报价平台类型；1=Xometry，2=嘉立创')
    material: Mapped[str | None] = mapped_column(String(200), nullable=True, comment='加工材料；存储对应报价平台的具体材料选项')
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True, comment='加工数量；正整数，默认1')
    surface_finish: Mapped[str | None] = mapped_column(String(200), nullable=True, comment='表面处理方式；存储对应报价平台的具体表面处理选项')
    extra_params: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment='平台差异化参数；JSON格式，例如颜色、公差、表面粗糙度等')
    enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True, comment='是否启用；true=启用，false=禁用')
    part_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment='关联图纸ID')

