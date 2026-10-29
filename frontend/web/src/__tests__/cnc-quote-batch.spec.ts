import { beforeEach, describe, expect, it, vi } from "vitest";
import CncQuoteBatchAPI, {
  type BatchRequest,
} from "@/api/module_cnc/cnc_quote_batch";

const { request } = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@utils", () => ({ request }));

beforeEach(() => {
  request.mockReset();
});

describe("CNC 批量报价 API 与交互契约", () => {
  it("preview 接口发送规范化的批量目标与请求体", async () => {
    const payload: BatchRequest = {
      request_id: "e4a2c1b0-1111-2222-3333-444455556666",
      targets: [
        { config_id: 101, account_id: 5, quantities: [1, 5, 10] },
      ],
    };
    await CncQuoteBatchAPI.preview(payload);

    expect(request).toHaveBeenCalledTimes(1);
    const callConfig = request.mock.calls[0]?.[0];
    expect(callConfig.url).toBe("/cnc/cnc_quote_batch/preview");
    expect(callConfig.method).toBe("post");
    expect(callConfig.data).toEqual(payload);
  });

  it("create 接口向后端提交批量报价任务并支持 AbortSignal", async () => {
    const controller = new AbortController();
    const payload: BatchRequest = {
      request_id: "00000000-0000-0000-0000-000000000001",
      targets: [{ config_id: 202, quantities: [1] }],
    };
    await CncQuoteBatchAPI.create(payload, controller.signal);

    const callConfig = request.mock.calls[0]?.[0];
    expect(callConfig.url).toBe("/cnc/cnc_quote_batch/create");
    expect(callConfig.method).toBe("post");
    expect(callConfig.data).toEqual(payload);
    expect(callConfig.signal).toBe(controller.signal);
  });

  it("list 接口支持分页 offset 和 limit 查询", async () => {
    await CncQuoteBatchAPI.list({ offset: 20, limit: 10 });

    const callConfig = request.mock.calls[0]?.[0];
    expect(callConfig.url).toBe("/cnc/cnc_quote_batch/list");
    expect(callConfig.method).toBe("get");
    expect(callConfig.params).toEqual({ offset: 20, limit: 10 });
  });

  it("detail 与 items 接口正确拼接批次 UUID 路径", async () => {
    const batchId = "batch-uuid-1234";
    await CncQuoteBatchAPI.detail(batchId);
    expect(request.mock.calls[0]?.[0].url).toBe(`/cnc/cnc_quote_batch/detail/${batchId}`);
    expect(request.mock.calls[0]?.[0].method).toBe("get");

    await CncQuoteBatchAPI.items(batchId, { offset: 0, limit: 50 });
    expect(request.mock.calls[1]?.[0].url).toBe(`/cnc/cnc_quote_batch/${batchId}/items`);
    expect(request.mock.calls[1]?.[0].params).toEqual({ offset: 0, limit: 50 });
  });

  it("cancel 接口提交批次终止指令", async () => {
    const batchId = "batch-to-cancel";
    await CncQuoteBatchAPI.cancel(batchId);

    const callConfig = request.mock.calls[0]?.[0];
    expect(callConfig.url).toBe(`/cnc/cnc_quote_batch/${batchId}/cancel`);
    expect(callConfig.method).toBe("post");
  });

  it("retryItem 与 attempts 接口处理子项级重试与历史轨迹", async () => {
    const itemId = "item-uuid-777";
    await CncQuoteBatchAPI.retryItem(itemId);
    expect(request.mock.calls[0]?.[0].url).toBe(`/cnc/cnc_quote_batch/items/${itemId}/retry`);
    expect(request.mock.calls[0]?.[0].method).toBe("post");

    await CncQuoteBatchAPI.attempts(itemId);
    expect(request.mock.calls[1]?.[0].url).toBe(`/cnc/cnc_quote_batch/items/${itemId}/attempts`);
    expect(request.mock.calls[1]?.[0].method).toBe("get");
  });
});
