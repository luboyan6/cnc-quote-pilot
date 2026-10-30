-- ==============================================================================
-- CNC 竞品自动比价 Agent 系统 (CNC Competitor Pricing Agent)
-- PostgreSQL DDL 建表脚本
-- 
-- 规范依据：
-- 1. 项目详细设计: CNC_Competitor_Pricing_Agent_SRS_Design_v1.0.md 第 6 节
-- 2. 实施架构设计: .trellis/tasks/10-21-cnc-pricing-mvp/design.md 第 6 节
-- 3. 基础框架规范: backend/app/core/base_model.py (ModelMixin, UserMixin 兼容整型 ID 与 sys_user 关联)
-- ==============================================================================

BEGIN;

-- ==============================================================================
-- 1. 平台配置表 (cnc_platform)
-- 记录竞品平台信息、官方入口白名单、能力集与检验级别
-- ==============================================================================
CREATE TABLE IF NOT EXISTS cnc_platform (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(64) NOT NULL UNIQUE,
    code VARCHAR(40) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    provider_group VARCHAR(50) NOT NULL,
    region VARCHAR(20) NOT NULL DEFAULT 'US',
    base_url TEXT NOT NULL,
    quote_entry_url TEXT NOT NULL,
    allowed_origins_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    capability_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT true,
    verified_level VARCHAR(20) NOT NULL DEFAULT 'E0',
    verified_at TIMESTAMPTZ,
    min_quote_gap_seconds INTEGER NOT NULL DEFAULT 30,
    max_daily_items INTEGER NOT NULL DEFAULT 60,
    
    -- ModelMixin & 审计通用字段
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_time TIMESTAMPTZ,
    created_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    updated_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    deleted_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE
);

COMMENT ON TABLE cnc_platform IS 'CNC 平台配置表';
COMMENT ON COLUMN cnc_platform.id IS '主键ID';
COMMENT ON COLUMN cnc_platform.uuid IS '全局唯一UUID';
COMMENT ON COLUMN cnc_platform.code IS '平台唯一代码(如 xometry_us, jlc_cnc_cn)';
COMMENT ON COLUMN cnc_platform.name IS '平台展示名称';
COMMENT ON COLUMN cnc_platform.provider_group IS '独立服务商分组标识';
COMMENT ON COLUMN cnc_platform.region IS '地区/国家代码(US, CN)';
COMMENT ON COLUMN cnc_platform.base_url IS '官方主页入口';
COMMENT ON COLUMN cnc_platform.quote_entry_url IS '官方报价下单入口';
COMMENT ON COLUMN cnc_platform.allowed_origins_json IS '允许出站的精确域名白名单';
COMMENT ON COLUMN cnc_platform.capability_json IS '平台能力集(文件上限/支持工艺/参数定义)';
COMMENT ON COLUMN cnc_platform.enabled IS '是否启用平台';
COMMENT ON COLUMN cnc_platform.verified_level IS '实测验证等级(E0~E3)';
COMMENT ON COLUMN cnc_platform.verified_at IS '最近验证通过时间';
COMMENT ON COLUMN cnc_platform.min_quote_gap_seconds IS '两次报价最小安全间隔秒数';
COMMENT ON COLUMN cnc_platform.max_daily_items IS '单日最大询价明细限制';

CREATE INDEX IF NOT EXISTS ix_cnc_platform_enabled_group ON cnc_platform(enabled, provider_group);
CREATE INDEX IF NOT EXISTS ix_cnc_platform_uuid ON cnc_platform(uuid);


-- ==============================================================================
-- 2. 平台账号表 (cnc_account)
-- 存储平台加密凭据、加密浏览器会话 Session 与有效性状态
-- ==============================================================================
CREATE TABLE IF NOT EXISTS cnc_account (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(64) NOT NULL UNIQUE,
    platform_id INTEGER NOT NULL REFERENCES cnc_platform(id) ON DELETE CASCADE ON UPDATE CASCADE,
    owner_id INTEGER NOT NULL REFERENCES sys_user(id) ON DELETE CASCADE ON UPDATE CASCADE,
    alias VARCHAR(64) NOT NULL,
    login_method VARCHAR(32) NOT NULL DEFAULT 'PASSWORD',
    credential_ciphertext BYTEA,
    session_ciphertext BYTEA,
    key_id VARCHAR(64),
    session_version INTEGER NOT NULL DEFAULT 1,
    account_fingerprint VARCHAR(128),
    pricing_context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    session_status VARCHAR(32) NOT NULL DEFAULT 'UNKNOWN',
    last_verified_at TIMESTAMPTZ,
    auth_expires_at TIMESTAMPTZ,
    enabled BOOLEAN NOT NULL DEFAULT true,
    authorization_note TEXT,
    
    -- ModelMixin & 审计通用字段
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_time TIMESTAMPTZ,
    created_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    updated_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    deleted_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT uq_cnc_account_platform_owner_alias UNIQUE (platform_id, owner_id, alias)
);

