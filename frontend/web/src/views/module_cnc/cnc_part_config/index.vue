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
          <template #extra_params="{ row }">
            <FaJsonPretty v-if="row?.extra_params != null" :value="row?.extra_params" height="140px" />
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
import CncPartConfigAPI, {
  type CncPartConfigForm,
  type CncPartConfigPageQuery,
  type CncPartConfigTable,
} from "@/api/module_cnc/cnc_part_config";

defineOptions({
  name: "CncPartConfig",
  inheritAttrs: false,
});


// 常量定义
const STATUS_OPTIONS = [
  { label: "启用", value: 0 },
  { label: "停用", value: 1 },
] as const;

const createInitialFormData = (): CncPartConfigForm => ({
  name: undefined,
  site_type: undefined,
  material: undefined,
  quantity: undefined,
  surface_finish: undefined,
  extra_params: undefined,
  enabled: false,
  part_id: undefined,
});

type CncPartConfigSearchFormParams = {
  name?: string;
  site_type?: string;
  material?: string;
  quantity?: string;
  surface_finish?: string;
  extra_params?: string;
  enabled?: string;
  part_id?: string;
} & AuditSearchFormParams;

const searchForm = ref<CncPartConfigSearchFormParams>({
  name: undefined,
  site_type: undefined,
  material: undefined,
  quantity: undefined,
  surface_finish: undefined,
  extra_params: undefined,
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

/** 业务搜索项（审计四字段由 FaSearchBar 的 includeAudit 属性追加） */
const businessSearchItems = computed(() => [
  {
    label: "配置名称，例如：Xometry铝合金标准加工",
    key: "name",
    type: "input",
    placeholder: "请输入配置名称，例如：Xometry铝合金标准加工",
    clearable: true,
    span: 6,
  },
  {
    label: "加工材料；存储对应报价平台的具体材料选项",
    key: "material",
    type: "input",
    placeholder: "请输入加工材料；存储对应报价平台的具体材料选项",
    clearable: true,
    span: 6,
  },
  {
    label: "加工数量；正整数，默认1",
    key: "quantity",
    type: "input",
    placeholder: "请输入加工数量；正整数，默认1",
    clearable: true,
    span: 6,
  },
  {
    label: "表面处理方式；存储对应报价平台的具体表面处理选项",
    key: "surface_finish",
    type: "input",
    placeholder: "请输入表面处理方式；存储对应报价平台的具体表面处理选项",
    clearable: true,
    span: 6,
  },
  {
    label: "平台差异化参数；JSON格式，例如颜色、公差、表面粗糙度等",
    key: "extra_params",
    type: "input",
    placeholder: "请输入平台差异化参数；JSON格式，例如颜色、公差、表面粗糙度等",
    clearable: true,
    span: 6,
  },
  {
    label: "是否启用；true=启用，false=禁用",
    key: "enabled",
    type: "input",
    placeholder: "请输入是否启用；true=启用，false=禁用",
    clearable: true,
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
      { prop: "name", label: "配置名称，例如：Xometry铝合金标准加工", minWidth: 120, showOverflowTooltip: true },
      { prop: "site_type", label: "报价平台类型；1=Xometry，2=嘉立创", minWidth: 120, showOverflowTooltip: true },
      { prop: "material", label: "加工材料；存储对应报价平台的具体材料选项", minWidth: 120, showOverflowTooltip: true },
      { prop: "quantity", label: "加工数量；正整数，默认1", minWidth: 120, showOverflowTooltip: true },
      { prop: "surface_finish", label: "表面处理方式；存储对应报价平台的具体表面处理选项", minWidth: 120, showOverflowTooltip: true },
      {
        prop: "enabled",
        label: "是否启用；true=启用，false=禁用",
        width: 80,
        status: {
          true: { type: "success", text: "是" },
          false: { type: "danger", text: "否" },
        },
      },
      { prop: "part_id", label: "关联图纸ID", minWidth: 120, showOverflowTooltip: true },
      { prop: "created_time", label: "创建时间", width: 168, sortable: true, showOverflowTooltip: true },
      { prop: "updated_time", label: "更新时间", width: 168, sortable: true, showOverflowTooltip: true },
      {
        prop: "operation",
        label: "操作",
        width: 180,
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

const detailFormData = ref<CncPartConfigTable>({});

const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "配置名称，例如：Xometry铝合金标准加工", prop: "name" },
  { label: "报价平台类型；1=Xometry，2=嘉立创", prop: "site_type" },
  { label: "加工材料；存储对应报价平台的具体材料选项", prop: "material" },
  { label: "加工数量；正整数，默认1", prop: "quantity" },
  { label: "表面处理方式；存储对应报价平台的具体表面处理选项", prop: "surface_finish" },
  { label: "平台差异化参数；JSON格式，例如颜色、公差、表面粗糙度等", prop: "extra_params", slot: "extra_params" },
  { label: "是否启用；true=启用，false=禁用", prop: "enabled" },
  { label: "关联图纸ID", prop: "part_id" },
  { label: "创建时间", prop: "created_time" },
  { label: "更新时间", prop: "updated_time" },
];

const formData = ref<CncPartConfigForm>(createInitialFormData());

const rules = reactive({
  name: [{ required: false, message: "请填写配置名称，例如：Xometry铝合金标准加工", trigger: "blur" }],
  site_type: [{ required: false, message: "请填写报价平台类型；1=Xometry，2=嘉立创", trigger: "blur" }],
  material: [{ required: false, message: "请填写加工材料；存储对应报价平台的具体材料选项", trigger: "blur" }],
  quantity: [{ required: false, message: "请填写加工数量；正整数，默认1", trigger: "blur" }],
  surface_finish: [{ required: false, message: "请填写表面处理方式；存储对应报价平台的具体表面处理选项", trigger: "blur" }],
  enabled: [{ required: false, message: "请填写是否启用；true=启用，false=禁用", trigger: "blur" }],
  part_id: [{ required: false, message: "请填写关联图纸ID", trigger: "blur" }],
});

const dialogFormItems: FormItem[] = [
  { key: "name", label: "配置名称，例如：Xometry铝合金标准加工", type: "input", props: { placeholder: "请输入配置名称，例如：Xometry铝合金标准加工" } },
  { key: "site_type", label: "报价平台类型；1=Xometry，2=嘉立创", type: "number", props: { placeholder: "请输入报价平台类型；1=Xometry，2=嘉立创" } },
  { key: "material", label: "加工材料；存储对应报价平台的具体材料选项", type: "input", props: { placeholder: "请输入加工材料；存储对应报价平台的具体材料选项" } },
  { key: "quantity", label: "加工数量；正整数，默认1", type: "number", props: { placeholder: "请输入加工数量；正整数，默认1" } },
  { key: "surface_finish", label: "表面处理方式；存储对应报价平台的具体表面处理选项", type: "input", props: { placeholder: "请输入表面处理方式；存储对应报价平台的具体表面处理选项" } },
  { key: "enabled", label: "是否启用；true=启用，false=禁用", type: "switch" },
  { key: "part_id", label: "关联图纸ID", type: "number", props: { placeholder: "请输入关联图纸ID" } },
];

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
  updateApi: (id: number, data: CncPartConfigForm) => CncPartConfigAPI.updateCncPartConfig(id, data),
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

const handleSearch = async (params: CncPartConfigSearchFormParams) => {
  await searchBarRef.value?.validate();
  replaceSearchParams({
    name: params.name,
    site_type: params.site_type,
    material: params.material,
    quantity: params.quantity,
    surface_finish: params.surface_finish,
    extra_params: params.extra_params,
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
    extra_params: undefined,
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
  const all: TableOperationAction[] = [
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
    },
  ];
  return all;
}

function formatOperationCell(row: CncPartConfigTable) {
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

const deleteRow = async (row: CncPartConfigTable) => {
  if (!row[PK]) return;
  try {
    await confirmDelete(`确定删除该图纸参数配置表吗？此操作不可恢复！`);
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
      selectedRows.value.map((row) => String(row["id"] ?? "")),
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
    // 非 SUCCESS 分支提示由 axios 拦截器统一处理
  } catch (error: unknown) {
    if (import.meta.env.DEV) console.error("[Import]", error);
    /* 接口错误已由拦截器提示 */
  }
}

</script>

<style lang="scss" scoped></style>
