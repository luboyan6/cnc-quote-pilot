<template>
  <div>
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
  </div>
</template>
<script setup lang="ts">
import { ref, watch } from "vue";
import { ElInput, ElButton } from "element-plus";
import type { CncLoginInput, CncLoginKey } from "@/api/module_cnc/cnc_account";
const props = defineProps<{
  frameUrl: string;
  viewport: { width: number; height: number };
  interactive: boolean;
  preparing: boolean;
  error: string;
  resetKey?: string;
}>();
const emit = defineEmits<{ input: [input: CncLoginInput] }>();
const manualText = ref("");
watch(
  () => [props.resetKey, props.interactive],
  () => {
    manualText.value = "";
  }
);
const keys: { label: string; value: CncLoginKey }[] = [
  { label: "Tab", value: "Tab" },
  { label: "回车", value: "Enter" },
  { label: "退格", value: "Backspace" },
  { label: "Esc", value: "Escape" },
];

function clickFrame(event: MouseEvent) {
  if (!props.interactive) return;
  const image = event.currentTarget as HTMLImageElement;
  const rect = image.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  image.focus();
  const { width, height } = props.viewport;
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
.browser-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
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