COMMENT ON TABLE cnc_account IS 'CNC 平台账号表';
COMMENT ON COLUMN cnc_account.platform_id IS '关联平台ID';
COMMENT ON COLUMN cnc_account.owner_id IS '账号责任人ID(关联 sys_user)';
COMMENT ON COLUMN cnc_account.alias IS '脱敏别名';
COMMENT ON COLUMN cnc_account.login_method IS '登录方式(PASSWORD, OTP, SSO, MANUAL_SESSION)';
COMMENT ON COLUMN cnc_account.credential_ciphertext IS '加密密码/凭据(AES-GCM密文)';
COMMENT ON COLUMN cnc_account.session_ciphertext IS '加密会话Cookie/Storage(AES-GCM密文)';
COMMENT ON COLUMN cnc_account.key_id IS '加密密钥标识';
COMMENT ON COLUMN cnc_account.session_version IS '会话更新版本(并发控制)';
COMMENT ON COLUMN cnc_account.account_fingerprint IS '账号匿名身份指纹';
COMMENT ON COLUMN cnc_account.pricing_context_json IS '客户等级、税收与地区商业上下文';
COMMENT ON COLUMN cnc_account.session_status IS '会话状态(UNKNOWN, VALID, EXPIRED, CHALLENGE, REVOKED)';
COMMENT ON COLUMN cnc_account.last_verified_at IS '最近一次会话有效性验证时间';
COMMENT ON COLUMN cnc_account.auth_expires_at IS '会话失效预估时间';
COMMENT ON COLUMN cnc_account.enabled IS '是否启用该账号';
COMMENT ON COLUMN cnc_account.authorization_note IS '授权备忘说明';

CREATE INDEX IF NOT EXISTS ix_cnc_account_platform_enabled ON cnc_account(platform_id, enabled);
CREATE INDEX IF NOT EXISTS ix_cnc_account_owner_id ON cnc_account(owner_id);
CREATE INDEX IF NOT EXISTS ix_cnc_account_session_status ON cnc_account(session_status);
CREATE INDEX IF NOT EXISTS ix_cnc_account_uuid ON cnc_account(uuid);


-- ==============================================================================
-- 3. CAD 图纸零件表 (cnc_part)
-- 对应 SRS 规格中 cnc_step_file，存储 3D STEP/STP 文件元数据与私有存储键
-- ==============================================================================
CREATE TABLE IF NOT EXISTS cnc_part (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(64) NOT NULL UNIQUE,
    owner_id INTEGER NOT NULL REFERENCES sys_user(id) ON DELETE CASCADE ON UPDATE CASCADE,
    original_name VARCHAR(255) NOT NULL,
    extension VARCHAR(16) NOT NULL DEFAULT 'step',
    sha256 CHAR(64) NOT NULL,
    size_bytes BIGINT NOT NULL CHECK (size_bytes > 0),
    storage_key TEXT NOT NULL UNIQUE,
    declared_unit VARCHAR(16) NOT NULL DEFAULT 'mm',
    geometry_info_json JSONB DEFAULT '{}'::jsonb,
    revoked_at TIMESTAMPTZ,
    retained_until TIMESTAMPTZ,
    
    -- ModelMixin & 审计通用字段
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_time TIMESTAMPTZ,
    created_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    updated_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    deleted_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT uq_cnc_part_owner_sha256 UNIQUE (owner_id, sha256)
);

