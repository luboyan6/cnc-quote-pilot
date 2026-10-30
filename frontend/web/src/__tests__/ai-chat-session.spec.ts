import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  createSession: vi.fn(),
  getSessionDetail: vi.fn(),
  getCapabilities: vi.fn(),
  getSkills: vi.fn(),
  uploadStepDrawing: vi.fn(),
}));
const evidenceApi = vi.hoisted(() => ({ getPrivateScreenshotBlob: vi.fn() }));
vi.mock("@/api/module_ai/chat", () => ({ default: api }));
vi.mock("@/api/module_cnc/cnc_quote_result", () => ({ default: evidenceApi }));
vi.mock("@utils/auth", () => ({ Auth: { getAccessToken: () => "test-token" } }));
vi.mock("@/views/module_ai/chat/components/FaSidebar.vue", () => ({
  default: { name: "FaSidebar" },
}));
vi.mock("@/views/module_ai/chat/components/FaChatNavbar.vue", () => ({
  default: { name: "FaChatNavbar" },
}));
vi.mock("@/views/module_ai/chat/components/FaChatMessages.vue", () => ({
  default: { name: "FaChatMessages" },
}));
vi.mock("@/views/module_ai/chat/components/FaChatInput.vue", () => ({
  default: { name: "FaChatInput" },
}));
vi.mock("@/views/module_ai/chat/components/FaAiModelConfigPanel.vue", () => ({
  default: { name: "FaAiModelConfigPanel" },
}));

import Chat from "@/views/module_ai/chat/index.vue";

class FakeSocket {
  static OPEN = 1;
  static CLOSED = 3;
  static instances: FakeSocket[] = [];
  readyState = 0;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor() {
    FakeSocket.instances.push(this);
  }
  open() {
    this.readyState = FakeSocket.OPEN;
    this.onopen?.();
  }
  send(value: string) {
    this.sent.push(value);
  }
  close() {
    this.readyState = FakeSocket.CLOSED;
    this.onclose?.();
  }
}

const Sidebar = defineComponent({
  name: "FaSidebar",
  emits: ["select-session", "new-session"],
  setup(_props, { expose }) {
    expose({ loadSessions: () => {} });
    return () => null;
  },
});
const Input = defineComponent({
  name: "FaChatInput",
  props: ["disabled", "sending"],
  emits: ["send", "stop"],
  template: "<div />",
});
const Messages = defineComponent({
  name: "FaChatMessages",
  props: ["messages", "error"],
  emits: ["prompt-click", "error-close", "open-evidence"],
  setup(_props, { expose }) {
    expose({ scrollToBottom: () => {} });
    return () => null;
  },
});
const mounted: ReturnType<typeof mount>[] = [];

function mountChat() {
  const wrapper = mount(Chat, {
    global: {
      stubs: {
        ElSplitter: { template: "<div><slot /></div>" },
        ElSplitterPanel: { template: "<div><slot /></div>" },
        ElDialog: { props: ["modelValue"], template: "<div><slot /></div>" },
        FaSidebar: Sidebar,
        FaChatInput: Input,
        FaChatMessages: Messages,
        FaChatNavbar: true,
        FaAiModelConfigPanel: true,
      },
    },
  });
  mounted.push(wrapper);
  FakeSocket.instances[0]!.open();
  return wrapper;
}

function response(content: string) {
  return { data: { code: 0, data: { messages: [{ role: "assistant", content }], runs: [] } } };
}

