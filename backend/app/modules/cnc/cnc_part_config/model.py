# -*- coding: utf-8 -*-

from sqlalchemy import Boolean, Integer, SmallInteger, BigInteger, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class CncPartConfigModel(ModelMixin, UserMixin):
    """
    图纸参数配置表
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

    # 详细参数扩展字段
    material_category: Mapped[str | None] = mapped_column(String(100), nullable=True, comment='材料分类(如铝合金、不锈钢、Plastic等)')
    material_code: Mapped[str | None] = mapped_column(String(100), nullable=True, comment='材料标准代码(如SUS304, 6061)')
    subprocess_code: Mapped[str | None] = mapped_column(String(100), nullable=True, comment='加工方式/子工艺(如MILLING, TURNING)')
    surface_finish_code: Mapped[str | None] = mapped_column(String(100), nullable=True, comment='表面处理工艺编码')
    surface_finish_options_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict, comment='表面处理二级细项配置(颜色/膜厚等)')
    tolerance: Mapped[str | None] = mapped_column(String(100), nullable=True, comment='选用精度公差(如±0.05mm, ±.005″)')
    roughness: Mapped[str | None] = mapped_column(String(100), nullable=True, comment='外观/表面粗糙度(如常规外观, 125uin/3.2um Ra)')
    has_threads: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment='是否含螺纹攻牙')
    thread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment='螺纹攻牙孔数')
    has_inserts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment='是否含压铆螺母/镶件')
    insert_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment='镶件安装数量')
    inspection_code: Mapped[str | None] = mapped_column(String(100), nullable=True, comment='出货检验要求代码')
    certification_code: Mapped[str | None] = mapped_column(String(100), nullable=True, comment='材质证明/质量认证标准')
    marking_code: Mapped[str | None] = mapped_column(String(100), nullable=True, comment='零件打标/丝印方式代码')
    marking_text: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='打标文本内容')
    delivery_code: Mapped[str | None] = mapped_column(String(100), nullable=True, comment='交付周期偏好')
    requires_2d_drawing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment='是否强制需要2D工程图纸')
    drawing_2d_file_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment='配套2D图纸文件ID')
    technical_notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment='加工技术注意事项说明')