COMMENT ON TABLE cnc_part IS 'CNC 3D 图纸零件表';
COMMENT ON COLUMN cnc_part.owner_id IS '文件所有者ID(关联 sys_user)';
COMMENT ON COLUMN cnc_part.original_name IS '图纸原始文件名';
COMMENT ON COLUMN cnc_part.extension IS '文件扩展名(step, stp)';
COMMENT ON COLUMN cnc_part.sha256 IS '文件SHA256哈希指纹';
COMMENT ON COLUMN cnc_part.size_bytes IS '文件大小(字节)';
COMMENT ON COLUMN cnc_part.storage_key IS '私有对象存储Key(非物理路径)';
COMMENT ON COLUMN cnc_part.declared_unit IS '声明尺寸单位(mm, inch)';
COMMENT ON COLUMN cnc_part.geometry_info_json IS '几何尺寸与特征信息(包围盒/体积)';
COMMENT ON COLUMN cnc_part.revoked_at IS '授权撤回时间';
COMMENT ON COLUMN cnc_part.retained_until IS '文件保存到期时间';

CREATE INDEX IF NOT EXISTS ix_cnc_part_owner_created ON cnc_part(owner_id, created_time);
CREATE INDEX IF NOT EXISTS ix_cnc_part_sha256 ON cnc_part(sha256);
CREATE INDEX IF NOT EXISTS ix_cnc_part_uuid ON cnc_part(uuid);


-- ==============================================================================
-- 4. 报价批次任务表 (cnc_quote_task)
-- 管理批量比价任务生命周期、触发源、幂等去重与总体状态
-- ==============================================================================
CREATE TABLE IF NOT EXISTS cnc_quote_task (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(64) NOT NULL UNIQUE,
    owner_id INTEGER NOT NULL REFERENCES sys_user(id) ON DELETE CASCADE ON UPDATE CASCADE,
    parent_task_id INTEGER REFERENCES cnc_quote_task(id) ON DELETE SET NULL,
    schedule_id INTEGER,
    trigger_type VARCHAR(32) NOT NULL DEFAULT 'MANUAL',
    idempotency_key VARCHAR(128),
    request_hash CHAR(64),
    template_version INTEGER NOT NULL DEFAULT 1,
    template_snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'QUEUED',
    total_items INTEGER NOT NULL DEFAULT 0,
    succeeded_items INTEGER NOT NULL DEFAULT 0,
    failed_items INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    cancel_requested_at TIMESTAMPTZ,
    deadline_at TIMESTAMPTZ,
    
    -- ModelMixin & 审计通用字段
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_time TIMESTAMPTZ,
    created_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    updated_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    deleted_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT uq_cnc_quote_task_owner_idempotency UNIQUE (owner_id, idempotency_key)
);

COMMENT ON TABLE cnc_quote_task IS 'CNC 报价批次任务表';
COMMENT ON COLUMN cnc_quote_task.owner_id IS '任务发起人ID';
COMMENT ON COLUMN cnc_quote_task.parent_task_id IS '重试/重跑来源批次ID';
COMMENT ON COLUMN cnc_quote_task.schedule_id IS '定时计划ID(若由计划触发)';
COMMENT ON COLUMN cnc_quote_task.trigger_type IS '触发类型(MANUAL, SCHEDULE, RETRY)';
COMMENT ON COLUMN cnc_quote_task.idempotency_key IS '客户端请求幂等键';
COMMENT ON COLUMN cnc_quote_task.request_hash IS '请求参数内容哈希(防同键异参)';
COMMENT ON COLUMN cnc_quote_task.template_version IS '使用的模板版本号';
COMMENT ON COLUMN cnc_quote_task.template_snapshot_json IS '冻结的批次参数快照';
COMMENT ON COLUMN cnc_quote_task.status IS '任务状态(QUEUED, RUNNING, WAITING, SUCCEEDED, PARTIAL, FAILED, CANCELLED)';
COMMENT ON COLUMN cnc_quote_task.total_items IS '包含的询价明细总数';
COMMENT ON COLUMN cnc_quote_task.succeeded_items IS '成功取得报价的明细数';
COMMENT ON COLUMN cnc_quote_task.failed_items IS '失败的明细数';
COMMENT ON COLUMN cnc_quote_task.started_at IS '开始执行时间';
COMMENT ON COLUMN cnc_quote_task.finished_at IS '执行完成时间';
COMMENT ON COLUMN cnc_quote_task.cancel_requested_at IS '请求取消时间';
COMMENT ON COLUMN cnc_quote_task.deadline_at IS '任务绝对超时时间';

