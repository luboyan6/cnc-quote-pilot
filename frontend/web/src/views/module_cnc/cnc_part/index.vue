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
            :perm-create="['module_cnc:cnc_part:create']"
            :perm-import="['module_cnc:cnc_part:import']"
            :perm-export="['module_cnc:cnc_part:export']"
            :perm-delete="['module_cnc:cnc_part:delete']"
            :perm-patch="['module_cnc:cnc_part:patch']"
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
      default-template-file-name="cnc_part_import_template.xlsx"
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
import CncPartAPI, {
  type CncPartForm,
  type CncPartPageQuery,
  type CncPartTable,
} from "@/api/module_cnc/cnc_part";

defineOptions({
  name: "CncPart",
  inheritAttrs: false,
});

// 常量定义
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const STATUS_OPTIONS = [
  { label: "启用", value: 0 },
  { label: "停用", value: 1 },
] as const;

const createInitialFormData = (): CncPartForm => ({
  extension: undefined,
  size_bytes: undefined,
  declared_unit: undefined,
  validation_status: undefined,
  upload_authorized: false,
  file_path: undefined,
  file_name: undefined,
  file_type: undefined,
});

type CncPartSearchFormParams = {
  extension?: string;
  size_bytes?: string;
  declared_unit?: string;
  validation_status?: string;
  upload_authorized?: string;
  file_path?: string;
  file_name?: string;
  file_type?: string;
} & AuditSearchFormParams;

const searchForm = ref<CncPartSearchFormParams>({
  extension: undefined,
  size_bytes: undefined,
  declared_unit: undefined,
  validation_status: undefined,
  upload_authorized: undefined,
  file_path: undefined,
  file_name: undefined,
  file_type: undefined,
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
    label: "文件扩展名",
    key: "extension",
    type: "input",
    placeholder: "请输入文件扩展名",
    clearable: true,
    span: 6,
  },
  {
    label: "文件大小",
    key: "size_bytes",
    type: "input",
    placeholder: "请输入文件大小",
    clearable: true,
    span: 6,
  },
  {
    label: "声明单位",
    key: "declared_unit",
    type: "input",
    placeholder: "请输入声明单位",
    clearable: true,
    span: 6,
  },
  {
    label: "上传授权",
    key: "upload_authorized",
    type: "input",
    placeholder: "请输入上传授权",
    clearable: true,
    span: 6,
  },
  {
    label: "文件名称",
    key: "file_name",
    type: "input",
    placeholder: "请输入文件名称",
    clearable: true,
    span: 6,
  },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } =
  useTableSelection<CncPartTable>();

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
    apiFn: CncPartAPI.listCncPart,
    apiParams: {
      page_no: 1,
      page_size: 10,
    },
    columnsFactory: resolveStatusColumns<CncPartTable>(() => [
      { type: "selection", width: 48, fixed: "left" },
      { type: "globalIndex", width: 56, label: "序号" },
      { prop: "extension", label: "文件扩展名", minWidth: 120, showOverflowTooltip: true },
      { prop: "size_bytes", label: "文件大小", minWidth: 120, showOverflowTooltip: true },
      { prop: "declared_unit", label: "声明单位", minWidth: 120, showOverflowTooltip: true },
      { prop: "validation_status", label: "校验状态", minWidth: 120, showOverflowTooltip: true },
      {
        prop: "upload_authorized",
        label: "上传授权",
        width: 80,
        status: {
          true: { type: "success", text: "是" },
          false: { type: "danger", text: "否" },
        },
      },
      { prop: "created_time", label: "创建时间", width: 168, sortable: true, showOverflowTooltip: true },
      { prop: "updated_time", label: "更新时间", width: 168, sortable: true, showOverflowTooltip: true },
      { prop: "file_path", label: "存储路径", minWidth: 120, showOverflowTooltip: true },
      { prop: "file_name", label: "文件名称", minWidth: 120, showOverflowTooltip: true },
      { prop: "file_type", label: "文件类型", minWidth: 120, showOverflowTooltip: true },
      {
        prop: "operation",
        label: "操作",
        width: 180,
        fixed: "right",
        align: "center",
        formatter: (row: CncPartTable) => formatOperationCell(row),
      },
    ]),
  },
});

const crudCols = toCrudCols(columns);

const exportQueryParams = computed(() => {
  return stripPaginationParams(searchParams as Record<string, unknown>);
});

const importContentConfig = computed<IContentConfig>(() => ({
  permPrefix: "module_cnc:cnc_part",
  cols: crudCols.value,
  indexAction: async () => ({}),
  importTemplate: () => CncPartAPI.downloadTemplateCncPart(),
}));

const exportContentConfig = computed(() => ({
  permPrefix: "module_cnc:cnc_part",
  cols: crudCols.value,
  exportsBlobAction: async (params: IObject) => {
    const merged = {
      ...(exportQueryParams.value as unknown as Record<string, unknown>),
      ...params,
    } as unknown as CncPartPageQuery;
    const res = await CncPartAPI.exportCncPart(merged);
    return res.data as Blob;
  },
}));

