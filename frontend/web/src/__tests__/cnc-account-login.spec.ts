import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAccountLogin } from "@/views/module_cnc/cnc_account/useAccountLogin";
import AccountLoginDialog from "@/views/module_cnc/cnc_account/AccountLoginDialog.vue";
import type { CncLoginSession } from "@/api/module_cnc/cnc_account";

const api = vi.hoisted(() => ({
  login: vi.fn(),
  loginStatus: vi.fn(),
  loginFrame: vi.fn(),
  loginInput: vi.fn(),
  verifyLogin: vi.fn(),
  closeLogin: vi.fn(),
}));
vi.mock("@/api/module_cnc/cnc_account", () => ({ default: api }));

function state(overrides: Partial<CncLoginSession> = {}): CncLoginSession {
  return {
    session_id: "session-1",
    account_id: 1,
    platform_name: "平台甲",
    username: "u***@test.example",
    status: "READY",
    reason: null,
    reused: false,
    viewport: { width: 1280, height: 720 },
    expires_at: "2026-10-22T12:00:00Z",
    ...overrides,
  };
}
function response(data: CncLoginSession) {
  return { data: { code: 0, data } };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
const mounted: Array<{ unmount: () => void }> = [];
function mountLogin() {
  let login!: ReturnType<typeof useAccountLogin>;
  mounted.push(
    mount(
      defineComponent({
        setup() {
          login = useAccountLogin();
          return () => null;
        },
      })
    )
  );
  return login;
}
beforeEach(() => {
  vi.useFakeTimers();
  Object.values(api).forEach((mock) => mock.mockReset());
  api.login.mockResolvedValue(response(state()));
  api.loginStatus.mockResolvedValue(response(state()));
  api.loginFrame.mockResolvedValue({ data: new Blob(["frame"], { type: "image/jpeg" }) });
  api.loginInput.mockResolvedValue(response(state()));
  api.verifyLogin.mockResolvedValue(response(state()));
  api.closeLogin.mockResolvedValue({ data: { code: 0 } });
  vi.stubGlobal("URL", {
    createObjectURL: vi.fn(() => "blob:private-frame"),
    revokeObjectURL: vi.fn(),
  });
});
afterEach(() => {
  mounted.splice(0).forEach((wrapper) => wrapper.unmount());
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("账号受控浏览器会话", () => {
  it("阻止停用账号和重复点击，显示服务端确认的复用状态", async () => {
    const login = mountLogin();
    await login.open({ id: 2, enabled: false });
    expect(api.login).not.toHaveBeenCalled();
    const pending = deferred<ReturnType<typeof response>>();
    api.login.mockReturnValue(pending.promise);
    const opening = login.open({ id: 1, enabled: true });
    expect(login.loadingIds.value.has(1)).toBe(true);
    await login.open({ id: 1, enabled: true });
    expect(api.login).toHaveBeenCalledTimes(1);
    pending.resolve(response(state({ reused: true })));
    await opening;
    expect(login.session.value?.reused).toBe(true);
    expect(login.loadingIds.value.size).toBe(0);
    await login.open({ id: 1, enabled: true });
    expect(api.login).toHaveBeenCalledTimes(1);
  });

  it("HTTP 失败不显示已登录，人工挑战需服务端验证才能 READY", async () => {
    const login = mountLogin();
    api.login.mockRejectedValueOnce(new Error("transport"));
    await login.open({ id: 1, enabled: true });
    expect(login.session.value).toBeUndefined();
    expect(login.error.value).toBeTruthy();
    api.login.mockResolvedValueOnce(response(state({ status: "WAITING_HUMAN" })));
    await login.open({ id: 1, enabled: true });
    expect(login.session.value?.status).toBe("WAITING_HUMAN");
    await login.command();
    expect(api.verifyLogin).toHaveBeenCalledWith(1, "session-1");
    expect(login.session.value?.status).toBe("READY");
  });

  it("串行轮询，连接失败立即清空画面并停止轮询", async () => {
    const login = mountLogin();
    await login.open({ id: 1, enabled: true });
    const pending = deferred<{ data: Blob }>();
    api.loginFrame.mockReturnValueOnce(pending.promise);
    await vi.advanceTimersByTimeAsync(1500);
    await vi.advanceTimersByTimeAsync(6000);
    expect(api.loginStatus).toHaveBeenCalledTimes(1);
    pending.resolve({ data: new Blob(["frame"], { type: "image/jpeg" }) });
    await flushPromises();
    expect(login.frameUrl.value).toBe("blob:private-frame");
    api.loginStatus.mockRejectedValueOnce(new Error("expired"));
    await vi.advanceTimersByTimeAsync(1500);
    expect(login.frameUrl.value).toBe("");
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:private-frame");
    await vi.advanceTimersByTimeAsync(6000);
    expect(api.loginStatus).toHaveBeenCalledTimes(2);
  });

  it("切换账号和关闭时拒绝迟到画面；关闭迟到创建的会话", async () => {
    const login = mountLogin();
    await login.open({ id: 1, enabled: true });
    const oldFrame = deferred<{ data: Blob }>();
    api.loginFrame.mockReturnValueOnce(oldFrame.promise);
    await vi.advanceTimersByTimeAsync(1500);
    api.login.mockResolvedValueOnce(response(state({ account_id: 2, session_id: "session-2" })));
    await login.open({ id: 2, enabled: true });
    oldFrame.resolve({ data: new Blob(["old"], { type: "image/jpeg" }) });
    await flushPromises();
    expect(login.frameUrl.value).toBe("");
    expect(api.closeLogin).toHaveBeenCalledWith(1, "session-1");
    login.close();
    const pending = deferred<ReturnType<typeof response>>();
    api.login.mockReturnValueOnce(pending.promise);
    const opening = login.open({ id: 1, enabled: true });
    // Wait until the reopen barrier has passed and the create request is in
    // flight; closing before dispatch intentionally creates nothing to release.
    await flushPromises();
    login.close();
    pending.resolve(response(state()));
    await opening;
    expect(login.visible.value).toBe(false);
    expect(login.session.value).toBeUndefined();
    expect(api.closeLogin).toHaveBeenLastCalledWith(1, "session-1");
  });

  it("人工操作阻止旧轮询覆盖新状态，卸载后关闭会话", async () => {
    const login = mountLogin();
    await login.open({ id: 1, enabled: true });
    const pending = deferred<ReturnType<typeof response>>();
    api.loginStatus.mockReturnValueOnce(pending.promise);
    await vi.advanceTimersByTimeAsync(1500);
    await login.command({ kind: "key", key: "Enter" });
    pending.resolve(response(state({ status: "WAITING_HUMAN" })));
    await flushPromises();
    expect(login.session.value?.status).toBe("READY");
    expect(api.loginInput).toHaveBeenCalledWith(1, "session-1", { kind: "key", key: "Enter" });
    mounted.pop()?.unmount();
    expect(api.closeLogin).toHaveBeenCalledWith(1, "session-1");
    expect(login.frameUrl.value).toBe("");
  });

  it("快速连续输入遵守服务端频率限制，关闭后不发送等待中的输入", async () => {
    const login = mountLogin();
    let lastAccepted = Number.NEGATIVE_INFINITY;
    api.loginInput.mockImplementation(async () => {
      if (Date.now() - lastAccepted < 100) throw new Error("INPUT_RATE_LIMITED");
      lastAccepted = Date.now();
      return response(state());
    });
    await login.open({ id: 1, enabled: true });
    await login.command({ kind: "scroll", delta_x: 0, delta_y: 100 });
    const next = login.command({ kind: "key", key: "Tab" });
    await vi.advanceTimersByTimeAsync(150);
    await next;
    expect(login.error.value).toBe("");
    expect(login.interactive.value).toBe(true);
    expect(api.loginInput).toHaveBeenCalledTimes(2);
    const cancelled = login.command({ kind: "text", text: "synthetic private input" });
    login.close();
    await vi.advanceTimersByTimeAsync(150);
    await cancelled;
    expect(api.loginInput).toHaveBeenCalledTimes(2);
  });
});

describe("受控浏览器输入", () => {
  it("已核验状态不提示重复登录，关闭状态明确区分空闲和会话到期", async () => {
    const wrapper = mount(AccountLoginDialog, {
      props: {
        visible: true,
        session: state({ reason: "LOGIN_VERIFIED" }),
        platformName: "平台甲",
        frameUrl: "",
        error: "",
        busy: false,
        interactive: true,
      },
      global: { stubs: { ElDialog: { template: "<div><slot /><slot name='footer'/></div>" } } },
    });
    mounted.push(wrapper);
    expect(wrapper.find(".el-alert").exists()).toBe(false);
    expect(wrapper.text()).toContain("已核验登录");
    await wrapper.setProps({
      session: state({ status: "CLOSED", reason: "SESSION_IDLE_EXPIRED" }),
      interactive: false,
    });
    expect(wrapper.get(".el-alert").text()).toContain("长时间未操作已关闭");
    await wrapper.setProps({
      session: state({ status: "CLOSED", reason: "SESSION_LIFETIME_EXPIRED" }),
    });
    expect(wrapper.get(".el-alert").text()).toContain("会话已过期");
  });

  it("缩放坐标映射至固定 viewport，并提供键盘、文本及滚动操作", async () => {
    const wrapper = mount(AccountLoginDialog, {
      props: {
        visible: true,
        session: state(),
        platformName: "平台甲",
        frameUrl: "blob:frame",
        error: "",
        busy: false,
        interactive: true,
      },
      global: { stubs: { ElDialog: { template: "<div><slot /><slot name='footer'/></div>" } } },
    });
    mounted.push(wrapper);
    const image = wrapper.get("img");
    vi.spyOn(image.element, "getBoundingClientRect").mockReturnValue({
      left: 10,
      top: 20,
      width: 640,
      height: 360,
    } as DOMRect);
    await image.trigger("click", { clientX: 330, clientY: 200 });
    expect(wrapper.emitted("input")?.[0]).toEqual([{ kind: "click", x: 640, y: 360 }]);
    await image.trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("input")?.[1]).toEqual([{ kind: "key", key: "Enter" }]);
    await image.trigger("wheel", { deltaY: 120, deltaX: 0 });
    expect(wrapper.emitted("input")?.[2]).toEqual([{ kind: "scroll", delta_x: 0, delta_y: 120 }]);
    await wrapper.get("input").setValue("123456");
    await wrapper.get("input").trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("input")?.[3]).toEqual([{ kind: "text", text: "123456" }]);
    expect((wrapper.get("input").element as HTMLInputElement).value).toBe("");
    const verify = wrapper.findAll("button").find((button) => button.text() === "验证登录");
    await verify?.trigger("click");
    expect(wrapper.emitted("verify")).toHaveLength(1);
    await wrapper.setProps({ interactive: false, session: state({ status: "FAILED" }) });
    await image.trigger("click", { clientX: 330, clientY: 200 });
    expect(wrapper.emitted("input")).toHaveLength(4);
  });
});
