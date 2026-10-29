<template>
  <div class="fa-full-height quote-result-container">
    <!-- 1. 顶部统计大盘指标卡片 -->
    <div class="stats-overview-grid">
      <!-- 总体成功率 & 质量指标 -->
      <ElCard shadow="hover" class="stat-card stat-card-success">
        <div class="stat-card-content">
          <div class="stat-text-box">
            <span class="stat-label">总体成功率</span>
            <div class="stat-value-row">
              <span class="stat-value text-emerald-600">
                {{ statsLoading ? "--" : stats.overall_success_rate }}%
              </span>
              <ElTag
                size="small"
                :type="stats.overall_success_rate >= 80 ? 'success' : stats.overall_success_rate >= 50 ? 'warning' : 'danger'"
                class="ml-2"
              >
                {{ stats.success_quotes }} / {{ stats.total_quotes }} 成功
              </ElTag>
            </div>
            <span class="stat-subtext">
              实际出价率: {{ stats.formal_quote_rate ?? "0.0%" }} · 完成率: {{ stats.completion_rate ?? "0.0%" }}
            </span>
          </div>
          <div class="stat-icon-wrapper bg-emerald-50 text-emerald-600">
            <ElIcon :size="28"><CircleCheck /></ElIcon>
          </div>
        </div>
      </ElCard>

      <!-- 报价性质分布 -->
      <ElCard shadow="hover" class="stat-card stat-card-dist">
        <div class="stat-card-content">
          <div class="stat-text-box">
            <span class="stat-label">报价性质分布</span>
            <div class="stat-value-row">
              <span class="stat-value text-blue-600">
                {{ stats.quoted_quotes }}
              </span>
              <span class="stat-unit-text">正式出价</span>
            </div>
            <span class="stat-subtext">
              估价: {{ stats.reference_estimate_quotes }} · 待审: {{ stats.pending_review_quotes }} · 失败: {{ stats.failed_quotes }}
            </span>
          </div>
          <div class="stat-icon-wrapper bg-blue-50 text-blue-600">
            <ElIcon :size="28"><DataAnalysis /></ElIcon>
          </div>
        </div>
      </ElCard>

      <!-- 平均耗时拆解 -->
      <ElCard shadow="hover" class="stat-card stat-card-speed">
        <div class="stat-card-content">
          <div class="stat-text-box">
            <span class="stat-label">平均执行耗时</span>
            <div class="stat-value-row">
              <span class="stat-value text-amber-600">
                {{ statsLoading ? "--" : stats.avg_duration_seconds }}
              </span>
              <span class="stat-unit">秒</span>
            </div>
            <span class="stat-subtext">
              活跃执行: ~{{ stats.avg_exec_seconds }}s · 排队: ~{{ stats.avg_queue_seconds }}s
            </span>
          </div>
          <div class="stat-icon-wrapper bg-amber-50 text-amber-600">
            <ElIcon :size="28"><Timer /></ElIcon>
          </div>
        </div>
      </ElCard>

      <!-- 嘉立创平台指标 -->
      <ElCard shadow="hover" class="stat-card stat-card-platform">
        <div class="stat-card-content">
          <div class="stat-text-box">
            <div class="flex items-center gap-2">
              <span class="stat-label">嘉立创中国 (JLC)</span>
              <ElTag size="small" type="primary">CNY</ElTag>
            </div>
            <div class="stat-value-row">
              <span class="stat-value text-blue-600">
                {{ jlcStat ? `${jlcStat.success_rate}%` : "--" }}
              </span>
              <span class="stat-unit-text">成功率</span>
            </div>
            <span class="stat-subtext">
              正式率: {{ jlcStat?.formal_quote_rate ?? "-" }} · {{ jlcStat?.total_quotes || 0 }} 次请求
            </span>
          </div>
          <div class="stat-icon-wrapper bg-blue-50 text-blue-600">
            <ElIcon :size="28"><Platform /></ElIcon>
          </div>
        </div>
      </ElCard>

      <!-- Xometry 平台指标 -->
      <ElCard shadow="hover" class="stat-card stat-card-platform">
        <div class="stat-card-content">
          <div class="stat-text-box">
            <div class="flex items-center gap-2">
              <span class="stat-label">Xometry US</span>
              <ElTag size="small" type="success">USD</ElTag>
            </div>
            <div class="stat-value-row">
              <span class="stat-value text-indigo-600">
                {{ xometryStat ? `${xometryStat.success_rate}%` : "--" }}
              </span>
              <span class="stat-unit-text">成功率</span>
            </div>
            <span class="stat-subtext">
              正式率: {{ xometryStat?.formal_quote_rate ?? "-" }} · {{ xometryStat?.total_quotes || 0 }} 次请求
            </span>
          </div>
          <div class="stat-icon-wrapper bg-indigo-50 text-indigo-600">
            <ElIcon :size="28"><TrendCharts /></ElIcon>
          </div>
        </div>
      </ElCard>
    </div>

    <!-- 2. 可比历史价格趋势折线图 -->
    <ElCard shadow="never" class="chart-card mt-3">
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <ElIcon class="text-primary"><TrendCharts /></ElIcon>
            <span class="font-semibold text-gray-800">可比历史价格走势与平台对比</span>
            <ElTag size="small" type="info">独立指纹分组 · 保留真实观测</ElTag>
          </div>
          <div class="flex items-center gap-3">
            <ElSelect
              v-model="chartFilterPartId"
              placeholder="按零件图纸筛选"
              clearable
              size="small"
              style="width: 200px"
              @change="fetchHistoryPriceData"
            >
              <ElOption
                v-for="item in partFilterOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </ElSelect>
            <ElButton size="small" :icon="Refresh" @click="fetchHistoryPriceData">
              刷新图表
            </ElButton>
            <ElButton
              size="small"
              text
              @click="showChartSection = !showChartSection"
            >
              {{ showChartSection ? "收起图表" : "展开图表" }}
            </ElButton>
          </div>
        </div>
      </template>

      <div v-show="showChartSection" class="chart-wrapper">
        <div ref="chartRef" style="width: 100%; height: 280px;" />
      </div>
    </ElCard>

    <!-- 3. 搜索过滤栏 -->
    <FaSearchBar
      v-show="showSearchBar"
      ref="searchBarRef"
      v-model="searchForm"
      :items="searchItems"
      :is-expand="false"
      :show-expand="false"
      :show-reset="true"
      :show-search="true"
      @search="handleSearch"
      @reset="onResetSearch"
    />

    <!-- 4. 报价结果数据表 -->
    <ElCard class="fa-table-card mt-3">
      <FaTableHeader
        v-model:columns="columnChecks"
        v-model:showSearchBar="showSearchBar"
        :loading="loading"
        @refresh="refreshData"
      >
        <template #left>
          <div class="flex items-center gap-2">
            <ElButton
              v-if="checkPerm('module_cnc:cnc_quote_result:delete')"
              type="danger"
              plain
              :disabled="selectedIds.length === 0"
              :icon="Delete"
              @click="handleBatchDelete"
            >
              批量删除
            </ElButton>
            <ElButton
              type="primary"
              plain
              :icon="Refresh"
              @click="refreshData"
            >
              刷新数据
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
        :height="520"
        @selection-change="onTableSelectionChange"
        @pagination:size-change="handleSizeChange"
        @pagination:current-change="handleCurrentChange"
      >
        <!-- 平台列 -->
        <template #platform="{ row }">
          <ElTag
            v-if="row.platform_id === 1"
            type="success"
            effect="light"
            class="font-medium"
          >
            🇺🇸 Xometry US
          </ElTag>
          <ElTag
            v-else-if="row.platform_id === 2"
            type="primary"
            effect="light"
            class="font-medium"
          >
            🇨🇳 嘉立创中国
          </ElTag>
          <ElTag v-else type="info">{{ row.platform_name || "-" }}</ElTag>
        </template>

        <!-- 报价金额列 -->
        <template #quote_amount="{ row }">
          <div v-if="row.unit_price != null" class="price-cell">
            <div class="price-main">
              <span class="currency-symbol">{{ row.currency === 'USD' ? '$' : '¥' }}</span>
              <span class="price-val">{{ row.unit_price }}</span>
              <span class="price-scope">/ 件</span>
            </div>
            <div v-if="row.total_amount" class="price-sub">
              总额: {{ row.currency === 'USD' ? '$' : '¥' }}{{ row.total_amount }}
              <ElTag v-if="row.tax_included" size="small" type="info" class="ml-1 scale-90">含税</ElTag>
            </div>
          </div>
          <span v-else class="text-gray-400">未出价</span>
        </template>

        <!-- 状态与报价性质列 -->
        <template #status="{ row }">
          <ElTag
            v-if="row.quote_status === 'QUOTED'"
            type="success"
            effect="dark"
            size="small"
          >
            正式报价
          </ElTag>
          <ElTag
            v-else-if="row.quote_status === 'REFERENCE_ESTIMATE'"
            type="primary"
            effect="plain"
            size="small"
          >
            参考估价
          </ElTag>
          <ElTag
            v-else-if="row.quote_status === 'PENDING_REVIEW'"
            type="warning"
            effect="plain"
            size="small"
          >
            待人工审核
          </ElTag>
          <ElTag
            v-else-if="row.quote_status === 'CANCELLED'"
            type="info"
            size="small"
          >
            已取消
          </ElTag>
          <ElTag
            v-else
            type="danger"
            size="small"
          >
            {{ row.error_code || row.error_message || "报价失败" }}
          </ElTag>
        </template>

        <!-- 执行耗时列 (带分段提示) -->
        <template #duration="{ row }">
          <ElTooltip placement="top">
            <template #content>
              <div class="text-xs flex flex-col gap-1">
                <div>总自然耗时: {{ row.total_wall_ms ?? row.elapsed_ms ?? 0 }} ms</div>
                <div>排队耗时: {{ row.queue_ms ?? 0 }} ms</div>
                <div>活跃执行: {{ row.active_execution_ms ?? 0 }} ms</div>
                <div v-if="row.human_wait_ms">人工等待: {{ row.human_wait_ms }} ms</div>
                <div v-if="row.reconcile_ms">核对耗时: {{ row.reconcile_ms }} ms</div>
              </div>
            </template>
            <ElTag
              v-if="row.duration_seconds != null"
              :type="Number(row.duration_seconds) <= 30 ? 'success' : Number(row.duration_seconds) <= 90 ? 'warning' : 'primary'"
              size="small"
              class="cursor-pointer"
            >
              ⏱️ {{ row.duration_seconds }}s
            </ElTag>
            <span v-else class="text-gray-400">-</span>
          </ElTooltip>
        </template>

        <!-- 受控证据截图列 -->
        <template #screenshot="{ row }">
          <div v-if="row.evidence_screenshot || row.evidence_id" class="flex items-center justify-center">
            <ElButton
              link
              type="primary"
              size="small"
              :icon="Picture"
              :loading="loadingBlobs.has(row.id)"
              @click="openScreenshotDialog(row)"
            >
              查看证据
            </ElButton>
          </div>
          <span v-else class="text-gray-400">无截图</span>
        </template>

        <!-- 操作列 -->
        <template #operation="{ row }">
          <div class="flex items-center gap-2">
            <ElButton
              link
              type="primary"
              size="small"
              :icon="View"
              @click="handleOpenDetail(row)"
            >
              详情
            </ElButton>
            <ElPopconfirm
              v-if="row.id != null"
              title="确定删除此条报价结果记录？"
              @confirm="handleDeleteRow(row.id)"
            >
              <template #reference>
                <ElButton
                  link
                  type="danger"
                  size="small"
                  :icon="Delete"
                >
                  删除
                </ElButton>
              </template>
            </ElPopconfirm>
          </div>
        </template>
      </FaTable>
    </ElCard>

    <!-- 5. 详情查看弹窗 -->
    <ElDialog
      v-model="detailVisible"
      title="报价执行详情与可比证据快照"
      width="860px"
      destroy-on-close
    >
      <div v-if="selectedDetail" class="detail-container">
        <!-- 基础信息 -->
        <ElDescriptions :column="2" border title="基本信息">
          <ElDescriptionsItem label="平台">
            <ElTag :type="selectedDetail.platform_id === 1 ? 'success' : 'primary'">
              {{ selectedDetail.platform_name || (selectedDetail.platform_id === 1 ? 'Xometry US' : '嘉立创中国') }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="状态">
            <ElTag :type="selectedDetail.success ? 'success' : 'danger'">
              {{ selectedDetail.quote_status }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="零件图纸" :span="2">
            {{ selectedDetail.part_name || `图纸#${selectedDetail.part_id}` }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="关联配置">
            {{ selectedDetail.config_name || `配置#${selectedDetail.config_id}` }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="账号别名">
            {{ selectedDetail.account_alias || "-" }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="批次 / 轮次">
            <span class="text-xs font-mono">
              批次: {{ selectedDetail.batch_id || "-" }} · 轮次: {{ selectedDetail.round_id || "-" }}
            </span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="报价时间">
            {{ selectedDetail.quoted_at || selectedDetail.created_time || "-" }}
          </ElDescriptionsItem>
        </ElDescriptions>

        <!-- 价格与商业条件 -->
        <ElDescriptions :column="2" border title="价格与商业条件" class="mt-4">
          <ElDescriptionsItem label="单件价格">
            <strong class="text-lg text-primary">
              {{ selectedDetail.currency === 'USD' ? '$' : '¥' }}{{ selectedDetail.unit_price ?? "0.00" }}
            </strong>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="总金额">
            <strong class="text-lg text-emerald-600">
              {{ selectedDetail.currency === 'USD' ? '$' : '¥' }}{{ selectedDetail.total_amount ?? "0.00" }}
            </strong>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="税费 / 含税">
            <span>{{ selectedDetail.tax_amount ? `${selectedDetail.currency === 'USD' ? '$' : '¥'}${selectedDetail.tax_amount}` : "-" }}</span>
            <ElTag size="small" class="ml-2" :type="selectedDetail.tax_included ? 'success' : 'info'">
              {{ selectedDetail.tax_included ? '含税' : '未注含税' }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="运费估算">
            {{ selectedDetail.shipping_amount ? `${selectedDetail.currency === 'USD' ? '$' : '¥'}${selectedDetail.shipping_amount}` : "免运费 / 需确认" }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="优惠券减免">
            {{ selectedDetail.discount_amount ? `-${selectedDetail.currency === 'USD' ? '$' : '¥'}${selectedDetail.discount_amount}` : "-" }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="交期原文">
            {{ selectedDetail.lead_time_raw || "标准交期" }}
          </ElDescriptionsItem>
          <ElDescriptionsItem v-if="selectedDetail.platform_quote_id" label="站方单号" :span="2">
            <code>{{ selectedDetail.platform_quote_id }}</code>
          </ElDescriptionsItem>
        </ElDescriptions>

        <!-- 工艺参数与指纹 -->
        <ElDescriptions :column="2" border title="生效工艺参数与可比指纹" class="mt-4">
          <ElDescriptionsItem label="加工材料">{{ selectedDetail.material || "默认" }}</ElDescriptionsItem>
          <ElDescriptionsItem label="表面处理">{{ selectedDetail.surface_finish || "默认" }}</ElDescriptionsItem>
          <ElDescriptionsItem label="加工数量">{{ selectedDetail.quantity || 1 }} 件</ElDescriptionsItem>
          <ElDescriptionsItem label="精度公差">{{ selectedDetail.tolerance || "标准公差" }}</ElDescriptionsItem>
          <ElDescriptionsItem label="表面粗糙度">{{ selectedDetail.roughness || "未指定" }}</ElDescriptionsItem>
          <ElDescriptionsItem label="图纸SHA256" :span="2">
            <code class="text-xs break-all text-gray-600">{{ selectedDetail.file_sha256 || "-" }}</code>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="可比指纹 (comparison_key)" :span="2">
            <code class="text-xs break-all text-blue-600 font-mono">{{ selectedDetail.comparison_key || "未生成指纹" }}</code>
          </ElDescriptionsItem>
        </ElDescriptions>

        <!-- 耗时拆解 -->
        <ElDescriptions :column="3" border title="分段耗时指标" class="mt-4">
          <ElDescriptionsItem label="总自然耗时">
            <span class="font-semibold text-amber-600">{{ selectedDetail.duration_seconds || 0 }}s</span>
            <span class="text-xs text-gray-400 ml-1">({{ selectedDetail.total_wall_ms ?? selectedDetail.elapsed_ms ?? 0 }}ms)</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="排队耗时">
            {{ selectedDetail.queue_ms || 0 }} ms
          </ElDescriptionsItem>
          <ElDescriptionsItem label="活跃执行耗时">
            {{ selectedDetail.active_execution_ms || 0 }} ms
          </ElDescriptionsItem>
          <ElDescriptionsItem label="人工介入等待">
            {{ selectedDetail.human_wait_ms || 0 }} ms
          </ElDescriptionsItem>
          <ElDescriptionsItem label="终态核对耗时">
            {{ selectedDetail.reconcile_ms || 0 }} ms
          </ElDescriptionsItem>
          <ElDescriptionsItem label="任务RunID">
            <code class="text-xs text-gray-500 font-mono">{{ selectedDetail.run_id }}</code>
          </ElDescriptionsItem>
        </ElDescriptions>

        <!-- 失败信息 -->
        <ElAlert
          v-if="!selectedDetail.success && (selectedDetail.error_code || selectedDetail.error_message)"
          :title="`执行异常 [${selectedDetail.error_code || 'ERROR'}]: ${selectedDetail.error_message || '未知异常'}`"
          type="error"
          show-icon
          :closable="false"
          class="mt-4"
        />

        <!-- 详情内的受控截图证据原图 -->
        <div v-if="selectedDetail.id != null && (selectedDetail.evidence_screenshot || selectedDetail.evidence_id)" class="mt-4">
          <div class="flex items-center justify-between mb-2">
            <h4 class="font-semibold text-gray-800">受控私有证据原图</h4>
            <ElButton
              size="small"
              type="primary"
              plain
              :loading="loadingBlobs.has(selectedDetail.id)"
              @click="openScreenshotDialog(selectedDetail)"
            >
              放大查看原图
            </ElButton>
          </div>
          <div class="border rounded p-2 bg-gray-50 text-center">
            <img
              v-if="blobUrlMap.get(selectedDetail.id)"
              :src="blobUrlMap.get(selectedDetail.id)"
              alt="证据原图"
              style="max-height: 380px; width: 100%; object-fit: contain;"
            />
            <div v-else class="py-8 text-gray-400 flex flex-col items-center gap-2">
              <ElButton
                type="primary"
                size="small"
                :loading="loadingBlobs.has(selectedDetail.id)"
                @click="loadScreenshotBlob(selectedDetail.id)"
              >
                加载私有证据图片
              </ElButton>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <ElButton @click="detailVisible = false">关闭</ElButton>
      </template>
    </ElDialog>

    <!-- 6. 受控私有截图原图查看弹窗 -->
    <ElDialog
      v-model="screenshotDialogVisible"
      :title="`报价受控证据 · ${screenshotTarget?.platform_name || ''} · ${screenshotTarget?.part_name || ''}`"
      width="90vw"
      top="3vh"
      destroy-on-close
      @close="closeScreenshotDialog"
    >
      <div v-if="screenshotTarget && screenshotTarget.id != null" class="screenshot-full-box">
        <div class="mb-2 text-sm text-gray-500 flex justify-between items-center">
          <span>抓取时间: {{ screenshotTarget.quoted_at || screenshotTarget.created_time || "-" }}</span>
          <span class="text-xs text-gray-400">已通过 Bearer Token 受控读取二进制流</span>
        </div>
        <div class="screenshot-img-wrap">
          <img
            v-if="blobUrlMap.get(screenshotTarget.id)"
            :src="blobUrlMap.get(screenshotTarget.id)"
            alt="报价受控证据"
            class="full-img"
          />
          <div v-else-if="loadingBlobs.has(screenshotTarget.id)" class="text-white py-12">
            正在安全拉取证据流...
          </div>
          <div v-else class="text-red-400 py-12">
            证据图片拉取失败或已被清理
          </div>
        </div>
      </div>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { CircleCheck, DataAnalysis, Delete, Picture, Platform, Refresh, Timer, TrendCharts, View } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { resolveStatusColumns } from "@utils";
import { checkPerm } from "@/utils/checkPerm";
import { useTable } from "@/hooks/core/useTable";
import FaSearchBar, { type SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import FaTableHeader from "@/components/tables/fa-table-header/index.vue";
import FaTable from "@/components/tables/fa-table/index.vue";
import CncQuoteResultAPI, {
  type CncHistoryPricePoint,
  type CncQuoteResultTable,
  type CncQuoteStats,
} from "@/api/module_cnc/cnc_quote_result";

echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  CanvasRenderer,
]);

defineOptions({
  name: "CncQuoteResult",
});

// ────────── 1. 顶部统计大盘 ──────────
const statsLoading = ref(false);
const stats = ref<CncQuoteStats>({
  total_quotes: 0,
  total_items: 0,
  completed_quotes: 0,
  quoted_quotes: 0,
  reference_estimate_quotes: 0,
  pending_review_quotes: 0,
  success_quotes: 0,
  failed_quotes: 0,
  cancelled_quotes: 0,
  waiting_human_quotes: 0,
  reconciling_quotes: 0,
  overall_success_rate: 0,
  completion_rate: "0.0%",
  formal_quote_rate: "0.0%",
  avg_duration_seconds: 0,
  avg_queue_seconds: 0,
  avg_exec_seconds: 0,
  fastest_seconds: 0,
  longest_seconds: 0,
  platform_stats: [],
});

const jlcStat = computed(() => stats.value.platform_stats.find((p) => p.platform_id === 2));
const xometryStat = computed(() => stats.value.platform_stats.find((p) => p.platform_id === 1));

async function fetchStats() {
  statsLoading.value = true;
  try {
    const res = await CncQuoteResultAPI.getQuoteStats();
    if (res.data?.data) {
      stats.value = res.data.data;
    }
  } catch (err) {
    console.error("获取报价统计指标失败:", err);
  } finally {
    statsLoading.value = false;
  }
}

// ────────── 2. 历史价格折线图 ──────────
const chartRef = ref<HTMLDivElement>();
let chartInstance: echarts.ECharts | null = null;
const showChartSection = ref(true);
const chartFilterPartId = ref<number | undefined>();
const historyData = ref<CncHistoryPricePoint[]>([]);

const partFilterOptions = computed(() => {
  const map = new Map<number, string>();
  historyData.value.forEach((item) => {
    if (item.part_id && !map.has(item.part_id)) {
      map.set(item.part_id, item.part_name || `零件#${item.part_id}`);
    }
  });
  return Array.from(map.entries()).map(([value, label]) => ({ label, value }));
});

async function fetchHistoryPriceData() {
  try {
    const res = await CncQuoteResultAPI.getHistoryPrices({
      part_id: chartFilterPartId.value,
      limit: 100,
    });
    historyData.value = res.data?.data || [];
    renderChart();
  } catch (err) {
    console.error("获取历史价格数据失败:", err);
  }
}

function renderChart() {
  if (!chartRef.value) return;
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value);
  }

  // 1. 提取所有有效时间轴点
  const validPoints = historyData.value.filter((d) => d.quoted_time);
  const timeLabels = Array.from(
    new Set(
      validPoints.map((d) => d.quoted_time!.slice(0, 19).replace("T", " "))
    )
  ).sort();

  if (timeLabels.length === 0) {
    chartInstance.clear();
    return;
  }

  // 2. 按可比键或平台/材料/数量分系列，确保曲线各点严格可比
  const seriesGroups = new Map<string, {
    name: string;
    currency: string;
    dataMap: Map<string, { unitPrice: number; priceDiff?: string | null; changeRate?: string | null; quoteKind: string }>;
  }>();

  for (const pt of validPoints) {
    const groupKey = pt.comparison_key || `${pt.platform_name}_${pt.currency}_${pt.quantity}pcs_${pt.material || 'default'}`;
    const seriesName = pt.comparison_key
      ? `${pt.platform_name} · ${pt.part_name || '图纸'} (${pt.currency} ¥/$, ${pt.quantity}件)`
      : `${pt.platform_name} · ${pt.material || '默认'} · ${pt.quantity}件 (${pt.currency})`;

    if (!seriesGroups.has(groupKey)) {
      seriesGroups.set(groupKey, {
        name: seriesName,
        currency: pt.currency,
        dataMap: new Map(),
      });
    }

    const timeStr = pt.quoted_time!.slice(0, 19).replace("T", " ");
    const numPrice = Number(pt.unit_price) || 0;
    seriesGroups.get(groupKey)!.dataMap.set(timeStr, {
      unitPrice: numPrice,
      priceDiff: pt.price_diff,
      changeRate: pt.change_rate,
      quoteKind: pt.quote_kind,
    });
  }

  const seriesNames: string[] = [];
  const seriesList: any[] = [];
  const colors = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4"];
  let colorIdx = 0;

  for (const [, grp] of seriesGroups) {
    seriesNames.push(grp.name);
    const yAxisIndex = grp.currency === "USD" ? 1 : 0;
    const seriesPoints = timeLabels.map((t) => {
      const entry = grp.dataMap.get(t);
      return entry ? entry.unitPrice : null;
    });

    seriesList.push({
      name: grp.name,
      type: "line",
      yAxisIndex,
      data: seriesPoints,
      smooth: false, // 严禁虚假连线
      connectNulls: true,
      showAllSymbol: true,
      itemStyle: { color: colors[colorIdx % colors.length] },
      lineStyle: { width: 2 },
    });
    colorIdx++;
  }

  const option = {
    tooltip: {
      trigger: "axis",
      formatter: (params: any[]) => {
        if (!params || params.length === 0) return "";
        let tip = `<div style="font-weight: bold; margin-bottom: 4px;">${params[0].axisValue}</div>`;
        params.forEach((item) => {
          if (item.value != null) {
            const sym = item.seriesName.includes("USD") || item.seriesName.includes("Xometry") ? "$" : "¥";
            tip += `<div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${item.color};margin-right:6px;"></span>${item.seriesName}: <b>${sym}${item.value}</b></div>`;
          }
        });
        return tip;
      },
    },
    legend: {
      data: seriesNames,
      top: 0,
      type: "scroll",
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "8%",
      top: "16%",
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: timeLabels,
      axisLabel: {
        rotate: 25,
        fontSize: 10,
        color: "#6b7280",
      },
    },
    yAxis: [
      {
        type: "value",
        name: "CNY (¥)",
        axisLabel: { formatter: "¥{value}" },
        splitLine: { lineStyle: { type: "dashed", color: "#f3f4f6" } },
      },
      {
        type: "value",
        name: "USD ($)",
        axisLabel: { formatter: "${value}" },
        splitLine: { show: false },
      },
    ],
    series: seriesList,
  };

  chartInstance.setOption(option, true);
}

function handleResize() {
  chartInstance?.resize();
}

// ────────── 3. 搜索栏与表格 ──────────
const showSearchBar = ref(true);
const selectedIds = ref<number[]>([]);

const searchForm = ref<Record<string, any>>({
  platform_id: undefined,
  quote_kind: undefined,
  currency: undefined,
  part_name: undefined,
  config_name: undefined,
  batch_id: undefined,
  round_id: undefined,
});

const searchItems = computed<SearchFormItem[]>(() => [
  {
    key: "platform_id",
    label: "报价平台",
    type: "select",
    options: [
      { label: "全部平台", value: undefined },
      { label: "Xometry US", value: 1 },
      { label: "嘉立创中国", value: 2 },
    ],
    placeholder: "请选择平台",
    span: 6,
  },
  {
    key: "quote_kind",
    label: "报价性质",
    type: "select",
    options: [
      { label: "全部性质", value: undefined },
      { label: "正式报价 (QUOTED)", value: "QUOTED" },
      { label: "参考估价 (REFERENCE_ESTIMATE)", value: "REFERENCE_ESTIMATE" },
      { label: "待人工审核 (PENDING_REVIEW)", value: "PENDING_REVIEW" },
      { label: "报价失败 (FAILED)", value: "FAILED" },
      { label: "已取消 (CANCELLED)", value: "CANCELLED" },
    ],
    placeholder: "请选择报价性质",
    span: 6,
  },
  {
    key: "currency",
    label: "币种",
    type: "select",
    options: [
      { label: "全部币种", value: undefined },
      { label: "人民币 (CNY)", value: "CNY" },
      { label: "美元 (USD)", value: "USD" },
    ],
    placeholder: "请选择币种",
    span: 6,
  },
  {
    key: "part_name",
    label: "零件图纸",
    type: "input",
    placeholder: "图纸文件名模糊搜索",
    span: 6,
  },
  {
    key: "config_name",
    label: "配置名称",
    type: "input",
    placeholder: "配置名称模糊搜索",
    span: 6,
  },
  {
    key: "batch_id",
    label: "批次 ID",
    type: "input",
    placeholder: "批次UUID精确匹配",
    span: 6,
  },
]);

const {
  columns,
  columnChecks,
  data,
  loading,
  pagination,
  searchParams,
  handleSizeChange,
  handleCurrentChange,
  refreshData: rawRefreshTable,
  replaceSearchParams,
  resetSearchParams,
} = useTable({
  core: {
    apiFn: CncQuoteResultAPI.listCncQuoteResult,
    apiParams: {
      page_no: 1,
      page_size: 10,
      order_by: JSON.stringify([{ id: "desc" }]),
    },
    columnsFactory: resolveStatusColumns<CncQuoteResultTable>(() => [
      { type: "selection", width: 48, fixed: "left" },
      { prop: "id", label: "ID", width: 68 },
      { prop: "platform", label: "报价平台", width: 140, useSlot: true },
      { prop: "part_name", label: "零件图纸", minWidth: 150, showOverflowTooltip: true },
      { prop: "config_name", label: "配置名称", minWidth: 140, showOverflowTooltip: true },
      { prop: "material", label: "材质", width: 120, showOverflowTooltip: true },
      { prop: "quantity", label: "数量", width: 65, align: "center" },
      { prop: "quote_amount", label: "报价金额", width: 150, useSlot: true },
      { prop: "lead_time_raw", label: "交期", width: 120, showOverflowTooltip: true },
      { prop: "duration", label: "执行耗时", width: 110, useSlot: true, align: "center" },
      { prop: "status", label: "状态 / 性质", width: 120, useSlot: true, align: "center" },
      { prop: "screenshot", label: "受控证据", width: 110, useSlot: true, align: "center" },
      { prop: "created_time", label: "报价时间", width: 168 },
      { prop: "operation", label: "操作", width: 150, fixed: "right", useSlot: true },
    ]),
  },
});

function handleSearch() {
  replaceSearchParams({ ...searchForm.value });
}

function onResetSearch() {
  searchForm.value = {
    platform_id: undefined,
    quote_kind: undefined,
    currency: undefined,
    part_name: undefined,
    config_name: undefined,
    batch_id: undefined,
    round_id: undefined,
  };
  resetSearchParams();
}

function refreshData() {
  void rawRefreshTable();
  void fetchStats();
  void fetchHistoryPriceData();
}

function onTableSelectionChange(rows: CncQuoteResultTable[]) {
  selectedIds.value = rows
    .map((r) => r.id)
    .filter((id): id is number => id != null);
}

async function handleDeleteRow(id: number) {
  try {
    await CncQuoteResultAPI.deleteCncQuoteResult([id]);
    ElMessage.success("删除记录成功");
    refreshData();
  } catch (err) {
    ElMessage.error("删除记录失败");
  }
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) return;
  try {
    await CncQuoteResultAPI.deleteCncQuoteResult(selectedIds.value);
    ElMessage.success(`成功删除 ${selectedIds.value.length} 条记录`);
    selectedIds.value = [];
    refreshData();
  } catch (err) {
    ElMessage.error("批量删除失败");
  }
}

// ────────── 4. 详情弹窗 ──────────
const detailVisible = ref(false);
const selectedDetail = ref<CncQuoteResultTable | null>(null);

function handleOpenDetail(row: CncQuoteResultTable) {
  selectedDetail.value = { ...row };
  detailVisible.value = true;
  if (row.id != null && (row.evidence_screenshot || row.evidence_id)) {
    void loadScreenshotBlob(row.id);
  }
}

// ────────── 5. 受控证据 Blob 缓存与生命周期管理 ──────────
const blobUrlMap = ref<Map<number, string>>(new Map());
const loadingBlobs = ref<Set<number>>(new Set());
const screenshotDialogVisible = ref(false);
const screenshotTarget = ref<CncQuoteResultTable | null>(null);

async function loadScreenshotBlob(id: number): Promise<string | null> {
  if (blobUrlMap.value.has(id)) {
    return blobUrlMap.value.get(id)!;
  }
  loadingBlobs.value.add(id);
  try {
    const res = await CncQuoteResultAPI.getScreenshotBlob(id);
    const blobUrl = URL.createObjectURL(res.data);
    blobUrlMap.value.set(id, blobUrl);
    return blobUrl;
  } catch (err) {
    console.error("加载受控截图证据失败:", err);
    ElMessage.error("获取受控证据原图失败或凭证无效");
    return null;
  } finally {
    loadingBlobs.value.delete(id);
  }
}

async function openScreenshotDialog(row: CncQuoteResultTable) {
  screenshotTarget.value = { ...row };
  screenshotDialogVisible.value = true;
  if (row.id != null) {
    await loadScreenshotBlob(row.id);
  }
}

function closeScreenshotDialog() {
  screenshotDialogVisible.value = false;
  screenshotTarget.value = null;
}

function cleanupBlobs() {
  blobUrlMap.value.forEach((url) => {
    URL.revokeObjectURL(url);
  });
  blobUrlMap.value.clear();
}

onMounted(() => {
  void fetchStats();
  void fetchHistoryPriceData();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  chartInstance?.dispose();
  chartInstance = null;
  cleanupBlobs();
});
</script>

<style scoped>
.quote-result-container {
  padding: 12px;
  overflow-y: auto;
}

.quote-result-container :deep(.fa-table-card) {
  flex: none;
  min-height: auto;
}

.quote-result-container :deep(.fa-table-card .el-card__body) {
  overflow: visible;
}

.stats-overview-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
}

@media (max-width: 1400px) {
  .stats-overview-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 900px) {
  .stats-overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .stats-overview-grid {
    grid-template-columns: 1fr;
  }
}

.stat-card {
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  transition: all 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.stat-card-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stat-text-box {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.stat-value-row {
  display: flex;
  align-items: baseline;
  margin: 4px 0;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-unit {
  font-size: 13px;
  color: #9ca3af;
  margin-left: 4px;
}

.stat-unit-text {
  font-size: 12px;
  color: #9ca3af;
  margin-left: 6px;
}

.stat-subtext {
  font-size: 11px;
  color: #9ca3af;
}

.stat-icon-wrapper {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-card {
  border-radius: 8px;
}

.chart-wrapper {
  padding-top: 8px;
}

.price-cell {
  display: flex;
  flex-direction: column;
}

.price-main {
  font-weight: 700;
  font-size: 14px;
  color: var(--el-color-primary);
}

.currency-symbol {
  font-size: 12px;
  margin-right: 2px;
}

.price-scope {
  font-size: 11px;
  color: #9ca3af;
  font-weight: normal;
  margin-left: 2px;
}

.price-sub {
  font-size: 11px;
  color: #6b7280;
}

.screenshot-full-box {
  display: flex;
  flex-direction: column;
}

.screenshot-img-wrap {
  background-color: #1f2937;
  padding: 12px;
  border-radius: 8px;
  display: flex;
  justify-content: center;
  align-items: center;
  max-height: 78vh;
  overflow: auto;
}

.full-img {
  max-width: 100%;
  max-height: 74vh;
  object-fit: contain;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}

.detail-container {
  max-height: 70vh;
  overflow-y: auto;
  padding-right: 6px;
}
</style>