beforeEach(() => {
  FakeSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeSocket);
  vi.stubEnv("VITE_APP_WS_ENDPOINT", "ws://localhost:8001");
  api.createSession.mockReset();
  api.getSessionDetail.mockReset();
  api.getCapabilities.mockReset();
  api.getCapabilities.mockResolvedValue({
    data: { code: 0, data: { protocol_version: 1, source_available: false } },
  });
  api.getSkills.mockReset();
  api.uploadStepDrawing.mockReset();
  evidenceApi.getPrivateScreenshotBlob.mockReset();
});
afterEach(() => {
  mounted.splice(0).forEach((wrapper) => wrapper.unmount());
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("聊天会话隔离和草稿", () => {
  it("切换会话会关闭旧生成连接，迟到的旧消息不能进入新会话", async () => {
    api.getSessionDetail
      .mockResolvedValueOnce(response("old history"))
      .mockResolvedValueOnce(response("new history"));
    const wrapper = mountChat();
    wrapper.findComponent(Sidebar).vm.$emit("select-session", { id: "a", title: "A" });
    await flushPromises();
    wrapper.findComponent(Input).vm.$emit("send", "question", undefined, vi.fn());
    await flushPromises();
    const oldSocket = FakeSocket.instances[0]!;
    const lateMessage = oldSocket.onmessage!;
    expect(oldSocket.sent).toHaveLength(1);

    wrapper.findComponent(Sidebar).vm.$emit("select-session", { id: "b", title: "B" });
    await flushPromises();
    expect(oldSocket.readyState).toBe(FakeSocket.CLOSED);
    lateMessage({ data: "late chunk" });
    const messages = wrapper.findComponent(Messages).props("messages") as {
      content: string;
      loading?: boolean;
    }[];
    expect(messages.map((message) => message.content)).toEqual(["new history"]);
    expect(messages[0]?.loading).toBe(false);
  });

  it("切换会话后忽略迟到的历史请求", async () => {
    let resolveOld!: (value: ReturnType<typeof response>) => void;
    api.getSessionDetail
      .mockReturnValueOnce(new Promise((resolve) => (resolveOld = resolve)))
      .mockResolvedValueOnce(response("new history"));
    const wrapper = mountChat();
    wrapper.findComponent(Sidebar).vm.$emit("select-session", { id: "a", title: "A" });
    wrapper.findComponent(Sidebar).vm.$emit("select-session", { id: "b", title: "B" });
    await flushPromises();
    resolveOld(response("old history"));
    await flushPromises();
    const messages = wrapper.findComponent(Messages).props("messages") as { content: string }[];
    expect(messages.map((message) => message.content)).toEqual(["new history"]);
  });

  it("刷新会话时恢复受限的证据结果引用", async () => {
    api.getSessionDetail.mockResolvedValueOnce({
      data: {
        code: 0,
        data: {
          messages: [
            { role: "assistant", content: "result", evidence_result_ids: [42, 42, 0, -1] },
          ],
          runs: [],
        },
      },
    });
    const wrapper = mountChat();
    await flushPromises();
    wrapper.findComponent(Sidebar).vm.$emit("select-session", { id: "a", title: "A" });
    await flushPromises();
    const messages = wrapper.findComponent(Messages).props("messages") as {
      evidenceResultIds?: number[];
    }[];
    expect(messages[0]?.evidenceResultIds).toEqual([42]);
  });

  it("创建会话失败或附件未上传时不清空用户草稿", async () => {
    api.createSession.mockRejectedValueOnce(new Error("failed"));
    const wrapper = mountChat();
    await flushPromises();
    const accepted = vi.fn();
    wrapper.findComponent(Input).vm.$emit("send", "draft", undefined, accepted);
    await flushPromises();
    expect(accepted).not.toHaveBeenCalled();
    expect(FakeSocket.instances[0]!.sent).toHaveLength(0);

    wrapper
      .findComponent(Input)
      .vm.$emit("send", "draft", [{ id: "file", name: "a.step" }], accepted);
    await flushPromises();
    expect(accepted).not.toHaveBeenCalled();
    expect(wrapper.findComponent(Messages).props("error")).toContain("暂不支持图纸附件");
    expect(FakeSocket.instances[0]!.sent).toHaveLength(0);
  });

  it("新协议只处理当前会话与轮次的结构化事件并显示工具失败", async () => {
    api.getCapabilities.mockResolvedValueOnce({
      data: { code: 0, data: { protocol_version: 2, source_available: true } },
    });
    api.getSkills.mockResolvedValueOnce({
      data: {
        code: 0,
        data: [{ name: "cnc-part", description: "查询图纸", allowed_tools: ["cnc_part_detail"] }],
      },
    });
    api.getSessionDetail.mockResolvedValueOnce(response("history"));
    const wrapper = mountChat();
    await flushPromises();
    wrapper.findComponent(Sidebar).vm.$emit("select-session", { id: "a", title: "A" });
    await flushPromises();
    wrapper.findComponent(Input).vm.$emit("skills-change", ["cnc-part"]);
    wrapper.findComponent(Input).vm.$emit("send", "question", undefined, vi.fn());
    await flushPromises();
    const socket = FakeSocket.instances[0]!;
    const request = JSON.parse(socket.sent[0]!) as {
      turn_id: string;
      skills: string[];
      protocol_version: number;
    };
    expect(request.protocol_version).toBe(2);
    expect(request.skills).toEqual(["cnc-part"]);
    const send = (
      type: string,
      seq: number,
      payload: Record<string, unknown> = {},
      turn = request.turn_id
    ) =>
      socket.onmessage?.({
        data: JSON.stringify({ session_id: "a", turn_id: turn, seq, type, payload }),
      });
    send("text.delta", 20, { text: "stale" }, "old-turn");
    send("turn.started", 1);
    send("text.delta", 2, { text: "real" });
    send("tool.started", 3, { name: "cnc_part_detail" });
    send("tool.failed", 4, { name: "cnc_part_detail" });
    send("turn.completed", 5);
    send("text.delta", 6, { text: "late" });
    const messages = wrapper.findComponent(Messages).props("messages") as {
      content: string;
      progress?: { status: string }[];
    }[];
    expect(messages.at(-1)?.content).toBe("real");
    expect(messages.at(-1)?.progress?.[0]?.status).toBe("failed");
  });

  it("上传失败保留草稿，重试沿用请求标识并只引用已保存图纸", async () => {
    api.getCapabilities.mockResolvedValueOnce({
      data: { code: 0, data: { protocol_version: 2, source_available: true } },
    });
    api.getSkills.mockResolvedValueOnce({ data: { code: 0, data: [] } });
    api.createSession.mockResolvedValue({ data: { code: 0, data: { id: "a" } } });
    api.uploadStepDrawing
      .mockImplementationOnce(async (file: File, requestId: string) => ({
        data: {
          code: 0,
          data: {
            request_id: requestId,
            state: "READY",
            part_id: 1,
            sha256: "a".repeat(64),
            size_bytes: file.size,
          },
        },
      }))
      .mockRejectedValueOnce(new Error("上传失败"))
      .mockImplementationOnce(async (file: File, requestId: string) => ({
        data: {
          code: 0,
          data: {
            request_id: requestId,
            state: "READY",
            part_id: 2,
            sha256: "b".repeat(64),
            size_bytes: file.size,
          },
        },
      }));
    const wrapper = mountChat();
    await flushPromises();
    const first = new File(["first"], "first.step");
    const second = new File(["second"], "second.stp");
    const files = [
      { id: "1", name: first.name, size: first.size, type: first.type, file: first },
      { id: "2", name: second.name, size: second.size, type: second.type, file: second },
    ];
    const accepted = vi.fn();
    wrapper.findComponent(Input).vm.$emit("send", "", files, accepted);
    await flushPromises();
    expect(accepted).not.toHaveBeenCalled();
    expect(FakeSocket.instances[0]!.sent).toHaveLength(0);
    expect(wrapper.findComponent(Messages).props("error")).toContain("上传失败");

    wrapper.findComponent(Input).vm.$emit("send", "", files, accepted);
    await flushPromises();
    expect(api.uploadStepDrawing).toHaveBeenCalledTimes(3);
    expect(api.uploadStepDrawing.mock.calls[1]![1]).toBe(api.uploadStepDrawing.mock.calls[2]![1]);
    const socket = FakeSocket.instances[0]!;
    const request = JSON.parse(socket.sent[0]!) as { turn_id: string; drawing_uploads: string[] };
    expect(request.drawing_uploads).toEqual([
      api.uploadStepDrawing.mock.calls[0]![1],
      api.uploadStepDrawing.mock.calls[1]![1],
    ]);
    expect(accepted).not.toHaveBeenCalled();
    socket.onmessage?.({
      data: JSON.stringify({
        session_id: "a",
        turn_id: request.turn_id,
        seq: 1,
        type: "turn.started",
        payload: {},
      }),
    });
    expect(accepted).toHaveBeenCalledTimes(1);
  });

  it("上传中切换会话时不会把迟到结果发送给新会话", async () => {
    api.getCapabilities.mockResolvedValueOnce({
      data: { code: 0, data: { protocol_version: 2, source_available: true } },
    });
    api.getSkills.mockResolvedValueOnce({ data: { code: 0, data: [] } });
    api.getSessionDetail.mockResolvedValue(response("history"));
    let complete!: (result: unknown) => void;
    api.uploadStepDrawing.mockReturnValueOnce(new Promise((resolve) => (complete = resolve)));
    const wrapper = mountChat();
    await flushPromises();
    wrapper.findComponent(Sidebar).vm.$emit("select-session", { id: "a", title: "A" });
    await flushPromises();
    const file = new File(["drawing"], "part.step");
    const accepted = vi.fn();
    wrapper
      .findComponent(Input)
      .vm.$emit(
        "send",
        "draft",
        [{ id: "1", name: file.name, size: file.size, type: file.type, file }],
        accepted
      );
    await flushPromises();
    const requestId = api.uploadStepDrawing.mock.calls[0]![1] as string;
    const oldSocket = FakeSocket.instances[0]!;
    wrapper.findComponent(Sidebar).vm.$emit("select-session", { id: "b", title: "B" });
    complete({
      data: {
        code: 0,
        data: {
          request_id: requestId,
          state: "READY",
          part_id: 1,
          sha256: "a".repeat(64),
          size_bytes: file.size,
        },
      },
    });
    await flushPromises();
    expect(oldSocket.sent).toHaveLength(0);
    expect(accepted).not.toHaveBeenCalled();
    expect(wrapper.findComponent(Messages).props("messages")).toEqual(
      expect.arrayContaining([expect.objectContaining({ content: "history" })])
    );
  });

  it("服务端拒绝图纸引用时保留草稿并复用已上传图纸", async () => {
    api.getCapabilities.mockResolvedValueOnce({
      data: { code: 0, data: { protocol_version: 2, source_available: true } },
    });
    api.getSkills.mockResolvedValueOnce({ data: { code: 0, data: [] } });
    api.createSession.mockResolvedValue({ data: { code: 0, data: { id: "a" } } });
    api.uploadStepDrawing.mockImplementation(async (file: File, requestId: string) => ({
      data: {
        code: 0,
        data: {
          request_id: requestId,
          state: "READY",
          part_id: 1,
          sha256: "a".repeat(64),
          size_bytes: file.size,
        },
      },
    }));
    const wrapper = mountChat();
    await flushPromises();
    const file = new File(["drawing"], "part.step");
    const files = [{ id: "1", name: file.name, size: file.size, type: file.type, file }];
    const accepted = vi.fn();
    wrapper.findComponent(Input).vm.$emit("send", "draft", files, accepted);
    await flushPromises();
    const socket = FakeSocket.instances[0]!;
    const turn = JSON.parse(socket.sent[0]!) as { turn_id: string };
    socket.onmessage?.({
      data: JSON.stringify({
        session_id: "a",
        turn_id: turn.turn_id,
        seq: 1,
        type: "turn.failed",
        payload: { code: "CHAT_DRAWING_UNAVAILABLE" },
      }),
    });
    await flushPromises();
    expect(accepted).not.toHaveBeenCalled();
    expect(wrapper.findComponent(Messages).props("messages")).toEqual([]);
    expect(wrapper.findComponent(Messages).props("error")).toContain("图纸不可用");

    wrapper.findComponent(Input).vm.$emit("send", "draft", files, accepted);
    await flushPromises();
    expect(api.uploadStepDrawing).toHaveBeenCalledTimes(1);
    expect(socket.sent).toHaveLength(2);
  });

  it("在已有会话上传期间停止不会发出生成或停止指令", async () => {
    api.getCapabilities.mockResolvedValueOnce({
      data: { code: 0, data: { protocol_version: 2, source_available: true } },
    });
    api.getSkills.mockResolvedValueOnce({ data: { code: 0, data: [] } });
    api.getSessionDetail.mockResolvedValue(response("history"));
    let complete!: (result: unknown) => void;
    api.uploadStepDrawing.mockReturnValueOnce(new Promise((resolve) => (complete = resolve)));
    const wrapper = mountChat();
    await flushPromises();
    wrapper.findComponent(Sidebar).vm.$emit("select-session", { id: "a", title: "A" });
    await flushPromises();
    const file = new File(["drawing"], "part.step");
    const accepted = vi.fn();
    wrapper
      .findComponent(Input)
      .vm.$emit(
        "send",
        "draft",
        [{ id: "1", name: file.name, size: file.size, type: file.type, file }],
        accepted
      );
    await flushPromises();
    const requestId = api.uploadStepDrawing.mock.calls[0]![1] as string;
    wrapper.findComponent(Input).vm.$emit("stop");
    complete({
      data: {
        code: 0,
        data: {
          request_id: requestId,
          state: "READY",
          part_id: 1,
          sha256: "a".repeat(64),
          size_bytes: file.size,
        },
      },
    });
    await flushPromises();
    expect(FakeSocket.instances[0]!.sent).toHaveLength(0);
    expect(accepted).not.toHaveBeenCalled();
  });

  it("旧引擎回滚后只读展示源码会话，不能向该历史会话发送消息", async () => {
    api.getSessionDetail.mockResolvedValue(response("source history"));
    const wrapper = mountChat();
    await flushPromises();
    wrapper.findComponent(Sidebar).vm.$emit("select-session", {
      id: "source:one",
      title: "source",
      read_only: true,
    });
    await flushPromises();
    expect(wrapper.findComponent(Input).props("disabled")).toBe(true);
    expect(wrapper.text()).toContain("当前可查看历史");
    wrapper.findComponent(Input).vm.$emit("send", "question", undefined, vi.fn());
    await flushPromises();
    expect(FakeSocket.instances[0]!.sent).toHaveLength(0);
    wrapper.findComponent(Sidebar).vm.$emit("new-session");
    await flushPromises();
    expect(wrapper.findComponent(Input).props("disabled")).toBe(false);
  });

  it("通过授权接口读取证据并在切换会话时释放 Blob", async () => {
    const NativeURL = globalThis.URL;
    const createObjectURL = vi.fn(() => "blob:private-evidence");
    const revokeObjectURL = vi.fn();
    class TestURL extends NativeURL {
      static override createObjectURL = createObjectURL;
      static override revokeObjectURL = revokeObjectURL;
    }
    vi.stubGlobal("URL", TestURL);
    api.getCapabilities.mockResolvedValueOnce({
      data: { code: 0, data: { protocol_version: 2, source_available: true } },
    });
    api.getSkills.mockResolvedValueOnce({ data: { code: 0, data: [] } });
    api.getSessionDetail.mockResolvedValue(response("history"));
    evidenceApi.getPrivateScreenshotBlob.mockResolvedValue({
      data: new Blob(["image"], { type: "image/png" }),
    });
    const wrapper = mountChat();
    await flushPromises();
    wrapper.findComponent(Sidebar).vm.$emit("select-session", { id: "a", title: "A" });
    await flushPromises();
    wrapper.findComponent(Input).vm.$emit("send", "查看结果", undefined, vi.fn());
    await flushPromises();
    const socket = FakeSocket.instances[0]!;
    const turn = JSON.parse(socket.sent[0]!) as { turn_id: string };
    const send = (type: string, seq: number, payload: Record<string, unknown> = {}) =>
      socket.onmessage?.({
        data: JSON.stringify({ session_id: "a", turn_id: turn.turn_id, seq, type, payload }),
      });
    send("turn.started", 1);
    send("evidence.available", 2, { result_id: 42 });
    send("turn.completed", 3);
    const messages = wrapper.findComponent(Messages).props("messages") as {
      evidenceResultIds?: number[];
    }[];
    expect(messages.at(-1)?.evidenceResultIds).toEqual([42]);
    wrapper.findComponent(Messages).vm.$emit("open-evidence", 42);
    await flushPromises();
    expect(evidenceApi.getPrivateScreenshotBlob).toHaveBeenCalledWith(42, expect.any(AbortSignal));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    wrapper.findComponent(Sidebar).vm.$emit("select-session", { id: "b", title: "B" });
    await flushPromises();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:private-evidence");
  });

  it("切换会话后忽略迟到的证据响应", async () => {
    const NativeURL = globalThis.URL;
    const createObjectURL = vi.fn(() => "blob:late");
    class TestURL extends NativeURL {
      static override createObjectURL = createObjectURL;
      static override revokeObjectURL = vi.fn();
    }
    vi.stubGlobal("URL", TestURL);
    api.getSessionDetail.mockResolvedValue(response("history"));
    let complete!: (value: unknown) => void;
    evidenceApi.getPrivateScreenshotBlob.mockReturnValue(
      new Promise((resolve) => (complete = resolve))
    );
    const wrapper = mountChat();
    await flushPromises();
    wrapper.findComponent(Sidebar).vm.$emit("select-session", { id: "a", title: "A" });
    await flushPromises();
    wrapper.findComponent(Messages).vm.$emit("open-evidence", 42);
    await flushPromises();
    const signal = evidenceApi.getPrivateScreenshotBlob.mock.calls[0]![1] as AbortSignal;
    wrapper.findComponent(Sidebar).vm.$emit("select-session", { id: "b", title: "B" });
    complete({ data: new Blob(["image"], { type: "image/png" }) });
    await flushPromises();
    expect(signal.aborted).toBe(true);
    expect(createObjectURL).not.toHaveBeenCalled();
  });
});
