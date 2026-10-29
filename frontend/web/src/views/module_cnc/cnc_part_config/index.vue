<template>
  <div class="fa-full-height">
    <FaSearchBar
      v-show="showSearchBar"
      ref="searchBarRef"
      v-model="searchForm"
      :items="businessSearchItems"
      :rules="searchBarRules"
      :is-expand="false"
      :show-expand="true"
      :show-reset="true"
      :show-search="true"
      :disabled-search="false"
      :default-expanded="false"
      include-audit
      @search="handleSearch"
      @reset="onResetSearch"
    />

    <ElCard class="fa-table-card" :style="{ 'margin-top': showSearchBar ? '12px' : '0' }">
      <FaTableHeader
        v-model:columns="columnChecks"
        v-model:showSearchBar="showSearchBar"
        :loading="loading"
        @refresh="handleRefresh"
      >
        <template #left>
          <div class="flex items-center gap-2">
            <FaTableHeaderLeft
              :remove-ids="selectedIds"
              :perm-create="['module_cnc:cnc_part_config:create']"
              :perm-import="['module_cnc:cnc_part_config:import']"
              :perm-export="['module_cnc:cnc_part_config:export']"
              :perm-delete="['module_cnc:cnc_part_config:delete']"
              :perm-patch="['module_cnc:cnc_part_config:patch']"
              :delete-loading="batchDeleting"
              :create-loading="createLoading"
              :more-loading="moreLoading"
              @add="handleAdd"
              @import="openImport"
              @export="openExport"
              @delete="handleBatchDelete"
              @more="handleMoreClick"
            />
            <ElButton
              type="success"
              plain
              @click="goToQuoteResults()"
            >
              📊 查看报价结果与报表
            </ElButton>
            <ElButton
              v-if="checkPerm('module_cnc:cnc_quote_batch:create')"
              type="primary"
              plain
              :disabled="selectedIds.length === 0"
              @click="openBatchQuoteDialog"
            >
              ⚡ 批量发起报价 {{ selectedIds.length ? `(${selectedIds.length})` : '' }}
            </ElButton>
          </div>
        </template>
      </FaTableHeader>

      <FaTable
        ref="faTableRef"
        :loading="loading"
        :data="data"
        :columns="columns"
        :pagination="pagination"
        @selection-change="onTableSelectionChange"
        @pagination:size-change="handleSizeChange"
        @pagination:current-change="handleCurrentChange"
      />
    </ElCard>

    <FaDialog
      v-model="dialogVisible.visible"
      :title="dialogVisible.title"
      width="880px"
      dialog-class="crud-embed-dialog"
      modal-class="crud-embed-dialog"
      :form-mode="dialogVisible.type"
      :confirm-loading="submitLoading"
      @cancel="handleCloseDialog"
      @close="handleCloseDialog"
      @confirm="handleSubmit()"
    >
      <template v-if="dialogVisible.type === 'detail'">
        <FaDescriptions :column="2" :data="detailFormData" :items="detailItems" max-height="70vh">
          <template #site_type="{ row }">
            <ElTag
              v-if="row?.site_type != null && getPlatformLabel(row?.site_type) !== '-'"
              type="primary"
            >
              {{ getPlatformLabel(row?.site_type) }}
            </ElTag>
            <span v-else>{{ row?.site_type ?? "-" }}</span>
          </template>
          <template #part_id="{ row }">
            {{ getPartLabel(row?.part_id) }}
          </template>
          <template #enabled="{ row }">
            <ElTag :type="row?.enabled ? 'success' : 'danger'">
              {{ row?.enabled ? "启用" : "禁用" }}
            </ElTag>
          </template>
          <template #requires_2d_drawing="{ row }">
            <ElTag :type="row?.requires_2d_drawing ? 'danger' : 'info'">
              {{ row?.requires_2d_drawing ? "需要2D图纸" : "无需2D图纸" }}
            </ElTag>
          </template>
          <template #has_threads="{ row }">
            <span v-if="row?.has_threads">是（{{ row?.thread_count || 0 }}孔）</span>
            <span v-else class="text-gray-400">无</span>
          </template>
          <template #has_inserts="{ row }">
            <span v-if="row?.has_inserts">是（{{ row?.insert_count || 0 }}件）</span>
            <span v-else class="text-gray-400">无</span>
          </template>
          <template #extra_params="{ row }">
            <FaJsonPretty
              v-if="row?.extra_params != null"
              :value="row?.extra_params"
              height="140px"
            />
            <span v-else class="text-gray-400">无</span>
          </template>
        </FaDescriptions>
      </template>
      <template v-else>
        <FaForm
          :key="formRenderKey"
          scrollbar
          max-height="70vh"
          ref="dataFormRef"
          v-model="formData"
          :items="dialogFormItems"
          :rules="rules"
          label-suffix=":"
          :label-width="96"
          label-position="right"
          :span="12"
          :gutter="16"
          :show-reset="false"
          :show-submit="false"
          class="crud-dialog-art-form"
        />
      </template>
    </FaDialog>

    <FaImportDialog
      v-model="importVisible"
      :content-config="importContentConfig"
      default-template-file-name="cnc_part_config_import_template.xlsx"
      @upload="handleCrudImportUpload"
    />

    <FaExportDialog
      v-model="exportVisible"
      :content-config="exportContentConfig"
      :query-params="exportQueryParams"
      :page-data="data"
      :selection-data="selectedRows"
    />
    <AutoQuoteDialog
      :visible="quote.visible.value"
      :config-name="quote.selectedRow.value?.name"
      :run="quote.run.value"
      :accounts="quote.accounts.value"
      :selected-account="quote.selectedAccount.value"
      :choosing-account="quote.choosingAccount.value"
      :frame-url="quote.frameUrl.value"
      :error="quote.error.value"
      :info="quote.info.value"
      :busy="quote.busy.value"
      :interactive="quote.interactive.value"
      @close="handleCloseQuote"
      @select-account="handleSelectQuoteAccount"
      @start="handleStartQuote"
      @input="handleQuoteCommand"
      @resume="handleQuoteCommand()"
      @declaration="handleQuoteDeclaration"
    />

    <!-- 批量发起报价弹窗 -->
    <ElDialog
      v-model="batchQuoteVisible"
      title="批量发起 CNC 自动报价"
      width="720px"
      destroy-on-close
    >
      <div class="batch-quote-dialog flex flex-col gap-3">
        <ElAlert
          title="将对所选图纸配置按设定的数量梯度提交批量自动化报价任务"
          type="info"
          :closable="false"
          show-icon
        />

        <div>
          <span class="font-medium text-sm text-gray-700">已选配置 ({{ selectedRows.length }}个):</span>
          <div class="max-h-36 overflow-y-auto mt-1 border rounded p-2 bg-gray-50 flex flex-col gap-1 text-xs">
            <div v-for="cfg in selectedRows" :key="cfg.id" class="flex justify-between items-center">
              <span><b>{{ cfg.name || `配置#${cfg.id}` }}</b> ({{ cfg.material || '默认' }} · {{ cfg.surface_finish || '默认' }})</span>
              <ElTag size="small">{{ getPlatformLabel(cfg.site_type) }}</ElTag>
            </div>
          </div>
        </div>

        <div>
          <label class="block font-medium text-sm text-gray-700 mb-1">加工数量梯度 (多个以英文逗号分隔):</label>
          <ElInput
            v-model="batchQuantitiesInput"
            placeholder="例如: 1, 5, 10, 50"
          />
          <span class="text-xs text-gray-400 mt-1 block">
            将生成 {{ parsedQuantities.length }} 个数量档位 × {{ selectedRows.length }} 个配置 = {{ parsedQuantities.length * selectedRows.length }} 个报价任务
          </span>
        </div>
      </div>

      <template #footer>
        <ElButton @click="batchQuoteVisible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="batchSubmitting"
          :disabled="parsedQuantities.length === 0 || selectedRows.length === 0"
          @click="submitBatchQuote"
        >
          确认发起
        </ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElButton, ElMessage, ElTag } from "element-plus";
