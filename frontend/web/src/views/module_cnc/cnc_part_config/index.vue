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
      width="860px"
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
          <template #enabled="{ row }">
            <ElTag :type="row?.enabled ? 'success' : 'danger'">
              {{ row?.enabled ? "启用" : "禁用" }}
            </ElTag>
          </template>
          <template #part_id="{ row }">
            {{ getPartLabel(row?.part_id) }}
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
          :label-width="90"
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
      @close="quote.close"
      @select-account="quote.selectedAccount.value = $event"
      @start="quote.chooseAccount"
      @input="quote.command"
      @resume="quote.command()"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
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
import CncPartConfigAPI, {
  type CncPartConfigForm,
  type CncPartConfigPageQuery,
  type CncPartConfigTable,
} from "@/api/module_cnc/cnc_part_config";

defineOptions({
  name: "CncPartConfig",
  inheritAttrs: false,
});

const quote = useAutoQuote();
function canAutoQuote() {
  return (
    [
      "module_cnc:cnc_part_config:update",
      "module_cnc:cnc_account:query",
      "module_cnc:cnc_account:update",
    ].every(checkPerm) &&
    (checkPerm("module_cnc:cnc_part_config:query") ||
      checkPerm("module_cnc:cnc_part_config:detail"))
  );
}
function handleAutoQuote(row: CncPartConfigTable) {
  if (canAutoQuote()) void quote.open(row);
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

onMounted(() => {
  void fetchPartOptions();
  void fetchPlatformOptions();
});

const createInitialFormData = (): CncPartConfigForm => ({
  name: undefined,
  site_type: undefined,
  material: undefined,
  quantity: 1,
  surface_finish: undefined,
  extra_params: undefined,
  enabled: true,
  part_id: undefined,
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
      { prop: "material", label: "加工材料", minWidth: 130, showOverflowTooltip: true },
      { prop: "quantity", label: "加工数量", width: 90, align: "center" },
      { prop: "surface_finish", label: "表面处理", minWidth: 130, showOverflowTooltip: true },
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
        prop: "part_id",
        label: "关联图纸",
        minWidth: 200,
        showOverflowTooltip: true,
        formatter: (row: CncPartConfigTable) => getPartLabel(row.part_id),
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
    }
  }
);

const detailFormData = ref<CncPartConfigTable>({});

const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "配置名称", prop: "name" },
  { label: "报价平台", prop: "site_type", slot: "site_type" },
  { label: "加工材料", prop: "material" },
  { label: "加工数量", prop: "quantity" },
  { label: "表面处理", prop: "surface_finish" },
  { label: "启用状态", prop: "enabled", slot: "enabled" },
  { label: "关联图纸", prop: "part_id", slot: "part_id" },
  { label: "创建时间", prop: "created_time" },
  { label: "更新时间", prop: "updated_time" },
  { label: "差异化参数", prop: "extra_params", slot: "extra_params", span: 2 },
];

const formData = ref<CncPartConfigForm>(createInitialFormData());

/** 表单校验规则：名称最多限制到 6 个字，配置必填项 */
const rules = reactive({
  name: [
    { required: true, message: "请输入配置名称", trigger: "blur" },
    { max: 6, message: "配置名称最多不超过6个字", trigger: "blur" },
  ],
  site_type: [{ required: true, message: "请选择报价平台", trigger: "change" }],
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
  part_id: [{ required: true, message: "请选择关联图纸", trigger: "change" }],
  surface_finish: [{ required: false, trigger: "blur" }],
  enabled: [{ required: false, trigger: "change" }],
});

/** 弹窗表单配置：标签精炼（<=6字），名称输入限制6个字 */
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
    key: "material",
    label: "加工材料",
    type: "input",
    props: {
      placeholder: "请输入加工材料，例如：铝合金 6061",
      clearable: true,
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
    key: "surface_finish",
    label: "表面处理",
    type: "input",
    props: {
      placeholder: "请输入表面处理，例如：本色喷砂",
      clearable: true,
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
    key: "enabled",
    label: "启用状态",
    type: "switch",
    props: {
      activeText: "启用",
      inactiveText: "禁用",
      inlinePrompt: true,
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
    // 成功 / 失败提示由 axios 拦截器统一处理
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
