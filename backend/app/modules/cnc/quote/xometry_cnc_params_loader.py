"""Xometry US CNC 加工参数库与约束校验器 (Python).

可供Python程序直接导入并读取 xometry_cnc_params.json，支持：
1. 全量参数查询（62种材质、28种表面处理、精密公差、表面粗糙度、质检认证、螺纹/镶件/标记等）
2. 参数联动约束校验（金属/塑料公差分组联动、材料与表面处理工艺兼容性约束、经济公差对质检方式的限制、2D工程图纸触发条件等）
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def get_default_json_path() -> Path:
    # 优先查找同目录或 backend/data/ 目录下的 xometry_cnc_params.json
    candidates = [
        Path(__file__).resolve().parent / "xometry_cnc_params.json",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "backend" / "data" / "xometry_cnc_params.json",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "xometry_cnc_params.json",
        Path("backend/data/xometry_cnc_params.json").resolve(),
        Path("xometry_cnc_params.json").resolve(),
        Path("data/xometry_cnc_params.json").resolve(),
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def load_xometry_cnc_params(file_path: str | Path | None = None) -> dict[str, Any]:
    """读取并返回完整的 Xometry US CNC 加工参数与约束规则字典."""
    path = Path(file_path).resolve() if file_path else get_default_json_path()
    if not path.exists():
        raise FileNotFoundError(f"找不到CNC参数定义文件: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class XometryCncParamCatalog:
    """Xometry US CNC 加工参数查询与配置校验器."""

    def __init__(self, data: dict[str, Any] | None = None, file_path: str | Path | None = None):
        self.raw_data = data or load_xometry_cnc_params(file_path)
        self.metadata = self.raw_data.get("metadata", {})
        self.params = self.raw_data.get("parameter_definitions", {})
        self.rules = self.raw_data.get("correlation_rules", {})

        # 快速索引字典构建
        self._materials_by_name = {m["name"]: m for m in self.params.get("materials", [])}
        self._subprocesses_by_name = {s["name"]: s for s in self.params.get("subprocesses", [])}
        self._finishes_by_name = {f["name"]: f for f in self.params.get("surface_finishes", [])}
        self._inspections_by_name = {i["name"]: i for i in self.params.get("inspections", [])}
        self._certifications_by_name = {c["name"]: c for c in self.params.get("certifications", [])}
        self._markings_by_name = {m["name"]: m for m in self.params.get("part_markings", [])}

    # ---------------- 基础查询方法 ----------------

    def get_material_categories(self) -> list[str]:
        """获取所有材料大类名称."""
        return self.params.get("material_categories", [])

    def get_all_materials(self) -> list[dict[str, Any]]:
        """获取所有材质列表 (包含62种材料定义及分类、成本层级与公差分组)."""
        return self.params.get("materials", [])

    def get_material_names(self, category: str | None = None) -> list[str]:
        """获取所有或指定大类下的材质名称列表."""
        materials = self.params.get("materials", [])
        if category:
            return [m["name"] for m in materials if m["category"] == category]
        return [m["name"] for m in materials]

    def get_material(self, name: str) -> dict[str, Any] | None:
        """根据材质名称获取详细定义."""
        return self._materials_by_name.get(name)

    def get_subprocesses(self) -> list[dict[str, Any]]:
        """获取所有推荐子工艺列表 (如 CNC Milling, Turning, Swiss-Type Turning 等)."""
        return self.params.get("subprocesses", [])

    def get_all_finishes(self) -> list[dict[str, Any]]:
        """获取所有表面后处理工艺定义 (如 Anodize, Chem Film, Plating, Passivate 等)."""
        return self.params.get("surface_finishes", [])

    def get_supported_finishes_for_material(self, material_name: str) -> list[str]:
        """获取指定材料支持的所有表面处理工艺名称列表 (基于材料大类与工艺匹配规则)."""
        mat = self._materials_by_name.get(material_name)
        if not mat:
            return []
        cat = mat.get("category", "")
        return self.rules.get("material_to_finish_rules", {}).get(cat, ["Standard", "Bead Blast", "Request finish"])

    def get_supported_tolerances_for_material(self, material_name: str) -> list[str]:
        """获取指定材料支持的精密公差选项 (金属公差组 vs 塑料/复合材料公差组)."""
        mat = self._materials_by_name.get(material_name)
        if not mat:
            return []
        if mat.get("tolerance_group") == "metal":
            return self.rules.get("material_to_tolerance_rules", {}).get("metal_rule", {}).get("allowed_tolerances", [])
        return self.rules.get("material_to_tolerance_rules", {}).get("plastic_and_composite_rule", {}).get("allowed_tolerances", [])

    def get_supported_roughnesses_for_material(self, material_name: str) -> list[str]:
        """获取工件支持的表面粗糙度选项."""
        return [r["value"] for r in self.params.get("surface_roughnesses", [])]

    def get_inspections(self) -> list[dict[str, Any]]:
        """获取所有质检选项定义."""
        return self.params.get("inspections", [])

    def get_certifications(self) -> list[dict[str, Any]]:
        """获取所有资质与认证选项定义 (如 ITAR/EAR, AS9100, ISO 9001 等)."""
        return self.params.get("certifications", [])

    def get_part_markings(self) -> list[dict[str, Any]]:
        """获取零件打标选项列表 (Silkscreen, Ink Stamp, Bag and Tag, Engraving, Laser Mark)."""
        return self.params.get("part_markings", [])

    # ---------------- 关联约束校验方法 ----------------

    def validate_quote_config(
        self,
        *,
        material: str,
        subprocess: str = "No Preference",
        finish: str = "Standard",
        tolerance: str | None = None,
        roughness: str = "125uin/3.2um Ra",
        inspection: str = "Standard Inspection",
        threads_count: int = 0,
        inserts_count: int = 0,
        part_markings: list[str] | None = None,
        certifications: list[str] | None = None,
        quantity: int = 1,
    ) -> dict[str, Any]:
        """全面校验 Xometry CNC 加工参数组合的合法性与关联依赖，并计算是否必须上传2D图纸.

        Returns:
            dict: {
                "valid": bool,
                "errors": list[str],
                "requires_2d_drawing": bool,
                "drawing_reasons": list[str]
            }
        """
        errors: list[str] = []
        drawing_reasons: list[str] = []

        # 1. 材质校验
        mat = self._materials_by_name.get(material)
        if not mat:
            errors.append(f"未知材质: '{material}'")
            return {"valid": False, "errors": errors, "requires_2d_drawing": False, "drawing_reasons": []}

        # 2. 子工艺校验
        if subprocess not in self._subprocesses_by_name:
            errors.append(f"未知加工子工艺: '{subprocess}'")

        # 3. 表面后处理兼容性校验
        supported_finishes = self.get_supported_finishes_for_material(material)
        if finish not in supported_finishes:
            errors.append(f"材质 '{material}' (属于 {mat.get('category')}) 不支持表面处理: '{finish}'")
        finish_def = self._finishes_by_name.get(finish)
        if finish_def and finish_def.get("requires_2d_drawing"):
            drawing_reasons.append(f"表面后处理 '{finish}' 需要在2D图纸中提供具体技术要求与说明")

        # 4. 精密公差校验与联动
        supported_tols = self.get_supported_tolerances_for_material(material)
        actual_tolerance = tolerance or supported_tols[0]
        if actual_tolerance not in supported_tols:
            errors.append(
                f"材质 '{material}' ({mat.get('tolerance_group')}分组) 不支持公差选项: '{actual_tolerance}' "
                f"(允许: {supported_tols})"
            )

        # 严于标准的公差需2D图纸
        if "tighter than" in actual_tolerance.lower():
            drawing_reasons.append(f"精密公差 '{actual_tolerance}' 必须上传2D图纸标注关键尺寸和公差要求")

        # 5. 质检与公差联动校验 (宽松公差仅支持 Standard Inspection)
        if actual_tolerance in ["±.010″ (±0.25mm)", "±.020″ (±0.5mm)"]:
            if inspection != "Standard Inspection":
                errors.append(
                    f"当选择经济宽松公差 '{actual_tolerance}' 时，质检仅支持 'Standard Inspection'，"
                    f"当前选择了 '{inspection}'"
                )
        if inspection not in self._inspections_by_name:
            errors.append(f"未知质检选项: '{inspection}'")

        # 6. 表面粗糙度校验
        valid_roughnesses = [r["value"] for r in self.params.get("surface_roughnesses", [])]
        if roughness not in valid_roughnesses:
            errors.append(f"未知表面粗糙度: '{roughness}' (允许: {valid_roughnesses})")
        elif roughness == "16uin/0.4um Ra":
            drawing_reasons.append("极高表面粗糙度要求 '16uin/0.4um Ra' 必须上传2D图纸指定关键受检面")

        # 7. 螺纹与攻丝孔加工校验
        if threads_count < 0:
            errors.append(f"螺纹孔数量不可为负数: {threads_count}")
        elif threads_count > 0:
            drawing_reasons.append(f"工件包含 {threads_count} 处螺纹加工，必须上传2D图纸注明螺纹规格与深度")

        # 8. 镶件/螺套安装校验
        if inserts_count < 0:
            errors.append(f"镶件数量不可为负数: {inserts_count}")
        elif inserts_count > 0:
            drawing_reasons.append(f"工件包含 {inserts_count} 处镶件安装，必须上传2D图纸注明镶件零件号与装配位置")

        # 9. 零件标记 (Part Marking) 校验
        markings = part_markings or []
        for m in markings:
            m_def = self._markings_by_name.get(m)
            if not m_def:
                errors.append(f"未知零件标记方式: '{m}'")
            elif m_def.get("requires_2d_drawing"):
                drawing_reasons.append(f"零件标记 '{m}' 必须上传2D图纸指定文字内容、颜色或图样坐标")

        # 10. 认证校验
        certs = certifications or []
        for c in certs:
            if c not in self._certifications_by_name:
                errors.append(f"未知认证资质要求: '{c}'")

        # 11. 数量校验
        if not isinstance(quantity, int) or quantity < 1:
            errors.append(f"加工数量必须为大于等于1的整数，当前为: {quantity}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "requires_2d_drawing": len(drawing_reasons) > 0,
            "drawing_reasons": drawing_reasons,
        }
