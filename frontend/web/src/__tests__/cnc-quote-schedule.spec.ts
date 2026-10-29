import { beforeEach, describe, expect, it, vi } from "vitest";
import CncQuoteScheduleAPI, {
  type ScheduleCreate,
  type ScheduleUpdate,
} from "@/api/module_cnc/cnc_quote_schedule";

const { request } = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@utils", () => ({ request }));

beforeEach(() => {
  request.mockReset();
});

describe("CNC 监测计划 API 契约", () => {
  it("create 接口向后端提交定时监测计划", async () => {
    const payload: ScheduleCreate = {
      name: "每日晨间询价",
      interval_minutes: 1440,
      timezone: "Asia/Shanghai",
      targets: [
        { config_id: 10, quantities: [1, 10] },
      ],
    };
    await CncQuoteScheduleAPI.create(payload);

    expect(request).toHaveBeenCalledTimes(1);
    const callConfig = request.mock.calls[0]?.[0];
    expect(callConfig.url).toBe("/cnc/cnc_quote_schedule/create");
    expect(callConfig.method).toBe("post");
    expect(callConfig.data).toEqual(payload);
  });

  it("update 接口通过 PUT 方法更新计划配置", async () => {
    const schedId = "sched-uuid-999";
    const updatePayload: ScheduleUpdate = {
      name: "每半天询价",
      interval_minutes: 720,
    };
    await CncQuoteScheduleAPI.update(schedId, updatePayload);

    const callConfig = request.mock.calls[0]?.[0];
    expect(callConfig.url).toBe(`/cnc/cnc_quote_schedule/update/${schedId}`);
    expect(callConfig.method).toBe("put");
    expect(callConfig.data).toEqual(updatePayload);
  });

  it("pause 与 resume 接口正确调用计划启停指令", async () => {
    const schedId = "sched-uuid-123";
    await CncQuoteScheduleAPI.pause(schedId);
    expect(request.mock.calls[0]?.[0]).toEqual({
      url: `/cnc/cnc_quote_schedule/${schedId}/pause`,
      method: "post",
      signal: undefined,
    });

    await CncQuoteScheduleAPI.resume(schedId);
    expect(request.mock.calls[1]?.[0]).toEqual({
      url: `/cnc/cnc_quote_schedule/${schedId}/resume`,
      method: "post",
      signal: undefined,
    });
  });

  it("rounds 接口分页获取执行轮次历史", async () => {
    const schedId = "sched-uuid-456";
    await CncQuoteScheduleAPI.rounds(schedId, { offset: 0, limit: 20 });

    const callConfig = request.mock.calls[0]?.[0];
    expect(callConfig.url).toBe(`/cnc/cnc_quote_schedule/${schedId}/rounds`);
    expect(callConfig.method).toBe("get");
    expect(callConfig.params).toEqual({ offset: 0, limit: 20 });
  });
});
