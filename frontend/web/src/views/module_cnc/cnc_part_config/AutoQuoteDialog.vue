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
        <ElDescriptionsItem label="当前选定交期" :span="2">{{ leadTimeLabel }}</ElDescriptionsItem>
        <ElDescriptionsItem v-if="run.result.tax_amount" label="税费">
          <span>{{ money(run.result.tax_amount) }}</span>
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="run.result.total_amount" label="总计（含税）">
          <strong style="color: var(--el-color-primary); font-size: 15px;">{{ money(run.result.total_amount) }}</strong>
          <span v-if="run.result.discount_amount" style="margin-left: 8px; color: var(--el-color-danger); font-size: 12px;">(券后约 {{ money(run.result.discount_amount) }})</span>
        </ElDescriptionsItem>
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

      <div v-if="leadTimeTiers.length" class="lead-time-tiers" style="margin-top: 16px;">
        <h4 style="margin: 0 0 8px; font-size: 14px; font-weight: 600;">各交期阶梯报价明细</h4>
        <ElTable :data="leadTimeTiers" size="small" border style="width: 100%;">
          <ElTableColumn prop="tier" label="交期类型" min-width="110">
            <template #default="{ row }">
              <ElTag :type="tierTagType(row.tier)" size="small">{{ row.tier }}</ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn label="单价" min-width="100">
            <template #default="{ row }">
              <strong style="color: var(--el-color-primary);">{{ money(row.unit_amount || row.part_amount) }}</strong>
            </template>
          </ElTableColumn>
          <ElTableColumn v-if="tiersHaveTotal" label="合计" min-width="100">
            <template #default="{ row }">{{ money(row.total_amount || row.amount) }}</template>
          </ElTableColumn>
          <ElTableColumn v-if="tiersHaveTax" label="税费" min-width="90">
            <template #default="{ row }">{{ money(row.tax_amount) }}</template>
          </ElTableColumn>
          <ElTableColumn label="预计到货" min-width="120">
            <template #default="{ row }">
              <span>{{ row.arrives_by || row.estimated_ship_date || row.days || "平台未提供" }}</span>
            </template>
          </ElTableColumn>
          <ElTableColumn label="平台原文" min-width="220">
            <template #default="{ row }">
              <span style="font-size: 12px; color: var(--el-text-color-secondary);">{{ row.raw || "-" }}</span>
            </template>
          </ElTableColumn>
        </ElTable>
      </div>
    </div>
    <details v-if="parameterRows.length" class="quote-parameters" :open="!!run?.result">
      <summary>报价参数{{ run?.result ? "与平台回读" : "" }}</summary>
      <ElTable :data="parameterRows" size="small" border>
        <ElTableColumn prop="label" label="参数" min-width="150" />
        <ElTableColumn prop="requested" label="本次配置" min-width="150" />
        <ElTableColumn v-if="run?.result" prop="effective" label="平台回读" min-width="150" />
      </ElTable>
    </details>
    <fieldset v-if="declaration" class="quote-declaration" :disabled="busy || !!error">
      <legend>本次图纸的出口声明</legend>
      <p class="declaration-file">{{ run?.file_name }}</p>
      <p class="declaration-statement">{{ declaration.statement }}</p>
      <p>请阅读平台声明，为本次图纸明确选择一项，确认后继续报价。</p>
      <ElRadioGroup
        v-model="declarationChoice"
        class="declaration-options"
        aria-label="本次图纸的出口声明选项"
        :disabled="busy || !!error"
      >
        <ElRadio v-for="option in declaration.options" :key="option.value" :value="option.value">
          {{ option.label }}
        </ElRadio>
      </ElRadioGroup>
    </fieldset>
    <template v-else-if="run?.status === 'WAITING_HUMAN'">
      <p class="quote-help">{{ humanHelp }}</p>
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
        v-if="terminal && run?.result"
        type="success"
        plain
        @click="goToResults"
      >
        查看报价结果报表
      </ElButton>
      <ElButton
        v-if="choosingAccount"
        type="primary"
        :loading="busy"
        :disabled="selectedAccount == null || busy"
        @click="emit('start')"
        >开始报价</ElButton
      >
      <ElButton
        v-if="declaration"
        type="primary"
        :loading="busy"
        :disabled="!canConfirmDeclaration"
        @click="confirmDeclaration"
        >确认声明并继续</ElButton
      >
      <ElButton
        v-else-if="run?.status === 'WAITING_HUMAN'"
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
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  ElAlert,
  ElButton,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElOption,
  ElRadio,
  ElRadioGroup,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from "element-plus";
