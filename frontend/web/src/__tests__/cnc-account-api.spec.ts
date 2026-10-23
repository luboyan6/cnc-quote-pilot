import { beforeEach, describe, expect, it, vi } from "vitest";
import CncAccountAPI, { type CncAccountForm } from "@/api/module_cnc/cnc_account";

const { request } = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@utils", () => ({ request }));
beforeEach(() => request.mockReset());

describe("CNC 账号 API", () => {
  it("修改密码留空时不发送密码，排除详情合入表单的内部字段", () => {
    const body = {
      platform_id: 2,
      username: "account",
      password: "",
      enabled: true,
      session_status: "VALID",
      session_ciphertext: "private-state",
      credential_ciphertext: "private-secret",
      lease_token: "private-lease",
    } as CncAccountForm;
    CncAccountAPI.updateCncAccount(8, body);
    const config = request.mock.calls[0]?.[0];
    if (!config) throw new Error("Expected update request");
    expect(config.url).toBe("/cnc/cnc_account/update/8");
    expect(config.data.password).toBeUndefined();
    expect(config.data).not.toHaveProperty("session_ciphertext");
    expect(config.data).not.toHaveProperty("credential_ciphertext");
    expect(config.data).not.toHaveProperty("session_status");
    expect(config.data).not.toHaveProperty("lease_token");
    expect(config.data.platform_id).toBe(2);
  });

  it("新建允许写入密码，登录请求只传账号 ID，画面通过鉴权请求获取 Blob", () => {
    CncAccountAPI.createCncAccount({ platform_id: 2, password: "new-password" });
    expect(request.mock.calls[0]?.[0].data.password).toBe("new-password");
    CncAccountAPI.login(8);
    expect(request.mock.calls[1]?.[0]).toEqual({ url: "/cnc/cnc_account/login/8", method: "post" });
    const controller = new AbortController();
    CncAccountAPI.loginFrame(8, "s/1", controller.signal);
    expect(request.mock.calls[2]?.[0]).toEqual({
      url: "/cnc/cnc_account/login/8/sessions/s%2F1/frame",
      method: "get",
      responseType: "blob",
      signal: controller.signal,
    });
  });
});
