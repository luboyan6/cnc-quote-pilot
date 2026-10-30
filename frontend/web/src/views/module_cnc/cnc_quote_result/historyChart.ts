import type { CncHistoryPricePoint } from "@/api/module_cnc/cnc_quote_result";

interface HistoryChartSeries {
  id: string;
  name: string;
  type: "line" | "scatter";
  yAxisIndex: number;
  data: { name: string; value: [number, number] }[];
}

/** Keep incomplete observations visible as isolated points, never as a trend. */
export function buildHistoryChart(points: CncHistoryPricePoint[]) {
  const groups = new Map<string, HistoryChartSeries>();
  let unplottable = 0;
  let incomparable = 0;
  let conditionNumber = 0;

  for (const point of points) {
    const time = point.observed_at || point.quoted_time;
    const timestamp = time ? Date.parse(time) : NaN;
    const rawPrice = point.unit_price;
    const price = rawPrice == null || String(rawPrice).trim() === "" ? NaN : Number(rawPrice);
    const currency = point.currency?.trim().toUpperCase();
    if (
      !Number.isFinite(timestamp) ||
      !Number.isFinite(price) ||
      (currency !== "CNY" && currency !== "USD")
    ) {
      unplottable++;
      continue;
    }

    const key = point.comparison_key?.trim();
    const platform = point.platform_name || "平台未知";
    const groupId = key ? `comparison:${currency}:${key}` : `incomplete:${currency}`;
    let group = groups.get(groupId);
    if (!group) {
      if (key) conditionNumber++;
      group = {
        id: groupId,
        name: key
          ? `${platform} · ${point.part_name || "图纸"} · ${currency} · 条件 ${conditionNumber}`
          : `条件不完整 · ${currency}（不可比较）`,
        type: key ? "line" : "scatter",
        yAxisIndex: currency === "USD" ? 1 : 0,
        data: [],
      };
      groups.set(groupId, group);
    }
    if (!key) incomparable++;
    group.data.push({
      name: `${platform} · ${point.part_name || "图纸未知"}`,
      value: [timestamp, price],
    });
  }

  const series = Array.from(groups.values());
  for (const group of series) group.data.sort((a, b) => a.value[0] - b.value[0]);
  return { series, incomparable, unplottable };
}
