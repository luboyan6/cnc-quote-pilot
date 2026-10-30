<template>
  <div class="fa-full-height">
    <ElSplitter :style="'height: 100%'">
      <ElSplitterPanel :size="isSidebarCollapsed ? 64 : 200" :min="64" :max="400">
        <div class="sidebar-container h-full" :class="{ collapsed: isSidebarCollapsed }">
          <FaSidebar
            ref="sidebarRef"
            :current-session-id="currentSessionId"
            :is-collapsed="isSidebarCollapsed"
            @select-session="handleSelectSession"
            @new-session="handleNewSession"
            @open-config="configDrawerVisible = true"
          />
        </div>
      </ElSplitterPanel>
      <ElSplitterPanel :min="300">
        <div class="chat-container flex flex-col h-full overflow-hidden">
          <div class="chat-header">
            <FaChatNavbar
              :connection-status="connectionStatus"
              :is-connected="isConnected"
              :message-count="messages.length"
              :is-sidebar-collapsed="isSidebarCollapsed"
              @clear-chat="handleClearChat"
              @toggle-connection="toggleConnection"
              @toggle-sidebar="toggleSidebar"
            />
          </div>
          <div class="chat-main flex-1 overflow-hidden">
            <FaChatMessages
              ref="chatMessagesRef"
              :messages="messages"
              :error="error"
              @prompt-click="handleSendMessage"
              @error-close="error = ''"
              @open-evidence="openEvidence"
            />
          </div>
          <div class="chat-footer">
            <div v-if="readOnlySession" class="readonly-hint" role="status">
              此会话来自源码引擎，当前可查看历史；请新建会话继续聊天。
            </div>
            <FaChatInput
              :disabled="!isConnected || !capabilitiesReady || readOnlySession"
              :sending="sending"
              :is-connected="isConnected"
              :skills="availableSkills"
              :selected-skills="selectedSkills"
              @send="handleSendMessage"
              @stop="handleStopMessage"
              @skills-change="selectedSkills = $event"
            />
          </div>
        </div>
      </ElSplitterPanel>
    </ElSplitter>

    <FaAiModelConfigPanel v-model="configDrawerVisible" />
    <ElDialog
      v-model="evidenceVisible"
      title="报价证据"
      width="80%"
      destroy-on-close
      @close="closeEvidence"
    >
      <p v-if="evidenceLoading" role="status">正在读取证据…</p>
      <p v-else-if="evidenceError" role="alert">{{ evidenceError }}</p>
      <img v-else-if="evidenceUrl" :src="evidenceUrl" alt="报价证据截图" class="evidence-image" />
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: "Chat",
  inheritAttrs: false,
});

