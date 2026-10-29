# -*- coding: utf-8 -*-
"""CNC 私有证据服务。

负责受控私有截图凭据的定位、写入、路径 containment 校验与 Cache-Control: no-store 保护。
"""

from pathlib import Path
from app.config.path_conf import BASE_DIR, STATIC_DIR
from .model import CncQuoteResultModel

# 私有证据存放根目录（严禁置于静态可公开访问目录）
PRIVATE_EVIDENCE_DIR: Path = (BASE_DIR / "data" / "evidence" / "private").resolve()


def ensure_private_evidence_dir() -> Path:
    PRIVATE_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    return PRIVATE_EVIDENCE_DIR


def resolve_evidence_path(result: CncQuoteResultModel) -> Path | None:
    """解析并校验报价结果截图文件的物理路径。

    支持两种证据来源：
    1. 新版受控证据：通过 evidence_id 存放在 PRIVATE_EVIDENCE_DIR，文件名格式为 `{evidence_id}.png`
    2. 兼容历史数据：通过 evidence_screenshot 相对路径（通常在 static/ 或 data/ 下）

    严格执行 path containment 检查，防止路径遍历与越界读取。
    """
    # 1. 优先尝试受控私有证据
    if result.evidence_id:
        # 移除非法字符，防目录遍历
        safe_evidence_id = Path(result.evidence_id).name
        target = (PRIVATE_EVIDENCE_DIR / f"{safe_evidence_id}.png").resolve()
        if target.is_relative_to(PRIVATE_EVIDENCE_DIR) and target.exists() and target.is_file():
            return target

    # 2. 兜底兼容旧版相对路径
    if result.evidence_screenshot:
        rel = str(result.evidence_screenshot).replace("\\", "/").lstrip("/")
        # 防止向上遍历
        if ".." in rel:
            return None

        # 检查是否在私有根目录或 STATIC_DIR 中
        candidate = (BASE_DIR / rel).resolve()
        # 仅允许在 BASE_DIR 内且必须属于 PRIVATE_EVIDENCE_DIR 或 STATIC_DIR
        is_safe = (
            candidate.is_relative_to(PRIVATE_EVIDENCE_DIR)
            or candidate.is_relative_to(STATIC_DIR)
        )
        if is_safe and candidate.exists() and candidate.is_file():
            return candidate

    return None


def store_private_evidence(evidence_id: str, image_bytes: bytes) -> Path:
    """写入新证据到私有目录，返回物理路径。"""
    root = ensure_private_evidence_dir()
    safe_name = Path(evidence_id).name
    file_path = (root / f"{safe_name}.png").resolve()
    if not file_path.is_relative_to(root):
        raise ValueError("Invalid evidence_id for private storage")
    file_path.write_bytes(image_bytes)
    return file_path