import { checkPerm } from "@/utils/checkPerm";
import AutoQuoteDialog from "./AutoQuoteDialog.vue";
import { isQuoteTerminal, useAutoQuote } from "./useAutoQuote";
import {
  renderTableOperationCell,
  resolveStatusColumns,
  stripPaginationParams,
  toCrudCols,
  type TableOperationAction,
} from "@utils";
import { useCrudForm } from "@/hooks/core/useCrudForm";
import { ResultEnum } from "@/enums/api/result.enum";
import type { IContentConfig, IObject } from "@/components/modal/types";
import type { AuditSearchFormParams } from "@/components/forms/fa-search-bar/auditSearchFormItems";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaDescriptions from "@/components/display/fa-descriptions/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import FaTableHeader from "@/components/tables/fa-table-header/index.vue";
import CncPlatformAPI, { type CncPlatformTable } from "@/api/module_cnc/cnc_platform";
import CncPartAPI, { type CncPartTable } from "@/api/module_cnc/cnc_part";
import type { CncLoginInput } from "@/api/module_cnc/cnc_account";
import CncPartConfigAPI, {
  type CncParamsCatalog,
  type CncPartConfigForm,
  type CncPartConfigPageQuery,
  type CncPartConfigTable,
  type CncQuoteDeclarationDecision,
} from "@/api/module_cnc/cnc_part_config";
import { useParamCatalog } from "./useParamCatalog";
import CncQuoteBatchAPI from "@/api/module_cnc/cnc_quote_batch";

defineOptions({
  name: "CncPartConfig",
});

const quote = useAutoQuote();
const router = useRouter();

function goToQuoteResults(configId?: number) {
  router.push({
    path: "/module_cnc/cnc_quote_result",
    query: configId ? { config_id: String(configId) } : undefined,
  });
}

// ────────── 批量发起报价 ──────────
const batchQuoteVisible = ref(false);
const batchQuantitiesInput = ref("1, 5, 10");
const batchSubmitting = ref(false);

const parsedQuantities = computed(() => {
  const parts = batchQuantitiesInput.value.split(/[,，\s]+/);
  const nums = parts
    .map((p) => parseInt(p.trim(), 10))
    .filter((n) => Number.isInteger(n) && n > 0 && n <= 100000);
  return Array.from(new Set(nums)).sort((a, b) => a - b);
});

function openBatchQuoteDialog() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning("请先勾选需要报价的图纸配置");
    return;
  }
  batchQuoteVisible.value = true;
}

function generateBatchUuid(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6]! & 0x0f) | 0x40;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