import { onActivated, onDeactivated, onMounted, onUnmounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import AiChatAPI, { type ChatSession, type ChatSkill } from "@/api/module_ai/chat";
import CncQuoteResultAPI from "@/api/module_cnc/cnc_quote_result";
import { Auth } from "@utils/auth";
import type { ChatMessage, UploadedFile } from "./types";
import { decodeChatEvent } from "./agentEvents";
import FaSidebar from "./components/FaSidebar.vue";
import FaChatNavbar from "./components/FaChatNavbar.vue";
import FaChatMessages from "./components/FaChatMessages.vue";
import FaChatInput from "./components/FaChatInput.vue";
import FaAiModelConfigPanel from "./components/FaAiModelConfigPanel.vue";

// 状态
const messages = ref<ChatMessage[]>([]);
const sending = ref(false);
const isConnected = ref(false);
const connectionStatus = ref<"connected" | "connecting" | "disconnected">("disconnected");
const error = ref("");
const currentSessionId = ref<string | null>(null);
const readOnlySession = ref(false);
const isSidebarCollapsed = ref(false);
const configDrawerVisible = ref(false);
const capabilitiesReady = ref(false);
const protocolVersion = ref<1 | 2>(1);
const availableSkills = ref<ChatSkill[]>([]);
const selectedSkills = ref<string[]>([]);
const evidenceVisible = ref(false);
const evidenceLoading = ref(false);
const evidenceError = ref("");
const evidenceUrl = ref<string | null>(null);
let evidenceGeneration = 0;
let evidenceRequest: AbortController | null = null;
let activeTurnId: string | null = null;
let lastEventSeq = 0;
let turnStarted = false;
let preparingTurn = false;
let pendingAcceptance: (() => void) | null = null;
let pendingMessageIds: string[] = [];

const discardPendingSubmission = () => {
  pendingAcceptance = null;
  if (pendingMessageIds.length) {
    messages.value = messages.value.filter((item) => !pendingMessageIds.includes(item.id));
    pendingMessageIds = [];
  }
};

// Refs
const chatMessagesRef = ref<{ scrollToBottom: () => void }>();
const sidebarRef = ref<{ loadSessions: () => void }>();

// WebSocket
let ws: WebSocket | null = null;
let sessionGeneration = 0;
const WS_URL = import.meta.env.VITE_APP_WS_ENDPOINT;

// ============ WebSocket 操作 ============
const connectWebSocket = () => {
  // CONNECTING / OPEN / CLOSING 期间一律拒绝重入：
  // 仅挡 OPEN 会在连接握手期间被重复调用，旧连接引用被覆盖后泄漏（后台照样连上并弹「连接成功」）
  if (ws && ws.readyState !== WebSocket.CLOSED) return;

  connectionStatus.value = "connecting";
  error.value = "";

  try {
    const url = new URL("/api/v1/ai/chat/ws", WS_URL);
    const token = Auth.getAccessToken();
    // 令牌经 Sec-WebSocket-Protocol 传递，避免出现在 URL 与服务端 access log 中
    const socket = token
      ? new WebSocket(url.toString(), ["access_token", `access_token.${token}`])
      : new WebSocket(url.toString());
    ws = socket;

    socket.onopen = () => {
      if (ws !== socket) return;
      isConnected.value = true;
      connectionStatus.value = "connected";
      ElMessage.success("连接成功");
    };

    socket.onmessage = (event) => {
      if (ws === socket) handleWebSocketMessage(event.data);
    };

    socket.onclose = () => {
      if (ws !== socket) return;
      if (preparingTurn) sessionGeneration++;
      preparingTurn = false;
      discardPendingSubmission();
      isConnected.value = false;
      connectionStatus.value = "disconnected";
      sending.value = false;
      finishLoadingMessages();
    };

    socket.onerror = () => {
      if (ws !== socket) return;
      if (preparingTurn) sessionGeneration++;
      preparingTurn = false;
      discardPendingSubmission();
      isConnected.value = false;
      connectionStatus.value = "disconnected";
      sending.value = false;
      ElMessage.error("连接失败，请检查服务器状态");
      finishLoadingMessages();
    };
  } catch {
    connectionStatus.value = "disconnected";
    error.value = "无法创建连接";
  }
};

const disconnectWebSocket = () => {
  if (ws) {
    const socket = ws;
    ws = null;
    // 先摘除回调再关闭：握手期中止 / 关闭竞态期间不应再触发任何提示或状态回调
    socket.onopen = null;
    socket.onmessage = null;
    socket.onerror = null;
    socket.onclose = null;
    socket.close(1000, "用户主动断开");
  }
  isConnected.value = false;
  connectionStatus.value = "disconnected";
  sending.value = false;
  preparingTurn = false;
  discardPendingSubmission();
  activeTurnId = null;
  finishLoadingMessages();
};

const invalidateSessionView = () => {
  sessionGeneration++;
  closeEvidence();
  if (sending.value) {
    // The legacy protocol has no turn ID. Closing its socket fences late chunks
    // while the server cancels and awaits the old generation on disconnect.
    disconnectWebSocket();
    connectWebSocket();
  }
};

const toggleConnection = () => {
  if (isConnected.value) {
    disconnectWebSocket();
    ElMessage.info("已断开连接");
  } else {
    connectWebSocket();
  }
};

// ============ 消息处理 ============
const handleWebSocketMessage = (data: string) => {
  const text = data || "";

  if (protocolVersion.value === 2) {
    const event = decodeChatEvent(text);
    if (!event) return;
    if (event.type === "request.error") {
      const errors: Record<string, string> = {
        INVALID_REQUEST: "请求格式无效，请检查消息后重试。",
        NO_ACTIVE_TURN: "当前没有可停止的生成任务。",
        TURN_IN_PROGRESS: "当前仍有生成任务，请稍后重试。",
      };
      error.value = Object.hasOwn(errors, event.payload.code)
        ? errors[event.payload.code]!
        : "请求未能处理，请重试。";
      if (["INVALID_REQUEST", "TURN_IN_PROGRESS"].includes(event.payload.code) && !turnStarted) {
        discardPendingSubmission();
        sending.value = false;
        activeTurnId = null;
      }
      return;
    }
    if (
      !sending.value ||
      event.session_id !== currentSessionId.value ||
      event.turn_id !== activeTurnId ||
      event.seq <= lastEventSeq
    )
      return;
    lastEventSeq = event.seq;
    if (event.type === "turn.started") {
      turnStarted = true;
      pendingMessageIds = [];
      pendingAcceptance?.();
      pendingAcceptance = null;
    }
    if (event.type === "text.delta" && typeof event.payload.text === "string") {
      const last = messages.value[messages.value.length - 1];
      if (last?.type === "assistant" && last.loading) last.content += event.payload.text;
      chatMessagesRef.value?.scrollToBottom();
    }
    if (event.type === "evidence.available") {
      const resultId = event.payload.result_id;
      const last = messages.value[messages.value.length - 1];
      if (
        typeof resultId === "number" &&
        Number.isSafeInteger(resultId) &&
        resultId > 0 &&
        last?.type === "assistant" &&
        last.loading
      ) {
        last.evidenceResultIds ||= [];
        if (!last.evidenceResultIds.includes(resultId)) last.evidenceResultIds.push(resultId);
      }
    }
    if (["skill.activated", "tool.started", "tool.completed", "tool.failed"].includes(event.type)) {
      const last = messages.value[messages.value.length - 1];
      const name = event.payload.name;
      if (last?.type === "assistant" && last.loading && typeof name === "string") {
        last.progress ||= [];
        if (event.type === "skill.activated") {
          last.progress.push({ id: event.seq, kind: "skill", name, status: "active" });
        } else if (event.type === "tool.started") {
          last.progress.push({ id: event.seq, kind: "tool", name, status: "active" });
        } else {
          const item = [...last.progress]
            .reverse()
            .find(
              (entry) => entry.kind === "tool" && entry.name === name && entry.status === "active"
            );
          const status = event.type === "tool.failed" ? "failed" : "completed";
          if (item) item.status = status;
          else last.progress.push({ id: event.seq, kind: "tool", name, status });
        }
      }
    }
    if (["turn.completed", "turn.stopped", "turn.failed"].includes(event.type)) {
      if (!turnStarted) discardPendingSubmission();
      finishLoadingMessages();
      sending.value = false;
      activeTurnId = null;
      if (event.type === "turn.stopped") ElMessage.info("已停止生成");
      if (event.type === "turn.stopped" && event.payload.history_status === "unavailable")
        error.value = "已停止生成，但聊天记录暂时无法保存。";
      if (event.type === "turn.stopped" && event.payload.history_status === "not_saved")
        error.value = "已停止生成，本轮尚未保存到聊天记录。";
      if (event.type === "turn.failed") {
        error.value =
          event.payload.code === "CHAT_DRAWING_UNAVAILABLE"
            ? "图纸不可用或文件已发生变化，请重新选择后再试。"
            : "本轮生成失败，请重试。";
      }
    }
    return;
  }

  // 服务端结束标记
  if (text === "[DONE]") {
    finishLoadingMessages();
    sending.value = false;
    return;
  }

  // 服务端停止确认标记
  if (text === "[STOPPED]") {
    finishLoadingMessages();
    sending.value = false;
    ElMessage.info("已停止生成");
    return;
  }

  // Chunks arriving after a terminal event belong to an older turn.
  if (!sending.value) return;

  const lastMessage = messages.value[messages.value.length - 1];

  if (lastMessage?.type === "assistant" && lastMessage.loading) {
    lastMessage.content += text;
  } else {
    addMessage("assistant", text);
  }

  chatMessagesRef.value?.scrollToBottom();
};

const addMessage = (type: "user" | "assistant", content: string, files?: UploadedFile[]) => {
  const id = generateId();
  messages.value.push({
    id,
    type,
    content,
    timestamp: Date.now(),
    collapsed: content.length > 200,
    files,
    loading: type === "assistant" ? true : false,
  });
  return id;
};

const finishLoadingMessages = () => {
  messages.value.forEach((msg) => {
    if (msg.type === "assistant" && msg.loading) {
      msg.loading = false;
      msg.collapsed = msg.content.length > 200;
    }
  });
};

function closeEvidence() {
  evidenceGeneration++;
  evidenceRequest?.abort();
  evidenceRequest = null;
  if (evidenceUrl.value) URL.revokeObjectURL(evidenceUrl.value);
  evidenceUrl.value = null;
  evidenceVisible.value = false;
  evidenceLoading.value = false;
  evidenceError.value = "";
}

async function openEvidence(resultId: number) {
  if (!Number.isSafeInteger(resultId) || resultId <= 0) return;
  closeEvidence();
  const generation = evidenceGeneration;
  const controller = new AbortController();
  evidenceRequest = controller;
  evidenceVisible.value = true;
  evidenceLoading.value = true;
  try {
    const response = await CncQuoteResultAPI.getPrivateScreenshotBlob(resultId, controller.signal);
    if (generation !== evidenceGeneration) return;
    if (!(response.data instanceof Blob) || !response.data.type.startsWith("image/")) {
      throw new Error("invalid image");
    }
    evidenceUrl.value = URL.createObjectURL(response.data);
  } catch {
    if (generation === evidenceGeneration) evidenceError.value = "证据不可用或当前无权查看。";
  } finally {
    if (generation === evidenceGeneration) {
      evidenceLoading.value = false;
      evidenceRequest = null;
    }
  }
}

const generateId = () => {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
};

const generateTurnId = () => {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
};

const loadCapabilities = async () => {
  try {
    const result = await AiChatAPI.getCapabilities();
    if (
      result.data?.code === 0 &&
      result.data.data?.source_available &&
      result.data.data.protocol_version === 2
    ) {
      protocolVersion.value = 2;
      const skills = await AiChatAPI.getSkills();
      if (skills.data?.code === 0) availableSkills.value = skills.data.data || [];
    }
  } catch {
    // Older deployments do not expose capabilities and retain the legacy WS.
  } finally {
    capabilitiesReady.value = true;
  }
};

// ============ 发送消息 ============
const handleSendMessage = async (
  message: string,
  files?: UploadedFile[],
  accepted?: () => void
) => {
  if (
    (!message && !files) ||
    !isConnected.value ||
    !capabilitiesReady.value ||
    sending.value ||
    readOnlySession.value
  )
    return;
  if (files?.length && protocolVersion.value !== 2) {
    error.value = "当前聊天暂不支持图纸附件，请先在图纸管理中上传。";
    return;
  }

  // A late history response must not append messages after a new send.
  const generation = ++sessionGeneration;
  const socket = ws;
  sending.value = true;
  preparingTurn = true;

  // 结束上一个加载中的消息
  finishLoadingMessages();

  try {
    for (const item of files || []) {
      if (!item.file || !/\.(step|stp|setp)$/i.test(item.name)) {
        throw new Error("请选择有效的 STEP 图纸文件。");
      }
      item.requestId ||= generateTurnId();
      if (!item.uploadReady) {
        const response = await AiChatAPI.uploadStepDrawing(item.file, item.requestId);
        const result = response.data?.data;
        if (
          response.data?.code !== 0 ||
          result?.state !== "READY" ||
          !result.part_id ||
          result.request_id.replaceAll("-", "").toLowerCase() !==
            item.requestId.replaceAll("-", "").toLowerCase() ||
          result.size_bytes !== item.file.size ||
          !/^[a-f0-9]{64}$/.test(result.sha256)
        ) {
          throw new Error("图纸上传未完成，请重试。");
        }
        item.uploadReady = true;
      }
      if (generation !== sessionGeneration) return;
    }

    const sessionId =
      currentSessionId.value || (await createNewSession(message || files?.[0]?.name || "图纸对话"));
    if (generation !== sessionGeneration) return;
    if (!sessionId) throw new Error("创建会话失败，请重试。");
    currentSessionId.value = sessionId;

    if (socket && socket === ws && socket.readyState === WebSocket.OPEN) {
      const turnId = protocolVersion.value === 2 ? generateTurnId() : null;
      activeTurnId = turnId;
      lastEventSeq = 0;
      turnStarted = false;
      pendingAcceptance = turnId ? accepted || null : null;
      socket.send(
        JSON.stringify({
          message,
          session_id: sessionId,
          ...(turnId
            ? {
                protocol_version: 2,
                turn_id: turnId,
                skills: selectedSkills.value,
                drawing_uploads: files?.map((item) => item.requestId) || [],
              }
            : {}),
        })
      );
      const userMessageId = addMessage("user", message, files);
      const assistantMessageId = generateId();
      messages.value.push({
        id: assistantMessageId,
        type: "assistant",
        content: "",
        timestamp: Date.now(),
        loading: true,
      });
      if (turnId) pendingMessageIds = [userMessageId, assistantMessageId];
      else accepted?.();
      preparingTurn = false;
      error.value = "";
      chatMessagesRef.value?.scrollToBottom();
      // 注意：sending 状态保持为 true，等待 [DONE] / [STOPPED] 标记清除
    } else {
      throw new Error("WebSocket 连接未建立");
    }
  } catch (cause) {
    if (generation !== sessionGeneration) return;
    discardPendingSubmission();
    preparingTurn = false;
    activeTurnId = null;
    error.value = cause instanceof Error ? cause.message : "发送消息失败，请检查连接状态";
    sending.value = false;
  }
};

// 停止当前生成
const handleStopMessage = () => {
  if (sending.value && preparingTurn) {
    // An upload may still complete; its stable request ID makes retry safe.
    sessionGeneration++;
    preparingTurn = false;
    sending.value = false;
    return;
  }
  if (ws?.readyState !== WebSocket.OPEN) return;
  try {
    ws.send(
      JSON.stringify({
        action: "stop",
        session_id: currentSessionId.value,
        ...(protocolVersion.value === 2 && activeTurnId
          ? { protocol_version: 2, turn_id: activeTurnId }
          : {}),
      })
    );
  } catch {
    ElMessage.error("停止指令发送失败");
  }
};

const createNewSession = async (firstMessage: string): Promise<string | null> => {
  try {
    const title = firstMessage.slice(0, 20) + (firstMessage.length > 20 ? "..." : "");
    const res = await AiChatAPI.createSession({ title });

    if (res.data?.code === 0 || res.data?.success) {
      sidebarRef.value?.loadSessions();
      return res.data.data?.id ?? null;
    }
    throw new Error("创建会话失败");
  } catch {
    return null;
  }
};

// ============ 会话操作 ============
const handleSelectSession = async (session: ChatSession) => {
  invalidateSessionView();
  const generation = sessionGeneration;
  currentSessionId.value = session.id;
  readOnlySession.value = session.read_only === true;
  messages.value = [];

  try {
    const response = await AiChatAPI.getSessionDetail(session.id);
    if (generation !== sessionGeneration || currentSessionId.value !== session.id) return;
    if (response.data?.code !== 0) {
      return;
    }

    const sessionData = response.data.data || {};
    const visibleMessages = sessionData.messages || [];
    const runs = sessionData.runs || [];

    const history = visibleMessages.length
      ? visibleMessages
      : runs.flatMap((run) => run.messages || []);
    history.forEach((msg) => {
      if (msg.role === "user" || msg.role === "assistant") {
        addMessage(msg.role, msg.content);
        const last = messages.value[messages.value.length - 1];
        if (msg.role === "assistant" && last && Array.isArray(msg.evidence_result_ids)) {
          last.evidenceResultIds = [...new Set(msg.evidence_result_ids)].filter(
            (id): id is number => typeof id === "number" && Number.isSafeInteger(id) && id > 0
          );
        }
      }
    });
    finishLoadingMessages();

    ElMessage.success(`已切换到会话：${session.title}`);
  } catch {
    if (generation === sessionGeneration) ElMessage.error("获取会话详情失败");
  }
};

const handleNewSession = () => {
  invalidateSessionView();
  currentSessionId.value = null;
  readOnlySession.value = false;
  messages.value = [];
  ElMessage.success("已开启新对话");
};

const handleClearChat = async () => {
  const generation = sessionGeneration;
  try {
    await ElMessageBox.confirm("确定要清空当前对话吗？此操作不可恢复。", "确认清空", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });
    if (generation !== sessionGeneration) return;
    invalidateSessionView();
    messages.value = [];
    ElMessage.success("对话已清空");
  } catch {
    ElMessage.info("已取消清空对话");
  }
};

