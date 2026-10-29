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
      在下方平台页面操作（支持点击与拖动）；完成验证码或登录后点击“验证登录”。关闭窗口会释放浏览器。
    </p>
    <ControlledBrowser
      :frame-url="frameUrl"
      :viewport="session?.viewport || { width: 1280, height: 720 }"
      :interactive="interactive"
      :preparing="preparing"
      :error="error"
      :reset-key="`${visible}-${session?.session_id}`"
      @input="emit('input', $event)"
    />
    <template #footer>
      <ElButton @click="emit('close')">关闭浏览器</ElButton>
      <ElButton type="primary" :loading="busy" :disabled="!interactive" @click="emit('verify')">
        验证登录
      </ElButton>
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { ElAlert, ElButton, ElDialog, ElTag } from "element-plus";
import type { CncLoginInput, CncLoginSession, CncLoginStatus } from "@/api/module_cnc/cnc_account";

import ControlledBrowser from "../components/ControlledBrowser.vue";

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
  browser_failed: "登录服务浏览器启动失败，请检查服务器浏览器依赖或联系管理员。",
  browser_cleanup_failed: "浏览器会话清理异常，请关闭窗口后重试。",
  BROWSER_UNAVAILABLE: "登录服务浏览器暂时不可用，请稍后重试或联系管理员。",
};
const reasonLabel = computed(
  () =>
    reasons[props.session?.reason || ""] ||
    (props.session?.status === "FAILED"
      ? props.session?.reason
        ? `登录失败（${props.session.reason}），请关闭窗口后重试。`
        : "登录未通过核验，请关闭窗口后检查账号与平台配置。"
      : "请在平台页面完成所需操作，然后点击验证登录。")
);
</script>

<style scoped lang="scss">
.login-status {
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
</style>
