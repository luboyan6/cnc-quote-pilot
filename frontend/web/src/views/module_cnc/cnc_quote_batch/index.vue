<template>
  <div class="fa-full-height batch-container">
    <!-- 顶部操作栏 -->
    <ElCard shadow="never" class="table-card">
      <div class="table-toolbar flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <span class="font-semibold text-base text-gray-800">CNC 批量报价任务</span>
          <ElTag size="small" type="info">共 {{ total }} 个批次</ElTag>
        </div>
        <div class="flex items-center gap-2">
          <ElButton :icon="Refresh" plain @click="fetchBatches">
            刷新
          </ElButton>
        </div>
      </div>

      <!-- 批次列表表格 -->
      <ElTable
        v-loading="loading"
        :data="batches"
        border
        stripe
        style="width: 100%"
      >
        <ElTableColumn prop="id" label="批次 ID" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="font-mono text-xs">{{ row.id }}</span>
          </template>
        </ElTableColumn>

        <ElTableColumn prop="source" label="来源" width="100" align="center">
          <template #default="{ row }">
            <ElTag size="small" :type="row.source === 'manual' ? 'primary' : 'warning'">
              {{ row.source === 'manual' ? '手动发起' : row.source }}
            </ElTag>
          </template>
        </ElTableColumn>

        <ElTableColumn prop="status" label="状态" width="130" align="center">
          <template #default="{ row }">
            <ElTag size="small" :type="getStatusTagType(row.status)">
              {{ formatStatus(row.status) }}
            </ElTag>
          </template>
        </ElTableColumn>

        <ElTableColumn label="进度 / 状态明细" min-width="260">
          <template #default="{ row }">
            <div class="flex items-center gap-1 flex-wrap">
              <span class="text-xs text-gray-500 mr-1">共 {{ row.item_count }} 项:</span>
              <ElTag
                v-if="row.counts?.COMPLETED"
                size="small"
                type="success"
              >
                完成 {{ row.counts.COMPLETED }}
              </ElTag>
              <ElTag
                v-if="row.counts?.RUNNING"
                size="small"
                type="primary"
              >
                运行中 {{ row.counts.RUNNING }}
              </ElTag>
              <ElTag
                v-if="row.counts?.WAITING_HUMAN"
                size="small"
                type="warning"
              >
                人工处理 {{ row.counts.WAITING_HUMAN }}
              </ElTag>
              <ElTag
                v-if="row.counts?.PENDING"
                size="small"
                type="info"
              >
                排队 {{ row.counts.PENDING }}
              </ElTag>
              <ElTag
                v-if="row.counts?.FAILED"
                size="small"
                type="danger"
              >
                失败 {{ row.counts.FAILED }}
              </ElTag>
              <ElTag
                v-if="row.counts?.CANCELLED"
                size="small"
                type="info"
              >
                已取消 {{ row.counts.CANCELLED }}
              </ElTag>
            </div>
          </template>
        </ElTableColumn>

        <ElTableColumn prop="created_at" label="创建时间" width="180" align="center">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </ElTableColumn>

        <ElTableColumn label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="flex items-center justify-center gap-2">
              <ElButton
                link
                type="primary"
                size="small"
                :icon="View"
                @click="openDetail(row)"
              >
                查看明细
              </ElButton>
              <ElPopconfirm
                v-if="canCancel(row.status) && checkPerm('module_cnc:cnc_quote_batch:cancel')"
                title="确定取消该批次剩余未执行项？"
                @confirm="handleCancelBatch(row.id)"
              >
                <template #reference>
                  <ElButton
                    link
                    type="danger"
                    size="small"
                    :icon="Close"
                  >
                    取消
                  </ElButton>
                </template>
              </ElPopconfirm>
            </div>
          </template>
        </ElTableColumn>
      </ElTable>

      <!-- 分页栏 -->
      <div class="flex justify-end mt-4">
        <ElPagination
          v-model:current-page="pageNo"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="fetchBatches"
          @current-change="fetchBatches"
        />
      </div>
    </ElCard>

    <!-- 批次子项明细抽屉 -->
    <ElDrawer
      v-model="drawerVisible"
      :title="`批次明细 · ${currentBatch?.id || ''}`"
      size="70%"
      destroy-on-close
      @close="closeDrawer"
    >
      <div v-if="currentBatch" class="drawer-content flex flex-col gap-4">
        <!-- 概览卡片 -->
        <ElDescriptions :column="3" border size="small">
          <ElDescriptionsItem label="批次状态">
            <ElTag size="small" :type="getStatusTagType(currentBatch.status)">
              {{ formatStatus(currentBatch.status) }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="请求ID">
            <span class="font-mono text-xs">{{ currentBatch.request_id }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="创建时间">
            {{ formatTime(currentBatch.created_at) }}
          </ElDescriptionsItem>
        </ElDescriptions>

        <div class="flex items-center justify-between mt-2">
          <span class="font-medium text-gray-700">子项任务列表 ({{ batchItems.length }}项)</span>
          <div class="flex items-center gap-2">
            <ElButton size="small" :icon="Refresh" :loading="itemsLoading" @click="fetchBatchItems">
              刷新子项
            </ElButton>
            <ElPopconfirm
              v-if="canCancel(currentBatch.status) && checkPerm('module_cnc:cnc_quote_batch:cancel')"
              title="确定取消本批次所有未终结任务？"
              @confirm="handleCancelBatch(currentBatch.id)"
            >
              <template #reference>
                <ElButton size="small" type="danger" plain :icon="Close">
                  取消整个批次
                </ElButton>
              </template>
            </ElPopconfirm>
          </div>
        </div>

        <!-- 子项表格 -->
        <ElTable
          v-loading="itemsLoading"
          :data="batchItems"
          border
          size="small"
          style="width: 100%"
        >
          <ElTableColumn prop="file_name" label="图纸文件" min-width="150" show-overflow-tooltip />
          <ElTableColumn prop="config_id" label="配置ID" width="80" align="center" />
          <ElTableColumn label="数量" width="70" align="center">
            <template #default="{ row }">
              {{ row.requested?.quantity || "-" }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="材质 / 表面处理" min-width="130" show-overflow-tooltip>
            <template #default="{ row }">
              {{ [row.requested?.material, row.requested?.surface_finish].filter(Boolean).join(" / ") || "-" }}
            </template>
          </ElTableColumn>
          <ElTableColumn prop="exec_status" label="执行状态" width="110" align="center">
            <template #default="{ row }">
              <ElTag size="small" :type="getStatusTagType(row.exec_status)">
                {{ formatStatus(row.exec_status) }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="quote_kind" label="报价性质" width="110" align="center">
            <template #default="{ row }">
              <ElTag v-if="row.quote_kind === 'QUOTED'" size="small" type="success">正式报价</ElTag>
              <ElTag v-else-if="row.quote_kind === 'REFERENCE_ESTIMATE'" size="small" type="primary">参考估价</ElTag>
              <ElTag v-else-if="row.quote_kind === 'PENDING_REVIEW'" size="small" type="warning">待人工审核</ElTag>
              <span v-else class="text-gray-400">-</span>
            </template>
          </ElTableColumn>
          <ElTableColumn label="重试次数" width="85" align="center">
            <template #default="{ row }">
              {{ row.attempt_count }} / {{ row.max_attempts }}
            </template>
          </ElTableColumn>
          <ElTableColumn prop="error_code" label="错误码" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.error_code" class="text-red-500 font-mono text-xs">{{ row.error_code }}</span>
              <span v-else class="text-gray-400">-</span>
            </template>
          </ElTableColumn>
          <ElTableColumn label="操作" width="130" fixed="right" align="center">
            <template #default="{ row }">
              <div class="flex items-center justify-center gap-1">
                <ElButton
                  link
                  type="primary"
                  size="small"
                  @click="openAttempts(row.id)"
                >
                  历史
                </ElButton>
                <ElButton
                  v-if="row.exec_status === 'FAILED' && checkPerm('module_cnc:cnc_quote_batch:retry')"
                  link
                  type="warning"
                  size="small"
                  @click="handleRetryItem(row.id)"
                >
                  重试
                </ElButton>
              </div>
            </template>
          </ElTableColumn>
        </ElTable>
      </div>
    </ElDrawer>

    <!-- 运行历史 Dialog -->
    <ElDialog
      v-model="attemptsVisible"
      title="子项重试与执行历史"
      width="650px"
      destroy-on-close
    >
      <div v-loading="attemptsLoading" class="attempts-container">
        <div v-if="attemptsList.length === 0" class="text-center py-6 text-gray-400">
          暂无执行历史记录
        </div>
        <div v-else class="flex flex-col gap-3">
          <div
            v-for="att in attemptsList"
            :key="att.attempt_no"
            class="p-3 border rounded bg-gray-50 flex flex-col gap-1 text-sm"
          >
            <div class="flex items-center justify-between">
              <span class="font-semibold">尝试 #{{ att.attempt_no }}</span>
              <ElTag size="small">{{ att.run?.status || "未知" }}</ElTag>
            </div>
            <div v-if="att.run?.reason" class="text-xs text-red-500 mt-1">
              原因: {{ att.run.reason }}
            </div>
            <div v-if="att.run?.result" class="text-xs text-emerald-600 mt-1">
              报价: {{ (att.run as any)?.result?.amount }} {{ (att.run as any)?.result?.currency }}
            </div>
          </div>
        </div>
      </div>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { Close, Refresh, View } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { checkPerm } from "@/utils/checkPerm";
import CncQuoteBatchAPI, {
  type BatchAttempt,
  type BatchDetail,
  type BatchItem,
} from "@/api/module_cnc/cnc_quote_batch";

defineOptions({
  name: "CncQuoteBatch",
});

const loading = ref(false);
const batches = ref<BatchDetail[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(10);

let abortController: AbortController | null = null;
let pollTimer: ReturnType<typeof setInterval> | null = null;

async function fetchBatches() {
  loading.value = true;
  try {
    const offset = (pageNo.value - 1) * pageSize.value;
    const res = await CncQuoteBatchAPI.list({ offset, limit: pageSize.value });
    if (res.data?.data) {
      batches.value = res.data.data.items || [];
      total.value = res.data.data.total || 0;
    }
  } catch (err) {
    console.error("加载批次列表失败:", err);
  } finally {
    loading.value = false;
  }
}

// ────────── 抽屉与子项 ──────────
const drawerVisible = ref(false);
const currentBatch = ref<BatchDetail | null>(null);
const batchItems = ref<BatchItem[]>([]);
const itemsLoading = ref(false);

async function openDetail(batch: BatchDetail | any) {
  currentBatch.value = batch as BatchDetail;
  drawerVisible.value = true;
  await fetchBatchItems();
  startPolling();
}

function closeDrawer() {
  drawerVisible.value = false;
  currentBatch.value = null;
  batchItems.value = [];
  stopPolling();
}

async function fetchBatchItems() {
  if (!currentBatch.value) return;
  itemsLoading.value = true;
  if (abortController) {
    abortController.abort();
  }
  abortController = new AbortController();

  try {
    const [detailRes, itemsRes] = await Promise.all([
      CncQuoteBatchAPI.detail(currentBatch.value.id, abortController.signal),
      CncQuoteBatchAPI.items(currentBatch.value.id, { offset: 0, limit: 100 }, abortController.signal),
    ]);
    if (detailRes.data?.data) {
      currentBatch.value = detailRes.data.data;
    }
    if (itemsRes.data?.data) {
      batchItems.value = itemsRes.data.data;
    }
  } catch (err: any) {
    if (err?.name !== "CanceledError" && err?.code !== "ERR_CANCELED") {
      console.error("加载批次子项失败:", err);
    }
  } finally {
    itemsLoading.value = false;
  }
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(() => {
    if (drawerVisible.value && currentBatch.value && !isTerminal(currentBatch.value.status)) {
      void fetchBatchItems();
    }
  }, 4000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
}

async function handleCancelBatch(id: string) {
  try {
    await CncQuoteBatchAPI.cancel(id);
    ElMessage.success("取消批次指令已提交");
    void fetchBatches();
    if (currentBatch.value?.id === id) {
      void fetchBatchItems();
    }
  } catch (err) {
    ElMessage.error("取消批次失败");
  }
}

async function handleRetryItem(itemId: string) {
  try {
    await CncQuoteBatchAPI.retryItem(itemId);
    ElMessage.success("已安排重新执行");
    void fetchBatchItems();
  } catch (err) {
    ElMessage.error("发起重试失败");
  }
}

// ────────── 历史尝试 ──────────
const attemptsVisible = ref(false);
const attemptsLoading = ref(false);
const attemptsList = ref<BatchAttempt[]>([]);

async function openAttempts(itemId: string) {
  attemptsVisible.value = true;
  attemptsLoading.value = true;
  try {
    const res = await CncQuoteBatchAPI.attempts(itemId);
    attemptsList.value = res.data?.data || [];
  } catch (err) {
    console.error("加载执行历史失败:", err);
  } finally {
    attemptsLoading.value = false;
  }
}

// ────────── 辅助格式化 ──────────
function isTerminal(status: string) {
  return ["COMPLETED", "FAILED", "PARTIAL_FAILED", "CANCELLED"].includes(status);
}

function canCancel(status: string) {
  return !isTerminal(status);
}

function formatStatus(status: string) {
  const map: Record<string, string> = {
    PENDING: "排队中",
    RUNNING: "运行中",
    RECONCILING: "核对中",
    WAITING_HUMAN: "待人工介入",
    COMPLETED: "已完成",
    FAILED: "全部失败",
    PARTIAL_FAILED: "部分失败",
    CANCELLED: "已取消",
    CANCELLING: "取消中",
    RETRY_WAIT: "等待重试",
  };
  return map[status] || status;
}

function getStatusTagType(status: string) {
  switch (status) {
    case "COMPLETED":
      return "success";
    case "RUNNING":
    case "RECONCILING":
      return "primary";
    case "WAITING_HUMAN":
    case "RETRY_WAIT":
      return "warning";
    case "FAILED":
    case "PARTIAL_FAILED":
      return "danger";
    case "CANCELLED":
    case "CANCELLING":
    case "PENDING":
    default:
      return "info";
  }
}

function formatTime(isoStr?: string | null) {
  if (!isoStr) return "-";
  return isoStr.slice(0, 19).replace("T", " ");
}

onMounted(() => {
  void fetchBatches();
});

onBeforeUnmount(() => {
  stopPolling();
});
</script>

<style scoped>
.batch-container {
  padding: 12px;
  overflow-y: auto;
}
.table-card {
  min-height: calc(100vh - 120px);
}
</style>