const { dialogVisible } = useCrudDialog();

const detailFormData = ref<CncPartTable>({});

const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "文件扩展名", prop: "extension" },
  { label: "文件大小", prop: "size_bytes" },
  { label: "声明单位", prop: "declared_unit" },
  { label: "校验状态", prop: "validation_status" },
  { label: "上传授权", prop: "upload_authorized" },
  { label: "创建时间", prop: "created_time" },
  { label: "更新时间", prop: "updated_time" },
  { label: "存储路径", prop: "file_path" },
  { label: "文件名称", prop: "file_name" },
  { label: "文件类型", prop: "file_type" },
];

const formData = ref<CncPartForm>(createInitialFormData());

const rules = reactive({
  extension: [{ required: false, message: "请填写文件扩展名", trigger: "blur" }],
  size_bytes: [{ required: false, message: "请填写文件大小", trigger: "blur" }],
  declared_unit: [{ required: false, message: "请填写声明单位", trigger: "blur" }],
  validation_status: [{ required: false, message: "请填写校验状态", trigger: "blur" }],
  upload_authorized: [{ required: false, message: "请填写上传授权", trigger: "blur" }],
  file_path: [{ required: false, message: "请填写存储路径", trigger: "blur" }],
  file_name: [{ required: false, message: "请填写文件名称", trigger: "blur" }],
  file_type: [{ required: false, message: "请填写文件类型", trigger: "blur" }],
});

const dialogFormItems: FormItem[] = [
  { key: "extension", label: "文件扩展名", type: "input", props: { placeholder: "请输入文件扩展名" } },
  { key: "size_bytes", label: "文件大小", type: "number", props: { placeholder: "请输入文件大小" } },
  { key: "declared_unit", label: "声明单位", type: "input", props: { placeholder: "请输入声明单位" } },
  { key: "validation_status", label: "校验状态", type: "select", placeholder: "请选择校验状态" },
  { key: "upload_authorized", label: "上传授权", type: "switch" },
  { key: "file_path", label: "存储路径", type: "input", props: { type: "textarea", rows: 4, placeholder: "请输入存储路径" } },
  { key: "file_name", label: "文件名称", type: "input", props: { placeholder: "请输入文件名称" } },
  { key: "file_type", label: "文件类型", type: "number", props: { placeholder: "请输入文件类型" } },
];

const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

const crud = useCrudForm<CncPartForm>({
  formData,
  initialFormData: createInitialFormData(),
  dialogVisible,
  dataFormRef,
  formRenderKey,
  detailApi: (id: number) => CncPartAPI.detailCncPart(id),
  createApi: (data: CncPartForm) => CncPartAPI.createCncPart(data),
  updateApi: (id: number, data: CncPartForm) => CncPartAPI.updateCncPart(id, data),
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

const handleSearch = async (params: CncPartSearchFormParams) => {
  await searchBarRef.value?.validate();
  replaceSearchParams({
    extension: params.extension,
    size_bytes: params.size_bytes,
    declared_unit: params.declared_unit,
    validation_status: params.validation_status,
    upload_authorized: params.upload_authorized,
    file_path: params.file_path,
    file_name: params.file_name,
    file_type: params.file_type,
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
    extension: undefined,
    size_bytes: undefined,
    declared_unit: undefined,
    validation_status: undefined,
    upload_authorized: undefined,
    file_path: undefined,
    file_name: undefined,
    file_type: undefined,
    created_id: undefined,
    updated_id: undefined,
    created_time: undefined,
    updated_time: undefined,
  };
  await resetSearchParams();
};

function buildRowActions(row: CncPartTable): TableOperationAction[] {
  const all: TableOperationAction[] = [
    {
      key: "detail",
      label: "详情",
      artType: "view",
      perm: "module_cnc:cnc_part:detail",
      run: () => void crud.handleOpenDialog("detail", row[PK] as number),
    },
    {
      key: "edit",
      label: "编辑",
      artType: "edit",
      icon: "ri:edit-2-line",
      perm: "module_cnc:cnc_part:update",
      run: () => void crud.handleOpenDialog("update", row[PK] as number),
    },
    {
      key: "delete",
      label: "删除",
      artType: "delete",
      icon: "ri:delete-bin-4-line",
      perm: "module_cnc:cnc_part:delete",
      run: () => deleteRow(row),
    },
  ];
  return all;
}

function formatOperationCell(row: CncPartTable) {
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

const deleteRow = async (row: CncPartTable) => {
  if (!row[PK]) return;
  try {
    await confirmDelete(`确定删除该图纸文件吗？此操作不可恢复！`);
    await CncPartAPI.deleteCncPart([row[PK] as number]);
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
    await CncPartAPI.deleteCncPart(ids);
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
    await CncPartAPI.batchCncPart({ ids, status });
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
    const res = await CncPartAPI.importCncPart(formData);
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