CREATE INDEX IF NOT EXISTS ix_cnc_quote_task_status_created ON cnc_quote_task(status, created_time);
CREATE INDEX IF NOT EXISTS ix_cnc_quote_task_owner_created ON cnc_quote_task(owner_id, created_time);
CREATE INDEX IF NOT EXISTS ix_cnc_quote_task_uuid ON cnc_quote_task(uuid);


-- ==============================================================================
-- 5. 报价明细项表 (cnc_quote_item)
-- 询价最小原子单元，绑定任务、图纸、账号及单次询价参数
-- ==============================================================================
CREATE TABLE IF NOT EXISTS cnc_quote_item (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(64) NOT NULL UNIQUE,
    task_id INTEGER NOT NULL REFERENCES cnc_quote_task(id) ON DELETE CASCADE ON UPDATE CASCADE,
    part_id INTEGER NOT NULL REFERENCES cnc_part(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    account_id INTEGER NOT NULL REFERENCES cnc_account(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    item_key CHAR(64) NOT NULL,
    requested_hash CHAR(64) NOT NULL,
    requested_params_json JSONB NOT NULL,
    effective_params_json JSONB,
    parameter_hash CHAR(64),
    comparison_group_hash CHAR(64),
    adapter_version VARCHAR(64) NOT NULL,
    mapping_version VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'QUEUED',
    phase VARCHAR(32) NOT NULL DEFAULT 'SESSION_CHECK',
    quote_status VARCHAR(32),
    attempt_no INTEGER NOT NULL DEFAULT 0,
    retry_count INTEGER NOT NULL DEFAULT 0,
    reauth_count INTEGER NOT NULL DEFAULT 0,
    lease_owner VARCHAR(64),
    lease_until TIMESTAMPTZ,
    execution_version INTEGER NOT NULL DEFAULT 1,
    quote_intent_at TIMESTAMPTZ,
    remote_quote_id VARCHAR(128),
    error_code VARCHAR(64),
    error_detail_redacted TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    active_elapsed_ms BIGINT NOT NULL DEFAULT 0,
    human_wait_ms BIGINT NOT NULL DEFAULT 0,
    review_wait_ms BIGINT NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ,
    queue_deadline_at TIMESTAMPTZ,
    
    -- ModelMixin & 审计通用字段
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_time TIMESTAMPTZ,
    created_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    updated_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    deleted_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT uq_cnc_quote_item_task_key UNIQUE (task_id, item_key)
);

COMMENT ON TABLE cnc_quote_item IS 'CNC 报价明细项表';
COMMENT ON COLUMN cnc_quote_item.task_id IS '所属批次任务ID';
COMMENT ON COLUMN cnc_quote_item.part_id IS '关联图纸零件ID';
COMMENT ON COLUMN cnc_quote_item.account_id IS '执行账号ID(平台由账号推导)';
COMMENT ON COLUMN cnc_quote_item.item_key IS '批次内组合去重唯一键';
COMMENT ON COLUMN cnc_quote_item.requested_hash IS '规范请求参数哈希';
COMMENT ON COLUMN cnc_quote_item.requested_params_json IS '用户要求参数快照(材料/表面/数量/公差)';
COMMENT ON COLUMN cnc_quote_item.effective_params_json IS '平台回显生效的参数';
COMMENT ON COLUMN cnc_quote_item.parameter_hash IS '完整有效参数指纹';
COMMENT ON COLUMN cnc_quote_item.comparison_group_hash IS '跨平台可比分组哈希';
COMMENT ON COLUMN cnc_quote_item.adapter_version IS '使用的适配器/插件版本';
COMMENT ON COLUMN cnc_quote_item.mapping_version IS '参数映射版本';
COMMENT ON COLUMN cnc_quote_item.status IS '状态(QUEUED, RUNNING, RETRY_WAIT, WAITING_HUMAN, WAITING_REVIEW, SUCCEEDED, NON_QUOTED, FAILED, TIMED_OUT, CANCELLED)';
COMMENT ON COLUMN cnc_quote_item.phase IS '当前阶段(SESSION_CHECK, UPLOADING, CONFIGURING, EXTRACTING 等)';
COMMENT ON COLUMN cnc_quote_item.quote_status IS '最近报价性质(QUOTED, PENDING_REVIEW, REFERENCE_ESTIMATE, NO_QUOTE, FAILED)';
COMMENT ON COLUMN cnc_quote_item.attempt_no IS '当前尝试轮次';
COMMENT ON COLUMN cnc_quote_item.retry_count IS '自动重试次数';
COMMENT ON COLUMN cnc_quote_item.reauth_count IS '重新认证次数';
COMMENT ON COLUMN cnc_quote_item.lease_owner IS '当前持有执行租约的 Worker';
COMMENT ON COLUMN cnc_quote_item.lease_until IS '租约有效截止时间';
COMMENT ON COLUMN cnc_quote_item.execution_version IS '乐观锁版本';
COMMENT ON COLUMN cnc_quote_item.quote_intent_at IS '进入最终点击提交意图时间';
COMMENT ON COLUMN cnc_quote_item.remote_quote_id IS '竞品站方生成的报价ID/零件ID';
COMMENT ON COLUMN cnc_quote_item.error_code IS '规范化业务错误代码';
COMMENT ON COLUMN cnc_quote_item.error_detail_redacted IS '脱敏后的错误详情';
COMMENT ON COLUMN cnc_quote_item.active_elapsed_ms IS '有效执行耗时(毫秒)';
COMMENT ON COLUMN cnc_quote_item.human_wait_ms IS '等待人工干预耗时(毫秒)';
COMMENT ON COLUMN cnc_quote_item.review_wait_ms IS '等待站方人工审核耗时(毫秒)';

CREATE INDEX IF NOT EXISTS ix_cnc_quote_item_status_next ON cnc_quote_item(status, next_attempt_at);
CREATE INDEX IF NOT EXISTS ix_cnc_quote_item_account_status ON cnc_quote_item(account_id, status);
CREATE INDEX IF NOT EXISTS ix_cnc_quote_item_param_created ON cnc_quote_item(parameter_hash, created_time);
CREATE INDEX IF NOT EXISTS ix_cnc_quote_item_lease_until ON cnc_quote_item(lease_until);
CREATE INDEX IF NOT EXISTS ix_cnc_quote_item_uuid ON cnc_quote_item(uuid);


-- ==============================================================================
-- 6. 报价结果与历史观测表 (cnc_quote_result)
-- 对应 SRS 中 cnc_quote_observation，采用追加写入(Append-Only)保证价格历史可追溯
-- ==============================================================================
CREATE TABLE IF NOT EXISTS cnc_quote_result (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(64) NOT NULL UNIQUE,
    item_id INTEGER NOT NULL REFERENCES cnc_quote_item(id) ON DELETE CASCADE ON UPDATE CASCADE,
    revision INTEGER NOT NULL DEFAULT 1,
    quote_status VARCHAR(32) NOT NULL,
    source_mode VARCHAR(32) NOT NULL DEFAULT 'INSTANT',
    unit_price NUMERIC(14, 4),
    line_subtotal NUMERIC(14, 4),
    tax_amount NUMERIC(14, 4),
    shipping_amount NUMERIC(14, 4),
    discount_amount NUMERIC(14, 4),
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    currency_scale INTEGER NOT NULL DEFAULT 2,
    price_scope VARCHAR(32) NOT NULL DEFAULT 'PARTS_ONLY',
    lead_time_raw TEXT,
    lead_time_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    platform_quote_id VARCHAR(128),
    platform_part_id VARCHAR(128),
    source_url_redacted TEXT,
    quoted_at TIMESTAMPTZ,
    observed_at TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    freshness_status VARCHAR(32) NOT NULL DEFAULT 'CURRENT_CONFIRMED',
    freshness_proof_json JSONB DEFAULT '{}'::jsonb,
    parameter_snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    parameter_hash CHAR(64) NOT NULL,
    comparison_group_hash CHAR(64),
    observation_fingerprint CHAR(64) NOT NULL,
    raw_text_redacted TEXT,
    
    -- ModelMixin & 审计通用字段
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_time TIMESTAMPTZ,
    created_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    updated_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    deleted_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,

    CONSTRAINT uq_cnc_quote_result_item_revision UNIQUE (item_id, revision),
    CONSTRAINT uq_cnc_quote_result_item_fingerprint UNIQUE (item_id, observation_fingerprint)
);

COMMENT ON TABLE cnc_quote_result IS 'CNC 报价结果与历史观测表';
COMMENT ON COLUMN cnc_quote_result.item_id IS '关联报价明细ID';
COMMENT ON COLUMN cnc_quote_result.revision IS '同明细多版本序号(追加更新)';
COMMENT ON COLUMN cnc_quote_result.quote_status IS '报价性质(QUOTED, PENDING_REVIEW, REFERENCE_ESTIMATE, NO_QUOTE, FAILED)';
COMMENT ON COLUMN cnc_quote_result.source_mode IS '来源模式(INSTANT 即时报价, MANUAL_REVIEW 人工审核)';
COMMENT ON COLUMN cnc_quote_result.unit_price IS '平台单价';
COMMENT ON COLUMN cnc_quote_result.line_subtotal IS '零件行总价';
COMMENT ON COLUMN cnc_quote_result.tax_amount IS '税额(未知填 null)';
COMMENT ON COLUMN cnc_quote_result.shipping_amount IS '运费(未知填 null)';
COMMENT ON COLUMN cnc_quote_result.discount_amount IS '优惠减免金额';
COMMENT ON COLUMN cnc_quote_result.currency IS '货币代码(USD, CNY, EUR)';
COMMENT ON COLUMN cnc_quote_result.currency_scale IS '货币小数位数';
COMMENT ON COLUMN cnc_quote_result.price_scope IS '价格包含口径(PARTS_ONLY 纯件, INCL_TAX 含税, DELIVERED 到手价)';
COMMENT ON COLUMN cnc_quote_result.lead_time_raw IS '平台交期原文(如 Arrives by Oct 28)';
COMMENT ON COLUMN cnc_quote_result.lead_time_json IS '结构化交期(工作日、发货日、到货日及起算规则)';
COMMENT ON COLUMN cnc_quote_result.platform_quote_id IS '竞品站方报价单号';
COMMENT ON COLUMN cnc_quote_result.platform_part_id IS '竞品站方零件识别码';
COMMENT ON COLUMN cnc_quote_result.source_url_redacted IS '脱敏后报价页面URL';
COMMENT ON COLUMN cnc_quote_result.quoted_at IS '站方出价时间戳';
COMMENT ON COLUMN cnc_quote_result.observed_at IS '本地自动化抓取观测时间戳';
COMMENT ON COLUMN cnc_quote_result.valid_until IS '报价有效期截止时间';
COMMENT ON COLUMN cnc_quote_result.freshness_status IS '新鲜度状态(RECALCULATED, CURRENT_CONFIRMED, CACHE_UNVERIFIED)';
COMMENT ON COLUMN cnc_quote_result.freshness_proof_json IS '新鲜度证据快照(网络报文/重新计价事件)';
COMMENT ON COLUMN cnc_quote_result.parameter_snapshot_json IS '报价时的完整有效参数快照';
COMMENT ON COLUMN cnc_quote_result.parameter_hash IS '完整参数指纹';
COMMENT ON COLUMN cnc_quote_result.comparison_group_hash IS '可比分组指纹';
COMMENT ON COLUMN cnc_quote_result.observation_fingerprint IS '观测数据内容指纹(防重复观测)';
COMMENT ON COLUMN cnc_quote_result.raw_text_redacted IS '价格及周边区域脱敏文本';

CREATE INDEX IF NOT EXISTS ix_cnc_quote_result_param_observed ON cnc_quote_result(parameter_hash, observed_at);
CREATE INDEX IF NOT EXISTS ix_cnc_quote_result_group_observed ON cnc_quote_result(comparison_group_hash, observed_at);
CREATE INDEX IF NOT EXISTS ix_cnc_quote_result_status_observed ON cnc_quote_result(quote_status, observed_at);
CREATE INDEX IF NOT EXISTS ix_cnc_quote_result_uuid ON cnc_quote_result(uuid);


-- ==============================================================================
-- 7. 定时监测计划表 (cnc_schedule)
-- 对应 SRS 中 cnc_monitor_schedule，配置周期性自动化比价计划
-- ==============================================================================
CREATE TABLE IF NOT EXISTS cnc_schedule (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(64) NOT NULL UNIQUE,
    owner_id INTEGER NOT NULL REFERENCES sys_user(id) ON DELETE CASCADE ON UPDATE CASCADE,
    name VARCHAR(128) NOT NULL,
    cron_expression VARCHAR(64),
    interval_minutes INTEGER NOT NULL DEFAULT 1440 CHECK (interval_minutes >= 5),
    timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Shanghai',
    template_version INTEGER NOT NULL DEFAULT 1,
    template_snapshot_json JSONB NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    next_run_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- ModelMixin & 审计通用字段
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_time TIMESTAMPTZ,
    created_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    updated_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    deleted_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE
);

COMMENT ON TABLE cnc_schedule IS 'CNC 定时监测计划表';
COMMENT ON COLUMN cnc_schedule.owner_id IS '计划责任人ID';
COMMENT ON COLUMN cnc_schedule.name IS '监测计划名称';
COMMENT ON COLUMN cnc_schedule.cron_expression IS 'Cron表达式';
COMMENT ON COLUMN cnc_schedule.interval_minutes IS '执行间隔分钟数(>=5)';
COMMENT ON COLUMN cnc_schedule.timezone IS '调度时区';
COMMENT ON COLUMN cnc_schedule.template_version IS '使用的模板版本号';
COMMENT ON COLUMN cnc_schedule.template_snapshot_json IS '冻结的比价批次配置模板';
COMMENT ON COLUMN cnc_schedule.enabled IS '计划启用开关';
COMMENT ON COLUMN cnc_schedule.next_run_at IS '下次计划运行时间';
COMMENT ON COLUMN cnc_schedule.last_run_at IS '上次执行时间';
COMMENT ON COLUMN cnc_schedule.version IS '并发更新版本号';

CREATE INDEX IF NOT EXISTS ix_cnc_schedule_enabled_next ON cnc_schedule(enabled, next_run_at);
CREATE INDEX IF NOT EXISTS ix_cnc_schedule_owner_id ON cnc_schedule(owner_id);
CREATE INDEX IF NOT EXISTS ix_cnc_schedule_uuid ON cnc_schedule(uuid);


-- ==============================================================================
-- 8. 执行事件与审计日志表 (cnc_execution_event)
-- 记录比价执行全流程事件、Deep Agents 异常诊断/策略选择/守卫校验详情
-- ==============================================================================
CREATE TABLE IF NOT EXISTS cnc_execution_event (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(64) NOT NULL UNIQUE,
    task_id INTEGER REFERENCES cnc_quote_task(id) ON DELETE CASCADE ON UPDATE CASCADE,
    item_id INTEGER REFERENCES cnc_quote_item(id) ON DELETE CASCADE ON UPDATE CASCADE,
    account_id INTEGER REFERENCES cnc_account(id) ON DELETE SET NULL ON UPDATE CASCADE,
    actor_user_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    attempt_no INTEGER NOT NULL DEFAULT 0,
    phase VARCHAR(32),
    event_type VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'INFO',
    error_code VARCHAR(64),
    message_redacted TEXT NOT NULL,
    payload_redacted_json JSONB DEFAULT '{}'::jsonb,
    trace_id VARCHAR(64),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- ModelMixin & 审计通用字段
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_time TIMESTAMPTZ,
    created_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    updated_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    deleted_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE
);

COMMENT ON TABLE cnc_execution_event IS 'CNC 执行事件与审计日志表';
COMMENT ON COLUMN cnc_execution_event.task_id IS '关联批次任务ID';
COMMENT ON COLUMN cnc_execution_event.item_id IS '关联报价明细ID';
COMMENT ON COLUMN cnc_execution_event.account_id IS '关联账号ID';
COMMENT ON COLUMN cnc_execution_event.actor_user_id IS '操作用户ID(若为人工操作)';
COMMENT ON COLUMN cnc_execution_event.attempt_no IS '执行尝试轮次';
COMMENT ON COLUMN cnc_execution_event.phase IS '执行阶段';
COMMENT ON COLUMN cnc_execution_event.event_type IS '事件类型(STEP_STARTED, STRATEGY_CHOSEN, RECOVERY_VERIFIED 等)';
COMMENT ON COLUMN cnc_execution_event.severity IS '日志级别(DEBUG, INFO, WARNING, ERROR, CRITICAL)';
COMMENT ON COLUMN cnc_execution_event.error_code IS '错误码';
COMMENT ON COLUMN cnc_execution_event.message_redacted IS '脱敏后的可读消息';
COMMENT ON COLUMN cnc_execution_event.payload_redacted_json IS '结构化事件详情(无敏感数据)';
COMMENT ON COLUMN cnc_execution_event.trace_id IS '分布式追踪ID';
COMMENT ON COLUMN cnc_execution_event.occurred_at IS '事件发生时间';

CREATE INDEX IF NOT EXISTS ix_cnc_execution_event_item_occurred ON cnc_execution_event(item_id, occurred_at);
CREATE INDEX IF NOT EXISTS ix_cnc_execution_event_task_occurred ON cnc_execution_event(task_id, occurred_at);
CREATE INDEX IF NOT EXISTS ix_cnc_execution_event_trace_id ON cnc_execution_event(trace_id);
CREATE INDEX IF NOT EXISTS ix_cnc_execution_event_uuid ON cnc_execution_event(uuid);


-- ==============================================================================
-- 9. 审计证据与截图表 (cnc_evidence)
-- 存储报价截图、参数回读快照、DOM 结构片段与错误快照
-- ==============================================================================
CREATE TABLE IF NOT EXISTS cnc_evidence (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(64) NOT NULL UNIQUE,
    item_id INTEGER NOT NULL REFERENCES cnc_quote_item(id) ON DELETE CASCADE ON UPDATE CASCADE,
    result_id INTEGER REFERENCES cnc_quote_result(id) ON DELETE CASCADE ON UPDATE CASCADE,
    event_id INTEGER REFERENCES cnc_execution_event(id) ON DELETE SET NULL ON UPDATE CASCADE,
    kind VARCHAR(32) NOT NULL,
    storage_key TEXT NOT NULL UNIQUE,
    content_type VARCHAR(64) NOT NULL DEFAULT 'image/png',
    sha256 CHAR(64) NOT NULL,
    size_bytes BIGINT NOT NULL CHECK (size_bytes > 0),
    sensitivity VARCHAR(16) NOT NULL DEFAULT 'CONFIDENTIAL',
    encrypted BOOLEAN NOT NULL DEFAULT false,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    retained_until TIMESTAMPTZ,
    available BOOLEAN NOT NULL DEFAULT true,
    
    -- ModelMixin & 审计通用字段
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_time TIMESTAMPTZ,
    created_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    updated_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE,
    deleted_id INTEGER REFERENCES sys_user(id) ON DELETE SET NULL ON UPDATE CASCADE
);

COMMENT ON TABLE cnc_evidence IS 'CNC 审计证据与截图表';
COMMENT ON COLUMN cnc_evidence.item_id IS '关联询价明细ID';
COMMENT ON COLUMN cnc_evidence.result_id IS '关联报价结果ID';
COMMENT ON COLUMN cnc_evidence.event_id IS '关联执行事件ID';
COMMENT ON COLUMN cnc_evidence.kind IS '证据类型(RESULT_SCREENSHOT, PARAM_SCREENSHOT, DOM_EXTRACT, ERROR_SCREENSHOT)';
COMMENT ON COLUMN cnc_evidence.storage_key IS '私有存储Key(防公开越权访问)';
COMMENT ON COLUMN cnc_evidence.content_type IS 'MIME类型(image/png 等)';
COMMENT ON COLUMN cnc_evidence.sha256 IS '证据文件SHA256哈希(防篡改)';
COMMENT ON COLUMN cnc_evidence.size_bytes IS '文件大小(字节)';
COMMENT ON COLUMN cnc_evidence.sensitivity IS '敏感等级(PUBLIC, INTERNAL, CONFIDENTIAL)';
COMMENT ON COLUMN cnc_evidence.encrypted IS '磁盘是否密文存储';
COMMENT ON COLUMN cnc_evidence.captured_at IS '抓取截获时间';
COMMENT ON COLUMN cnc_evidence.retained_until IS '证据保留截止期限';
COMMENT ON COLUMN cnc_evidence.available IS '证据是否完好可读';

CREATE INDEX IF NOT EXISTS ix_cnc_evidence_item_captured ON cnc_evidence(item_id, captured_at);
CREATE INDEX IF NOT EXISTS ix_cnc_evidence_result_id ON cnc_evidence(result_id);
CREATE INDEX IF NOT EXISTS ix_cnc_evidence_sha256 ON cnc_evidence(sha256);
CREATE INDEX IF NOT EXISTS ix_cnc_evidence_uuid ON cnc_evidence(uuid);

COMMIT;
