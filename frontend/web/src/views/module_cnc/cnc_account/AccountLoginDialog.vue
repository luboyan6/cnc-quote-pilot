<template>
  <ElDialog
    :model-value="visible"
    :title="`平台登录 · ${session?.platform_name || platformName}`"
    width="min(1328px, 96vw)"
    top="3vh"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    destroy-on-close
    @update:model-value="!$event && emit('close')"
  >
    <div class="login-status" role="status" aria-live="polite">
      <ElTag :type="statusTone">{{ statusLabel }}</ElTag>
      <span v-if="session">{{ session.username }}</span>
      <span v-if="session?.reused">已复用浏览器会话</span>
    </div>
    <ElAlert
      v-if="error || (session && ['WAITING_HUMAN', 'FAILED', 'CLOSED'].includes(session.status))"
      :title="error || reasonLabel"
      :type="error || session?.status === 'FAILED' ? 'error' : 'warning'"
      :closable="false"
      show-icon
      class="login-notice"
    />
    <p class="login-help">
      在下方平台页面操作；完成验证码或登录后点击“验证登录”。关闭窗口会释放浏览器。
    </p>
    <div class="browser-frame">
      <img
        v-if="frameUrl"
        :src="frameUrl"
        alt="当前账号的平台浏览器画面，点击可操作平台页面"
        tabindex="0"
        draggable="false"
        :aria-disabled="!interactive"
        @click="clickFrame"
        @wheel.prevent="scrollFrame"
        @keydown="pressKey"
      />
      <div v-else class="frame-placeholder" :aria-busy="preparing">
        {{ error ? "画面连接已停止" : preparing ? "正在准备平台页面…" : "暂无可用画面" }}
      </div>
    </div>
    <div class="browser-controls">
      <ElInput
        v-model="manualText"
        type="password"
        show-password
        autocomplete="off"
        aria-label="发送到平台当前焦点的文本"
        placeholder="点击平台输入框，再输入文本"
        :maxlength="256"
        :disabled="!interactive"
        @keydown.enter.prevent="sendText"
      />
      <ElButton :disabled="!interactive || !manualText" @click="sendText">发送文本</ElButton>
      <ElButton
        v-for="key in keys"
        :key="key.value"
        :disabled="!interactive"
        @click="sendKey(key.value)"
      >
        {{ key.label }}
      </ElButton>
      <ElButton :disabled="!interactive" @click="scroll(-480)">向上滚动</ElButton>
      <ElButton :disabled="!interactive" @click="scroll(480)">向下滚动</ElButton>
    </div>
    <template #footer>
      <ElButton @click="emit('close')">关闭浏览器</ElButton>
      <ElButton type="primary" :loading="busy" :disabled="!interactive" @click="emit('verify')">
        验证登录
      </ElButton>
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElAlert, ElButton, ElDialog, ElInput, ElTag } from "element-plus";
import type {
  CncLoginInput,
  CncLoginKey,
  CncLoginSession,
  CncLoginStatus,
} from "@/api/module_cnc/cnc_account";

