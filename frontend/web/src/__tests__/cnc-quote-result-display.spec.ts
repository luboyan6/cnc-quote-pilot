import { describe, expect, it } from "vitest";
import type { CncPlatformStat } from "@/api/module_cnc/cnc_quote_result";
import {
  formatAmount,
  summarizePlatformStats,
} from "@/views/module_cnc/cnc_quote_result/resultDisplay";

function platform(overrides: Partial<CncPlatformStat>): CncPlatformStat {
  return {
    platform_id: 2,
    platform_name: "嘉立创",
    platform_code: "jlc_cnc_cn",
    currency: "CNY",
    total_quotes: 3,
    formal_quotes: 1,
    reference_estimates: 1,
    pending_reviews: 0,
    success_quotes: 2,
    failed_quotes: 1,
    success_rate: 66.7,
    avg_duration_seconds: 1,
    min_unit_price: null,
    max_unit_price: null,
    latest_quote_time: null,
    ...overrides,
  };
}

describe("报价结果展示口径", () => {
  it("金额保留原始精度，不替未知币种添加人民币符号", () => {
    expect(formatAmount("123456789.1234", "USD")).toBe("$123456789.1234");
    expect(formatAmount("0", "CNY")).toBe("¥0");
    expect(formatAmount("12.00", null)).toBe("12.00（币种未知）");
    expect(formatAmount("12.00", "EUR")).toBe("EUR 12.00");
    expect(formatAmount(null, "CNY")).toBe("未知");
  });

  it("按真实平台代码合并各币种分组，不依赖数字 ID 猜平台", () => {
    const result = summarizePlatformStats(
      [
        platform({}),
        platform({
          platform_id: 8,
          currency: "USD",
          total_quotes: 1,
          formal_quotes: 1,
          reference_estimates: 0,
          failed_quotes: 0,
        }),
        platform({ platform_id: 2, platform_code: null, total_quotes: 99 }),
      ],
      "jlc_cnc_cn"
    );
    expect(result).toEqual({ total_quotes: 4, success_rate: 75, formal_quote_rate: "50.0%" });
    expect(summarizePlatformStats([platform({ platform_code: null })], "jlc_cnc_cn")).toBeNull();
  });
});
