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
      :confirm-loading="submitLoading || stepUploading"
      @cancel="handleCloseDialog"
      @close="handleCloseDialog"
      @confirm="handleSubmit()"
    >
      <template v-if="dialogVisible.type === 'detail'">
        <FaDescriptions :column="1" :data="detailFormData" :items="detailItems" max-height="70vh">
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
        >
          <!-- STEP 图纸上传与反向回显展示插槽 -->
          <template #upload_step>
            <div class="step-upload-container w-full" :aria-busy="stepUploading">
              <!-- 反向展示区：已有关联图纸（修改回显，或新增上传成功） -->
              <div
                v-if="formData.file_path || formData.file_name"
                class="step-file-card flex items-center justify-between p-3 rounded-lg border border-solid border-blue-200 dark:border-blue-900 bg-blue-50/50 dark:bg-blue-950/20"
              >
                <div class="flex items-center gap-3 min-w-0 mr-3">
                  <div
                    class="w-10 h-10 rounded-lg flex items-center justify-center bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400 flex-shrink-0"
                  >
                    <ElIcon :size="22"><Document /></ElIcon>
                  </div>
                  <div class="min-w-0">
                    <div class="flex items-center gap-2">
                      <span
                        class="font-medium text-sm text-gray-800 dark:text-gray-200 truncate max-w-[280px]"
                        :title="formData.file_name || ''"
                      >
                        {{ formData.file_name || "已关联图纸" }}
                      </span>
                      <ElTag size="small" type="info" effect="light">已关联</ElTag>
                      <ElTag v-if="formData.extension" size="small" type="info" effect="plain">
                        {{ formData.extension.toUpperCase() }}
                      </ElTag>
                    </div>
                    <div
                      class="text-xs text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-2 truncate"
                    >
                      <span v-if="formData.size_bytes">{{
                        formatFileSize(formData.size_bytes)
                      }}</span>
                      <span v-if="formData.size_bytes" class="text-gray-300 dark:text-gray-600"
                        >|</span
                      >
                      <span class="truncate max-w-[340px]" :title="formData.file_path || ''">
                        路径: {{ formData.file_path || "未知" }}
                      </span>
                    </div>
                  </div>
                </div>

                <div class="step-file-actions flex items-center gap-2 flex-shrink-0">
                  <ElButton
                    type="primary"
                    plain
                    size="small"
                    :loading="stepUploading"
                    :disabled="!canUploadStep || submitLoading"
                    @click="triggerStepUpload"
                  >
                    <ElIcon class="mr-1"><UploadFilled /></ElIcon>
                    重新上传
                  </ElButton>
                  <ElButton
                    v-if="formData.file_path"
                    type="info"
                    plain
                    size="small"
                    :disabled="!canDownloadStep"
                    @click="handlePreviewFile(formData.file_path)"
                  >
                    <ElIcon class="mr-1"><Download /></ElIcon>
                    下载
                  </ElButton>
                  <ElButton
                    type="danger"
                    text
                    size="small"
                    :disabled="stepUploading || submitLoading"
                    @click="handleClearUploadedFile"
                  >
                    <ElIcon class="mr-1"><Delete /></ElIcon>
                    移除
                  </ElButton>
                </div>
              </div>

              <!-- 未上传图纸状态 -->
              <div
                v-else
                class="step-upload-action flex items-center justify-between p-3 rounded-lg border border-dashed border-gray-300 dark:border-zinc-700 bg-gray-50/60 dark:bg-zinc-800/30 hover:border-primary transition-colors"
              >
                <div class="step-upload-prompt flex items-center gap-3">
                  <ElButton
                    type="primary"
                    :loading="stepUploading"
                    :disabled="!canUploadStep || submitLoading"
                    @click="triggerStepUpload"
                  >
                    <ElIcon class="mr-1"><UploadFilled /></ElIcon>
                    上传 STEP 图纸
                  </ElButton>
                  <div class="text-xs text-gray-400">
                    <span
                      >支持
                      <span class="text-gray-700 dark:text-gray-300 font-medium"
                        >.step / .stp / .setp</span
                      >，最大 50MB。上传后自动填充文件名称和本地存储路径。</span
                    >
                  </div>
                </div>
              </div>

              <!-- 隐藏的文件选择 input -->
              <input
                ref="stepFileInputRef"
                type="file"
                class="hidden"
                accept=".step,.stp,.setp"
                aria-label="选择 STEP 图纸"
                :disabled="!canUploadStep || stepUploading || submitLoading"
                @change="handleStepFileSelected"
              />
            </div>
          </template>
        </FaForm>
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
import { nextTick, onBeforeUnmount, ref, reactive, computed, watch } from "vue";
import { ElMessage } from "element-plus";
import { Document, UploadFilled, Download, Delete } from "@element-plus/icons-vue";
import type { AxiosResponse } from "axios";
import {
  renderTableOperationCell,
  resolveStatusColumns,
  stripPaginationParams,
  toCrudCols,
  request,
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
import download from "@/utils/download";
import { checkPerm } from "@/utils/checkPerm";
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
  id: undefined,
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
    label: "文件名称",
    key: "file_name",
    type: "input",
    placeholder: "请输入文件名称",
    clearable: true,
    span: 6,
  },
  {
    label: "存储路径",
    key: "file_path",
    type: "input",
    placeholder: "请输入存储路径",
    clearable: true,
    span: 6,
  },
  // 其余搜索项先隐藏
  // {
  //   label: "文件扩展名",
  //   key: "extension",
  //   type: "input",
  //   placeholder: "请输入文件扩展名",
  //   clearable: true,
  //   span: 6,
  // },
  // {
  //   label: "文件大小",
  //   key: "size_bytes",
  //   type: "input",
  //   placeholder: "请输入文件大小",
  //   clearable: true,
  //   span: 6,
  // },
  // {
  //   label: "声明单位",
  //   key: "declared_unit",
  //   type: "input",
  //   placeholder: "请输入声明单位",
  //   clearable: true,
  //   span: 6,
  // },
  // {
  //   label: "上传授权",
  //   key: "upload_authorized",
  //   type: "input",
  //   placeholder: "请输入上传授权",
  //   clearable: true,
  //   span: 6,
  // },
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
      { prop: "file_name", label: "文件名称", minWidth: 180, showOverflowTooltip: true },
      { prop: "file_path", label: "存储路径", minWidth: 260, showOverflowTooltip: true },
      // 其余列先隐藏
      // { prop: "extension", label: "文件扩展名", minWidth: 120, showOverflowTooltip: true },
      // { prop: "size_bytes", label: "文件大小", minWidth: 120, showOverflowTooltip: true },
      // { prop: "declared_unit", label: "声明单位", minWidth: 120, showOverflowTooltip: true },
      // { prop: "validation_status", label: "校验状态", minWidth: 120, showOverflowTooltip: true },
      // {
      //   prop: "upload_authorized",
      //   label: "上传授权",
      //   width: 80,
      //   status: {
      //     true: { type: "success", text: "是" },
      //     false: { type: "danger", text: "否" },
      //   },
      // },
      // {
      //   prop: "created_time",
      //   label: "创建时间",
      //   width: 168,
      //   sortable: true,
      //   showOverflowTooltip: true,
      // },
      // {
      //   prop: "updated_time",
      //   label: "更新时间",
      //   width: 168,
      //   sortable: true,
      //   showOverflowTooltip: true,
      // },
      // { prop: "file_type", label: "文件类型", minWidth: 120, showOverflowTooltip: true },
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
  { label: "文件名称", prop: "file_name" },
  { label: "存储路径", prop: "file_path" },
  // 其余字段先隐藏
  // { label: "文件扩展名", prop: "extension" },
  // { label: "文件大小", prop: "size_bytes" },
  // { label: "声明单位", prop: "declared_unit" },
  // { label: "校验状态", prop: "validation_status" },
  // { label: "上传授权", prop: "upload_authorized" },
  // { label: "创建时间", prop: "created_time" },
  // { label: "更新时间", prop: "updated_time" },
  // { label: "文件类型", prop: "file_type" },
];

