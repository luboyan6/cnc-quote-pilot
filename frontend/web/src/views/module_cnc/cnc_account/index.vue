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
            :perm-create="['module_cnc:cnc_account:create']"
            :perm-import="['module_cnc:cnc_account:import']"
            :perm-export="['module_cnc:cnc_account:export']"
            :perm-delete="['module_cnc:cnc_account:delete']"
            :perm-patch="['module_cnc:cnc_account:patch']"
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
      width="680px"
      dialog-class="crud-embed-dialog"
      modal-class="crud-embed-dialog"
      :form-mode="dialogVisible.type"
      :confirm-loading="submitLoading"
      @cancel="handleCloseDialog"
      @close="handleCloseDialog"
      @confirm="handleSubmit()"
    >
      <template v-if="dialogVisible.type === 'detail'">
        <FaDescriptions :column="2" :data="detailFormData" :items="detailItems" max-height="70vh" />
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
          :span="24"
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
      default-template-file-name="cnc_account_import_template.xlsx"
      @upload="handleCrudImportUpload"
    />

    <FaExportDialog
      v-model="exportVisible"
      :content-config="exportContentConfig"
      :query-params="exportQueryParams"
      :page-data="data"
      :selection-data="selectedRows"
    />

    <AccountLoginDialog
      :visible="login.visible.value"
      :session="login.session.value"
      :platform-name="login.selectedPlatform.value"
      :frame-url="login.frameUrl.value"
      :error="login.error.value"
      :busy="login.busy.value"
      :interactive="login.interactive.value"
      @close="login.close"
      @input="login.command"
      @verify="login.command()"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from "vue";
import { ElButton } from "element-plus";
import { checkPerm } from "@/utils/checkPerm";
import AccountLoginDialog from "./AccountLoginDialog.vue";
import { useAccountLogin } from "./useAccountLogin";
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
import CncAccountAPI, {
  type CncAccountForm,
  type CncAccountPageQuery,
  type CncAccountTable,
} from "@/api/module_cnc/cnc_account";
import CncPlatformAPI, { type CncPlatformTable } from "@/api/module_cnc/cnc_platform";

defineOptions({
  name: "CncAccount",
  inheritAttrs: false,
});

const login = useAccountLogin();

/** 平台下拉数据源 */
const platformOptions = ref<{ label: string; value: number }[]>([]);
const platformOptionsLoading = ref(false);

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

onMounted(() => {
  fetchPlatformOptions();
});

const createInitialFormData = (): CncAccountForm => ({
  platform_id: undefined,
  username: undefined,
  password: undefined,
  enabled: true, // 默认启用账号
});

type CncAccountSearchFormParams = {
  platform_id?: number | string;
  username?: string;
  enabled?: boolean | string;
} & AuditSearchFormParams;

const searchForm = ref<CncAccountSearchFormParams>({
  platform_id: undefined,
  username: undefined,
  enabled: undefined,
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
    label: "平台名称",
    key: "platform_id",
    type: "select",
    options: platformOptions.value,
    placeholder: "请选择平台名称",
    clearable: true,
    span: 6,
  },
  {
    label: "账号",
    key: "username",
    type: "input",
    placeholder: "请输入账号",
    clearable: true,
    span: 6,
  },
  {
    label: "启用状态",
    key: "enabled",
    type: "select",
    options: [
      { label: "启用", value: true },
      { label: "停用", value: false },
    ],
    placeholder: "请选择状态",
    clearable: true,
    span: 6,
  },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } =
  useTableSelection<CncAccountTable>();

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
    apiFn: CncAccountAPI.listCncAccount,
    apiParams: {
      page_no: 1,
      page_size: 10,
    },
    columnsFactory: resolveStatusColumns<CncAccountTable>(() => [
      { type: "selection", width: 48, fixed: "left" },
      { type: "globalIndex", width: 56, label: "序号" },
      {
        prop: "platform_name",
        label: "平台名称",
        minWidth: 140,
        showOverflowTooltip: true,
        formatter: (row: CncAccountTable) =>
          row.platform_name || (row.platform_id ? `平台#${row.platform_id}` : "-"),
      },
      { prop: "username", label: "账号", minWidth: 120, showOverflowTooltip: true },
      {
        prop: "enabled",
        label: "启用状态",
        width: 90,
        status: {
          true: { type: "success", text: "是" },
          false: { type: "danger", text: "否" },
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
        width: 220,
        fixed: "right",
        align: "center",
        formatter: (row: CncAccountTable) => formatOperationCell(row),
      },
    ]),
  },
});

const crudCols = toCrudCols(columns);

const exportQueryParams = computed(() => {
  return stripPaginationParams(searchParams as Record<string, unknown>);
});

const importContentConfig = computed<IContentConfig>(() => ({
  permPrefix: "module_cnc:cnc_account",
  cols: crudCols.value,
  indexAction: async () => ({}),
  importTemplate: () => CncAccountAPI.downloadTemplateCncAccount(),
}));

