import { beforeEach, describe, expect, it, vi } from "vitest";
import CncQuoteResultAPI, {
  type CncHistoryPricePoint,
  type CncQuoteResultPageQuery,
  type CncQuoteStats,
} from "@/api/module_cnc/cnc_quote_result";

const { request } = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@utils", () => ({ request }));

beforeEach(() => {
  request.mockReset();
});

describe("CNC 报价结果与受控证据 API 契约", () => {
  it("listCncQuoteResult 支持多维度过滤参数 (批次/轮次/报价性质/币种)", async () => {
    const query: CncQuoteResultPageQuery = {
      page_no: 1,
      page_size: 20,
      batch_id: "batch-101",
      round_id: "round-202",
      quote_kind: "QUOTED",
      currency: "CNY",
    };
    await CncQuoteResultAPI.listCncQuoteResult(query);

    const callConfig = request.mock.calls[0]?.[0];
    expect(callConfig.url).toBe("/cnc/cnc_quote_result/list");
    expect(callConfig.method).toBe("get");
    expect(callConfig.params).toEqual(query);
  });

  it("getQuoteStats 获取包含正式报价率和完成率的大盘统计指标", async () => {
    const mockStats: CncQuoteStats = {
      total_quotes: 100,
      total_items: 90,
      completed_quotes: 80,
      quoted_quotes: 70,
      reference_estimate_quotes: 10,
      pending_review_quotes: 5,
      success_quotes: 80,
      failed_quotes: 10,
      cancelled_quotes: 5,
      waiting_human_quotes: 0,
      reconciling_quotes: 0,
      overall_success_rate: 88.89,
      completion_rate: "88.89%",
      formal_quote_rate: "77.78%",
      avg_duration_seconds: 24.5,
      avg_queue_seconds: 3.2,
      avg_exec_seconds: 21.3,
      fastest_seconds: 12.0,
      longest_seconds: 58.0,
      platform_stats: [
        {
          platform_id: 2,
          platform_name: "嘉立创中国",
          platform_code: "jlc_cnc",
          total_quotes: 60,
          formal_quotes: 50,
          reference_estimates: 5,
          pending_reviews: 2,
          success_quotes: 55,
          failed_quotes: 5,
          success_rate: 91.67,
          formal_quote_rate: "83.33%",
          avg_duration_seconds: 20.0,
          min_unit_price: "15.5000",
          max_unit_price: "128.0000",
          currency: "CNY",
          latest_quote_time: "2026-10-28T18:00:00Z",
        },
      ],
    };

    request.mockResolvedValueOnce({ data: { code: 0, data: mockStats } });
    const res = await CncQuoteResultAPI.getQuoteStats();

    expect(request.mock.calls[0]?.[0].url).toBe("/cnc/cnc_quote_result/stats");
    expect(res.data.data.formal_quote_rate).toBe("77.78%");
    expect(res.data.data.completion_rate).toBe("88.89%");
    expect(res.data.data.platform_stats[0]?.min_unit_price).toBe("15.5000");
  });

  it("getHistoryPrices 保留高精度 Decimal 价格字符串与差额变动率", async () => {
    const mockPoints: CncHistoryPricePoint[] = [
      {
        id: 1,
        platform_id: 2,
        platform_name: "嘉立创中国",
        unit_price: "45.1234",
        total_amount: "451.2340",
        price_diff: "+5.1234",
        change_rate: "+12.81%",
        currency: "CNY",
        quantity: 10,
        quote_kind: "QUOTED",
        comparison_key: "cmp_jlc_456_10pcs",
        duration_seconds: 18.2,
      },
      {
        id: 2,
        platform_id: 1,
        platform_name: "Xometry US",
        unit_price: "12.5000",
        total_amount: "125.0000",
        price_diff: null,
        change_rate: null,
        currency: "USD",
        quantity: 10,
        quote_kind: "QUOTED",
        comparison_key: "cmp_xom_456_10pcs",
        duration_seconds: 32.1,
      },
    ];

    request.mockResolvedValueOnce({ data: { code: 0, data: mockPoints } });
    const res = await CncQuoteResultAPI.getHistoryPrices({ limit: 50 });

    expect(request.mock.calls[0]?.[0].url).toBe("/cnc/cnc_quote_result/history-prices");
    expect(res.data.data[0]?.unit_price).toBe("45.1234");
    expect(res.data.data[0]?.price_diff).toBe("+5.1234");
    expect(res.data.data[0]?.change_rate).toBe("+12.81%");
    expect(res.data.data[1]?.price_diff).toBeNull();
  });

  it("getScreenshotBlob 强制以 responseType: blob 请求，禁止绕过鉴权拼接公共URL", async () => {
    const resultId = 88;
    const fakeBlob = new Blob(["fake-image-bytes"], { type: "image/png" });
    request.mockResolvedValueOnce({ data: fakeBlob });

    const controller = new AbortController();
    const res = await CncQuoteResultAPI.getScreenshotBlob(resultId, controller.signal);

    const callConfig = request.mock.calls[0]?.[0];
    expect(callConfig.url).toBe(`/cnc/cnc_quote_result/screenshot/${resultId}`);
    expect(callConfig.method).toBe("get");
    expect(callConfig.responseType).toBe("blob");
    expect(callConfig.signal).toBe(controller.signal);
    expect(res.data).toBe(fakeBlob);
  });

  it("聊天证据请求仅允许已发布的私有图片", async () => {
    request.mockResolvedValueOnce({ data: new Blob(["image"], { type: "image/png" }) });
    await CncQuoteResultAPI.getPrivateScreenshotBlob(88);
    const config = request.mock.calls[0]?.[0];
    expect(config.url).toBe("/cnc/cnc_quote_result/screenshot/88");
    expect(config.params).toEqual({ private_only: true });
    expect(config.responseType).toBe("blob");
  });

  it("支持受控 URL.createObjectURL 与 URL.revokeObjectURL 生命周期管理", () => {
    const fakeBlob = new Blob(["img-data"], { type: "image/png" });
    const createObjectURLSpy = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:http://localhost/test-uuid");
    const revokeObjectURLSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

    const objectUrl = URL.createObjectURL(fakeBlob);
    expect(createObjectURLSpy).toHaveBeenCalledWith(fakeBlob);
    expect(objectUrl).toBe("blob:http://localhost/test-uuid");

    URL.revokeObjectURL(objectUrl);
    expect(revokeObjectURLSpy).toHaveBeenCalledWith("blob:http://localhost/test-uuid");

    createObjectURLSpy.mockRestore();
    revokeObjectURLSpy.mockRestore();
  });
});