const formData = ref<CncPartForm>(createInitialFormData());

// 校验规则：文件名称与存储路径为核心必填，其他列设置为非必填
const rules = reactive({
  file_name: [{ required: true, message: "请上传图纸或输入文件名称", trigger: "blur" }],
  file_path: [{ required: true, message: "请上传图纸或输入存储路径", trigger: "blur" }],
  extension: [{ required: false, trigger: "blur" }],
  size_bytes: [{ required: false, trigger: "blur" }],
  declared_unit: [{ required: false, trigger: "blur" }],
  validation_status: [{ required: false, trigger: "change" }],
  upload_authorized: [{ required: false, trigger: "change" }],
  file_type: [{ required: false, trigger: "blur" }],
});

const dialogFormItems: FormItem[] = [
  {
    key: "upload_step",
    label: "图纸上传",
    span: 24,
  },
  {
    key: "file_name",
    label: "文件名称",
    type: "input",
    span: 24,
    props: { placeholder: "请输入文件名称（上传图纸自动识别填充）", clearable: true },
  },
  {
    key: "file_path",
    label: "存储路径",
    type: "input",
    span: 24,
    props: {
      type: "textarea",
      rows: 2,
      placeholder: "请输入存储路径（上传图纸自动识别填充）",
      clearable: true,
    },
  },
  // 其余字段先隐藏
  // {
  //   key: "extension",
  //   label: "文件扩展名",
  //   type: "input",
  //   span: 12,
  //   props: { placeholder: "请输入文件扩展名（如 step 或 stp）", clearable: true },
  // },
  // {
  //   key: "size_bytes",
  //   label: "文件大小",
  //   type: "number",
  //   span: 12,
  //   props: { placeholder: "请输入文件大小（字节）", min: 0, style: { width: "100%" } },
  // },
  // {
  //   key: "declared_unit",
  //   label: "声明单位",
  //   type: "input",
  //   span: 12,
  //   props: { placeholder: "请输入声明单位（如 mm）", clearable: true },
  // },
  // {
  //   key: "validation_status",
  //   label: "校验状态",
  //   type: "select",
  //   span: 12,
  //   placeholder: "请选择校验状态",
  //   props: {
  //     clearable: true,
  //     options: [
  //       { label: "待校验 (PENDING)", value: "PENDING" },
  //       { label: "基础检查通过 (HEADER_VALID)", value: "HEADER_VALID" },
  //       { label: "已拒绝 (REJECTED)", value: "REJECTED" },
  //     ],
  //   },
  // },
  // {
  //   key: "upload_authorized",
  //   label: "上传授权",
  //   type: "switch",
  //   span: 12,
  // },
  // {
  //   key: "file_type",
  //   label: "文件类型",
  //   type: "number",
  //   span: 12,
  //   props: { placeholder: "请输入文件类型", min: 0, style: { width: "100%" } },
  // },
];

