import { describe, expect, it } from "vitest";
import type { CncHistoryPricePoint } from "@/api/module_cnc/cnc_quote_result";
import { buildHistoryChart } from "@/views/module_cnc/cnc_quote_result/historyChart";

function observation(overrides: Partial<CncHistoryPricePoint>): CncHistoryPricePoint {
  return {
    id: 1,
    platform_id: 1,
    platform_name: "Xometry",
    part_name: "Part A",
    unit_price: "12.50",
    currency: "USD",
    quantity: 1,
    quote_kind: "QUOTED",
    comparison_key: "complete-A",
    duration_seconds: null,
    quoted_time: "2026-10-28T09:00:00Z",
    observed_at: "2026-10-29T09:00:00Z",
    ...overrides,
  };
}

describe("报价历史图表", () => {
  it("只连接同一可比条件，保留同一时刻的每次观测", () => {
    const chart = buildHistoryChart([
      observation({ id: 1 }),
      observation({ id: 2 }),
      observation({ id: 3, comparison_key: "complete-B", unit_price: "14.00" }),
      observation({ id: 4, comparison_key: null, part_name: "Part B" }),
      observation({ id: 5, comparison_key: null, part_name: "Part C" }),
    ]);

    const complete = chart.series.find((series) => series.id === "comparison:USD:complete-A");
    expect(complete?.type).toBe("line");
    expect(complete?.data).toHaveLength(2);
    expect(complete?.data[0]?.value).toEqual([Date.parse("2026-10-29T09:00:00Z"), 12.5]);
    expect(
      chart.series.find((series) => series.id === "comparison:USD:complete-B")?.data
    ).toHaveLength(1);
    const incomplete = chart.series.find((series) => series.id === "incomplete:USD");
    expect(incomplete?.type).toBe("scatter");
    expect(incomplete?.data.map((item) => item.name)).toEqual([
      "Xometry · Part B",
      "Xometry · Part C",
    ]);
    expect(chart.incomparable).toBe(2);
  });

  it("不把未知币种、时间或价格画成零价，并保留真实零价", () => {
    const chart = buildHistoryChart([
      observation({ id: 1, currency: null }),
      observation({ id: 2, observed_at: null, quoted_time: null }),
      observation({ id: 3, unit_price: "" }),
      observation({ id: 4, unit_price: "0", observed_at: null, comparison_key: null }),
    ]);

    expect(chart.unplottable).toBe(3);
    expect(chart.series[0]?.data[0]?.value).toEqual([Date.parse("2026-10-28T09:00:00Z"), 0]);
    expect(chart.series[0]?.type).toBe("scatter");
  });
});