async function submitBatchQuote() {
  if (parsedQuantities.value.length === 0 || selectedRows.value.length === 0) return;
  batchSubmitting.value = true;
  try {
    const targets = selectedRows.value.map((r) => ({
      config_id: r.id!,
      quantities: parsedQuantities.value,
    }));
    const res = await CncQuoteBatchAPI.create({
      request_id: generateBatchUuid(),
      targets,
    });
    const itemCount = res.data?.data?.item_count || targets.length * parsedQuantities.value.length;
    ElMessage.success(`批量报价任务创建成功 (包含 ${itemCount} 项)`);
    batchQuoteVisible.value = false;
    faTableRef.value?.elTableRef?.clearSelection();
    router.push("/module_cnc/cnc_quote_batch");
  } catch (err: any) {
    ElMessage.error(err?.message || "批量报价发起失败");
  } finally {
    batchSubmitting.value = false;
  }
}

function canAutoQuote(): boolean {
  const hasConfigPerm =
    checkPerm("module_cnc:cnc_part_config:query") ||
    checkPerm("module_cnc:cnc_part_config:detail");
  return (
    hasConfigPerm &&
    checkPerm("module_cnc:cnc_part_config:update") &&
    checkPerm("module_cnc:cnc_account:query") &&
    checkPerm("module_cnc:cnc_account:update")
  );
}

function handleAutoQuote(row: CncPartConfigTable) {
  if (canAutoQuote()) void quote.open(row);
}

/** 报价运行复用账号模块的登录会话；每个交互入口重验当前页面权限。 */
function handleStartQuote() {
  if (canAutoQuote()) void quote.chooseAccount();
}
function handleSelectQuoteAccount(accountId: number) {
  if (
    canAutoQuote() &&
    !quote.busy.value &&
    quote.choosingAccount.value &&
    quote.accounts.value.some((account) => account.id === accountId)
  )
    quote.selectedAccount.value = accountId;
}
function handleQuoteCommand(input?: CncLoginInput) {
  if (canAutoQuote()) void quote.command(input);
}
function handleQuoteDeclaration(decision: CncQuoteDeclarationDecision) {
  if (canAutoQuote()) void quote.confirmDeclaration(decision);
}
function handleCloseQuote() {
  quote.close();
}

/** 报价平台下拉数据源 */
const platformOptions = ref<{ label: string; value: number }[]>([]);
const platformOptionsLoading = ref(false);
const platformLabels = computed(
  () => new Map(platformOptions.value.map((p) => [p.value, p.label]))
);

function getPlatformLabel(id: unknown): string {
  return typeof id !== "number" ? "-" : platformLabels.value.get(id) || `平台#${id}`;
}

async function fetchPlatformOptions() {
  if (platformOptionsLoading.value) return;
  platformOptionsLoading.value = true;
  try {
    const items: CncPlatformTable[] = [];
    let pageNo = 1;
    while (true) {
      const res = await CncPlatformAPI.listCncPlatform({ page_no: pageNo, page_size: 100 });
      const page = res.data.data;
      items.push(...page.items);
      if (!page.has_next || page.items.length === 0) break;
      pageNo += 1;
    }
    platformOptions.value = items.flatMap((p) =>
      p.id == null ? [] : [{ label: p.name || `平台#${p.id}`, value: p.id }]
    );
  } catch (error) {
    console.error("加载平台列表失败:", error);
  } finally {
    platformOptionsLoading.value = false;
  }
}

/** 启用状态选项 */
const STATUS_OPTIONS = [
  { label: "启用", value: true },
  { label: "禁用", value: false },
] as const;

const partOptions = ref<{ label: string; value: number; disabled?: boolean }[]>([]);
const partOptionsLoading = ref(false);
const partOptionsError = ref(false);
const partLabels = computed(
  () => new Map(partOptions.value.map((part) => [part.value, part.label]))
);

function getPartLabel(id: unknown): string {
  return typeof id !== "number" ? "-" : partLabels.value.get(id) || `图纸#${id}`;
}

async function fetchPartOptions() {
  if (partOptionsLoading.value) return;
  partOptionsLoading.value = true;
  partOptionsError.value = false;
  try {
    const items: CncPartTable[] = [];
    let pageNo = 1;
    while (true) {
      const response = await CncPartAPI.listCncPart({ page_no: pageNo, page_size: 100 });
      const page = response.data.data;
      items.push(...page.items);
      if (!page.has_next || page.items.length === 0) break;
      pageNo += 1;
    }
    partOptions.value = items.flatMap((part) => {
      if (part.id == null) return [];
      const fileName = part.file_name || part.file_path?.split(/[\\/]/).pop();
      return [{ label: fileName || `图纸#${part.id}`, value: part.id }];
    });
  } catch (error: unknown) {
    partOptionsError.value = true;
    console.error("加载图纸列表失败:", error);
  } finally {
    partOptionsLoading.value = false;
  }
}

function handlePartDropdownVisible(visible: boolean) {
  if (visible) void fetchPartOptions();
}

/** 参数字典与联动规则 */
const { loadCatalog, catalogCache, JLC_DEFAULT_CATALOG, XOM_DEFAULT_CATALOG } = useParamCatalog();

const createInitialFormData = (): CncPartConfigForm => ({
  name: undefined,
  site_type: undefined,
  part_id: undefined,
  quantity: 1,
  material_category: undefined,
  material_code: undefined,
  material: undefined,
  surface_finish_code: undefined,
  surface_finish: undefined,
  tolerance: undefined,
  roughness: undefined,
  subprocess_code: undefined,
  has_threads: false,
  thread_count: 0,
  has_inserts: false,
  insert_count: 0,
  inspection_code: undefined,
  certification_code: undefined,
  marking_code: undefined,
  marking_text: undefined,
  delivery_code: undefined,
  requires_2d_drawing: false,
  technical_notes: undefined,
  extra_params: undefined,
  enabled: true,
});