const exportContentConfig = computed(() => ({
  permPrefix: "module_cnc:cnc_account",
  cols: crudCols.value,
  exportsBlobAction: async (params: IObject) => {
    const merged = {
      ...(exportQueryParams.value as unknown as Record<string, unknown>),
      ...params,
    } as unknown as CncAccountPageQuery;
    const res = await CncAccountAPI.exportCncAccount(merged);
    return res.data as Blob;
  },
}));

const { dialogVisible } = useCrudDialog();

watch(
  () => dialogVisible.visible,
  (visible) => {
    if (visible && dialogVisible.type !== "detail") {
      void fetchPlatformOptions();
    }
  }
);

const detailFormData = ref<CncAccountTable>({});

const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "平台名称", prop: "platform_name" },
  { label: "账号", prop: "username" },
  { label: "启用状态", prop: "enabled" },
  { label: "创建时间", prop: "created_time" },
  { label: "更新时间", prop: "updated_time" },
];

const formData = ref<CncAccountForm>(createInitialFormData());

const rules = computed(() => ({
  platform_id: [{ required: true, message: "请选择平台名称", trigger: "change" }],
  username: [{ required: true, message: "请填写账号", trigger: "blur" }],
  password: [{ required: dialogVisible.type === "create", message: "请填写密码", trigger: "blur" }],
  enabled: [{ required: true, message: "请选择启用状态", trigger: "change" }],
}));

const dialogFormItems = computed<FormItem[]>(() => [
  {
    key: "platform_id",
    label: "平台名称",
    type: "select",
    props: {
      options: platformOptions.value,
      loading: platformOptionsLoading.value,
      placeholder: "请选择平台名称",
      filterable: true,
      clearable: true,
      style: { width: "100%" },
    },
  },
  {
    key: "username",
    label: "账号",
    type: "input",
    props: { placeholder: "请输入账号" },
  },
  {
    key: "password",
    label: "密码",
    type: "input",
    props: {
      type: "password",
      showPassword: true,
      placeholder: dialogVisible.type === "update" ? "留空保留原密码" : "请输入密码",
    },
  },
  {
    key: "enabled",
    label: "启用状态",
    type: "switch",
  },
]);

const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

const crud = useCrudForm<CncAccountForm>({
  formData,
  initialFormData: createInitialFormData(),
  dialogVisible,
  dataFormRef,
  formRenderKey,
  detailApi: (id: number) => CncAccountAPI.detailCncAccount(id),
  createApi: (data: CncAccountForm) => CncAccountAPI.createCncAccount(data),
  updateApi: (id: number, data: CncAccountForm) => CncAccountAPI.updateCncAccount(id, data),
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

const handleSearch = async (params: CncAccountSearchFormParams) => {
  await searchBarRef.value?.validate();
  replaceSearchParams({
    platform_id: params.platform_id,
    username: params.username,
    enabled: params.enabled,
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
    platform_id: undefined,
    username: undefined,
    enabled: undefined,
    created_id: undefined,
    updated_id: undefined,
    created_time: undefined,
    updated_time: undefined,
  };
  await resetSearchParams();
};

function buildRowActions(row: CncAccountTable): TableOperationAction[] {
  const all: TableOperationAction[] = [
    {
      key: "detail",
      label: "详情",
      artType: "view",
      perm: "module_cnc:cnc_account:detail",
      run: () => void crud.handleOpenDialog("detail", row[PK] as number),
    },
    {
      key: "edit",
      label: "编辑",
      artType: "edit",
      icon: "ri:edit-2-line",
      perm: "module_cnc:cnc_account:update",
      run: () => void crud.handleOpenDialog("update", row[PK] as number),
    },
    {
      key: "delete",
      label: "删除",
      artType: "delete",
      icon: "ri:delete-bin-4-line",
      perm: "module_cnc:cnc_account:delete",
      run: () => deleteRow(row),
    },
  ];
  return all;
}

function formatOperationCell(row: CncAccountTable) {
  const canLogin = checkPerm("module_cnc:cnc_account:update");
  return h("div", { class: "inline-flex flex-wrap items-center justify-end gap-1" }, [
    canLogin
      ? h(
          ElButton,
          {
            link: true,
            type: "primary",
            size: "small",
            loading: row.id != null && login.loadingIds.value.has(row.id),
            disabled: row.enabled !== true,
            onClick: (event: MouseEvent) => {
              event.stopPropagation();
              handleAutoLogin(row);
            },
          },
          () => "登录"
        )
      : null,
    renderTableOperationCell(buildRowActions(row), { maxInline: 3 }),
  ]);
}

const handleAutoLogin = (row: CncAccountTable) => {
  if (!checkPerm("module_cnc:cnc_account:update")) return;
  void login.open(row);
};

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

const deleteRow = async (row: CncAccountTable) => {
  if (!row[PK]) return;
  try {
    await confirmDelete(`确定删除该网站账号吗？此操作不可恢复！`);
    await CncAccountAPI.deleteCncAccount([row[PK] as number]);
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
    await CncAccountAPI.deleteCncAccount(ids);
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
    await CncAccountAPI.batchCncAccount({ ids, status });
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
    const res = await CncAccountAPI.importCncAccount(formData);
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