import type { CncLoginInput } from "@/api/module_cnc/cnc_account";
import type {
  CncLeadTimeTier,
  CncQuoteAccount,
  CncQuoteDeclarationChoice,
  CncQuoteDeclarationDecision,
  CncQuoteRun,
  CncQuoteStage,
  CncQuoteStatus,
} from "@/api/module_cnc/cnc_part_config";
import ControlledBrowser from "../components/ControlledBrowser.vue";
import { isQuoteTerminal } from "./useAutoQuote";
import { quoteReasonMessage } from "./quoteMessages";

const router = useRouter();

function goToResults() {
  emit("close");
  router.push("/module_cnc/cnc_quote_result");
}

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
  declaration: [decision: CncQuoteDeclarationDecision];
}>();
const declarationChoice = ref<CncQuoteDeclarationChoice>();
const declaration = computed(() =>
  props.run?.status === "WAITING_HUMAN" ? props.run.export_declaration : null
);
watch(
  [() => props.visible, () => props.run?.run_id, () => declaration.value?.declaration_id],
  () => {
    declarationChoice.value = undefined;
  },
  { flush: "sync" }
);
const canConfirmDeclaration = computed(
  () =>
    props.visible &&
    !props.busy &&
    !props.error &&
    !!declaration.value?.options.some((option) => option.value === declarationChoice.value)
);
function confirmDeclaration() {
  if (!canConfirmDeclaration.value || !declaration.value || !declarationChoice.value) return;
  emit("declaration", {
    declaration_id: declaration.value.declaration_id,
    choice: declarationChoice.value,
  });
}
const humanHelp = computed(() => {
  if (!props.run?.can_input) return "本阶段暂不接受人工操作，请根据提示核对平台状态。";
  if (props.run.stage === "login") return "在下方平台页面完成登录或验证，再点击“验证并继续”。";
  return "在下方平台页面完成当前阶段的处理，再点击“验证并继续”。";
});
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
const leadTimeTiers = computed<CncLeadTimeTier[]>(() => {
  const result = props.run?.result;
  if (!result) return [];
  if (Array.isArray(result.lead_time_tiers) && result.lead_time_tiers.length) {
    return result.lead_time_tiers;
  }
  const lead = result.lead_time;
  if (lead && Array.isArray(lead.tiers) && lead.tiers.length) {
    return lead.tiers as CncLeadTimeTier[];
  }
  return [];
});
/** 币种符号按平台回报取，不能默认人民币：Xometry 报 USD，嘉立创报 CNY。 */
const currencySymbol = computed(() => {
  const code = (props.run?.result?.currency || "").toUpperCase();
  if (!code || code === "CNY" || code === "RMB") return "¥";
  if (code === "USD") return "$";
  if (code === "EUR") return "€";
  return `${code} `;
});
function money(value?: string | null) {
  return value ? `${currencySymbol.value}${value}` : "平台未提供";
}
function tierTagType(tier: string) {
  const key = (tier || "").toLowerCase();
  if (key.includes("fast") || key.includes("expedit") || key.includes("加急")) return "danger";
  if (key.includes("least") || key.includes("econ") || key.includes("经济")) return "info";
  return "primary";
}
const tiersHaveTotal = computed(() => leadTimeTiers.value.some((row) => row.total_amount || row.amount));
const tiersHaveTax = computed(() => leadTimeTiers.value.some((row) => row.tax_amount));

const leadTimeLabel = computed(() => {
  const lead = props.run?.result?.lead_time;
  if (!lead) return "平台未提供";
  if (typeof lead.text === "string" && lead.text) return lead.text;
  if (typeof lead.raw_text === "string" && lead.raw_text) return lead.raw_text;
  if (typeof lead.tier === "string" && typeof lead.days === "string") {
    return `${lead.tier} (${lead.days})`;
  }
  if (typeof lead.raw === "string") return lead.raw;
  return "平台未提供可确认的交期原文";
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
.quote-parameters,
.quote-declaration {
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

.quote-declaration {
  padding: 16px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
}

.declaration-file {
  font-weight: 600;
  overflow-wrap: anywhere;
}

.declaration-statement {
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.declaration-options {
  display: grid;
  gap: 12px;

  :deep(.el-radio) {
    height: auto;
    margin-right: 0;
  }

  :deep(.el-radio__label) {
    line-height: 1.6;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
  }
}
</style>
