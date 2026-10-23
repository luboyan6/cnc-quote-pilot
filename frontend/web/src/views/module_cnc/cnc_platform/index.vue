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
        @refresh="refreshData"
      >
        <template #left>
          <FaTableHeaderLeft
            :remove-ids="selectedIds"
            :perm-create="['module_cnc:cnc_platform:create']"
            :perm-import="['module_cnc:cnc_platform:import']"
            :perm-export="['module_cnc:cnc_platform:export']"
            :perm-delete="['module_cnc:cnc_platform:delete']"
            :perm-patch="['module_cnc:cnc_platform:patch']"
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
      width="920px"
      dialog-class="crud-embed-dialog"
      modal-class="crud-embed-dialog"
      :form-mode="dialogVisible.type"
      :confirm-loading="submitLoading"
      @cancel="handleCloseDialog"
      @close="handleCloseDialog"
      @confirm="handleSubmit()"
    >
      <template v-if="dialogVisible.type === 'detail'">
        <FaDescriptions
          :column="4"
          :data="detailFormData"
          :items="detailItems"
          max-height="70vh"
        >
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
          :label-width="100"
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
      default-template-file-name="cnc_platform_import_template.xlsx"
      @upload="handleCrudImportUpload"
    />

    <FaExportDialog
      v-model="exportVisible"
      :content-config="exportContentConfig"
      :query-params="exportQueryParams"
      :page-data="data"
      :selection-data="selectedRows"
    />
  </div>
</template>

<script setup lang="ts">
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
import CncPlatformAPI, {
  type CncPlatformForm,
  type CncPlatformPageQuery,
  type CncPlatformTable,
} from "@/api/module_cnc/cnc_platform";

defineOptions({
  name: "CncPlatform",
  inheritAttrs: false,
});

// 常量定义
const STATUS_OPTIONS = [
  { label: "启用", value: 0 },
  { label: "停用", value: 1 },
] as const;

const createInitialFormData = (): CncPlatformForm => ({
  name: undefined,
  login_url: undefined,
  quote_entry_url: undefined,
});

type CncPlatformSearchFormParams = {
  name?: string;
  login_url?: string;
  quote_entry_url?: string;
} & AuditSearchFormParams;

const searchForm = ref<CncPlatformSearchFormParams>({
  name: undefined,
  login_url: undefined,
  quote_entry_url: undefined,
  created_id: undefined,
  updated_id: undefined,
  created_time: undefined,
  updated_time: undefined,
});

/** 搜索区域默认展开展示 */
const showSearchBar = ref(true);

const searchBarRef = ref<{ validate: () => Promise<boolean> } | null>(null);
const searchBarRules: Record<string, unknown> = {};

/** 业务搜索项（审计四字段由 FaSearchBar 的 includeAudit 属性追加） */
const businessSearchItems = computed(() => [
  {
    label: "平台显示名称",
    key: "name",
    type: "input",
    placeholder: "请输入平台显示名称",
    clearable: true,
    span: 6,
  },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } =
  useTableSelection<CncPlatformTable>();

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
    apiFn: CncPlatformAPI.listCncPlatform,
    apiParams: {
      page_no: 1,
      page_size: 10,
    },
    columnsFactory: resolveStatusColumns<CncPlatformTable>(() => [
      { type: "selection", width: 48, fixed: "left" },
      { type: "globalIndex", width: 56, label: "序号" },
      { prop: "name", label: "平台显示名称", minWidth: 120, showOverflowTooltip: true },
      { prop: "created_time", label: "创建时间", width: 168, sortable: true, showOverflowTooltip: true },
      { prop: "updated_time", label: "更新时间", width: 168, sortable: true, showOverflowTooltip: true },
      {
        prop: "created_by",
        label: "创建人",
        minWidth: 100,
        formatter: (row: CncPlatformTable) => row.created_by?.name ?? "—",
      },
      {
        prop: "updated_by",
        label: "更新人",
        minWidth: 100,
        formatter: (row: CncPlatformTable) => row.updated_by?.name ?? "—",
      },
      { prop: "login_url", label: "登录地址", minWidth: 120, showOverflowTooltip: true },
      { prop: "quote_entry_url", label: "询价地址", minWidth: 120, showOverflowTooltip: true },
      {
        prop: "operation",
        label: "操作",
        width: 180,
        fixed: "right",
        align: "center",
        formatter: (row: CncPlatformTable) => formatOperationCell(row),
      },
    ]),
  },
});

const crudCols = toCrudCols(columns);

const exportQueryParams = computed(() => {
  return stripPaginationParams(searchParams as Record<string, unknown>);
});

const importContentConfig = computed<IContentConfig>(() => ({
  permPrefix: "module_cnc:cnc_platform",
  cols: crudCols.value,
  indexAction: async () => ({}),
  importTemplate: () => CncPlatformAPI.downloadTemplateCncPlatform(),
}));

