import { computed, onBeforeUnmount, onDeactivated, ref } from "vue";
import API, {
  type CncPartConfigTable,
  type CncQuoteAccount,
  type CncQuoteRun,
  type CncQuoteStatus,
} from "@/api/module_cnc/cnc_part_config";
import type { CncLoginInput } from "@/api/module_cnc/cnc_account";
import { ResultEnum } from "@/enums/api/result.enum";
import { quoteErrorMessage } from "./quoteMessages";

const TERMINAL = new Set<CncQuoteStatus>([
  "QUOTED",
  "REFERENCE_ESTIMATE",
  "PENDING_REVIEW",
  "FAILED",
  "CANCELLED",
]);
export function isQuoteTerminal(run: CncQuoteRun) {
  return TERMINAL.has(run.status);
}

function requestUuid(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  // getRandomValues also works on a LAN HTTP admin origin; Math.random does not
  // provide a suitable collision boundary for a durable mutation request ID.
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6]! & 0x0f) | 0x40;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/** A serial, actor-private run. Mutating requests are never automatically retried. */
export function useAutoQuote() {
  const visible = ref(false);
  const run = ref<CncQuoteRun>();
  const selectedRow = ref<CncPartConfigTable>();
  const accounts = ref<CncQuoteAccount[]>([]);
  const selectedAccount = ref<number>();
  const choosingAccount = ref(false);
  const loadingIds = ref(new Set<number>());
  const frameUrl = ref("");
  const error = ref("");
  const info = ref("");
  const busy = ref(false);
  const interactive = computed(
    () =>
      !error.value && !busy.value && run.value?.status === "WAITING_HUMAN" && run.value.can_input
  );
  let epoch = 0;
  let disposed = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let controller: AbortController | undefined;
  let nextInputAt = 0;
  const closing = new Map<number, Promise<void>>();
  const starting = new Set<Promise<void>>();

  function clearFrame() {
    if (frameUrl.value) URL.revokeObjectURL(frameUrl.value);
    frameUrl.value = "";
  }
  function stopPolling() {
    clearTimeout(timer);
    timer = undefined;
    controller?.abort();
    controller = undefined;
  }
  function release(current: CncQuoteRun) {
    if (isQuoteTerminal(current)) return Promise.resolve();
    const pending = API.cancelQuote(current.config_id, current.run_id)
      .then(() => undefined)
      .catch(() => {
        // A disconnected client cannot confirm cancellation; server leases still expire.
      })
      .finally(() => {
        if (closing.get(current.config_id) === pending) closing.delete(current.config_id);
      });
    closing.set(current.config_id, pending);
    return pending;
  }
  function close() {
    epoch += 1;
    stopPolling();
    const previous = run.value;
    run.value = undefined;
    selectedRow.value = undefined;
    accounts.value = [];
    selectedAccount.value = undefined;
    choosingAccount.value = false;
    visible.value = false;
    busy.value = false;
    nextInputAt = 0;
    error.value = "";
    info.value = "";
    clearFrame();
    if (previous) void release(previous);
  }
  function accept(data: CncQuoteRun, expected: CncQuoteRun) {
    if (
      data.run_id !== expected.run_id ||
      data.config_id !== expected.config_id ||
      data.account_id !== expected.account_id
    )
      throw new Error("Run mismatch");
    run.value = data;
    if (isQuoteTerminal(data)) {
      info.value = "";
      clearFrame();
    }
  }
  function schedule(generation: number) {
    if (
      generation !== epoch ||
      !visible.value ||
      error.value ||
      !run.value ||
      isQuoteTerminal(run.value)
    )
      return;
    timer = setTimeout(() => void poll(generation), 1500);
  }
  async function poll(generation: number) {
    const current = run.value;
    if (!current || generation !== epoch || !visible.value) return;
    if (busy.value) {
      schedule(generation);
      return;
    }
    const request = new AbortController();
    controller = request;
    try {
      const response = await API.quoteStatus(current.config_id, current.run_id, request.signal);
      if (generation !== epoch) return;
      if (response.data.code !== ResultEnum.SUCCESS) throw new Error("Status unavailable");
      accept(response.data.data, current);
      if (response.data.data.status === "WAITING_HUMAN" && response.data.data.can_input) {
        const frame = await API.quoteFrame(current.config_id, current.run_id, request.signal);
        if (generation !== epoch) return;
        if (frame.data.type !== "image/jpeg" || !frame.data.size) throw new Error("Invalid frame");
        const next = URL.createObjectURL(frame.data);
        clearFrame();
        frameUrl.value = next;
      } else clearFrame();
    } catch {
      if (generation !== epoch || request.signal.aborted) return;
      error.value = "报价状态连接中断，无法确认平台进度。请关闭窗口后检查运行状态。";
      clearFrame();
    } finally {
      if (controller === request) controller = undefined;
      schedule(generation);
    }
  }
  function start(generation: number, id: number, accountId: number) {
    const pending = createRun(generation, id, accountId).finally(() => starting.delete(pending));
    starting.add(pending);
    return pending;
  }
  async function createRun(generation: number, id: number, accountId: number) {
    const eligibleAccounts = new Set(accounts.value.map((account) => account.id));
    busy.value = true;
    choosingAccount.value = false;
    loadingIds.value.add(id);
    try {
      // Kept for this invocation only; no automatic POST retry on transport failure.
      const requestId = requestUuid();
      const response = await API.startQuote(id, { account_id: accountId, request_id: requestId });
      if (response.data.code !== ResultEnum.SUCCESS) throw response;
      if (
        response.data.data.config_id !== id ||
        !eligibleAccounts.has(response.data.data.account_id)
      )
        throw new Error("Run unavailable");
      if (generation !== epoch || disposed) {
        await release(response.data.data);
        return;
      }
      selectedAccount.value = response.data.data.account_id;
      if (response.data.data.account_id !== accountId && !isQuoteTerminal(response.data.data))
        info.value = "此配置已有进行中的报价，已恢复原账号的运行；如需切换账号，请先停止。";
      run.value = response.data.data;
      schedule(generation);
    } catch (failure) {
      if (generation === epoch && !disposed)
        error.value = quoteErrorMessage(
          failure,
          "无法确认报价是否已启动，请关闭窗口后检查配置和服务状态。再次打开会先检查已有运行。"
        );
    } finally {
      loadingIds.value.delete(id);
      if (generation === epoch) busy.value = false;
    }
  }
  async function open(row: CncPartConfigTable) {
    const id = row.id;
    if (disposed || id == null || row.enabled !== true || loadingIds.value.has(id)) return;
    if (visible.value && selectedRow.value?.id === id) return;
    close();
    const generation = epoch;
    visible.value = true;
    selectedRow.value = { ...row };
    loadingIds.value.add(id);
    busy.value = true;
    const request = new AbortController();
    controller = request;
    try {
      // A different configuration may use the same account. Finish the prior
      // close before admitting another run, so its owner can release the lease.
      await Promise.all([...starting, ...closing.values()]);
      if (generation !== epoch || disposed) return;
      const response = await API.quoteAccounts(id, request.signal);
      if (generation !== epoch || disposed) return;
      if (response.data.code !== ResultEnum.SUCCESS) throw response;
      accounts.value = response.data.data;
      if (!accounts.value.length) {
        error.value = "此平台没有可用账号，请先在账号管理中配置并启用账号。";
        return;
      }
      if (accounts.value.length > 1) {
        choosingAccount.value = true;
        return;
      }
      selectedAccount.value = accounts.value[0]!.id;
      await start(generation, id, selectedAccount.value);
    } catch (failure) {
      if (generation === epoch && !disposed)
        error.value = quoteErrorMessage(
          failure,
          "无法读取可用账号，请检查权限、平台配置及服务状态。"
        );
    } finally {
      if (controller === request) controller = undefined;
      loadingIds.value.delete(id);
      if (generation === epoch) busy.value = false;
    }
  }
  async function chooseAccount() {
    const id = selectedRow.value?.id;
    const accountId = selectedAccount.value;
    if (
      busy.value ||
      !choosingAccount.value ||
      id == null ||
      !accounts.value.some((a) => a.id === accountId)
    )
      return;
    await start(epoch, id, accountId!);
  }
  async function command(input?: CncLoginInput) {
    const current = run.value;
    if (!current || !interactive.value) return;
    const generation = ++epoch;
    busy.value = true;
    stopPolling();
    try {
      if (input) {
        const delay = nextInputAt - Date.now();
        if (delay > 0) await new Promise((resolve) => setTimeout(resolve, delay));
        if (generation !== epoch || disposed) return;
      }
      const response = input
        ? await API.quoteInput(current.config_id, current.run_id, input)
        : await API.resumeQuote(current.config_id, current.run_id);
      if (generation !== epoch) return;
      if (response.data.code !== ResultEnum.SUCCESS) throw new Error("Command unconfirmed");
      if (input) nextInputAt = Date.now() + 110;
      accept(response.data.data, current);
      clearFrame();
    } catch {
      if (generation === epoch) {
        error.value = "操作结果未能确认，已停止继续发送。请关闭窗口后检查运行状态。";
        clearFrame();
      }
    } finally {
      if (generation === epoch) {
        busy.value = false;
        schedule(generation);
      }
    }
  }
  onDeactivated(close);
  onBeforeUnmount(() => {
    disposed = true;
    close();
  });
  return {
    visible,
    run,
    selectedRow,
    accounts,
    selectedAccount,
    choosingAccount,
    loadingIds,
    frameUrl,
    error,
    info,
    busy,
    interactive,
    open,
    close,
    chooseAccount,
    command,
  };
}
