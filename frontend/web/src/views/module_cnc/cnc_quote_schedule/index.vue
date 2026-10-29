<template>
  <div class="fa-full-height schedule-container">
    <ElCard shadow="never" class="table-card">
      <div class="table-toolbar flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <span class="font-semibold text-base text-gray-800">CNC 定时监测计划</span>
          <ElTag size="small" type="info">共 {{ total }} 个计划</ElTag>
        </div>
        <div class="flex items-center gap-2">
          <ElButton :icon="Refresh" plain @click="fetchSchedules">
            刷新
          </ElButton>
        </div>
      </div>

      <!-- 计划列表 -->
      <ElTable
        v-loading="loading"
        :data="schedules"
        border
        stripe
        style="width: 100%"
      >
        <ElTableColumn prop="name" label="计划名称" min-width="160" show-overflow-tooltip />

        <ElTableColumn prop="interval_minutes" label="执行周期" width="120" align="center">
          <template #default="{ row }">
            <span>每 {{ row.interval_minutes }} 分钟</span>
          </template>
        </ElTableColumn>

        <ElTableColumn prop="timezone" label="时区" width="120" align="center" />

        <ElTableColumn prop="status" label="状态" width="130" align="center">
          <template #default="{ row }">
            <ElTag size="small" :type="row.status === 'ENABLED' ? 'success' : 'warning'">
              {{ row.status === 'ENABLED' ? '正常监测中' : '已暂停' }}
            </ElTag>
          </template>
        </ElTableColumn>

        <ElTableColumn prop="next_run_at" label="下次执行时间" width="170" align="center">
          <template #default="{ row }">
            {{ formatTime(row.next_run_at) }}
          </template>
        </ElTableColumn>

        <ElTableColumn prop="last_round_at" label="上次轮次时间" width="170" align="center">
          <template #default="{ row }">
            {{ formatTime(row.last_round_at) }}
          </template>
        </ElTableColumn>

        <ElTableColumn prop="pause_reason" label="暂停原因" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.pause_reason" class="text-xs text-amber-600">{{ row.pause_reason }}</span>
            <span v-else class="text-gray-400">-</span>
          </template>
        </ElTableColumn>

        <ElTableColumn label="操作" width="220" fixed="right" align="center">
          <template #default="{ row }">
            <div class="flex items-center justify-center gap-2">
              <ElButton
                link
                type="primary"
                size="small"
                :icon="View"
                @click="openRounds(row)"
              >
                轮次历史
              </ElButton>
              <ElButton
                v-if="row.status === 'ENABLED' && checkPerm('module_cnc:cnc_quote_schedule:update')"
                link
                type="warning"
                size="small"
                :icon="VideoPause"
                @click="handlePause(row.id)"
              >
                暂停
              </ElButton>
              <ElButton
                v-else-if="checkPerm('module_cnc:cnc_quote_schedule:update')"
                link
                type="success"
                size="small"
                :icon="VideoPlay"
                @click="handleResume(row.id)"
              >
                恢复
              </ElButton>
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
          @size-change="fetchSchedules"
          @current-change="fetchSchedules"
        />
      </div>
    </ElCard>

    <!-- 轮次明细抽屉 -->
    <ElDrawer
      v-model="roundsVisible"
      :title="`监测轮次明细 · ${currentSchedule?.name || ''}`"
      size="65%"
      destroy-on-close
    >
      <div v-if="currentSchedule" class="drawer-content flex flex-col gap-4">
        <ElDescriptions :column="3" border size="small">
          <ElDescriptionsItem label="计划状态">
            <ElTag size="small" :type="currentSchedule.status === 'ENABLED' ? 'success' : 'warning'">
              {{ currentSchedule.status === 'ENABLED' ? '正常监测中' : '已暂停' }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="周期">
            每 {{ currentSchedule.interval_minutes }} 分钟
          </ElDescriptionsItem>
          <ElDescriptionsItem label="时区">
            {{ currentSchedule.timezone }}
          </ElDescriptionsItem>
        </ElDescriptions>

        <div class="flex items-center justify-between mt-2">
          <span class="font-medium text-gray-700">轮次执行记录 ({{ roundsList.length }}轮)</span>
          <ElButton size="small" :icon="Refresh" :loading="roundsLoading" @click="fetchRounds">
            刷新轮次
          </ElButton>
        </div>

        <ElTable
          v-loading="roundsLoading"
          :data="roundsList"
          border
          size="small"
          style="width: 100%"
        >
          <ElTableColumn prop="round_no" label="轮次号" width="80" align="center">
            <template #default="{ row }">
              <span class="font-semibold">#{{ row.round_no }}</span>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="scheduled_for" label="计划执行时间" width="170" align="center">
            <template #default="{ row }">
              {{ formatTime(row.scheduled_for) }}
            </template>
          </ElTableColumn>
          <ElTableColumn prop="status" label="轮次状态" width="110" align="center">
            <template #default="{ row }">
              <ElTag size="small" :type="getRoundStatusType(row.status)">
                {{ formatRoundStatus(row.status) }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="batch_id" label="关联批次ID" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.batch_id" class="font-mono text-xs text-primary">{{ row.batch_id }}</span>
              <span v-else class="text-gray-400">-</span>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="skip_reason" label="跳过/异常原因" min-width="130" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.skip_reason" class="text-xs text-red-500">{{ row.skip_reason }}</span>
              <span v-else class="text-gray-400">-</span>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="finished_at" label="结束时间" width="170" align="center">
            <template #default="{ row }">
              {{ formatTime(row.finished_at) }}
            </template>
          </ElTableColumn>
        </ElTable>
      </div>
    </ElDrawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Refresh, VideoPause, VideoPlay, View } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { checkPerm } from "@/utils/checkPerm";
import CncQuoteScheduleAPI, {
  type ScheduleDetail,
  type ScheduleRound,
} from "@/api/module_cnc/cnc_quote_schedule";

defineOptions({
  name: "CncQuoteSchedule",
});

const loading = ref(false);
const schedules = ref<ScheduleDetail[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(10);

async function fetchSchedules() {
  loading.value = true;
  try {
    const offset = (pageNo.value - 1) * pageSize.value;
    const res = await CncQuoteScheduleAPI.list({ offset, limit: pageSize.value });
    if (res.data?.data) {
      schedules.value = res.data.data.items || [];
      total.value = res.data.data.total || 0;
    }
  } catch (err) {
    console.error("加载监测计划失败:", err);
  } finally {
    loading.value = false;
  }
}

async function handlePause(id: string) {
  try {
    await CncQuoteScheduleAPI.pause(id);
    ElMessage.success("计划已成功暂停");
    void fetchSchedules();
  } catch (err) {
    ElMessage.error("暂停计划失败");
  }
}

async function handleResume(id: string) {
  try {
    await CncQuoteScheduleAPI.resume(id);
    ElMessage.success("计划已恢复监测");
    void fetchSchedules();
  } catch (err) {
    ElMessage.error("恢复计划失败");
  }
}

// ────────── 轮次明细 ──────────
const roundsVisible = ref(false);
const currentSchedule = ref<ScheduleDetail | null>(null);
const roundsList = ref<ScheduleRound[]>([]);
const roundsLoading = ref(false);

async function openRounds(sched: ScheduleDetail | any) {
  currentSchedule.value = sched as ScheduleDetail;
  roundsVisible.value = true;
  await fetchRounds();
}

async function fetchRounds() {
  if (!currentSchedule.value) return;
  roundsLoading.value = true;
  try {
    const res = await CncQuoteScheduleAPI.rounds(currentSchedule.value.id, { offset: 0, limit: 50 });
    roundsList.value = res.data?.data || [];
  } catch (err) {
    console.error("获取轮次明细失败:", err);
  } finally {
    roundsLoading.value = false;
  }
}

function formatTime(isoStr?: string | null) {
  if (!isoStr) return "-";
  return isoStr.slice(0, 19).replace("T", " ");
}

function formatRoundStatus(status: string) {
  const map: Record<string, string> = {
    PENDING: "待调度",
    RUNNING: "执行中",
    COMPLETED: "已完成",
    FAILED: "执行异常",
    SKIPPED: "已跳过",
  };
  return map[status] || status;
}

function getRoundStatusType(status: string) {
  switch (status) {
    case "COMPLETED":
      return "success";
    case "RUNNING":
      return "primary";
    case "SKIPPED":
      return "warning";
    case "FAILED":
      return "danger";
    default:
      return "info";
  }
}

onMounted(() => {
  void fetchSchedules();
});
</script>

<style scoped>
.schedule-container {
  padding: 12px;
  overflow-y: auto;
}
.table-card {
  min-height: calc(100vh - 120px);
}
</style>
