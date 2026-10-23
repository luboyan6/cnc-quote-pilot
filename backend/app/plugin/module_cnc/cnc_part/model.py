# -*- coding: utf-8 -*-

from sqlalchemy import String, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class CncPartModel(ModelMixin, UserMixin):
    """
    图纸文件表
    """
    __tablename__: str = 'cnc_part'
    __table_args__: dict[str, str] = {'comment': '图纸文件'}
    extension: Mapped[str | None] = mapped_column(String(8), nullable=True, comment='文件扩展名；字典：step=STEP 图纸，stp=STEP 图纸的另一扩展名')
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment='文件大小，单位：字节，必须大于 0')
    declared_unit: Mapped[str | None] = mapped_column(String(16), nullable=True, comment='图纸声明单位，例如 mm=毫米；为空表示未知，示例并非完整字典')
    validation_status: Mapped[str | None] = mapped_column(String(24), nullable=True, comment='文件校验状态；字典：PENDING=待校验，HEADER_VALID=文件头基础检查通过，REJECTED=已拒绝；不代表几何或可加工性通过')
    upload_authorized: Mapped[bool | None] = mapped_column(Boolean, nullable=True, comment='第三方上传授权；字典：false=未授权，true=已授权')
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment='文件存储路径')
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='文件名称')
    file_type: Mapped[int | None] = mapped_column(String(64), nullable=True, comment='文件类型')

