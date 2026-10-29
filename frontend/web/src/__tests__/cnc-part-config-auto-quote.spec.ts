import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAutoQuote } from "@/views/module_cnc/cnc_part_config/useAutoQuote";
import AutoQuoteDialog from "@/views/module_cnc/cnc_part_config/AutoQuoteDialog.vue";
import type { CncQuoteRun } from "@/api/module_cnc/cnc_part_config";

const api = vi.hoisted(() => ({
  quoteAccounts: vi.fn(),
  startQuote: vi.fn(),
  quoteStatus: vi.fn(),
  quoteFrame: vi.fn(),
  quoteInput: vi.fn(),
  resumeQuote: vi.fn(),
  confirmQuoteDeclaration: vi.fn(),
  cancelQuote: vi.fn(),
}));
vi.mock("@/api/module_cnc/cnc_part_config", () => ({ default: api }));

function run(overrides: Partial<CncQuoteRun> = {}): CncQuoteRun {
  return {
    run_id: "run-1",
    config_id: 42,
    account_id: 7,
    platform_name: "平台甲",
    masked_username: "u***@example.com",
    file_name: "part.step",
    status: "RUNNING",
    stage: "upload",
    reason: null,
    viewport: { width: 1280, height: 720 },
    expires_at: "2026-10-23T12:00:00Z",
    can_input: false,
    requested: { material: "铝合金6061", quantity: "3", surface_finish: "喷砂", tolerance: "标准" },
    result: null,
    ...overrides,
  };
}
function response<T>(data: T) {
  return { data: { code: 0, data } };
}
function declaration() {
  return {
    declaration_id: "statement-v1",
    statement: "Current platform declaration\nRead the full statement before choosing.",
    options: [
      { value: "not_controlled" as const, label: "No — this file is not controlled" },
      { value: "controlled" as const, label: "Yes — this file is controlled" },
    ],
  };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
const mounted: Array<{ unmount: () => void }> = [];
function mountQuote() {
  let quote!: ReturnType<typeof useAutoQuote>;
  mounted.push(
    mount(
      defineComponent({
        setup() {
          quote = useAutoQuote();
          return () => null;
        },
      })
    )
  );
  return quote;
}
const row = { id: 42, enabled: true, site_type: 205, name: "配置甲" };
const account = { id: 7, alias: "生产账号", masked_username: "u***@example.com" };
beforeEach(() => {
  vi.useFakeTimers();
  Object.values(api).forEach((mock) => mock.mockReset());
  api.quoteAccounts.mockResolvedValue(response([account]));
  api.startQuote.mockResolvedValue(response(run()));
  api.quoteStatus.mockResolvedValue(response(run()));
  api.quoteFrame.mockResolvedValue({ data: new Blob(["frame"], { type: "image/jpeg" }) });
  api.quoteInput.mockResolvedValue(response(run({ status: "WAITING_HUMAN", can_input: true })));
  api.resumeQuote.mockResolvedValue(response(run()));
  api.confirmQuoteDeclaration.mockResolvedValue(response(run()));
  api.cancelQuote.mockResolvedValue(response(run({ status: "CANCELLED" })));
  vi.stubGlobal("URL", {
    createObjectURL: vi.fn(() => "blob:private-quote"),
    revokeObjectURL: vi.fn(),
  });
});
afterEach(() => {
  mounted.splice(0).forEach((wrapper) => wrapper.unmount());
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("产品配置自动报价生命周期", () => {
  it("浏览器未提供randomUUID时仍生成有效请求ID，缺少安全随机源时释放loading状态", async () => {
    const quote = mountQuote();
    vi.stubGlobal("crypto", { getRandomValues: (bytes: Uint8Array) => bytes.fill(1) });
    await quote.open(row);
    expect(api.startQuote).toHaveBeenCalledWith(42, {
      account_id: 7,
      request_id: "01010101-0101-4101-8101-010101010101",
    });
    quote.close();
    vi.stubGlobal("crypto", {});
    await quote.open(row);
    expect(quote.busy.value).toBe(false);
    expect(quote.loadingIds.value.size).toBe(0);
    expect(quote.error.value).toContain("无法确认报价是否已启动");
    expect(api.startQuote).toHaveBeenCalledTimes(1);
  });

  it("不使用停用行；无账号给出配置提示，一个账号自动选择，与平台ID枚举无关", async () => {
    const quote = mountQuote();
    await quote.open({ ...row, enabled: false });
    expect(api.quoteAccounts).not.toHaveBeenCalled();
    api.quoteAccounts.mockResolvedValueOnce(response([]));
    await quote.open(row);
    expect(quote.error.value).toContain("没有可用账号");
    expect(api.startQuote).not.toHaveBeenCalled();
    quote.close();
    await quote.open(row);
    expect(api.quoteAccounts).toHaveBeenLastCalledWith(42, expect.any(AbortSignal));
    expect(api.startQuote).toHaveBeenCalledWith(42, {
      account_id: 7,
      request_id: expect.stringMatching(/^[\da-f-]{36}$/),
    });
    expect(quote.run.value?.config_id).toBe(42);
  });

  it.each([
    ["accounts", "http-error"],
    ["accounts", "rejected-envelope"],
    ["accounts", "business-code"],
    ["start", "http-error"],
    ["start", "rejected-envelope"],
    ["start", "business-code"],
  ] as const)("%s 的 %s 固定原因显示中文并停止，不自动重发", async (operation, failure) => {
    const quote = mountQuote();
    const reason =
      operation === "accounts"
        ? "PLATFORM_CONFIGURATION_INVALID"
        : "THIRD_PARTY_UPLOAD_NOT_AUTHORIZED";
    const envelope = { data: { code: -1, msg: reason, data: null } };
    const request = operation === "accounts" ? api.quoteAccounts : api.startQuote;
    if (failure === "business-code") request.mockResolvedValueOnce(envelope);
    else if (failure === "rejected-envelope") request.mockRejectedValueOnce(envelope);
    else {
      const error = new Error(reason);
      error.name = "HttpError";
      request.mockRejectedValueOnce(error);
    }

    await quote.open(row);
    expect(quote.error.value).toContain(
      operation === "accounts" ? "请检查报价平台配置" : "尚未授权上传至第三方平台"
    );
    expect(quote.error.value).not.toContain(reason);
    expect(quote.run.value).toBeUndefined();
    expect(quote.busy.value).toBe(false);
    expect(quote.loadingIds.value.size).toBe(0);
    await vi.advanceTimersByTimeAsync(6000);
    expect(api.quoteAccounts).toHaveBeenCalledTimes(1);
    expect(api.startQuote).toHaveBeenCalledTimes(operation === "start" ? 1 : 0);
    expect(api.quoteStatus).not.toHaveBeenCalled();
  });

  it.each(["accounts", "start"] as const)(
    "%s 的未知或传输异常不直接显示服务器内容，也不重发",
    async (operation) => {
      const quote = mountQuote();
      const request = operation === "accounts" ? api.quoteAccounts : api.startQuote;
      request.mockRejectedValueOnce(new Error("private token=do-not-display"));
      await quote.open(row);
      expect(quote.error.value).toContain(operation === "accounts" ? "无法读取" : "无法确认");
      expect(quote.error.value).not.toContain("private token");
      await vi.advanceTimersByTimeAsync(6000);
      expect(request).toHaveBeenCalledTimes(1);
    }
  );

  it("多个账号需明确选择，不能发送列表之外的账号", async () => {
    const quote = mountQuote();
    api.quoteAccounts.mockResolvedValueOnce(
      response([account, { ...account, id: 9, alias: "备用" }])
    );
    await quote.open(row);
    expect(quote.choosingAccount.value).toBe(true);
    expect(api.startQuote).not.toHaveBeenCalled();
    quote.selectedAccount.value = 404;
    await quote.chooseAccount();
    expect(api.startQuote).not.toHaveBeenCalled();
    quote.selectedAccount.value = 9;
    api.startQuote.mockResolvedValueOnce(response(run({ account_id: 9 })));
    await quote.chooseAccount();
    expect(api.startQuote).toHaveBeenCalledWith(42, expect.objectContaining({ account_id: 9 }));
    expect(quote.run.value?.account_id).toBe(9);
  });

  it("恢复同配置原账号的活动报价并提示，不重复发起或自动停止", async () => {
    const quote = mountQuote();
    api.quoteAccounts.mockResolvedValueOnce(
      response([account, { ...account, id: 9, masked_username: "b***@example.com" }])
    );
    await quote.open(row);
    quote.selectedAccount.value = 9;
    await quote.chooseAccount();
    expect(api.startQuote).toHaveBeenCalledTimes(1);
    expect(api.startQuote).toHaveBeenCalledWith(42, expect.objectContaining({ account_id: 9 }));
    expect(quote.selectedAccount.value).toBe(7);
    expect(quote.run.value?.account_id).toBe(7);
    expect(quote.error.value).toBe("");
    const dialog = mount(AutoQuoteDialog, {
      props: {
        visible: true,
        run: quote.run.value,
        accounts: quote.accounts.value,
        choosingAccount: false,
        frameUrl: "",
        error: quote.error.value,
        info: quote.info.value,
        busy: false,
        interactive: false,
      },
      global: { stubs: { ElDialog: { template: "<div><slot/><slot name='footer'/></div>" } } },
    });
    mounted.push(dialog);
    expect(dialog.text()).toContain(account.masked_username);
    expect(dialog.text()).not.toContain("b***@example.com");
    expect(dialog.text()).toContain("已恢复原账号的运行；如需切换账号，请先停止");
    expect(api.cancelQuote).not.toHaveBeenCalled();
    api.quoteStatus.mockResolvedValueOnce(response(run({ status: "QUOTED", stage: "complete" })));
    await vi.advanceTimersByTimeAsync(1500);
    expect(quote.info.value).toBe("");
  });

  it("不接纳可用账号列表以外的返回运行", async () => {
    const quote = mountQuote();
    api.startQuote.mockResolvedValueOnce(response(run({ account_id: 404 })));
    await quote.open(row);
    expect(quote.run.value).toBeUndefined();
    expect(quote.error.value).toContain("无法确认报价是否已启动");
    expect(api.cancelQuote).not.toHaveBeenCalled();
  });

  it("重复点击或重开活动行保留同一运行，不重复POST、不取消活动运行", async () => {
    const quote = mountQuote();
    const pending = deferred<ReturnType<typeof response<CncQuoteRun>>>();
    api.startQuote.mockReturnValueOnce(pending.promise);
    const opening = quote.open(row);
    await flushPromises();
    await quote.open(row);
    expect(api.startQuote).toHaveBeenCalledTimes(1);
    pending.resolve(response(run()));
    await opening;
    await quote.open(row);
    expect(api.startQuote).toHaveBeenCalledTimes(1);
    expect(api.cancelQuote).not.toHaveBeenCalled();
  });

  it("关闭后迟到的创建响应会停止服务器运行", async () => {
    const quote = mountQuote();
    const pending = deferred<ReturnType<typeof response<CncQuoteRun>>>();
    api.startQuote.mockReturnValueOnce(pending.promise);
    const opening = quote.open(row);
    await flushPromises();
    quote.close();
    pending.resolve(response(run()));
    await opening;
    expect(quote.visible.value).toBe(false);
    expect(quote.run.value).toBeUndefined();
    expect(api.cancelQuote).toHaveBeenCalledWith(42, "run-1");
  });

  it("重新打开前等待取消回执，后续活动运行不会被旧关闭取消", async () => {
    const quote = mountQuote();
    await quote.open(row);
    const cancelling = deferred<ReturnType<typeof response<CncQuoteRun>>>();
    api.cancelQuote.mockReturnValueOnce(cancelling.promise);
    quote.close();
    const reopening = quote.open(row);
    await flushPromises();
    expect(api.startQuote).toHaveBeenCalledTimes(1);
    cancelling.resolve(response(run({ status: "CANCELLED" })));
    api.startQuote.mockResolvedValueOnce(response(run({ run_id: "run-2" })));
    await reopening;
    expect(quote.run.value?.run_id).toBe("run-2");
    expect(api.cancelQuote).toHaveBeenCalledTimes(1);
  });

  it("串行轮询；切换配置后拒绝迟到画面并释放URL", async () => {
    const quote = mountQuote();
    await quote.open(row);
    api.quoteStatus.mockResolvedValue(response(run({ status: "WAITING_HUMAN", can_input: true })));
    await vi.advanceTimersByTimeAsync(1500);
    expect(quote.frameUrl.value).toBe("blob:private-quote");
    const pending = deferred<{ data: Blob }>();
    api.quoteFrame.mockReturnValueOnce(pending.promise);
    await vi.advanceTimersByTimeAsync(1500);
    await vi.advanceTimersByTimeAsync(6000);
    expect(api.quoteStatus).toHaveBeenCalledTimes(2);
    api.startQuote.mockResolvedValueOnce(response(run({ run_id: "run-2", config_id: 99 })));
    await quote.open({ ...row, id: 99 });
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:private-quote");
    pending.resolve({ data: new Blob(["old"], { type: "image/jpeg" }) });
    await flushPromises();
    expect(quote.run.value?.config_id).toBe(99);
    expect(quote.frameUrl.value).toBe("");
  });

  it("切换配置时等待旧运行停止，避免同一账号仍被旧配置占用", async () => {
    const quote = mountQuote();
    await quote.open(row);
    const cancelling = deferred<ReturnType<typeof response<CncQuoteRun>>>();
    api.cancelQuote.mockReturnValueOnce(cancelling.promise);
    api.startQuote.mockResolvedValueOnce(response(run({ run_id: "run-2", config_id: 99 })));
    const switching = quote.open({ ...row, id: 99 });
    await flushPromises();
    expect(api.cancelQuote).toHaveBeenCalledWith(42, "run-1");
    expect(api.startQuote).toHaveBeenCalledTimes(1);
    cancelling.resolve(response(run({ status: "CANCELLED" })));
    await switching;
    expect(api.startQuote).toHaveBeenCalledTimes(2);
    expect(quote.run.value?.config_id).toBe(99);
  });

  it("切换配置时等待迟到的创建及停止回执后才使用同一账号", async () => {
    const quote = mountQuote();
    const creating = deferred<ReturnType<typeof response<CncQuoteRun>>>();
    const cancelling = deferred<ReturnType<typeof response<CncQuoteRun>>>();
    api.startQuote.mockReturnValueOnce(creating.promise);
    api.cancelQuote.mockReturnValueOnce(cancelling.promise);
    const opening = quote.open(row);
    await flushPromises();
    api.startQuote.mockResolvedValueOnce(response(run({ run_id: "run-2", config_id: 99 })));
    const switching = quote.open({ ...row, id: 99 });
    await flushPromises();
    expect(api.startQuote).toHaveBeenCalledTimes(1);
    creating.resolve(response(run()));
    await flushPromises();
    expect(api.cancelQuote).toHaveBeenCalledWith(42, "run-1");
    expect(api.startQuote).toHaveBeenCalledTimes(1);
    cancelling.resolve(response(run({ status: "CANCELLED" })));
    await Promise.all([opening, switching]);
    expect(api.startQuote).toHaveBeenCalledTimes(2);
    expect(quote.run.value?.config_id).toBe(99);
  });

  it("自动阶段拒绝输入；只有可交互的人工阶段允许验证并继续，旧轮询不能覆盖新状态", async () => {
    const quote = mountQuote();
    await quote.open(row);
    await quote.command({ kind: "key", key: "Enter" });
    expect(api.quoteInput).not.toHaveBeenCalled();
    api.quoteStatus.mockResolvedValueOnce(
      response(run({ status: "WAITING_HUMAN", can_input: true }))
    );
    await vi.advanceTimersByTimeAsync(1500);
    expect(quote.interactive.value).toBe(true);
    const pending = deferred<ReturnType<typeof response<CncQuoteRun>>>();
    api.quoteStatus.mockReturnValueOnce(pending.promise);
    await vi.advanceTimersByTimeAsync(1500);
    await quote.command();
    expect(api.resumeQuote).toHaveBeenCalledWith(42, "run-1");
    pending.resolve(response(run({ status: "WAITING_HUMAN", can_input: true })));
    await flushPromises();
    expect(quote.run.value?.status).toBe("RUNNING");
    expect(quote.interactive.value).toBe(false);
  });

  it("人工阶段未开放输入时保留原因，不请求不存在的画面", async () => {
    const quote = mountQuote();
    await quote.open(row);
    api.quoteStatus.mockResolvedValue(
      response(run({ status: "WAITING_HUMAN", can_input: false, reason: "MUTATION_UNCONFIRMED" }))
    );
    await vi.advanceTimersByTimeAsync(3000);
    expect(api.quoteFrame).not.toHaveBeenCalled();
    expect(quote.run.value?.reason).toBe("MUTATION_UNCONFIRMED");
    expect(quote.error.value).toBe("");
    await quote.command();
    expect(api.resumeQuote).not.toHaveBeenCalled();
  });

  it("出口声明只接受当前声明的可选值，确认期间不重复发送且不能以通用输入绕过", async () => {
    const quote = mountQuote();
    const snapshot = run({
      status: "WAITING_HUMAN",
      can_input: true,
      export_declaration: { ...declaration(), options: [declaration().options[0]!] },
    });
    api.startQuote.mockResolvedValueOnce(response(snapshot));
    api.quoteStatus.mockResolvedValue(response(snapshot));
    await quote.open(row);
    await vi.advanceTimersByTimeAsync(1500);
    expect(api.quoteFrame).not.toHaveBeenCalled();
    expect(quote.interactive.value).toBe(false);
    await quote.command();
    await quote.command({ kind: "key", key: "Enter" });
    expect(api.resumeQuote).not.toHaveBeenCalled();
    expect(api.quoteInput).not.toHaveBeenCalled();
    await quote.confirmDeclaration({ declaration_id: "old-statement", choice: "not_controlled" });
    await quote.confirmDeclaration({ declaration_id: "statement-v1", choice: "controlled" });
    expect(api.confirmQuoteDeclaration).not.toHaveBeenCalled();

    const pending = deferred<ReturnType<typeof response<CncQuoteRun>>>();
    api.confirmQuoteDeclaration.mockReturnValueOnce(pending.promise);
    const decision = { declaration_id: "statement-v1", choice: "not_controlled" as const };
    const confirming = quote.confirmDeclaration(decision);
    await quote.confirmDeclaration(decision);
    expect(quote.busy.value).toBe(true);
    expect(api.confirmQuoteDeclaration).toHaveBeenCalledTimes(1);
    expect(api.confirmQuoteDeclaration).toHaveBeenCalledWith(42, "run-1", decision);
    pending.resolve(response(run()));
    await confirming;
    expect(quote.run.value?.status).toBe("RUNNING");
    expect(quote.busy.value).toBe(false);
  });

  it("声明确认使旧轮询失效，关闭后等待确认请求结算再启动下一配置", async () => {
    const quote = mountQuote();
    api.startQuote.mockResolvedValueOnce(
      response(run({ status: "WAITING_HUMAN", export_declaration: declaration() }))
    );
    await quote.open(row);
    const oldRead = deferred<ReturnType<typeof response<CncQuoteRun>>>();
    api.quoteStatus.mockReturnValueOnce(oldRead.promise);
    await vi.advanceTimersByTimeAsync(1500);
    const pending = deferred<ReturnType<typeof response<CncQuoteRun>>>();
    api.confirmQuoteDeclaration.mockReturnValueOnce(pending.promise);
    const confirming = quote.confirmDeclaration({
      declaration_id: "statement-v1",
      choice: "not_controlled",
    });
    oldRead.resolve(response(run({ status: "FAILED" })));
    await flushPromises();
    expect(quote.run.value?.status).toBe("WAITING_HUMAN");
    api.startQuote.mockResolvedValueOnce(response(run({ run_id: "run-2", config_id: 99 })));
    const switching = quote.open({ ...row, id: 99 });
    await flushPromises();
    expect(api.cancelQuote).toHaveBeenCalledWith(42, "run-1");
    expect(api.startQuote).toHaveBeenCalledTimes(1);
    pending.resolve(response(run()));
    await Promise.all([confirming, switching]);
    expect(quote.run.value?.run_id).toBe("run-2");
    expect(quote.run.value?.config_id).toBe(99);
    expect(quote.error.value).toBe("");
  });

  it("声明操作结果不明确时停止且不自动重试，不显示未知服务端内容", async () => {
    const quote = mountQuote();
    api.startQuote.mockResolvedValueOnce(
      response(run({ status: "WAITING_HUMAN", export_declaration: declaration() }))
    );
    await quote.open(row);
    api.confirmQuoteDeclaration.mockRejectedValueOnce(new Error("private token=hidden"));
    const decision = { declaration_id: "statement-v1", choice: "not_controlled" as const };
    await quote.confirmDeclaration(decision);
    await quote.confirmDeclaration(decision);
    await vi.advanceTimersByTimeAsync(6000);
    expect(api.confirmQuoteDeclaration).toHaveBeenCalledTimes(1);
    expect(api.quoteStatus).not.toHaveBeenCalled();
    expect(quote.error.value).toContain("未重复发送");
    expect(quote.error.value).not.toContain("private token");
    expect(quote.busy.value).toBe(false);
  });

  it("输入/继续结果不明确时不自动重试；网络错误停止轮询并清理画面", async () => {
    const quote = mountQuote();
    api.startQuote.mockResolvedValueOnce(
      response(run({ status: "WAITING_HUMAN", can_input: true }))
    );
    await quote.open(row);
    api.quoteInput.mockRejectedValueOnce(new Error("timeout"));
    await quote.command({ kind: "text", text: "private challenge" });
    await vi.advanceTimersByTimeAsync(6000);
    expect(api.quoteInput).toHaveBeenCalledTimes(1);
    expect(api.quoteStatus).not.toHaveBeenCalled();
    expect(quote.error.value).toContain("未能确认");
    quote.close();
    await quote.open(row);
    api.quoteStatus.mockRejectedValueOnce(new Error("transport"));
    await vi.advanceTimersByTimeAsync(6000);
    expect(api.quoteStatus).toHaveBeenCalledTimes(1);
    expect(quote.frameUrl.value).toBe("");
  });

  it("输入按服务端限制限速，离开页面后停止待发输入和释放运行", async () => {
    const quote = mountQuote();
    api.startQuote.mockResolvedValueOnce(
      response(run({ status: "WAITING_HUMAN", can_input: true }))
    );
    await quote.open(row);
    await quote.command({ kind: "key", key: "Tab" });
    const second = quote.command({ kind: "key", key: "Enter" });
    expect(api.quoteInput).toHaveBeenCalledTimes(1);
    mounted.pop()?.unmount();
    await vi.advanceTimersByTimeAsync(150);
    await second;
    expect(api.quoteInput).toHaveBeenCalledTimes(1);
    expect(api.cancelQuote).toHaveBeenCalledWith(42, "run-1");
  });

  it("终态停止轮询，关闭只保留结果，不取消已完成报价", async () => {
    const quote = mountQuote();
    await quote.open(row);
    api.quoteStatus.mockResolvedValueOnce(response(run({ status: "QUOTED", stage: "complete" })));
    await vi.advanceTimersByTimeAsync(9000);
    expect(api.quoteStatus).toHaveBeenCalledTimes(1);
    quote.close();
    expect(api.cancelQuote).not.toHaveBeenCalled();
  });
});

describe("报价结果弹窗", () => {
  function mountDialog(snapshot: CncQuoteRun) {
    const wrapper = mount(AutoQuoteDialog, {
      props: {
        visible: true,
        run: snapshot,
        accounts: [],
        choosingAccount: false,
        frameUrl: "",
        error: "",
        busy: false,
        interactive: false,
      },
      global: {
        stubs: {
          ElDialog: { template: "<div><slot/><slot name='footer'/></div>" },
          ElTable: { template: "<div><slot/></div>" },
          ElTableColumn: true,
        },
      },
    });
    mounted.push(wrapper);
    return wrapper;
  }
  it("十进制金额不经浮点换算，区分单价/估价/审核及未知税运与交期", async () => {
    const snapshot = run({
      status: "REFERENCE_ESTIMATE",
      result: {
        status: "REFERENCE_ESTIMATE",
        amount: "123456.78901234",
        currency: "USD",
        price_scope: "unit",
        lead_time: { text: "Ships in 5 business days" },
        effective: {
          material: "铝合金6061",
          quantity: "3",
          surface_finish: "喷砂",
          tolerance: "标准",
        },
        priced_at: null,
        observed_at: "2026-10-23T10:00:00Z",
        tax_included: null,
        shipping_included: null,
      },
    });
    const wrapper = mountDialog(snapshot);
    expect(wrapper.text()).toContain("参考估价");
    expect(wrapper.text()).not.toContain("报价成功");
    expect(wrapper.text()).toContain("123456.78901234");
    expect(wrapper.text()).toContain("/ 件");
    expect(wrapper.text()).toContain("Ships in 5 business days");
    expect(wrapper.text()).toContain("平台未明确");
    await wrapper.setProps({
      run: run({
        status: "PENDING_REVIEW",
        result: {
          ...snapshot.result!,
          status: "PENDING_REVIEW",
          amount: null,
          currency: null,
          lead_time: { days: 3 },
        },
      }),
    });
    expect(wrapper.text()).toContain("等待平台人工审核");
    expect(wrapper.text()).toContain("平台尚未返回金额");
    expect(wrapper.text()).toContain("平台未提供可确认的交期原文");
    expect(wrapper.text()).not.toContain('{"days":3}');
  });

  it("仅人工阶段显示受控画面，未启用人工输入时按钮关闭", async () => {
    const wrapper = mountDialog(run());
    expect(wrapper.find(".browser-frame").exists()).toBe(false);
    await wrapper.setProps({
      run: run({ status: "WAITING_HUMAN", can_input: false, reason: "MUTATION_UNCONFIRMED" }),
    });
    expect(wrapper.text()).toContain("回执尚未确认");
    const resume = wrapper.findAll("button").find((button) => button.text() === "验证并继续");
    expect(resume?.attributes("disabled")).toBeDefined();
    expect(wrapper.find(".frame-placeholder").attributes("aria-busy")).toBe("false");
  });

  it("声明显示完整文本和本次文件，不预选、不开放通用输入，并在声明或运行改变时重置选择", async () => {
    const snapshot = run({
      status: "WAITING_HUMAN",
      reason: "QUOTE_EXPORT_DECLARATION_REQUIRED",
      export_declaration: declaration(),
    });
    const wrapper = mountDialog(snapshot);
    expect(wrapper.text()).toContain(declaration().statement);
    expect(wrapper.get(".declaration-file").text()).toBe("part.step");
    expect(wrapper.find(".frame-placeholder").exists()).toBe(false);
    expect(wrapper.findAll("button").some((button) => button.text() === "验证并继续")).toBe(false);
    expect(
      wrapper
        .findAll<HTMLInputElement>('input[type="radio"]')
        .every((radio) => !radio.element.checked)
    ).toBe(true);
    const confirm = () =>
      wrapper.findAll("button").find((button) => button.text() === "确认声明并继续")!;
    expect(confirm().attributes("disabled")).toBeDefined();
    await wrapper.get('input[type="radio"][value="not_controlled"]').setValue(true);
    expect(confirm().attributes("disabled")).toBeUndefined();
    await wrapper.setProps({ run: { ...snapshot } });
    expect(confirm().attributes("disabled")).toBeUndefined();
    await confirm().trigger("click");
    expect(wrapper.emitted("declaration")).toEqual([
      [{ declaration_id: "statement-v1", choice: "not_controlled" }],
    ]);

    await wrapper.setProps({
      run: {
        ...snapshot,
        export_declaration: { ...declaration(), declaration_id: "statement-v2" },
      },
    });
    expect(confirm().attributes("disabled")).toBeDefined();
    await wrapper.get('input[type="radio"][value="controlled"]').setValue(true);
    await wrapper.setProps({ run: { ...snapshot, run_id: "run-2" } });
    expect(confirm().attributes("disabled")).toBeDefined();
  });

  it("声明文本作为纯文本显示，忙碌或错误时禁止确认，非登录阶段使用当前阶段提示", async () => {
    const wrapper = mountDialog(
      run({
        status: "WAITING_HUMAN",
        export_declaration: { ...declaration(), statement: "<img src=x onerror=alert(1)>" },
      })
    );
    expect(wrapper.get(".declaration-statement").text()).toBe("<img src=x onerror=alert(1)>");
    expect(wrapper.find(".declaration-statement img").exists()).toBe(false);
    await wrapper.get('input[type="radio"][value="not_controlled"]').setValue(true);
    await wrapper.setProps({ busy: true });
    const confirm = () =>
      wrapper.findAll("button").find((button) => button.text() === "确认声明并继续")!;
    expect(confirm().attributes("disabled")).toBeDefined();
    await wrapper.setProps({ busy: false, error: "声明操作回执尚未确认" });
    expect(confirm().attributes("disabled")).toBeDefined();
    await wrapper.setProps({
      error: "",
      run: run({ status: "WAITING_HUMAN", stage: "configure", can_input: true }),
    });
    expect(wrapper.get(".quote-help").text()).toContain("完成当前阶段的处理");
    expect(wrapper.get(".quote-help").text()).not.toContain("完成登录");
  });

  it("实际执行器原因显示明确中文，未知原因不会直接展示服务端内容", async () => {
    const wrapper = mountDialog(run({ status: "FAILED", reason: "parameters_mismatch" }));
    expect(wrapper.get(".el-alert").text()).toContain("平台回读参数与本次配置不一致");
    await wrapper.setProps({
      run: run({ status: "FAILED", reason: "PROVIDER_AUTOMATION_UNVERIFIED" }),
    });
    expect(wrapper.get(".el-alert").text()).toContain("自动上传和报价尚未通过验证");
    await wrapper.setProps({
      run: run({ status: "FAILED", reason: "JLC_EFFECTIVE_PARAMETERS_UNVERIFIED" }),
    });
    expect(wrapper.get(".el-alert").text()).toContain("嘉立创加工参数回读尚未完成验证");
    await wrapper.setProps({ run: run({ status: "FAILED", reason: "mutation_uncertain" }) });
    expect(wrapper.get(".el-alert").text()).toContain("回执尚未确认");
    await wrapper.setProps({ run: run({ status: "FAILED", reason: "private server content" }) });
    expect(wrapper.get(".el-alert").text()).toContain("本次报价未完成");
    expect(wrapper.text()).not.toContain("private server content");
  });

  it.each([
    ["QUOTE_PRIOR_MUTATION_UNCONFIRMED_NO_RETRY", "请先核对原运行"],
    ["QUOTE_CONFIGURATION_RECONCILING", "未重复点击保存"],
    ["QUOTE_CONFIGURATION_UNCONFIRMED_NO_RETRY", "未重复保存"],
  ])("参数保存原因 %s 显示可操作中文说明", (reason, expected) => {
    const wrapper = mountDialog(run({ status: "RUNNING", stage: "configure", reason }));
    expect(wrapper.get(".el-alert").text()).toContain(expected);
    expect(wrapper.text()).not.toContain(reason);
  });

  it.each(["constructor", "__proto__"])("未知原因 %s 使用固定兜底文案", (reason) => {
    const wrapper = mountDialog(run({ status: "FAILED", reason }));
    expect(wrapper.get(".el-alert").text()).toContain("本次报价未完成");
    expect(wrapper.text()).not.toContain(reason);
  });
});