const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value;
};

// ============ 生命周期 ============
onMounted(() => {
  connectWebSocket();
  void loadCapabilities();
});
onUnmounted(() => {
  sessionGeneration++;
  closeEvidence();
  disconnectWebSocket();
});

// KeepAlive 缓存切换：离开视图即断开，回到视图按需重连。
// 缺失 deactivated 时被缓存实例会持续占用 WebSocket 连接（登出后旧实例的连接也不会释放）。
onActivated(() => {
  if (!isConnected.value) connectWebSocket();
});
onDeactivated(() => {
  sessionGeneration++;
  closeEvidence();
  disconnectWebSocket();
});
</script>

<style lang="scss" scoped>
/* 拆分条容器样式 */
:deep(.el-splitter) {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  box-shadow: var(--el-box-shadow-light);
}

:deep(.el-splitter-panel) {
  overflow: hidden;
}

.sidebar-container {
  background: transparent;
  transition: width 0.3s ease;
}

.chat-header {
  height: auto;
  padding: 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.chat-main {
  flex: 1;
  overflow: hidden;
}

.chat-footer {
  height: auto;
  min-height: 80px;
  padding: 0;
  border-top: 1px solid var(--el-border-color-lighter);
}

.readonly-hint {
  padding: 10px 20px 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  text-align: center;
}

.evidence-image {
  display: block;
  max-width: 100%;
  max-height: 75vh;
  margin: 0 auto;
  object-fit: contain;
}
</style>
