import { computed, onBeforeUnmount, onDeactivated, ref } from "vue";
import CncAccountAPI, {
  type CncAccountTable,
  type CncLoginInput,
  type CncLoginSession,
} from "@/api/module_cnc/cnc_account";
import { ResultEnum } from "@/enums/api/result.enum";

const POLL_INTERVAL = 1500;

/** One visible account, one serial poll; late responses never replace another account's frame. */
export function useAccountLogin() {
  const visible = ref(false);
  const session = ref<CncLoginSession>();
  const openingAccount = ref<number>();
  const loadingIds = ref(new Set<number>());
  const frameUrl = ref("");
  const error = ref("");
  const busy = ref(false);
  const selectedPlatform = ref("");
  let generation = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let pollController: AbortController | undefined;
  let disposed = false;
  let nextInputAt = 0;
  const closingAccounts = new Map<number, Promise<void>>();

  const interactive = computed(
    () =>
      !error.value &&
      !busy.value &&
      (session.value?.status === "READY" || session.value?.status === "WAITING_HUMAN")
  );

  function clearFrame() {
    if (frameUrl.value) URL.revokeObjectURL(frameUrl.value);
    frameUrl.value = "";
  }

  function stopPolling() {
    clearTimeout(timer);
    timer = undefined;
    pollController?.abort();
    pollController = undefined;
  }

  function accept(data: CncLoginSession, expected: CncLoginSession) {
    if (data.session_id !== expected.session_id || data.account_id !== expected.account_id) {
      throw new Error("Session mismatch");
    }
    session.value = data;
    if (data.status !== "READY" && data.status !== "WAITING_HUMAN") clearFrame();
  }

  function release(data: CncLoginSession) {
    const closing = CncAccountAPI.closeLogin(data.account_id, data.session_id)
      .then(() => undefined)
      .catch(() => {
        // Server idle/lifetime expiry also releases the browser if this best-effort close fails.
      })
      .finally(() => {
        if (closingAccounts.get(data.account_id) === closing)
          closingAccounts.delete(data.account_id);
      });
    closingAccounts.set(data.account_id, closing);
    return closing;
  }

  function close() {
    generation += 1;
    stopPolling();
    const previous = session.value;
    session.value = undefined;
    openingAccount.value = undefined;
    busy.value = false;
    nextInputAt = 0;
    error.value = "";
    visible.value = false;
    clearFrame();
    if (previous) void release(previous);
  }

  function schedule(epoch: number) {
    const status = session.value?.status;
    if (
      epoch !== generation ||
      !visible.value ||
      error.value ||
      status === "FAILED" ||
      status === "CLOSED"
    )
      return;
    timer = setTimeout(() => void poll(epoch), POLL_INTERVAL);
  }

  async function poll(epoch: number) {
    const current = session.value;
    if (!current || epoch !== generation || !visible.value) return;
    if (busy.value) {
      schedule(epoch);
      return;
    }
    const controller = new AbortController();
    pollController = controller;
    try {
      const res = await CncAccountAPI.loginStatus(
        current.account_id,
        current.session_id,
        controller.signal
      );
      if (epoch !== generation) return;
      if (res.data.code !== ResultEnum.SUCCESS) throw new Error("Status failed");
      accept(res.data.data, current);
      if (["READY", "WAITING_HUMAN"].includes(res.data.data.status)) {
        const frame = await CncAccountAPI.loginFrame(
          current.account_id,
          current.session_id,
          controller.signal
        );
        if (epoch !== generation) return;
        if (frame.data.type !== "image/jpeg" || frame.data.size === 0)
          throw new Error("Invalid frame");
        const nextUrl = URL.createObjectURL(frame.data);
        clearFrame();
        frameUrl.value = nextUrl;
      }
    } catch {
      if (epoch !== generation || controller.signal.aborted) return;
      error.value = "平台画面连接中断，请关闭窗口后重新登录。";
      clearFrame();
    } finally {
      if (pollController === controller) pollController = undefined;
      schedule(epoch);
    }
  }

  async function open(row: CncAccountTable) {
    const id = row.id;
    if (disposed || id == null || row.enabled !== true || loadingIds.value.has(id)) return;
    if (visible.value && session.value?.account_id === id) return;
    close();
    const epoch = generation;
    visible.value = true;
    openingAccount.value = id;
    selectedPlatform.value = row.platform_name || "平台登录";
    loadingIds.value.add(id);
    try {
      await closingAccounts.get(id);
      if (epoch !== generation || disposed) return;
      const res = await CncAccountAPI.login(id);
      if (res.data.code !== ResultEnum.SUCCESS || res.data.data.account_id !== id)
        throw new Error("Login failed");
      if (epoch !== generation || disposed) {
        void release(res.data.data);
        return;
      }
      session.value = res.data.data;
      schedule(epoch);
    } catch {
      if (epoch === generation && !disposed)
        error.value = "无法启动平台登录，请检查账号、平台配置及服务状态后重试。";
    } finally {
      loadingIds.value.delete(id);
      if (epoch === generation) openingAccount.value = undefined;
    }
  }

  async function command(input?: CncLoginInput) {
    const current = session.value;
    if (!current || !interactive.value) return;
    const epoch = ++generation;
    busy.value = true;
    stopPolling();
    try {
      if (input) {
        // Pace from the previous response so network jitter cannot violate the
        // server's 100 ms input limit. Each command is still sent only once.
        const delay = nextInputAt - Date.now();
        if (delay > 0) await new Promise((resolve) => setTimeout(resolve, delay));
        if (epoch !== generation || disposed) return;
      }
      const res = input
        ? await CncAccountAPI.loginInput(current.account_id, current.session_id, input)
        : await CncAccountAPI.verifyLogin(current.account_id, current.session_id);
      if (epoch !== generation) return;
      if (res.data.code !== ResultEnum.SUCCESS) throw new Error("Command failed");
      if (input) nextInputAt = Date.now() + 110;
      accept(res.data.data, current);
    } catch {
      if (epoch === generation) {
        error.value = "操作结果未能确认，请关闭窗口后重新登录。";
        clearFrame();
      }
    } finally {
      if (epoch === generation) {
        busy.value = false;
        schedule(epoch);
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
    session,
    openingAccount,
    loadingIds,
    frameUrl,
    error,
    busy,
    selectedPlatform,
    interactive,
    open,
    close,
    command,
  };
}
