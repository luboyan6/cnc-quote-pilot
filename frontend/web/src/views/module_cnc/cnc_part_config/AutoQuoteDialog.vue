<template>
  <ElDialog
    :model-value="visible"
    :title="`自动报价 · ${configName || '产品配置'}`"
    :width="run?.status === 'WAITING_HUMAN' ? 'min(1328px, 96vw)' : 'min(860px, 96vw)'"
    top="4vh"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    destroy-on-close
    @update:model-value="!$event && emit('close')"
  >
    <div class="quote-status" role="status" aria-live="polite">
      <ElTag :type="statusTone">{{ statusLabel }}</ElTag>
      <span v-if="run">{{ run.platform_name }} · {{ run.masked_username }}</span>
      <span v-if="run && !terminal">{{ stageLabel }}</span>
    </div>
    <ElAlert
      v-if="info"
      :title="info"
      type="info"
      :closable="false"
      show-icon
      class="quote-notice"
    />
    <ElAlert
      v-if="error || run?.reason || choosingAccount"
      :title="notice"
      :type="
        error || run?.status === 'FAILED'
          ? 'error'
          : statusTone === 'success'
            ? 'success'
            : 'warning'
      "
      :closable="false"
      show-icon
      class="quote-notice"
    />
    <div v-if="choosingAccount" class="account-choice">
      <label for="quote-account">选择此平台的报价账号</label>
      <ElSelect
        id="quote-account"
        :model-value="selectedAccount"
        placeholder="请选择账号"
        :disabled="busy"
        @update:model-value="emit('select-account', $event)"
      >
        <ElOption
          v-for="account in accounts"
          :key="account.id"
          :value="account.id"
          :label="`${account.alias || '账号'} · ${account.masked_username}`"
        />
      </ElSelect>
    </div>

    <ElDescriptions v-if="run" :column="2" border class="quote-summary">
      <ElDescriptionsItem label="图纸" :span="2">{{ run.file_name }}</ElDescriptionsItem>
      <ElDescriptionsItem label="材料">{{ run.requested.material || "未设置" }}</ElDescriptionsItem>
      <ElDescriptionsItem label="数量">{{ run.requested.quantity || "未设置" }}</ElDescriptionsItem>
      <ElDescriptionsItem label="表面处理" :span="2">{{
        run.requested.surface_finish || "未设置"
      }}</ElDescriptionsItem>
    </ElDescriptions>
    <div v-if="run?.result" class="quote-result">
      <p class="result-kind">{{ resultLabels[run.result.status] }}</p>
      <p class="quote-amount">
        <template v-if="run.result.amount !== null">
          <span>{{ run.result.currency || "币种未确认" }}</span>
          <strong>{{ run.result.amount }}</strong>
          <span>{{
            run.result.price_scope === "unit"
              ? "/ 件"
              : run.result.price_scope === "line"
                ? "本行总价"
                : "价格口径未确认"
          }}</span>
        </template>
        <span v-else>平台尚未返回金额</span>
      </p>
      <ElDescriptions :column="2" border>
        <ElDescriptionsItem label="交期" :span="2">{{ leadTimeLabel }}</ElDescriptionsItem>
        <ElDescriptionsItem label="含税">{{
          includedLabel(run.result.tax_included)
        }}</ElDescriptionsItem>
        <ElDescriptionsItem label="含运费">{{
          includedLabel(run.result.shipping_included)
        }}</ElDescriptionsItem>
        <ElDescriptionsItem label="平台报价时间" :span="2">{{
          run.result.priced_at || "平台未提供"
        }}</ElDescriptionsItem>
        <ElDescriptionsItem label="读取时间" :span="2">{{
          run.result.observed_at
        }}</ElDescriptionsItem>
      </ElDescriptions>
    </div>
    <details v-if="parameterRows.length" class="quote-parameters" :open="!!run?.result">
      <summary>报价参数{{ run?.result ? "与平台回读" : "" }}</summary>
      <ElTable :data="parameterRows" size="small" border>
        <ElTableColumn prop="label" label="参数" min-width="150" />
        <ElTableColumn prop="requested" label="本次配置" min-width="150" />
        <ElTableColumn v-if="run?.result" prop="effective" label="平台回读" min-width="150" />
      </ElTable>
    </details>
    <template v-if="run?.status === 'WAITING_HUMAN'">
      <p class="quote-help">在下方平台页面完成登录或验证，再点击“验证并继续”。</p>
      <ControlledBrowser
        :frame-url="frameUrl"
        :viewport="run.viewport"
        :interactive="interactive"
        :preparing="run.can_input && !frameUrl && !error"
        :error="error"
        :reset-key="run.run_id"
        @input="emit('input', $event)"
      />
    </template>
    <p v-else-if="!terminal && !choosingAccount && !error" class="quote-help" :aria-busy="true">
      {{ busy && !run ? "正在准备报价…" : "报价正在运行，请保留此窗口。关闭窗口会停止本次运行。" }}
    </p>
    <template #footer>
      <ElButton @click="emit('close')">{{
        terminal || choosingAccount || !run ? "关闭" : "停止并关闭"
      }}</ElButton>
      <ElButton
        v-if="choosingAccount"
        type="primary"
        :loading="busy"
        :disabled="selectedAccount == null || busy"
        @click="emit('start')"
        >开始报价</ElButton
      >
      <ElButton
        v-if="run?.status === 'WAITING_HUMAN'"
        type="primary"
        :loading="busy"
        :disabled="!interactive"
        @click="emit('resume')"
        >验证并继续</ElButton
      >
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
import { computed } from "vue";
import {
  ElAlert,
  ElButton,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from "element-plus";
import type { CncLoginInput } from "@/api/module_cnc/cnc_account";
import type {
  CncQuoteAccount,
  CncQuoteRun,
  CncQuoteStage,
  CncQuoteStatus,
} from "@/api/module_cnc/cnc_part_config";
import ControlledBrowser from "../components/ControlledBrowser.vue";
import { isQuoteTerminal } from "./useAutoQuote";
import { quoteReasonMessage } from "./quoteMessages";

const props = defineProps<{
  visible: boolean;
  configName?: string;
  run?: CncQuoteRun;
  accounts: CncQuoteAccount[];
  selectedAccount?: number;
  choosingAccount: boolean;
  frameUrl: string;
  error: string;
  info?: string;
  busy: boolean;
  interactive: boolean;
}>();
const emit = defineEmits<{
  close: [];
  "select-account": [id: number];
  start: [];
  input: [input: CncLoginInput];
  resume: [];
}>();
const resultLabels = {
  QUOTED: "平台报价",
  REFERENCE_ESTIMATE: "系统参考估价",
  PENDING_REVIEW: "等待平台人工审核",
};
const statusLabels: Record<CncQuoteStatus, string> = {
  STARTING: "准备报价",
  AUTHENTICATING: "正在登录",
  RUNNING: "正在报价",
  WAITING_HUMAN: "需人工处理",
  QUOTED: "报价成功",
  REFERENCE_ESTIMATE: "参考估价",
  PENDING_REVIEW: "待人工审核",
  FAILED: "报价失败",
  CANCELLED: "已停止",
};
const stageLabels: Record<CncQuoteStage, string> = {
  prepare: "准备文件",
  login: "核验登录",
  upload: "上传图纸",
  parse: "解析模型",
  configure: "设置加工参数",
  quote: "获取报价",
  persist: "保存报价结果",
  complete: "已完成",
};
const terminal = computed(() => !!props.run && isQuoteTerminal(props.run));
const statusLabel = computed(() =>
  props.error
    ? "操作未能确认"
    : props.choosingAccount
      ? "选择报价账号"
      : statusLabels[props.run?.status || "STARTING"]
);
const stageLabel = computed(() => (props.run ? stageLabels[props.run.stage] : "准备报价"));
const statusTone = computed(() => {
  if (props.error || props.run?.status === "FAILED") return "danger";
  if (props.run?.status === "QUOTED") return "success";
  if (["WAITING_HUMAN", "REFERENCE_ESTIMATE", "PENDING_REVIEW"].includes(props.run?.status || ""))
    return "warning";
  return "info";
});
const notice = computed(() => {
  if (props.error) return props.error;
  if (props.choosingAccount) return "此平台有多个可用账号，请选择本次使用的账号。";
  const reason = quoteReasonMessage(props.run?.reason);
  if (reason) return reason;
  switch (props.run?.status) {
    case "QUOTED":
      return "已取得并保存本次平台报价。";
    case "REFERENCE_ESTIMATE":
      return "当前金额为系统参考估价，请以平台最终报价为准。";
    case "PENDING_REVIEW":
      return "平台已反馈待人工审核，尚未取得最终报价。";
    case "FAILED":
      return "本次报价未完成，请检查账号、图纸和加工参数。";
    case "CANCELLED":
      return "本次运行已停止，已发送的操作记录仍保留。";
    case "WAITING_HUMAN":
      return "平台需要人工处理，请在下方完成验证后继续。";
    default:
      return "正在执行本次报价，请等待平台返回。";
  }
});
const parameterLabels: Record<string, string> = {
  material: "材料",
  quantity: "数量",
  surface_finish: "表面处理",
};
const parameterRows = computed(() =>
  Object.entries(props.run?.requested || {}).map(([key, requested]) => ({
    label: parameterLabels[key] || key,
    requested,
    effective: props.run?.result?.effective[key] ?? "未回读",
  }))
);
const leadTimeLabel = computed(() => {
  const lead = props.run?.result?.lead_time;
  if (!lead) return "平台未提供";
  return typeof lead.text === "string"
    ? lead.text
    : typeof lead.raw_text === "string"
      ? lead.raw_text
      : typeof lead.raw === "string"
        ? lead.raw
        : "平台未提供可确认的交期原文";
});
function includedLabel(value: boolean | null) {
  return value === null ? "平台未明确" : value ? "是" : "否";
}
</script>

<style scoped lang="scss">
.quote-status {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.quote-notice,
.quote-summary,
.quote-result,
.quote-parameters {
  margin-top: 16px;
}

.account-choice {
  display: grid;
  gap: 8px;
  margin-top: 20px;
}

.quote-result {
  padding: 20px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.result-kind {
  margin: 0;
  color: var(--el-text-color-secondary);
}

.quote-amount {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: baseline;
  margin: 12px 0 20px;
}

.quote-amount strong {
  font-size: 32px;
  font-variant-numeric: tabular-nums;
}

.quote-parameters summary {
  margin-bottom: 12px;
  cursor: pointer;
}

.quote-help {
  margin: 16px 0;
  color: var(--el-text-color-secondary);
}
</style>