const exportContentConfig = computed(() => ({
  permPrefix: "module_cnc:cnc_platform",
  cols: crudCols.value,
  exportsBlobAction: async (params: IObject) => {
    const merged = {
      ...(exportQueryParams.value as unknown as Record<string, unknown>),
      ...params,
    } as unknown as CncPlatformPageQuery;
    const res = await CncPlatformAPI.exportCncPlatform(merged);
    return res.data as Blob;
  },
}));

const { dialogVisible } = useCrudDialog();

const detailFormData = ref<CncPlatformTable>({});

const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "平台显示名称", prop: "name" },
  { label: "创建时间", prop: "created_time" },
  { label: "更新时间", prop: "updated_time" },
  { label: "创建人", prop: "created_by.name" },
  { label: "更新人", prop: "updated_by.name" },
  { label: "登录地址", prop: "login_url" },
  { label: "询价地址", prop: "quote_entry_url" },
];

const formData = ref<CncPlatformForm>(createInitialFormData());

const rules = reactive({
  name: [{ required: false, message: "请填写平台显示名称", trigger: "blur" }],
  login_url: [{ required: false, message: "请填写登录地址", trigger: "blur" }],
  quote_entry_url: [{ required: false, message: "请填写询价地址", trigger: "blur" }],
});

const dialogFormItems: FormItem[] = [
  { key: "name", label: "平台显示名称", type: "input", props: { placeholder: "请输入平台显示名称" } },
  { key: "login_url", label: "登录地址", type: "input", props: { type: "textarea", rows: 4, placeholder: "请输入登录地址" } },
  { key: "quote_entry_url", label: "询价地址", type: "input", props: { type: "textarea", rows: 4, placeholder: "请输入询价地址" } },
];

const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

const crud = useCrudForm<CncPlatformForm>({
  formData,
  initialFormData: createInitialFormData(),
  dialogVisible,
  dataFormRef,
  formRenderKey,
  detailApi: (id: number) => CncPlatformAPI.detailCncPlatform(id),
  createApi: (data: CncPlatformForm) => CncPlatformAPI.createCncPlatform(data),
  updateApi: (id: number, data: CncPlatformForm) => CncPlatformAPI.updateCncPlatform(id, data),
  titles: { create: "新增", update: "修改", detail: "详情" },
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

const handleSearch = async (params: CncPlatformSearchFormParams) => {
  await searchBarRef.value?.validate();
  replaceSearchParams({
    name: params.name,
    login_url: params.login_url,
    quote_entry_url: params.quote_entry_url,
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
    login_url: undefined,
    quote_entry_url: undefined,
    created_id: undefined,
    updated_id: undefined,
    created_time: undefined,
    updated_time: undefined,
  };
  await resetSearchParams();
};

function buildRowActions(row: CncPlatformTable): TableOperationAction[] {
  const all: TableOperationAction[] = [
    {
      key: "detail",
      label: "详情",
      artType: "view",
      perm: "module_cnc:cnc_platform:detail",
      run: () => void crud.handleOpenDialog("detail", row[PK] as number),
    },
    {
      key: "edit",
      label: "编辑",
      artType: "edit",
      icon: "ri:edit-2-line",
      perm: "module_cnc:cnc_platform:update",
      run: () => void crud.handleOpenDialog("update", row[PK] as number),
    },
    {
      key: "delete",
      label: "删除",
      artType: "delete",
      icon: "ri:delete-bin-4-line",
      perm: "module_cnc:cnc_platform:delete",
      run: () => deleteRow(row),
    },
  ];
  return all;
}

function formatOperationCell(row: CncPlatformTable) {
  return renderTableOperationCell(buildRowActions(row), {
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

const deleteRow = async (row: CncPlatformTable) => {
  if (!row[PK]) return;
  try {
    await confirmDelete(`确定删除该竞价平台吗？此操作不可恢复！`);
    await CncPlatformAPI.deleteCncPlatform([row[PK] as number]);
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
      selectedRows.value.map((row) => String(row["id"] ?? "")),
    );
    batchDeleting.value = true;
    await CncPlatformAPI.deleteCncPlatform(ids);
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
    await CncPlatformAPI.batchCncPlatform({ ids, status });
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
    const res = await CncPlatformAPI.importCncPlatform(formData);
    if (res.data.code === ResultEnum.SUCCESS) {
      ElMessage.success(res.data.msg || "导入成功");
      importVisible.value = false;
      await refreshData();
    }
    // 非 SUCCESS 分支提示由 axios 拦截器统一处理
  } catch (error: unknown) {
    if (import.meta.env.DEV) console.error("[Import]", error);
    /* 接口错误已由拦截器提示 */
  }
}

</script>

<style lang="scss" scoped></style>