const formData = ref<CncPartConfigForm>(createInitialFormData());

const currentCatalog = computed<CncParamsCatalog | null>(() => {
  const site = formData.value.site_type;
  if (!site) return null;
  if (catalogCache.value[site]) return catalogCache.value[site];
  if (site === 2) return JLC_DEFAULT_CATALOG as unknown as CncParamsCatalog;
  if (site === 1) return XOM_DEFAULT_CATALOG as unknown as CncParamsCatalog;
  return null;
});

const materialCategoryOptions = computed(() => {
  const cats = currentCatalog.value?.material_categories || [];
  return cats.map((cat) => ({ label: cat, value: cat }));
});

const materialCodeOptions = computed(() => {
  const mats = currentCatalog.value?.materials || [];
  const selectedCat = formData.value.material_category;
  const filtered = selectedCat ? mats.filter((m) => m.category === selectedCat) : mats;
  return filtered.map((m) => ({
    label: m.code ? `${m.name} (${m.code})` : m.name,
    value: m.code || m.name,
    name: m.name,
    code: m.code,
    category: m.category,
    supported_finishes: m.supported_finishes,
    supported_tolerances: m.supported_tolerances,
    supported_roughnesses: m.supported_roughnesses,
  }));
});

const currentMaterialItem = computed(() => {
  const mats = currentCatalog.value?.materials || [];
  const code = formData.value.material_code;
  const name = formData.value.material;
  return mats.find((m) => (code && m.code === code) || (name && m.name === name)) || null;
});

const surfaceFinishOptions = computed(() => {
  const allFinishes = currentCatalog.value?.surface_finishes || [];
  const supported = currentMaterialItem.value?.supported_finishes;
  if (supported && supported.length > 0) {
    return supported.map((s) => ({ label: s, value: s }));
  }
  return allFinishes.map((f) => ({ label: f.name, value: f.name }));
});

const toleranceOptions = computed(() => {
  const allTolerances = currentCatalog.value?.tolerances || [];
  const supported = currentMaterialItem.value?.supported_tolerances;
  if (supported && supported.length > 0) {
    return supported.map((t) => ({ label: t, value: t }));
  }
  return allTolerances.map((t) => ({ label: t.name, value: t.name }));
});

const roughnessOptions = computed(() => {
  const allRoughnesses = currentCatalog.value?.roughnesses || [];
  const supported = currentMaterialItem.value?.supported_roughnesses;
  if (supported && supported.length > 0) {
    return supported.map((r) => ({ label: r, value: r }));
  }
  return allRoughnesses.map((r) => ({ label: r.name, value: r.name }));
});

const subprocessOptions = computed(() => {
  const subs = currentCatalog.value?.subprocesses || [];
  return subs.map((s) => ({ label: s.name, value: s.code || s.name }));
});

const inspectionOptions = computed(() => {
  const ins = currentCatalog.value?.inspections || [];
  return ins.map((i) => ({ label: i.name, value: i.code || i.name }));
});

const certificationOptions = computed(() => {
  const certs = currentCatalog.value?.certifications || [];
  return certs.map((c) => ({ label: c.name, value: c.code || c.name }));
});

const markingOptions = computed(() => {
  const marks = currentCatalog.value?.markings || [];
  return marks.map((m) => ({ label: m.name, value: m.code || m.name }));
});

const deliveryOptions = computed(() => {
  const delivs = currentCatalog.value?.delivery_tiers || [];
  return delivs.map((d) => ({ label: d.name, value: d.code || d.name }));
});

function handleMaterialCodeSelect(val: string) {
  const found = materialCodeOptions.value.find((opt) => opt.value === val);
  if (found) {
    formData.value.material = found.name;
    formData.value.material_code = found.code || found.name;
    if (found.category && !formData.value.material_category) {
      formData.value.material_category = found.category;
    }
    if (
      found.supported_finishes &&
      found.supported_finishes.length > 0 &&
      formData.value.surface_finish &&
      !found.supported_finishes.includes(formData.value.surface_finish)
    ) {
      formData.value.surface_finish = undefined;
    }
  }
}

function check2dDrawingTrigger() {
  let need2d = false;
  const tol = formData.value.tolerance || "";
  if (["±0.05", "±0.02", "±.001", "±.002"].some((t) => tol.includes(t))) {
    need2d = true;
  }
  if (formData.value.has_threads && (formData.value.thread_count ?? 0) > 0) {
    need2d = true;
  }
  if (formData.value.has_inserts && (formData.value.insert_count ?? 0) > 0) {
    need2d = true;
  }
  const sf = formData.value.surface_finish;
  const finishItem = currentCatalog.value?.surface_finishes?.find((f) => f.name === sf);
  if (finishItem?.requires_2d_drawing) {
    need2d = true;
  }
  if (need2d) {
    formData.value.requires_2d_drawing = true;
  }
}

watch(
  () => formData.value.site_type,
  async (newSite) => {
    if (newSite) {
      await loadCatalog(newSite);
    }
  }
);

watch(
  () => [
    formData.value.tolerance,
    formData.value.has_threads,
    formData.value.thread_count,
    formData.value.has_inserts,
    formData.value.insert_count,
    formData.value.surface_finish,
  ],
  () => {
    check2dDrawingTrigger();
  }
);

