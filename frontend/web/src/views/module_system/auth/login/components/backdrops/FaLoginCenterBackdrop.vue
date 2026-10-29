<!-- 居中布局：与左侧栏一致的科技感渐变底色 + 柔和光晕（不参与交互） -->
<template>
  <div
    class="login-center-backdrop pointer-events-none"
    :class="{ 'login-center-backdrop--viewport-fixed': viewportFixed }"
    aria-hidden="true"
  >
    <div class="login-center-backdrop__bg" />
    <div class="login-center-backdrop__grid" />
    <div class="center-glow center-glow--top" />
    <div class="center-glow center-glow--bottom" />
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "LoginCenterBackdrop" });

interface Props {
  /** 铺满视口并置于底层（与固定顶栏配合） */
  viewportFixed?: boolean;
}

withDefaults(defineProps<Props>(), { viewportFixed: false });
</script>

<style scoped lang="scss">
.login-center-backdrop {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

.login-center-backdrop--viewport-fixed {
  position: fixed;
  inset: 0;
  z-index: 0;
}

.login-center-backdrop__bg {
  position: absolute;
  inset: 0;
  background-color: color-mix(
    in srgb,
    var(--el-color-primary-light-9) 70%,
    var(--default-box-color)
  );
  transition: background-color 0.3s ease;
}

.login-center-backdrop__grid {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(
    circle,
    color-mix(in srgb, var(--el-color-primary) 10%, transparent) 1px,
    transparent 1px
  );
  background-size: 28px 28px;
  mask-image: radial-gradient(ellipse at center, rgb(0 0 0 / 100%) 20%, rgb(0 0 0 / 10%) 80%);
}

.center-glow {
  position: absolute;
  pointer-events: none;
  border-radius: 9999px;
  opacity: 0.4;
  filter: blur(90px);
  transition: all 0.5s ease;
}

.center-glow--top {
  top: 5%;
  left: 20%;
  width: 450px;
  height: 450px;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--el-color-primary) 45%, transparent) 0%,
    transparent 70%
  );
}

.center-glow--bottom {
  right: 18%;
  bottom: 8%;
  width: 400px;
  height: 400px;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--el-color-success) 35%, transparent) 0%,
    transparent 70%
  );
}

html.dark .login-center-backdrop__bg {
  background-color: color-mix(in srgb, var(--el-color-primary-light-9) 25%, #0b0f19);
}

html.dark .center-glow {
  opacity: 0.22;
}
</style>
