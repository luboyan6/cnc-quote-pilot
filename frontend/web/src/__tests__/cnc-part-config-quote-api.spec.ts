import { beforeEach, describe, expect, it, vi } from "vitest";
import API from "@/api/module_cnc/cnc_part_config";
const { request } = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@utils", () => ({ request }));
beforeEach(() => request.mockReset());

describe("报价私有接口", () => {
  it("启动只发送账号和本次请求ID，不将行上的路径/参数/凭据当成上传依据", () => {
    const data = {
      account_id: 7,
      request_id: "request-1",
      file_path: "/private/file.step",
      material: "untrusted",
      password: "private",
    };
    API.startQuote(42, data);
    expect(request).toHaveBeenCalledWith({
      url: "/cnc/cnc_part_config/42/quote/runs",
      method: "post",
      data: { account_id: 7, request_id: "request-1" },
    });
  });
  it("画面经鉴权请求获取Blob，并编码运行ID，状态轮询可取消", () => {
    const controller = new AbortController();
    API.quoteFrame(42, "run/1", controller.signal);
    expect(request).toHaveBeenLastCalledWith({
      url: "/cnc/cnc_part_config/42/quote/runs/run%2F1/frame",
      method: "get",
      responseType: "blob",
      signal: controller.signal,
    });
    API.quoteStatus(42, "run/1", controller.signal);
    expect(request).toHaveBeenLastCalledWith({
      url: "/cnc/cnc_part_config/42/quote/runs/run%2F1",
      method: "get",
      signal: controller.signal,
    });
    API.resumeQuote(42, "run/1");
    expect(request).toHaveBeenLastCalledWith({
      url: "/cnc/cnc_part_config/42/quote/runs/run%2F1/resume",
      method: "post",
    });
    API.cancelQuote(42, "run/1");
    expect(request).toHaveBeenLastCalledWith({
      url: "/cnc/cnc_part_config/42/quote/runs/run%2F1",
      method: "delete",
    });
  });

  it("声明确认只发送当前声明ID和选项，不接受客户端文件或身份依据", () => {
    const decision = {
      declaration_id: "current-statement",
      choice: "not_controlled" as const,
      file_hash: "client-hash",
      actor_id: 999,
      statement: "replacement",
    };
    API.confirmQuoteDeclaration(42, "run/1", decision);
    expect(request).toHaveBeenCalledWith({
      url: "/cnc/cnc_part_config/42/quote/runs/run%2F1/declaration",
      method: "post",
      data: { declaration_id: "current-statement", choice: "not_controlled" },
    });
  });
});
