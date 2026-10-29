from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema


class CncPartCreateSchema(BaseModel):
    """
    图纸文件新增入参模型
    """

    file_name: str | None = Field(default=None, description="文件名称")
    file_path: str | None = Field(default=None, description="文件存储路径")
    # extension: str | None = Field(default=None, description="文件扩展名；字典：step=STEP 图纸，stp=STEP 图纸的另一扩展名")
    # size_bytes: int | None = Field(default=None, description="文件大小，单位：字节，必须大于 0")
    # declared_unit: str | None = Field(default=None, description="图纸声明单位，例如 mm=毫米；为空表示未知，示例并非完整字典")
    # file_type: int | None = Field(default=None, description="文件类型")


class CncPartUpdateSchema(BaseModel):
    """
    图纸文件更新入参模型
    """

    file_name: str | None = Field(default=None, description="文件名称")
    file_path: str | None = Field(default=None, description="文件存储路径")
    # extension: str | None = Field(default=None, description="文件扩展名；字典：step=STEP 图纸，stp=STEP 图纸的另一扩展名")
    # size_bytes: int | None = Field(default=None, description="文件大小，单位：字节，必须大于 0")
    # declared_unit: str | None = Field(default=None, description="图纸声明单位，例如 mm=毫米；为空表示未知，示例并非完整字典")
    # file_type: int | None = Field(default=None, description="文件类型")


class CncPartListOutSchema(BaseModel):
    """
    图纸文件列表查询响应模型 (仅保留文件名与存储路径)
    """

    model_config = ConfigDict(from_attributes=True)

    file_name: str | None = Field(default=None, description="文件名称")
    file_path: str | None = Field(default=None, description="文件存储路径")


class CncPartOutSchema(CncPartCreateSchema, BaseSchema, UserBySchema):
    """
    图纸文件查询响应模型 (CncPartOutSchema)

    【Agent 阅读与字段解析指南】:
    包含零件图纸的完整信息，用于 Agent 在执行报价或配置工艺前读取图纸元数据。

    关键字段:
    - id (int): 图纸唯一标识 ID。
    - file_name (str | None): 原始文件名（如 'bracket.step'）。
    - file_path (str | None): 服务端存储路径（Agent 获取此路径并在上传阶段加载文件二进制）。
    - extension (str | None): 扩展名 ('step' / 'stp')。
    - size_bytes (int | None): 文件体积（字节）。
    - declared_unit (str | None): 尺寸单位（如 'mm'）。
    - created_time / updated_time: 创建与修改时间。
    - created_id / updated_id: 创建者与修改者信息。
    """

    model_config = ConfigDict(from_attributes=True)


class CncPartQueryParam(BaseQueryParam, UserByQueryParam):
    """
    图纸文件查询过滤参数 (CncPartQueryParam)

    【Agent 查询参数构造指南】:
    用于 GET /cnc/cnc_part/list 接口的 URL Query 参数，各字段标注了后端 SQL 过滤规则：
    - file_name (str | None): 文件名模糊查询 (q='like')，如按名称检索图纸。
    - file_path (str | None): 存储路径模糊查询 (q='like')。
    - 继承审计过滤 (UserByQueryParam): 支持 created_id, updated_id 等过滤。
    """

    file_name: str | None = Field(None, description="文件名称模糊搜索", json_schema_extra={"q": "like"})
    file_path: str | None = Field(None, description="文件存储路径模糊搜索", json_schema_extra={"q": "like"})
    # extension: str | None = Field(None, description="文件扩展名(step/stp)", json_schema_extra={"q": "like"})
    # size_bytes: int | None = Field(None, description="文件大小(字节)", json_schema_extra={"q": "eq"})
    # declared_unit: str | None = Field(None, description="图纸声明单位(例如 mm)", json_schema_extra={"q": "like"})
    # file_type: int | None = Field(None, description="文件类型精确匹配", json_schema_extra={"q": "eq"})