const props = defineProps<{
  visible: boolean;
  session?: CncLoginSession;
  platformName: string;
  frameUrl: string;
  error: string;
  busy: boolean;
  interactive: boolean;
}>();
const emit = defineEmits<{
  close: [];
  input: [input: CncLoginInput];
  verify: [];
}>();
const manualText = ref("");
watch(
  () => [props.visible, props.session?.session_id],
  () => {
    manualText.value = "";
  }
);
const labels: Record<CncLoginStatus, string> = {
  STARTING: "准备浏览器",
  AUTHENTICATING: "正在登录",
  READY: "已核验登录",
  WAITING_HUMAN: "需人工处理",
  FAILED: "登录失败",
  CLOSED: "会话已关闭",
};
const statusLabel = computed(() =>
  props.error ? "连接失败" : labels[props.session?.status || "STARTING"]
);
const preparing = computed(
  () => !props.session || ["STARTING", "AUTHENTICATING"].includes(props.session.status)
);
const statusTone = computed(() => {
  if (props.error || props.session?.status === "FAILED") return "danger";
  if (props.session?.status === "READY") return "success";
  return props.session?.status === "WAITING_HUMAN" ? "warning" : "info";
});
const reasons: Record<string, string> = {
  PROVIDER_VERIFICATION_REQUIRED: "平台需要人工处理，请在下方完成登录或验证后点击验证登录。",
  MANUAL_LOGIN_REQUIRED: "此账号需要人工登录，请在下方完成后点击验证登录。",
  LOGIN_IDENTITY_VERIFICATION_REQUIRED: "尚未核验目标账号，请在平台页面完成登录或验证后重试。",
  QUOTE_PAGE_IDENTITY_REQUIRED: "询价页面尚未核验目标账号，请完成平台验证后重试。",
  CHALLENGE_REQUIRED: "平台要求人工验证，请在下方完成后点击验证登录。",
  AUTHENTICATION_FAILED: "平台登录失败，请检查账号配置后重试。",
  IDENTITY_MISMATCH: "当前平台账号与目标账号不一致，请关闭窗口并检查配置。",
  ACCOUNT_CHANGED_OR_LEASE_LOST: "账号已更新或会话已失效，请关闭窗口后重新登录。",
  LOGIN_ATTEMPT_UNCONFIRMED: "登录提交结果未能确认，请关闭窗口后重新登录。",
  SESSION_IDLE_EXPIRED: "浏览器因长时间未操作已关闭，请重新登录。",
  SESSION_LIFETIME_EXPIRED: "浏览器会话已过期，请重新登录。",
  SESSION_CLOSED: "浏览器已关闭，请重新登录。",
  browser_dependency_missing: "登录服务缺少浏览器依赖，请联系管理员。",
  browser_capacity: "登录窗口数量已达上限，请关闭其他窗口后重试。",
  policy_blocked: "平台访问未通过安全检查，请检查网络或平台配置。",
};
const reasonLabel = computed(
  () =>
    reasons[props.session?.reason || ""] ||
    (props.session?.status === "FAILED"
      ? "登录未通过核验，请关闭窗口后检查账号与平台配置。"
      : "请在平台页面完成所需操作，然后点击验证登录。")
);
const keys: { label: string; value: CncLoginKey }[] = [
  { label: "Tab", value: "Tab" },
  { label: "回车", value: "Enter" },
  { label: "退格", value: "Backspace" },
  { label: "Esc", value: "Escape" },
];

function clickFrame(event: MouseEvent) {
  if (!props.interactive || !props.session) return;
  const image = event.currentTarget as HTMLImageElement;
  const rect = image.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  image.focus();
  const { width, height } = props.session.viewport;
  emit("input", {
    kind: "click",
    x: Math.max(
      0,
      Math.min(width - 1, Math.floor(((event.clientX - rect.left) * width) / rect.width))
    ),
    y: Math.max(
      0,
      Math.min(height - 1, Math.floor(((event.clientY - rect.top) * height) / rect.height))
    ),
  });
}
function scroll(delta: number) {
  if (props.interactive) emit("input", { kind: "scroll", delta_x: 0, delta_y: delta });
}
function scrollFrame(event: WheelEvent) {
  if (!props.interactive) return;
  const multiplier = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 720 : 1;
  emit("input", {
    kind: "scroll",
    delta_x: Math.max(-1500, Math.min(1500, Math.round(event.deltaX * multiplier))),
    delta_y: Math.max(-1500, Math.min(1500, Math.round(event.deltaY * multiplier))),
  });
}
function sendKey(key: CncLoginKey) {
  if (props.interactive) emit("input", { kind: "key", key });
}
function pressKey(event: KeyboardEvent) {
  // Tab retains local keyboard navigation; the explicit Tab control targets the remote page.
  if (!props.interactive || event.key === "Tab" || event.ctrlKey || event.metaKey || event.altKey)
    return;
  const key = event.key === " " ? "Space" : event.key;
  if (
    keys.some((item) => item.value === key) ||
    ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Delete", "Space"].includes(key)
  ) {
    event.preventDefault();
    sendKey(key as CncLoginKey);
  }
}
function sendText() {
  if (!props.interactive || !manualText.value) return;
  const text = manualText.value;
  manualText.value = "";
  emit("input", { kind: "text", text });
}
</script>

<style scoped lang="scss">
.login-status,
.browser-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.login-notice {
  margin-top: 12px;
}

.login-help {
  margin: 12px 0;
  color: var(--el-text-color-secondary);
}

.browser-frame {
  overflow: hidden;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
}

.browser-frame img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  cursor: pointer;
}

.browser-frame img:focus-visible {
  outline: 3px solid var(--el-color-primary);
  outline-offset: -3px;
}

.frame-placeholder {
  display: grid;
  place-items: center;
  min-height: 240px;
  aspect-ratio: 16 / 9;
  color: var(--el-text-color-secondary);
}

.browser-controls {
  margin-top: 12px;
}

.browser-controls .el-input {
  flex: 1 1 240px;
}

.browser-controls .el-button + .el-button {
  margin-left: 0;
}
</style>