onMounted(() => {
  void fetchPartOptions();
  void fetchPlatformOptions();
});

type CncPartConfigSearchFormParams = {
  name?: string;
  site_type?: number;
  material?: string;
  quantity?: number;
  surface_finish?: string;
  enabled?: boolean;
  part_id?: number;
} & AuditSearchFormParams;

const searchForm = ref<CncPartConfigSearchFormParams>({
  name: undefined,
  site_type: undefined,
  material: undefined,
  quantity: undefined,
  surface_finish: undefined,
  enabled: undefined,
  part_id: undefined,
  created_id: undefined,
  updated_id: undefined,
  created_time: undefined,
  updated_time: undefined,
});

/** 搜索区域默认展开展示 */
const showSearchBar = ref(true);

const searchBarRef = ref<{ validate: () => Promise<boolean> } | null>(null);
const searchBarRules: Record<string, unknown> = {};

/** 业务搜索项（名称与标签均控制在 6 个字内） */
const businessSearchItems = computed(() => [
  {
    label: "配置名称",
    key: "name",
    type: "input",
    placeholder: "请输入配置名称",
    clearable: true,
    props: {
      maxlength: 6,
    },
    span: 6,
  },
  {
    label: "报价平台",
    key: "site_type",
    type: "select",
    options: platformOptions.value,
    placeholder: "请选择报价平台",
    clearable: true,
    props: {
      filterable: true,
      loading: platformOptionsLoading.value,
    },
    span: 6,
  },
  {
    label: "加工材料",
    key: "material",
    type: "input",
    placeholder: "请输入加工材料",
    clearable: true,
    span: 6,
  },
  {
    label: "表面处理",
    key: "surface_finish",
    type: "input",
    placeholder: "请输入表面处理",
    clearable: true,
    span: 6,
  },
  {
    label: "启用状态",
    key: "enabled",
    type: "select",
    options: STATUS_OPTIONS,
    placeholder: "请选择启用状态",
    clearable: true,
    span: 6,
  },
  {
    label: "关联图纸",
    key: "part_id",
    type: "select",
    options: partOptions.value,
    placeholder: "请选择关联图纸",
    clearable: true,
    props: {
      filterable: true,
      loading: partOptionsLoading.value,
      onVisibleChange: handlePartDropdownVisible,
    },
    span: 6,
  },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } =
  useTableSelection<CncPartConfigTable>();

const createLoading = ref(false);
const moreLoading = ref(false);

const PK = "id" as const;

const {
  columns,
  columnChecks,
  data,
  loading,
  pagination,
  searchParams,
  getData,
  replaceSearchParams,
  resetSearchParams,
  handleSizeChange,
  handleCurrentChange,
  refreshData,
  refreshCreate,
  refreshUpdate,
  refreshRemove,
} = useTable({
  core: {
    apiFn: CncPartConfigAPI.listCncPartConfig,
    apiParams: {
      page_no: 1,
      page_size: 10,
    },
    columnsFactory: resolveStatusColumns<CncPartConfigTable>(() => [
      { type: "selection", width: 48, fixed: "left" },
      { type: "globalIndex", width: 56, label: "序号" },
      { prop: "name", label: "配置名称", minWidth: 120, showOverflowTooltip: true },
      {
        prop: "site_type",
        label: "报价平台",
        minWidth: 110,
        showOverflowTooltip: true,
        formatter: (row: CncPartConfigTable) => getPlatformLabel(row.site_type),
      },
      {
        prop: "part_id",
        label: "关联图纸",
        minWidth: 180,
        showOverflowTooltip: true,
        formatter: (row: CncPartConfigTable) => getPartLabel(row.part_id),
      },
      { prop: "material", label: "加工材料", minWidth: 140, showOverflowTooltip: true },
      { prop: "surface_finish", label: "表面处理", minWidth: 120, showOverflowTooltip: true },
      {
        prop: "tolerance",
        label: "公差精度",
        minWidth: 120,
        showOverflowTooltip: true,
        formatter: (row: CncPartConfigTable) => row.tolerance || "-",
      },
      { prop: "quantity", label: "加工数量", width: 90, align: "center" },
      {
        prop: "requires_2d_drawing",
        label: "2D图纸",
        width: 95,
        align: "center",
        formatter: (row: CncPartConfigTable) => (row.requires_2d_drawing ? "需要" : "无需"),
      },
      {
        prop: "enabled",
        label: "启用状态",
        width: 90,
        align: "center",
        status: {
          true: { type: "success", text: "启用" },
          false: { type: "danger", text: "禁用" },
        },
      },
      {
        prop: "created_time",
        label: "创建时间",
        width: 168,
        sortable: true,
        showOverflowTooltip: true,
      },
      {
        prop: "updated_time",
        label: "更新时间",
        width: 168,
        sortable: true,
        showOverflowTooltip: true,
      },
      {
        prop: "operation",
        label: "操作",
        width: 270,
        fixed: "right",
        align: "center",
        formatter: (row: CncPartConfigTable) => formatOperationCell(row),
      },
    ]),
  },
});

const crudCols = toCrudCols(columns);

const exportQueryParams = computed(() => {
  return stripPaginationParams(searchParams as Record<string, unknown>);
});

const importContentConfig = computed<IContentConfig>(() => ({
  permPrefix: "module_cnc:cnc_part_config",
  cols: crudCols.value,
  indexAction: async () => ({}),
  importTemplate: () => CncPartConfigAPI.downloadTemplateCncPartConfig(),
}));

const exportContentConfig = computed(() => ({
  permPrefix: "module_cnc:cnc_part_config",
  cols: crudCols.value,
  exportsBlobAction: async (params: IObject) => {
    const merged = {
      ...(exportQueryParams.value as unknown as Record<string, unknown>),
      ...params,
    } as unknown as CncPartConfigPageQuery;
    const res = await CncPartConfigAPI.exportCncPartConfig(merged);
    return res.data as Blob;
  },
}));

const { dialogVisible } = useCrudDialog();

watch(
  () => dialogVisible.visible,
  (visible) => {
    if (visible) {
      void fetchPartOptions();
      void fetchPlatformOptions();
      if (formData.value.site_type) {
        void loadCatalog(formData.value.site_type);
      }
    }
  }
);

const detailFormData = ref<CncPartConfigTable>({});

const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "配置名称", prop: "name" },
  { label: "报价平台", prop: "site_type", slot: "site_type" },
  { label: "关联图纸", prop: "part_id", slot: "part_id" },
  { label: "加工数量", prop: "quantity" },
  { label: "材料分类", prop: "material_category" },
  { label: "加工材料", prop: "material" },
  { label: "表面处理", prop: "surface_finish" },
  { label: "选用公差", prop: "tolerance" },
  { label: "粗糙度", prop: "roughness" },
  { label: "加工工艺", prop: "subprocess_code" },
  { label: "螺纹攻牙", prop: "has_threads", slot: "has_threads" },
  { label: "压铆镶件", prop: "has_inserts", slot: "has_inserts" },
  { label: "出货检验", prop: "inspection_code" },
  { label: "质量认证", prop: "certification_code" },
  { label: "发货时效", prop: "delivery_code" },
  { label: "2D图纸需求", prop: "requires_2d_drawing", slot: "requires_2d_drawing" },
  { label: "启用状态", prop: "enabled", slot: "enabled" },
  { label: "创建时间", prop: "created_time" },
  { label: "更新时间", prop: "updated_time" },
  { label: "技术备注", prop: "technical_notes", span: 2 },
  { label: "差异化参数", prop: "extra_params", slot: "extra_params", span: 2 },
];

