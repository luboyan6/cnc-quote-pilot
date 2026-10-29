"""JLC CNC China (嘉立创CNC中国站) 加工参数库与约束校验器 (Python).

可供Python程序直接导入并读取 jlc_cnc_params.json，支持：
1. 全量参数查询（材料、表面处理工艺、公差、外观粗糙度、交期档位等）
2. 参数联动约束校验（材料对工艺/公差/粗糙度的约束、工艺间互斥规则、2D图纸触发条件等）
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def get_default_json_path() -> Path:
    # 支持从 backend 目录、项目根目录以及任意相对路径定位 jlc_cnc_params.json
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent.parent / "backend" / "data" / "jlc_cnc_params.json",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "jlc_cnc_params.json",
        Path(__file__).resolve().parent / "jlc_cnc_params.json",
        Path("backend/data/jlc_cnc_params.json").resolve(),
        Path("data/jlc_cnc_params.json").resolve(),
        Path("jlc_cnc_params.json").resolve(),
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def load_jlc_cnc_params(file_path: str | Path | None = None) -> dict[str, Any]:
    """读取并返回完整的嘉立创CNC加工参数与约束规则字典."""
    path = Path(file_path).resolve() if file_path else get_default_json_path()
    if not path.exists():
        raise FileNotFoundError(f"找不到CNC参数定义文件: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class JlcCncParamCatalog:
    """嘉立创CNC加工参数查询与配置校验器."""

    def __init__(self, data: dict[str, Any] | None = None, file_path: str | Path | None = None):
        self.raw_data = data or load_jlc_cnc_params(file_path)
        self.metadata = self.raw_data.get("metadata", {})
        self.params = self.raw_data.get("parameter_definitions", {})
        self.rules = self.raw_data.get("correlation_rules", {})

        # 快速索引字典构建
        self._materials_by_name = {m["name"]: m for m in self.params.get("materials", [])}
        self._materials_by_id = {m["material_id"]: m for m in self.params.get("materials", [])}
        self._crafts_by_name = {c["name"]: c for c in self.params.get("surface_treatments", [])}
        self._crafts_by_id = {c["craft_id"]: c for c in self.params.get("surface_treatments", [])}
        self._tolerances_by_val = {t["value"]: t for t in self.params.get("tolerances", [])}
        self._roughnesses_by_type = {r["type"]: r for r in self.params.get("appearance_roughness", [])}
        self._deliveries_by_code = {d["delivery_type_code"]: d for d in self.params.get("delivery", [])}

    def get_categories(self) -> list[str]:
        return self.params.get("material_categories", [])

    def get_all_materials(self) -> list[dict[str, Any]]:
        return self.params.get("materials", [])

    def get_material_names(self, category: str | None = None) -> list[str]:
        materials = self.params.get("materials", [])
        if category:
            return [m["name"] for m in materials if m["category"] == category]
        return [m["name"] for m in materials]

    def get_material(self, name_or_id: str) -> dict[str, Any] | None:
        return self._materials_by_name.get(name_or_id) or self._materials_by_id.get(name_or_id)

    def get_all_crafts(self) -> list[dict[str, Any]]:
        return self.params.get("surface_treatments", [])

    def get_craft(self, name_or_id: str) -> dict[str, Any] | None:
        return self._crafts_by_name.get(name_or_id) or self._crafts_by_id.get(name_or_id)

    def get_supported_crafts_for_material(self, material_name: str) -> list[dict[str, Any]]:
        mat = self._materials_by_name.get(material_name)
        if not mat:
            return []
        return [self._crafts_by_id[cid] for cid in mat.get("supported_craft_ids", []) if cid in self._crafts_by_id]

    def get_supported_tolerances_for_material(self, material_name: str) -> list[str]:
        mat = self._materials_by_name.get(material_name)
        return mat.get("supported_tolerances", []) if mat else []

    def get_supported_roughness(
        self, material_name: str, selected_craft_names: list[str] | None = None
    ) -> list[str]:
        mat = self._materials_by_name.get(material_name)
        if not mat:
            return []

        base_roughness = set(mat.get("supported_roughnesses", []))
        if not selected_craft_names:
            return [r for r in ["常规外观", "严格外观", "极致外观"] if r in base_roughness]

        craft_roughness_sets = []
        for cname in selected_craft_names:
            craft = self._crafts_by_name.get(cname)
            if craft:
                craft_roughness_sets.append(set(craft.get("allowed_roughness_types", [])))

        if not craft_roughness_sets:
            return list(base_roughness)

        allowed = base_roughness
        for s in craft_roughness_sets:
            allowed = allowed.intersection(s)

        return [r for r in ["常规外观", "严格外观", "极致外观"] if r in allowed]

    def get_delivery_options(self) -> list[dict[str, Any]]:
        return self.params.get("delivery", [])

    def check_craft_mutual_exclusion(self, craft_names: list[str]) -> tuple[bool, list[str]]:
        conflicts = []
        exclusions = self.rules.get("surface_treatment_constraints", {}).get("mutual_exclusions", {})
        for i, c1 in enumerate(craft_names):
            excluded = exclusions.get(c1, [])
            for c2 in craft_names[i + 1 :]:
                if c2 in excluded:
                    conflicts.append(f"工艺 '{c1}' 与 '{c2}' 互斥，不可同时选择")
        return len(conflicts) == 0, conflicts

    def validate_quote_config(
        self,
        *,
        material: str,
        surface_mode: int = 1,
        surface_treatments: list[str] | None = None,
        tolerance: str = "GB/T 1804-2000 m级",
        need_inspection_report: bool = False,
        roughness: str = "常规外观",
        has_thread: bool = False,
        has_assembly: bool = False,
        quantity: int = 1,
        delivery_code: str = "BD",
    ) -> dict[str, Any]:
        errors = []
        drawing_reasons = []

        mat = self._materials_by_name.get(material)
        if not mat:
            errors.append(f"未知材质: '{material}'")
            return {"valid": False, "errors": errors, "requires_2d_drawing": False, "drawing_reasons": []}

        crafts = surface_treatments or []
        if surface_mode == 2:
            if not crafts:
                errors.append("已选择'需要表面处理'模式，但未指定具体表面处理工艺")
            if len(crafts) > 5:
                errors.append(f"表面处理工艺最多选择5项，当前选择了 {len(crafts)} 项")

            supported_crafts = set(mat.get("supported_craft_names", []))
            for c in crafts:
                if c not in supported_crafts:
                    errors.append(f"材质 '{material}' 不支持表面处理工艺: '{c}'")
                craft_def = self._crafts_by_name.get(c)
                if craft_def and craft_def.get("requires_2d_drawing"):
                    drawing_reasons.append(f"表面处理工艺 '{c}' 需要2D图纸明确打标/丝印位置及内容")

            _, conflicts = self.check_craft_mutual_exclusion(crafts)
            errors.extend(conflicts)

        supported_tols = mat.get("supported_tolerances", [])
        if tolerance not in supported_tols:
            errors.append(f"材质 '{material}' 不支持最严公差: '{tolerance}' (支持: {supported_tols})")
        tol_def = self._tolerances_by_val.get(tolerance)
        if tol_def and tol_def.get("requires_2d_drawing"):
            drawing_reasons.append(f"最严公差 '{tolerance}' 需上传2D工程图纸指定关键尺寸公差")

        allowed_roughness = self.get_supported_roughness(material, crafts if surface_mode == 2 else None)
        if roughness not in allowed_roughness:
            errors.append(f"当前材质与表面处理组合下不支持外观要求 '{roughness}' (允许: {allowed_roughness})")
        rough_def = self._roughnesses_by_type.get(roughness)
        if rough_def and rough_def.get("requires_2d_drawing"):
            drawing_reasons.append(f"外观要求 '{roughness}' 需上传2D工程图纸明确外观检测面")

        if has_thread:
            drawing_reasons.append("工件存在螺纹加工，需上传2D图纸标注螺纹规格、螺距与有效螺纹深")

        if has_assembly:
            drawing_reasons.append("工件存在装配关系，需上传装配工程图纸或配合公差说明")

        if not isinstance(quantity, int) or quantity < 1:
            errors.append(f"加工数量必须为大于等于1的整数，当前为: {quantity}")

        if delivery_code not in self._deliveries_by_code:
            errors.append(f"未知交期代码: '{delivery_code}' (支持: UD/BD/ED)")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "requires_2d_drawing": len(drawing_reasons) > 0,
            "drawing_reasons": drawing_reasons,
        }