const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

// 图纸上传与文件管理状态
const canUploadStep = computed(() => checkPerm("module_common:file:upload"));
const canDownloadStep = computed(() => checkPerm("module_common:file:download"));
const stepUploading = ref(false);
const stepFileInputRef = ref<HTMLInputElement | null>(null);
let stepUploadController: AbortController | undefined;

function cancelStepUpload() {
  stepUploadController?.abort();
  stepUploadController = undefined;
  stepUploading.value = false;
}

// 关闭或切换表单时使旧请求失效，防止回填到另一条图纸记录。
watch(() => [dialogVisible.visible, formRenderKey.value], cancelStepUpload, { flush: "sync" });
onBeforeUnmount(cancelStepUpload);

function triggerStepUpload() {
  if (!canUploadStep.value || stepUploading.value || submitLoading.value) return;
  stepFileInputRef.value?.click();
}

function formatFileSize(bytes?: number): string {
  if (!bytes || bytes <= 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function handlePreviewFile(filePath?: string) {
  if (!filePath || !canDownloadStep.value) return;
  if (filePath.startsWith("http://") || filePath.startsWith("https://")) {
    window.open(filePath, "_blank", "noopener,noreferrer");
  } else {
    void download.name(filePath, false);
  }
}

function handleClearUploadedFile() {
  if (stepUploading.value || submitLoading.value) return;
  formData.value.file_name = undefined;
  formData.value.file_path = undefined;
  formData.value.extension = undefined;
  formData.value.size_bytes = undefined;
  formData.value.validation_status = undefined;
  // CRUD ignores null/omitted values; an empty declaration clears the saved unit.
  formData.value.declared_unit = "";
  formData.value.file_type = undefined;
  formData.value.upload_authorized = false;
  if (stepFileInputRef.value) {
    stepFileInputRef.value.value = "";
  }
}

async function handleStepFileSelected(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file || !canUploadStep.value || stepUploading.value || submitLoading.value) return;

  // 1. 扩展名校验
  const ext = (file.name.split(".").pop() || "").toLowerCase();
  if (!["step", "stp", "setp"].includes(ext)) {
    ElMessage.warning("请上传 .step、.stp 或 .setp 格式的图纸文件");
    return;
  }

  if (file.size === 0) {
    ElMessage.warning("图纸文件不能为空");
    return;
  }

  // 2. 文件大小校验（50MB）
  const maxMb = 50;
  if (file.size > maxMb * 1024 * 1024) {
    ElMessage.warning(`图纸文件大小不能超过 ${maxMb}MB`);
    return;
  }

  const controller = new AbortController();
  stepUploadController = controller;
  stepUploading.value = true;
  try {
    const uploadFormData = new FormData();
    uploadFormData.append("file", file);

    const response = await request.post<
      ApiResponse<UploadFilePath>,
      AxiosResponse<ApiResponse<UploadFilePath>>
    >("/common/file/upload", uploadFormData, {
      params: { upload_type: "file" },
      headers: { "Content-Type": "multipart/form-data" },
      signal: controller.signal,
    });

    if (controller.signal.aborted) return;
    const fileInfo = response.data.data;
    if (response.data.code !== ResultEnum.SUCCESS || !fileInfo?.file_path) {
      throw new Error(response.data.msg || "上传失败，服务端未返回文件存储路径");
    }

    // 统一存储路径格式（正斜杠）
    const safePath = fileInfo.file_path.replace(/\\/g, "/");

    // 自动识别并填充文件名称和本地上传路径等
    formData.value.file_name = fileInfo.origin_name || file.name;
    formData.value.file_path = safePath;
    formData.value.extension = ext;
    formData.value.size_bytes = file.size;
    formData.value.validation_status = "PENDING";
    // Prior declarations and third-party consent belong to the replaced file.
    // CRUD ignores null/omitted values; an empty declaration clears the saved unit.
    formData.value.declared_unit = "";
    formData.value.file_type = undefined;
    formData.value.upload_authorized = false;

    // 清除由于之前可能未填写产生的表单校验提示
    dataFormRef.value?.clearValidate?.(["file_name", "file_path"]);
  } catch (error: unknown) {
    if (controller.signal.aborted) return;
    console.error("STEP 图纸上传失败:", error);
    ElMessage.error(error instanceof Error ? error.message : "图纸上传失败，请稍后重试");
  } finally {
    if (stepUploadController === controller) {
      stepUploadController = undefined;
      stepUploading.value = false;
    }
  }
}

// 监听修改打开时的数据注入，清除初始多余校验提示
watch(
  () => formData.value.id,
  () => {
    nextTick(() => {
      dataFormRef.value?.clearValidate?.();
    });
  }
);

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
  if (stepUploading.value) {
    ElMessage.warning("请等待图纸上传完成后再提交");
    return;
  }
  if (submitLoading.value) return;
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
      selectedRows.value.map((row) => String(row["id"] ?? ""))
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
  } catch (error: unknown) {
    if (import.meta.env.DEV) console.error("[Import]", error);
  }
}
</script>

<style lang="scss" scoped>
.step-upload-container {
  margin-bottom: 8px;
}

.step-file-card,
.step-upload-prompt,
.step-file-actions {
  flex-wrap: wrap;
  gap: 12px;
}

.step-file-actions {
  margin-top: 4px;
}
</style>
