# -*- coding: utf-8 -*-
"""
生成 CNC 平台图纸参数元数据库与零件配置表增强的 PostgreSQL DDL & DML SQL 脚本。
数据源：
1. backend/data/jlc_cnc_params.json (嘉立创CNC中国站)
2. backend/data/xometry_cnc_params.json (Xometry US)
"""

import json
import uuid
from pathlib import Path


def escape_sql_string(val: str | None) -> str:
    if val is None:
        return "NULL"
    escaped = val.replace("'", "''")
    return f"'{escaped}'"


def escape_sql_json(val: dict | list | None) -> str:
    if val is None:
        return "'{}'::jsonb"
    raw_str = json.dumps(val, ensure_ascii=False)
    escaped = raw_str.replace("'", "''")
    return f"'{escaped}'::jsonb"


def generate_uuid() -> str:
    return uuid.uuid4().hex


def main():
    root_dir = Path(__file__).resolve().parent.parent
    jlc_path = root_dir / "data" / "jlc_cnc_params.json"
    xom_path = root_dir / "data" / "xometry_cnc_params.json"

    with open(jlc_path, "r", encoding="utf-8") as f:
        jlc = json.load(f)

    with open(xom_path, "r", encoding="utf-8") as f:
        xom = json.load(f)

    ddl_statements = []
    dml_statements = []

    # =========================================================================
    # DDL 部分
    # =========================================================================
    ddl_statements.append("""-- ==============================================================================
-- CNC 竞品自动比价 Agent 系统 (CNC Competitor Pricing Agent)
-- CNC 图纸参数配置元数据库与参数联动表 DDL
--
-- 适用数据库: PostgreSQL 14+
-- 包含表:
-- 1. cnc_param_dict (CNC 平台加工参数字典主表)
-- 2. cnc_param_relation (CNC 参数联动关联表: 材料与工艺/公差/粗糙度可用集、工艺互斥)
-- 3. cnc_param_constraint_rule (CNC 业务约束与2D图纸触发规则表)
-- 4. cnc_part_config 结构增强 (对已有图纸参数配置表进行详细配置字段扩充)
-- ==============================================================================

BEGIN;

-- ==============================================================================
-- 1. CNC 平台加工参数字典主表 (cnc_param_dict)
-- 集中存储各平台材料、表面处理、精度公差、表面粗糙度、加工子方式、检验与认证等基础选项
-- ==============================================================================
CREATE TABLE IF NOT EXISTS cnc_param_dict (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(64) NOT NULL UNIQUE,
    platform_code VARCHAR(40) NOT NULL,
    param_type VARCHAR(40) NOT NULL,
    category VARCHAR(100),
    code VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT false,
    sort_order INTEGER NOT NULL DEFAULT 1,
    requires_2d_drawing BOOLEAN NOT NULL DEFAULT false,
    options_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    properties_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    description TEXT,
    
    -- ModelMixin & 审计通用字段
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_time TIMESTAMPTZ,
    created_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    updated_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    deleted_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT uq_cnc_param_dict_platform_type_code UNIQUE (platform_code, param_type, code)
);

COMMENT ON TABLE cnc_param_dict IS 'CNC 平台加工参数字典主表';
COMMENT ON COLUMN cnc_param_dict.id IS '主键ID';
COMMENT ON COLUMN cnc_param_dict.uuid IS '全局唯一UUID';
COMMENT ON COLUMN cnc_param_dict.platform_code IS '平台代码(jlc_cnc_cn, xometry_us)';
COMMENT ON COLUMN cnc_param_dict.param_type IS '参数类型(MATERIAL, SURFACE_FINISH, TOLERANCE, ROUGHNESS, SUBPROCESS, INSPECTION, CERTIFICATION, MARKING, DELIVERY)';
COMMENT ON COLUMN cnc_param_dict.category IS '参数所属类别(材料分类如铝合金、工艺分类如阳极氧化)';
COMMENT ON COLUMN cnc_param_dict.code IS '参数唯一编码/代码(如 SUS304, G45, JGDB1, CLEAR_ANODIZE)';
COMMENT ON COLUMN cnc_param_dict.name IS '参数对外显示名称(如 不锈钢-304, Aluminum 6061-T6x, 喷砂+普通阳极氧化)';
COMMENT ON COLUMN cnc_param_dict.is_default IS '是否该平台或该分类下的默认推荐选项';
COMMENT ON COLUMN cnc_param_dict.sort_order IS '排序权重(越小越靠前)';
COMMENT ON COLUMN cnc_param_dict.requires_2d_drawing IS '选择该参数是否强制触发2D工程图纸上传';
COMMENT ON COLUMN cnc_param_dict.options_schema_json IS '二级子配置属性结构(如颜色/膜厚/光泽度等可选值定义)';
COMMENT ON COLUMN cnc_param_dict.properties_json IS '扩展参数定义(如材料厚度范围、是否金属、成本梯队、公差组)';
COMMENT ON COLUMN cnc_param_dict.description IS '技术选型引导与加工注意事项说明';

CREATE INDEX IF NOT EXISTS ix_cnc_param_dict_query ON cnc_param_dict(platform_code, param_type, category, is_deleted);
CREATE INDEX IF NOT EXISTS ix_cnc_param_dict_code ON cnc_param_dict(platform_code, code);
CREATE INDEX IF NOT EXISTS ix_cnc_param_dict_uuid ON cnc_param_dict(uuid);


-- ==============================================================================
-- 2. CNC 参数联动关联表 (cnc_param_relation)
-- 维护材料所允许的表面处理、材料允许的公差、材料允许的粗糙度以及工艺互斥等关联约束
-- ==============================================================================
CREATE TABLE IF NOT EXISTS cnc_param_relation (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(64) NOT NULL UNIQUE,
    platform_code VARCHAR(40) NOT NULL,
    relation_type VARCHAR(40) NOT NULL,
    source_type VARCHAR(40) NOT NULL,
    source_code VARCHAR(100) NOT NULL,
    target_type VARCHAR(40) NOT NULL,
    target_code VARCHAR(100) NOT NULL,
    is_allowed BOOLEAN NOT NULL DEFAULT true,
    condition_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- ModelMixin & 审计通用字段
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_time TIMESTAMPTZ,
    created_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    updated_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    deleted_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT uq_cnc_param_rel_rule UNIQUE (platform_code, relation_type, source_code, target_code)
);

COMMENT ON TABLE cnc_param_relation IS 'CNC 参数联动与关联约束表';
COMMENT ON COLUMN cnc_param_relation.id IS '主键ID';
COMMENT ON COLUMN cnc_param_relation.uuid IS '全局唯一UUID';
COMMENT ON COLUMN cnc_param_relation.platform_code IS '所属平台代码';
COMMENT ON COLUMN cnc_param_relation.relation_type IS '关系类型(MATERIAL_SUPPORT_FINISH, MATERIAL_SUPPORT_TOLERANCE, MATERIAL_SUPPORT_ROUGHNESS, FINISH_MUTEX, TOLERANCE_RESTRICT_INSPECTION)';
COMMENT ON COLUMN cnc_param_relation.source_type IS '源参数类型(如 MATERIAL, SURFACE_FINISH)';
COMMENT ON COLUMN cnc_param_relation.source_code IS '源项代码/名称(如 铝合金-6061, Aluminum 6061-T6x, 仅喷砂)';
COMMENT ON COLUMN cnc_param_relation.target_type IS '目标参数类型(如 SURFACE_FINISH, TOLERANCE, ROUGHNESS, INSPECTION)';
COMMENT ON COLUMN cnc_param_relation.target_code IS '目标项代码/名称(如 喷砂+普通阳极氧化, ±0.05mm, 钝化)';
COMMENT ON COLUMN cnc_param_relation.is_allowed IS '是否允许/支持(true=支持, false=互斥/不可用)';
COMMENT ON COLUMN cnc_param_relation.condition_json IS '附加条件与限制说明';

CREATE INDEX IF NOT EXISTS ix_cnc_param_rel_lookup ON cnc_param_relation(platform_code, relation_type, source_code, is_allowed);
CREATE INDEX IF NOT EXISTS ix_cnc_param_rel_target ON cnc_param_relation(platform_code, relation_type, target_code);


-- ==============================================================================
-- 3. CNC 业务约束与2D图纸触发规则表 (cnc_param_constraint_rule)
-- 维护高精公差、螺纹攻牙、镶件压铆、特殊工艺等全局联动判定规则
-- ==============================================================================
CREATE TABLE IF NOT EXISTS cnc_param_constraint_rule (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(64) NOT NULL UNIQUE,
    platform_code VARCHAR(40) NOT NULL,
    rule_code VARCHAR(64) NOT NULL,
    rule_name VARCHAR(200) NOT NULL,
    rule_category VARCHAR(40) NOT NULL,
    trigger_condition_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    action_type VARCHAR(40) NOT NULL,
    error_message TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- ModelMixin & 审计通用字段
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_time TIMESTAMPTZ,
    created_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    updated_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    deleted_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT uq_cnc_param_rule_platform_code UNIQUE (platform_code, rule_code)
);

COMMENT ON TABLE cnc_param_constraint_rule IS 'CNC 业务约束与2D图纸触发规则表';
COMMENT ON COLUMN cnc_param_constraint_rule.id IS '主键ID';
COMMENT ON COLUMN cnc_param_constraint_rule.uuid IS '全局唯一UUID';
COMMENT ON COLUMN cnc_param_constraint_rule.platform_code IS '平台代码';
COMMENT ON COLUMN cnc_param_constraint_rule.rule_code IS '规则唯一编号';
COMMENT ON COLUMN cnc_param_constraint_rule.rule_name IS '规则名称';
COMMENT ON COLUMN cnc_param_constraint_rule.rule_category IS '规则类别(DRAWING_2D_TRIGGER, MUTEX_CONSTRAINT, THICKNESS_LIMIT)';
COMMENT ON COLUMN cnc_param_constraint_rule.trigger_condition_json IS '规则触发条件表达式(JSONB结构)';
COMMENT ON COLUMN cnc_param_constraint_rule.action_type IS '触发动作(REQUIRE_2D_DRAWING, FORBID_COMBINATION, WARNING_NOTICE)';
COMMENT ON COLUMN cnc_param_constraint_rule.error_message IS '校验不满足时的友好提示文案';
COMMENT ON COLUMN cnc_param_constraint_rule.is_active IS '是否启用该规则';

CREATE INDEX IF NOT EXISTS ix_cnc_param_rule_lookup ON cnc_param_constraint_rule(platform_code, rule_category, is_active);


-- ==============================================================================
-- 4. 图纸参数配置表增强 (cnc_part_config 结构扩展)
-- 为前端 cnc_part_config 模块提供丰富的结构化详细参数存储字段，完全保持向后兼容
-- ==============================================================================
ALTER TABLE IF EXISTS cnc_part_config 
    ADD COLUMN IF NOT EXISTS material_category VARCHAR(100),
    ADD COLUMN IF NOT EXISTS material_code VARCHAR(100),
    ADD COLUMN IF NOT EXISTS subprocess_code VARCHAR(100),
    ADD COLUMN IF NOT EXISTS surface_finish_code VARCHAR(100),
    ADD COLUMN IF NOT EXISTS surface_finish_options_json JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS tolerance VARCHAR(100),
    ADD COLUMN IF NOT EXISTS roughness VARCHAR(100),
    ADD COLUMN IF NOT EXISTS has_threads BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS thread_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS has_inserts BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS insert_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS inspection_code VARCHAR(100),
    ADD COLUMN IF NOT EXISTS certification_code VARCHAR(100),
    ADD COLUMN IF NOT EXISTS marking_code VARCHAR(100),
    ADD COLUMN IF NOT EXISTS marking_text VARCHAR(255),
    ADD COLUMN IF NOT EXISTS delivery_code VARCHAR(100),
    ADD COLUMN IF NOT EXISTS requires_2d_drawing BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS drawing_2d_file_id INTEGER REFERENCES cnc_part(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS technical_notes TEXT;

COMMENT ON COLUMN cnc_part_config.material_category IS '材料类别(如 铝合金, 不锈钢, Aluminum, Plastic)';
COMMENT ON COLUMN cnc_part_config.material_code IS '材料标准代码(如 SUS304, 6061, P111)';
COMMENT ON COLUMN cnc_part_config.subprocess_code IS '加工方式/子工艺(如 MILLING, TURNING, ROUTER, NO_PREFERENCE)';
COMMENT ON COLUMN cnc_part_config.surface_finish_code IS '表面处理工艺编码(如 JGDB1, ANODIZE_BLACK)';
COMMENT ON COLUMN cnc_part_config.surface_finish_options_json IS '表面处理二级细项配置(如颜色、膜厚、光泽度等)';
COMMENT ON COLUMN cnc_part_config.tolerance IS '选用精度公差(如 ±0.05mm, ±.005″)';
COMMENT ON COLUMN cnc_part_config.roughness IS '外观/表面粗糙度(如 常规外观, 严格外观, 125uin/3.2um Ra)';
COMMENT ON COLUMN cnc_part_config.has_threads IS '是否含螺纹攻牙';
COMMENT ON COLUMN cnc_part_config.thread_count IS '螺纹攻牙孔数';
COMMENT ON COLUMN cnc_part_config.has_inserts IS '是否含压铆螺母/镶件';
COMMENT ON COLUMN cnc_part_config.insert_count IS '镶件安装数量';
COMMENT ON COLUMN cnc_part_config.inspection_code IS '出货检验要求代码(如 CMM全检、出厂检验报告)';
COMMENT ON COLUMN cnc_part_config.certification_code IS '材质证明/质量认证标准(如 C of C, Material certs)';
COMMENT ON COLUMN cnc_part_config.marking_code IS '零件打标/丝印方式代码';
COMMENT ON COLUMN cnc_part_config.marking_text IS '激光打标或丝印内容文本';
COMMENT ON COLUMN cnc_part_config.delivery_code IS '交付周期偏好(加急/标准/经济)';
COMMENT ON COLUMN cnc_part_config.requires_2d_drawing IS '是否需要提供2D工程图纸(由所选公差/螺纹/工艺规则自动综合计算)';
COMMENT ON COLUMN cnc_part_config.drawing_2d_file_id IS '配套关联的2D图纸/PDF文件ID';
COMMENT ON COLUMN cnc_part_config.technical_notes IS '加工技术注意事项及备忘备注';

COMMIT;
""")

    # =========================================================================
    # DML 部分 - JLC 嘉立创数据生成
    # =========================================================================
    jlc_code = "jlc_cnc_cn"
    jlc_defs = jlc.get("parameter_definitions", {})

    dml_statements.append("\n-- ==============================================================================")
    dml_statements.append("-- DML: 插入 嘉立创CNC中国站 (jlc_cnc_cn) 全量加工参数")
    dml_statements.append("-- ==============================================================================\n")
    dml_statements.append("BEGIN;\n")

    # 1. JLC 材料
    for m in jlc_defs.get("materials", []):
        uid = generate_uuid()
        code = m.get("code") or m.get("material_id")
        name = m.get("name")
        cat = m.get("category")
        is_def = "true" if m.get("is_default") else "false"
        sort_order = m.get("sort_order", 1)
        props = {
            "material_id": m.get("material_id"),
            "thickness_limit": m.get("thickness_limit"),
            "default_craft_names": m.get("default_craft_names"),
        }
        desc = m.get("guidance_remark") or ""
        sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{jlc_code}', 'MATERIAL', {escape_sql_string(cat)}, {escape_sql_string(code)}, {escape_sql_string(name)}, {is_def}, {sort_order}, false, '{{}}'::jsonb, {escape_sql_json(props)}, {escape_sql_string(desc)})
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET
name = EXCLUDED.name, category = EXCLUDED.category, properties_json = EXCLUDED.properties_json, description = EXCLUDED.description;"""
        dml_statements.append(sql)

    # 2. JLC 表面处理工艺
    for c in jlc_defs.get("surface_treatments", []):
        uid = generate_uuid()
        code = c.get("code") or c.get("craft_id")
        name = c.get("name")
        cat = c.get("category") or "表面处理"
        req_2d = "true" if c.get("requires_2d_drawing") else "false"
        options = c.get("options") or {}
        props = {
            "craft_id": c.get("craft_id"),
            "allowed_roughness_types": c.get("allowed_roughness_types", []),
            "mutually_exclusive_craft_ids": c.get("mutually_exclusive_craft_ids", []),
        }
        desc = c.get("remark") or ""
        sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{jlc_code}', 'SURFACE_FINISH', {escape_sql_string(cat)}, {escape_sql_string(code)}, {escape_sql_string(name)}, false, 1, {req_2d}, {escape_sql_json(options)}, {escape_sql_json(props)}, {escape_sql_string(desc)})
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET
name = EXCLUDED.name, requires_2d_drawing = EXCLUDED.requires_2d_drawing, options_schema_json = EXCLUDED.options_schema_json, properties_json = EXCLUDED.properties_json, description = EXCLUDED.description;"""
        dml_statements.append(sql)

    # 3. JLC 公差等级
    for idx, t in enumerate(jlc_defs.get("tolerances", []), start=1):
        uid = generate_uuid()
        val = t.get("value")
        code = t.get("tolerance_id") or f"JLC_TOL_{idx}"
        is_def = "true" if t.get("is_default") else "false"
        req_2d = "true" if t.get("requires_2d_drawing") else "false"
        sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{jlc_code}', 'TOLERANCE', '公差标准', {escape_sql_string(code)}, {escape_sql_string(val)}, {is_def}, {idx}, {req_2d}, '{{}}'::jsonb, '{{}}'::jsonb, '嘉立创CNC加工标准精度等级')
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET name = EXCLUDED.name;"""
        dml_statements.append(sql)

    # 4. JLC 粗糙度/外观等级
    for idx, r in enumerate(jlc_defs.get("appearance_roughness", []), start=1):
        uid = generate_uuid()
        val = r.get("type")
        code = r.get("roughness_id") or f"JLC_ROUGH_{idx}"
        is_def = "true" if r.get("is_default") else "false"
        req_2d = "true" if r.get("requires_2d_drawing") else "false"
        sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{jlc_code}', 'ROUGHNESS', '外观粗糙度', {escape_sql_string(code)}, {escape_sql_string(val)}, {is_def}, {idx}, {req_2d}, '{{}}'::jsonb, '{{}}'::jsonb, '嘉立创CNC外观与表面粗糙度要求')
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET name = EXCLUDED.name;"""
        dml_statements.append(sql)

    # 5. JLC 交期档位
    for d in jlc_defs.get("delivery", []):
        uid = generate_uuid()
        code = d.get("delivery_type_code")
        name = d.get("name")
        is_def = "true" if d.get("is_default") else "false"
        sort_order = d.get("sort_order", 1)
        props = {"delivery_hours": d.get("delivery_hours"), "work_days": d.get("work_days")}
        sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{jlc_code}', 'DELIVERY', '交期档位', {escape_sql_string(code)}, {escape_sql_string(name)}, {is_def}, {sort_order}, false, '{{}}'::jsonb, {escape_sql_json(props)}, '嘉立创CNC标准发货周期档位')
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET name = EXCLUDED.name, properties_json = EXCLUDED.properties_json;"""
        dml_statements.append(sql)

    # 6. JLC 检验报告
    insp = jlc_defs.get("inspection_report", {})
    if insp:
        for idx, opt in enumerate(insp.get("options", []), start=1):
            uid = generate_uuid()
            code = f"JLC_INSP_{idx}"
            is_def = "true" if opt == insp.get("default") else "false"
            sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{jlc_code}', 'INSPECTION', '出厂检验', '{code}', {escape_sql_string(opt)}, {is_def}, {idx}, false, '{{}}'::jsonb, '{{}}'::jsonb, {escape_sql_string(insp.get("description"))})
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET name = EXCLUDED.name;"""
            dml_statements.append(sql)

    # 7. JLC 材料联动关联 (Material -> Craft, Tolerance, Roughness)
    for m in jlc_defs.get("materials", []):
        m_name = m.get("name")
        # 材料 -> 支持的表面处理
        for craft_name in m.get("supported_craft_names", []):
            uid = generate_uuid()
            sql = f"""INSERT INTO cnc_param_relation (uuid, platform_code, relation_type, source_type, source_code, target_type, target_code, is_allowed, condition_json)
VALUES ('{uid}', '{jlc_code}', 'MATERIAL_SUPPORT_FINISH', 'MATERIAL', {escape_sql_string(m_name)}, 'SURFACE_FINISH', {escape_sql_string(craft_name)}, true, '{{}}'::jsonb)
ON CONFLICT (platform_code, relation_type, source_code, target_code) DO NOTHING;"""
            dml_statements.append(sql)

        # 材料 -> 支持的公差
        for tol in m.get("supported_tolerances", []):
            uid = generate_uuid()
            sql = f"""INSERT INTO cnc_param_relation (uuid, platform_code, relation_type, source_type, source_code, target_type, target_code, is_allowed, condition_json)
VALUES ('{uid}', '{jlc_code}', 'MATERIAL_SUPPORT_TOLERANCE', 'MATERIAL', {escape_sql_string(m_name)}, 'TOLERANCE', {escape_sql_string(tol)}, true, '{{}}'::jsonb)
ON CONFLICT (platform_code, relation_type, source_code, target_code) DO NOTHING;"""
            dml_statements.append(sql)

        # 材料 -> 支持的粗糙度
        for r_name in m.get("supported_roughnesses", []):
            uid = generate_uuid()
            sql = f"""INSERT INTO cnc_param_relation (uuid, platform_code, relation_type, source_type, source_code, target_type, target_code, is_allowed, condition_json)
VALUES ('{uid}', '{jlc_code}', 'MATERIAL_SUPPORT_ROUGHNESS', 'MATERIAL', {escape_sql_string(m_name)}, 'ROUGHNESS', {escape_sql_string(r_name)}, true, '{{}}'::jsonb)
ON CONFLICT (platform_code, relation_type, source_code, target_code) DO NOTHING;"""
            dml_statements.append(sql)

    # 8. JLC 工艺互斥关联
    for c in jlc_defs.get("surface_treatments", []):
        c_name = c.get("name")
        # 建立与互斥工艺的关系
        mutex_ids = set(c.get("mutually_exclusive_craft_ids", []))
        if mutex_ids:
            for other_c in jlc_defs.get("surface_treatments", []):
                if other_c.get("craft_id") in mutex_ids:
                    uid = generate_uuid()
                    sql = f"""INSERT INTO cnc_param_relation (uuid, platform_code, relation_type, source_type, source_code, target_type, target_code, is_allowed, condition_json)
VALUES ('{uid}', '{jlc_code}', 'FINISH_MUTEX', 'SURFACE_FINISH', {escape_sql_string(c_name)}, 'SURFACE_FINISH', {escape_sql_string(other_c.get("name"))}, false, '{{"conflict": "工艺互斥无法同时选择"}}'::jsonb)
ON CONFLICT (platform_code, relation_type, source_code, target_code) DO NOTHING;"""
                    dml_statements.append(sql)

    # 9. JLC 约束规则
    jlc_rules = jlc.get("correlation_rules", {})
    # 2D 图纸触发规则
    d2d = jlc_rules.get("drawing_2d_triggers", {})
    for idx, cond_item in enumerate(d2d.get("mandatory_2d_conditions", []), start=1):
        uid = generate_uuid()
        code = f"JLC_2D_TRIGGER_{idx}"
        param_name = cond_item.get("parameter") or f"2D图纸触发条件#{idx}"
        vals = cond_item.get("values_triggering_2d", [])
        name = f"2D图纸触发: {param_name}"
        cond = {"parameter": param_name, "values": vals}
        msg = cond_item.get("reason") or "该选项需上传2D工程图纸以明确公差与技术要求"
        sql = f"""INSERT INTO cnc_param_constraint_rule (uuid, platform_code, rule_code, rule_name, rule_category, trigger_condition_json, action_type, error_message, is_active)
VALUES ('{uid}', '{jlc_code}', '{code}', {escape_sql_string(name)}, 'DRAWING_2D_TRIGGER', {escape_sql_json(cond)}, 'REQUIRE_2D_DRAWING', {escape_sql_string(msg)}, true)
ON CONFLICT (platform_code, rule_code) DO UPDATE SET rule_name = EXCLUDED.rule_name, trigger_condition_json = EXCLUDED.trigger_condition_json, error_message = EXCLUDED.error_message;"""
        dml_statements.append(sql)

    dml_statements.append("\nCOMMIT;\n")

    # =========================================================================
    # DML 部分 - Xometry US 数据生成
    # =========================================================================
    xom_code = "xometry_us"
    xom_defs = xom.get("parameter_definitions", {})

    dml_statements.append("\n-- ==============================================================================")
    dml_statements.append("-- DML: 插入 Xometry US (xometry_us) 全量加工参数")
    dml_statements.append("-- ==============================================================================\n")
    dml_statements.append("BEGIN;\n")

    # 1. Xometry 子工艺 (Subprocesses)
    for idx, sub in enumerate(xom_defs.get("subprocesses", []), start=1):
        uid = generate_uuid()
        code = sub.get("code")
        name = sub.get("name")
        is_def = "true" if sub.get("is_default") else "false"
        desc = sub.get("description") or ""
        sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{xom_code}', 'SUBPROCESS', '加工子工艺', {escape_sql_string(code)}, {escape_sql_string(name)}, {is_def}, {idx}, false, '{{}}'::jsonb, '{{}}'::jsonb, {escape_sql_string(desc)})
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;"""
        dml_statements.append(sql)

    # 2. Xometry 材料 (Materials)
    for idx, m in enumerate(xom_defs.get("materials", []), start=1):
        uid = generate_uuid()
        name = m.get("name")
        cat = m.get("category")
        code = name.upper().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "").replace("/", "_")[:50]
        is_def = "true" if m.get("is_default") else "false"
        props = {
            "is_metal": m.get("is_metal"),
            "tolerance_group": m.get("tolerance_group"),
            "cost_tier": m.get("cost_tier"),
        }
        desc = m.get("description") or ""
        sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{xom_code}', 'MATERIAL', {escape_sql_string(cat)}, {escape_sql_string(code)}, {escape_sql_string(name)}, {is_def}, {idx}, false, '{{}}'::jsonb, {escape_sql_json(props)}, {escape_sql_string(desc)})
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET
name = EXCLUDED.name, category = EXCLUDED.category, properties_json = EXCLUDED.properties_json, description = EXCLUDED.description;"""
        dml_statements.append(sql)

    # 3. Xometry 表面处理 (Surface Finishes)
    for idx, f_item in enumerate(xom_defs.get("surface_finishes", []), start=1):
        uid = generate_uuid()
        name = f_item.get("name")
        cat = f_item.get("category")
        code = name.upper().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "").replace("/", "_")[:50]
        is_def = "true" if f_item.get("is_default") else "false"
        req_2d = "true" if f_item.get("requires_2d_drawing") else "false"
        desc = f_item.get("description") or ""
        sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{xom_code}', 'SURFACE_FINISH', {escape_sql_string(cat)}, {escape_sql_string(code)}, {escape_sql_string(name)}, {is_def}, {idx}, {req_2d}, '{{}}'::jsonb, '{{}}'::jsonb, {escape_sql_string(desc)})
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET
name = EXCLUDED.name, category = EXCLUDED.category, requires_2d_drawing = EXCLUDED.requires_2d_drawing, description = EXCLUDED.description;"""
        dml_statements.append(sql)

    # 4. Xometry 精度公差 (Precision Tolerances)
    for idx, t in enumerate(xom_defs.get("precision_tolerances", []), start=1):
        uid = generate_uuid()
        code = t.get("tolerance_id") or f"XOM_TOL_{idx}"
        val = t.get("value")
        is_def = "true" if t.get("is_default") else "false"
        req_2d = "true" if t.get("requires_2d_drawing") else "false"
        props = {"applicable_group": t.get("applicable_group"), "inspection_limit": t.get("inspection_limit")}
        desc = t.get("description") or ""
        sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{xom_code}', 'TOLERANCE', '公差等级', {escape_sql_string(code)}, {escape_sql_string(val)}, {is_def}, {idx}, {req_2d}, '{{}}'::jsonb, {escape_sql_json(props)}, {escape_sql_string(desc)})
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET name = EXCLUDED.name, properties_json = EXCLUDED.properties_json;"""
        dml_statements.append(sql)

    # 5. Xometry 表面粗糙度 (Surface Roughnesses)
    for idx, r in enumerate(xom_defs.get("surface_roughnesses", []), start=1):
        uid = generate_uuid()
        val = r.get("value")
        code = f"XOM_ROUGH_{idx}"
        is_def = "true" if r.get("is_default") else "false"
        req_2d = "true" if r.get("requires_2d_drawing") else "false"
        desc = r.get("description") or ""
        sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{xom_code}', 'ROUGHNESS', '表面粗糙度', '{code}', {escape_sql_string(val)}, {is_def}, {idx}, {req_2d}, '{{}}'::jsonb, '{{}}'::jsonb, {escape_sql_string(desc)})
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET name = EXCLUDED.name;"""
        dml_statements.append(sql)

    # 6. Xometry 检验要求 (Inspections)
    for idx, insp in enumerate(xom_defs.get("inspections", []), start=1):
        uid = generate_uuid()
        code = insp.get("code") or f"XOM_INSP_{idx}"
        name = insp.get("name")
        is_def = "true" if insp.get("is_default") else "false"
        req_rep = insp.get("requires_report", False)
        desc = insp.get("description") or ""
        props = {"requires_report": req_rep}
        sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{xom_code}', 'INSPECTION', '检验等级', {escape_sql_string(code)}, {escape_sql_string(name)}, {is_def}, {idx}, false, '{{}}'::jsonb, {escape_sql_json(props)}, {escape_sql_string(desc)})
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET name = EXCLUDED.name, properties_json = EXCLUDED.properties_json;"""
        dml_statements.append(sql)

    # 7. Xometry 质量认证 (Certifications)
    for idx, cert in enumerate(xom_defs.get("certifications", []), start=1):
        uid = generate_uuid()
        code = cert.get("code") or f"XOM_CERT_{idx}"
        name = cert.get("name")
        desc = cert.get("description") or ""
        sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{xom_code}', 'CERTIFICATION', '质量认证', {escape_sql_string(code)}, {escape_sql_string(name)}, false, {idx}, false, '{{}}'::jsonb, '{{}}'::jsonb, {escape_sql_string(desc)})
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET name = EXCLUDED.name;"""
        dml_statements.append(sql)

    # 8. Xometry 零件打标 (Part Markings)
    for idx, mark in enumerate(xom_defs.get("part_markings", []), start=1):
        uid = generate_uuid()
        name = mark.get("name")
        code = f"XOM_MARK_{idx}"
        req_2d = "true" if mark.get("requires_2d_drawing") else "false"
        desc = mark.get("description") or ""
        sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{xom_code}', 'MARKING', '零件打标', '{code}', {escape_sql_string(name)}, false, {idx}, {req_2d}, '{{}}'::jsonb, '{{}}'::jsonb, {escape_sql_string(desc)})
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET name = EXCLUDED.name;"""
        dml_statements.append(sql)

    # 9. Xometry 交期档位 (Lead Time Tiers)
    for idx, lt in enumerate(xom_defs.get("lead_time_tiers", []), start=1):
        uid = generate_uuid()
        tier = lt.get("tier")
        name = lt.get("display_name")
        desc = lt.get("description") or ""
        is_def = "true" if tier == "Standard" else "false"
        sql = f"""INSERT INTO cnc_param_dict (uuid, platform_code, param_type, category, code, name, is_default, sort_order, requires_2d_drawing, options_schema_json, properties_json, description)
VALUES ('{uid}', '{xom_code}', 'DELIVERY', '交期档位', {escape_sql_string(tier)}, {escape_sql_string(name)}, {is_def}, {idx}, false, '{{}}'::jsonb, '{{}}'::jsonb, {escape_sql_string(desc)})
ON CONFLICT (platform_code, param_type, code) DO UPDATE SET name = EXCLUDED.name;"""
        dml_statements.append(sql)

    # 10. Xometry 材料联动关联 (Material -> Finish, Tolerance, Roughness)
    for m in xom_defs.get("materials", []):
        m_name = m.get("name")
        # 材料 -> 表面处理
        for f_name in m.get("supported_finishes", []):
            uid = generate_uuid()
            sql = f"""INSERT INTO cnc_param_relation (uuid, platform_code, relation_type, source_type, source_code, target_type, target_code, is_allowed, condition_json)
VALUES ('{uid}', '{xom_code}', 'MATERIAL_SUPPORT_FINISH', 'MATERIAL', {escape_sql_string(m_name)}, 'SURFACE_FINISH', {escape_sql_string(f_name)}, true, '{{}}'::jsonb)
ON CONFLICT (platform_code, relation_type, source_code, target_code) DO NOTHING;"""
            dml_statements.append(sql)

        # 材料 -> 公差
        for tol in m.get("supported_tolerances", []):
            uid = generate_uuid()
            sql = f"""INSERT INTO cnc_param_relation (uuid, platform_code, relation_type, source_type, source_code, target_type, target_code, is_allowed, condition_json)
VALUES ('{uid}', '{xom_code}', 'MATERIAL_SUPPORT_TOLERANCE', 'MATERIAL', {escape_sql_string(m_name)}, 'TOLERANCE', {escape_sql_string(tol)}, true, '{{}}'::jsonb)
ON CONFLICT (platform_code, relation_type, source_code, target_code) DO NOTHING;"""
            dml_statements.append(sql)

        # 材料 -> 粗糙度
        for r_val in m.get("supported_roughnesses", []):
            uid = generate_uuid()
            sql = f"""INSERT INTO cnc_param_relation (uuid, platform_code, relation_type, source_type, source_code, target_type, target_code, is_allowed, condition_json)
VALUES ('{uid}', '{xom_code}', 'MATERIAL_SUPPORT_ROUGHNESS', 'MATERIAL', {escape_sql_string(m_name)}, 'ROUGHNESS', {escape_sql_string(r_val)}, true, '{{}}'::jsonb)
ON CONFLICT (platform_code, relation_type, source_code, target_code) DO NOTHING;"""
            dml_statements.append(sql)

    # 11. Xometry 约束规则
    xom_rules = xom.get("correlation_rules", {})
    rule_idx = 1
    # 紧公差触发规则
    tight_tols = xom_rules.get("tight_tolerance_to_drawing_rules", {})
    if tight_tols:
        uid = generate_uuid()
        code = f"XOM_TIGHT_TOL_RULE_{rule_idx}"
        rule_idx += 1
        name = "紧公差要求2D工程图"
        cond = {"triggers": tight_tols.get("triggers", [])}
        msg = tight_tols.get("reason") or "选择紧公差等级必须上传2D工程图纸进行尺寸标注"
        sql = f"""INSERT INTO cnc_param_constraint_rule (uuid, platform_code, rule_code, rule_name, rule_category, trigger_condition_json, action_type, error_message, is_active)
VALUES ('{uid}', '{xom_code}', '{code}', '{name}', 'DRAWING_2D_TRIGGER', {escape_sql_json(cond)}, 'REQUIRE_2D_DRAWING', {escape_sql_string(msg)}, true)
ON CONFLICT (platform_code, rule_code) DO NOTHING;"""
        dml_statements.append(sql)

    # 特殊特征触发2D图纸
    feat_rules = xom_rules.get("feature_to_drawing_rules", {})
    for feat_k, feat_v in feat_rules.items():
        uid = generate_uuid()
        code = f"XOM_FEAT_{feat_k.upper()}"
        name = f"特征触发2D图纸: {feat_k}"
        msg = feat_v.get("reason") or "包含特殊加工特征必须上传2D工程图纸"
        sql = f"""INSERT INTO cnc_param_constraint_rule (uuid, platform_code, rule_code, rule_name, rule_category, trigger_condition_json, action_type, error_message, is_active)
VALUES ('{uid}', '{xom_code}', '{code}', {escape_sql_string(name)}, 'DRAWING_2D_TRIGGER', {escape_sql_json(feat_v)}, 'REQUIRE_2D_DRAWING', {escape_sql_string(msg)}, true)
ON CONFLICT (platform_code, rule_code) DO NOTHING;"""
        dml_statements.append(sql)

    dml_statements.append("\nCOMMIT;\n")

    # =========================================================================
    # 写入文件
    # =========================================================================
    sql_dir = root_dir / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)

    # 1. 完整一体化文件
    full_path = sql_dir / "cnc_param_schema_and_data.sql"
    with open(full_path, "w", encoding="utf-8") as f:
        f.write("".join(ddl_statements))
        f.write("\n\n")
        f.write("\n".join(dml_statements))
    print(f"Generated full SQL script: {full_path}")

    # 2. 纯 DDL 文件
    ddl_path = sql_dir / "create_cnc_param_tables.sql"
    with open(ddl_path, "w", encoding="utf-8") as f:
        f.write("".join(ddl_statements))
    print(f"Generated DDL SQL script: {ddl_path}")

    # 3. 纯 DML 文件
    dml_path = sql_dir / "init_cnc_param_data.sql"
    with open(dml_path, "w", encoding="utf-8") as f:
        f.write("\n".join(dml_statements))
    print(f"Generated DML SQL script: {dml_path}")


if __name__ == "__main__":
    main()
