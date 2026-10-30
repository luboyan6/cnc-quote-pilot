from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class CncPartModel(ModelMixin, UserMixin):
    """
    图纸文件模型 (CncPartModel)

    【业务概述】
    表示用于 CNC 机加工报价的 3D CAD 零件图纸实体（主要为 ISO-10303 STEP/STP 格式）。
    图纸是整个 CNC 报价流程的核心输入源：由用户上传并存储，
    经基础格式与文件头解析校验后，关联加工工艺配置（cnc_part_config），
    并由 Agent 通过浏览器自动化操作上传至各供应商平台（立创、Xometry 等）获取报价结果。

    【核心设计与字段说明】
    1. 文件基础存储属性:
       - id (int): 图纸主键 ID (继承自 ModelMixin 自增主键)。
       - file_name (str | None): 原始文件名（例如 'housing_bracket_v2.step'）。
       - file_path (str | None): 本地存储路径或对象存储路径（自动化上传 Agent 根据此路径读取文件字节）。
       - file_type (int | None): 文件类型标识 / 存储分类。
       - extension (str | None): 文件扩展名（小写无点，如 'step', 'stp'）。
       - size_bytes (int | None): 文件大小（字节 Bytes，必须大于 0）。

    2. CAD 规范与单位:
       - declared_unit (str | None): 尺寸单位（如 'mm'=毫米，'in'=英寸；为空表示未知，默认采用毫米）。

    3. 审计与生命周期 (继承自 ModelMixin & UserMixin):
       - created_id / updated_id (int): 创建人与更新人用户 ID，用于数据权限隔离。
       - created_time / updated_time (datetime): 创建时间与最后修改时间。
       - is_deleted (bool): 软删除标记（默认 false，为 true 表示已逻辑删除）。
    """

    __tablename__: str = "cnc_part"
    __table_args__: dict[str, str] = {"comment": "图纸文件"}

    uuid = None
    extension: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="文件扩展名；字典：step=STEP 图纸，stp=STEP 图纸的另一扩展名")
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="文件大小，单位：字节，必须大于 0")
    declared_unit: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="图纸声明单位，例如 mm=毫米；为空表示未知，示例并非完整字典")
    validation_status: Mapped[str | None] = mapped_column(String(24), nullable=True, comment="文件校验状态；字典：PENDING=待校验，HEADER_VALID=文件头基础检查通过，REJECTED=已拒绝；不代表几何或可加工性通过")
    upload_authorized: Mapped[bool | None] = mapped_column(Boolean, nullable=True, comment="第三方上传授权；字典：false=未授权，true=已授权")
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="文件存储路径")
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="文件名称")
    file_type: Mapped[int | None] = mapped_column(String(64), nullable=True, comment="文件类型")