/** 表单校验规则：名称最多限制到 6 个字，配置必填项 */
const rules = reactive({
  name: [
    { required: true, message: "请输入配置名称", trigger: "blur" },
    { max: 6, message: "配置名称最多不超过6个字", trigger: "blur" },
  ],
  site_type: [{ required: true, message: "请选择报价平台", trigger: "change" }],
  part_id: [{ required: true, message: "请选择关联图纸", trigger: "change" }],
  material: [{ required: true, message: "请输入加工材料", trigger: "blur" }],
  quantity: [
    { required: true, message: "请输入加工数量", trigger: "blur" },
    {
      validator: (_rule: unknown, value: unknown, callback: (error?: Error) => void) => {
        if (value == null || value === "") {
          callback(new Error("请输入加工数量"));
        } else if (Number(value) < 1 || !Number.isInteger(Number(value))) {
          callback(new Error("加工数量必须为大于0的整数"));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
  surface_finish: [{ required: false, trigger: "blur" }],
  enabled: [{ required: false, trigger: "change" }],
});

/** 弹窗表单配置：精确维护 ElSelect 顺序保证测试契约与实际联动效果 */
const dialogFormItems = computed<FormItem[]>(() => [
  {
    key: "name",
    label: "配置名称",
    type: "input",
    props: {
      maxlength: 6,
      showWordLimit: true,
      placeholder: "请输入配置名称（最多6个字）",
      clearable: true,
    },
  },
  {
    key: "site_type",
    label: "报价平台",
    type: "select",
    props: {
      options:
        formData.value.site_type != null && !platformLabels.value.has(formData.value.site_type)
          ? [
              ...platformOptions.value,
              {
                label: getPlatformLabel(formData.value.site_type),
                value: formData.value.site_type,
                disabled: true,
              },
            ]
          : platformOptions.value,
      loading: platformOptionsLoading.value,
      placeholder: "请选择报价平台",
      filterable: true,
      clearable: true,
      style: { width: "100%" },
    },
  },
  {
    key: "part_id",
    label: "关联图纸",
    type: "select",
    props: {
      options:
        formData.value.part_id != null && !partLabels.value.has(formData.value.part_id)
          ? [
              ...partOptions.value,
              {
                label: getPartLabel(formData.value.part_id),
                value: formData.value.part_id,
                disabled: true,
              },
            ]
          : partOptions.value,
      loading: partOptionsLoading.value,
      filterable: true,
      clearable: true,
      placeholder: "请选择关联图纸",
      noDataText: partOptionsError.value
        ? "图纸加载失败，请重新打开下拉框重试"
        : "暂无图纸，请先在图纸管理中新增",
      onVisibleChange: handlePartDropdownVisible,
      style: { width: "100%" },
    },
  },
  {
    key: "quantity",
    label: "加工数量",
    type: "number",
    props: {
      min: 1,
      step: 1,
      precision: 0,
      controlsPosition: "right",
      placeholder: "请输入加工数量（默认1）",
      style: { width: "100%" },
    },
  },
  {
    key: "material_category",
    label: "材料分类",
    type: "select",
    props: {
      options: materialCategoryOptions.value,
      placeholder: "请选择材料分类",
      filterable: true,
      clearable: true,
      style: { width: "100%" },
    },
  },
  {
    key: "material_code",
    label: "标准材料",
    type: "select",
    props: {
      options: materialCodeOptions.value,
      placeholder: "请选择标准材料牌号",
      filterable: true,
      clearable: true,
      onChange: handleMaterialCodeSelect,
      style: { width: "100%" },
    },
  },
  {
    key: "material",
    label: "加工材料",
    type: "input",
    props: {
      placeholder: "请输入加工材料，例如：铝合金 6061",
      clearable: true,
    },
  },
  {
    key: "surface_finish",
    label: "表面处理",
    type: "select",
    props: {
      options: surfaceFinishOptions.value,
      placeholder: "请选择表面处理工艺",
      filterable: true,
      allowCreate: true,
      defaultFirstOption: true,
      clearable: true,
      style: { width: "100%" },
    },
  },
  {
    key: "tolerance",
    label: "选用公差",
    type: "select",
    props: {
      options: toleranceOptions.value,
      placeholder: "请选择精度公差等级",
      filterable: true,
      allowCreate: true,
      defaultFirstOption: true,
      clearable: true,
      style: { width: "100%" },
    },
  },
  {
    key: "roughness",
    label: "粗糙度",
    type: "select",
    props: {
      options: roughnessOptions.value,
      placeholder: "请选择表面粗糙度",
      filterable: true,
      allowCreate: true,
      defaultFirstOption: true,
      clearable: true,
      style: { width: "100%" },
    },
  },
  {
    key: "subprocess_code",
    label: "加工工艺",
    type: "select",
    props: {
      options: subprocessOptions.value,
      placeholder: "请选择加工子工艺",
      filterable: true,
      clearable: true,
      style: { width: "100%" },
    },
  },
  {
    key: "delivery_code",
    label: "发货时效",
    type: "select",
    props: {
      options: deliveryOptions.value,
      placeholder: "请选择发货时效偏好",
      filterable: true,
      clearable: true,
      style: { width: "100%" },
    },
  },
  {
    key: "has_threads",
    label: "螺纹攻牙",
    type: "switch",
    props: {
      activeText: "有螺纹",
      inactiveText: "无螺纹",
      inlinePrompt: true,
    },
  },
  {
    key: "thread_count",
    label: "攻牙孔数",
    type: "number",
    hidden: !formData.value.has_threads,
    props: {
      min: 1,
      step: 1,
      precision: 0,
      controlsPosition: "right",
      placeholder: "请输入攻牙孔数量",
      style: { width: "100%" },
    },
  },
  {
    key: "has_inserts",
    label: "压铆镶件",
    type: "switch",
    props: {
      activeText: "有镶件",
      inactiveText: "无镶件",
      inlinePrompt: true,
    },
  },
  {
    key: "insert_count",
    label: "镶件数量",
    type: "number",
    hidden: !formData.value.has_inserts,
    props: {
      min: 1,
      step: 1,
      precision: 0,
      controlsPosition: "right",
      placeholder: "请输入镶件数量",
      style: { width: "100%" },
    },
  },
  {
    key: "inspection_code",
    label: "出货检验",
    type: "select",
    props: {
      options: inspectionOptions.value,
      placeholder: "请选择出货检验要求",
      filterable: true,
      clearable: true,
      style: { width: "100%" },
    },
  },
  {
    key: "certification_code",
    label: "质量认证",
    type: "select",
    hidden: formData.value.site_type !== 1 && !formData.value.certification_code,
    props: {
      options: certificationOptions.value,
      placeholder: "请选择质量认证/报告",
      filterable: true,
      clearable: true,
      style: { width: "100%" },
    },
  },
  {
    key: "marking_code",
    label: "零件打标",
    type: "select",
    props: {
      options: markingOptions.value,
      placeholder: "请选择零件打标方式",
      filterable: true,
      clearable: true,
      style: { width: "100%" },
    },
  },
  {
    key: "marking_text",
    label: "打标内容",
    type: "input",
    hidden: !formData.value.marking_code,
    props: {
      placeholder: "请输入打标文字内容",
      clearable: true,
    },
  },
  {
    key: "requires_2d_drawing",
    label: "需2D图纸",
    type: "switch",
    props: {
      activeText: "必须",
      inactiveText: "非必需",
      inlinePrompt: true,
    },
  },
  {
    key: "enabled",
    label: "启用状态",
    type: "switch",
    props: {
      activeText: "启用",
      inactiveText: "禁用",
      inlinePrompt: true,
    },
  },
  {
    key: "technical_notes",
    label: "技术备注",
    type: "input",
    span: 24,
    props: {
      type: "textarea",
      rows: 2,
      placeholder: "请输入特殊工艺要求、关键公差面标注或加工说明",
      clearable: true,
    },
  },
]);

const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

const crud = useCrudForm<CncPartConfigForm>({
  formData,
  initialFormData: createInitialFormData(),
  dialogVisible,
  dataFormRef,
  formRenderKey,
  detailApi: (id: number) => CncPartConfigAPI.detailCncPartConfig(id),
  createApi: (data: CncPartConfigForm) => CncPartConfigAPI.createCncPartConfig(data),
  updateApi: (id: number, data: CncPartConfigForm) =>
    CncPartConfigAPI.updateCncPartConfig(id, data),
  titles: { create: "新增配置", update: "修改配置", detail: "配置详情" },
  detailFormData,
  onCreateSuccess: async () => {
    await refreshCreate();
  },
  onUpdateSuccess: async () => {
    await refreshUpdate();
  },
});

const { submitLoading } = crud;

const { importVisible, exportVisible, openImport, openExport } = useImportExport();

async function handleRefresh() {
  await Promise.all([refreshData(), fetchPartOptions(), fetchPlatformOptions()]);
}

const handleSearch = async (params: CncPartConfigSearchFormParams) => {
  await searchBarRef.value?.validate();
  replaceSearchParams({
    name: params.name,
    site_type: params.site_type,
    material: params.material,
    quantity: params.quantity,
    surface_finish: params.surface_finish,
    enabled: params.enabled,
    part_id: params.part_id,
    created_id: params.created_id ?? undefined,
    updated_id: params.updated_id ?? undefined,
    created_time:
      Array.isArray(params.created_time) && params.created_time.length === 2
        ? params.created_time
        : undefined,
    updated_time:
      Array.isArray(params.updated_time) && params.updated_time.length === 2
        ? params.updated_time
        : undefined,
  } as Record<string, unknown>);
  await getData();
};

const onResetSearch = async () => {
  searchForm.value = {
    name: undefined,
    site_type: undefined,
    material: undefined,
    quantity: undefined,
    surface_finish: undefined,
    enabled: undefined,
    part_id: undefined,
    created_id: undefined,
    updated_id: undefined,
    created_time: undefined,
    updated_time: undefined,
  };
  await resetSearchParams();
};

function buildRowActions(row: CncPartConfigTable): TableOperationAction[] {
  const all: TableOperationAction[] = [];
  const running = quote.run.value;
  const isRowRunning =
    row.id != null &&
    (quote.loadingIds.value.has(row.id) ||
      (running?.config_id === row.id && !isQuoteTerminal(running)));

  if (canAutoQuote()) {
    all.push({
      key: "quote",
      label: isRowRunning ? "自动报价中..." : "自动报价",
      artType: "more",
      icon: isRowRunning ? "svg-spinners:180-ring-with-bg" : "ri:money-cny-circle-line",
      iconColor: "var(--el-color-primary)",
      disabled: row.enabled !== true || isRowRunning,
      run: () => {
        if (row.enabled !== true || isRowRunning) return;
        handleAutoQuote(row);
      },
    });
  }

  all.push({
    key: "quote_records",
    label: "报价结果",
    artType: "more",
    icon: "ri:file-chart-line",
    iconColor: "var(--el-color-success)",
    run: () => goToQuoteResults(row.id),
  });

  all.push(
    {
      key: "detail",
      label: "详情",
      artType: "view",
      perm: "module_cnc:cnc_part_config:detail",
      run: () => void crud.handleOpenDialog("detail", row[PK] as number),
    },
    {
      key: "edit",
      label: "编辑",
      artType: "edit",
      icon: "ri:edit-2-line",
      perm: "module_cnc:cnc_part_config:update",
      run: () => void crud.handleOpenDialog("update", row[PK] as number),
    },
    {
      key: "delete",
      label: "删除",
      artType: "delete",
      icon: "ri:delete-bin-4-line",
      perm: "module_cnc:cnc_part_config:delete",
      run: () => deleteRow(row),
    }
  );

  return all;
}

function formatOperationCell(row: CncPartConfigTable) {
  return renderTableOperationCell(buildRowActions(row), {
    maxInline: 4,
    wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1",
  });
}

async function handleAdd() {
  createLoading.value = true;
  try {
    await crud.handleOpenDialog("create");
  } finally {
    createLoading.value = false;
  }
}

async function handleCloseDialog() {
  await crud.handleCloseDialog();
}

async function handleSubmit() {
  await crud.handleSubmit();
}

const deleteRow = async (row: CncPartConfigTable) => {
  if (!row[PK]) return;
  try {
    await confirmDelete(`确定删除该图纸参数配置吗？此操作不可恢复！`);
    await CncPartConfigAPI.deleteCncPartConfig([row[PK] as number]);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  }
};

async function handleBatchDelete() {
  const ids = selectedIds.value;
  if (ids.length === 0) return;
  try {
    await confirmBatchDelete(
      ids.length,
      selectedRows.value.map((row) => String(row["id"] ?? ""))
    );
    batchDeleting.value = true;
    await CncPartConfigAPI.deleteCncPartConfig(ids);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  } finally {
    batchDeleting.value = false;
  }
}

async function handleMoreClick(value: "enable" | "disable") {
  const ids = selectedIds.value;
  if (ids.length === 0) {
    ElMessage.warning("请先在列表中勾选数据");
    return;
  }
  try {
    await confirmToggleStatus(value);
    moreLoading.value = true;
    const status = value === "enable" ? 0 : 1;
    await CncPartConfigAPI.batchCncPartConfig({ ids, status });
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshData();
  } catch {
    // 用户取消或操作失败
  } finally {
    moreLoading.value = false;
  }
}

async function handleCrudImportUpload(formData: FormData) {
  try {
    const res = await CncPartConfigAPI.importCncPartConfig(formData);
    if (res.data.code === ResultEnum.SUCCESS) {
      ElMessage.success(res.data.msg || "导入成功");
      importVisible.value = false;
      await refreshData();
    }
  } catch (error: unknown) {
    if (import.meta.env.DEV) console.error("[Import]", error);
  }
}
</script>

<style lang="scss" scoped></style>
