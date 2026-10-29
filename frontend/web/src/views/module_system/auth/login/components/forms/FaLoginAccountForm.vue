<!-- 账号密码登录表单（含快捷角色切换、验证码、滑块及辅助登录） -->
<template>
  <div>
    <ElForm
      ref="formRef"
      :model="loginForm"
      :rules="rules"
      :key="formKey"
      class="login-page-form"
      :validate-on-rule-change="false"
      @keyup.enter="$emit('submit')"
    >
      <!-- 快捷角色体验分段选择器（提升演示与日常调试效率） -->
      <div class="demo-account-switcher mb-3">
        <div class="flex items-center justify-between mb-1.5 px-0.5">
          <span
            class="text-xs font-medium text-(--el-text-color-secondary) flex items-center gap-1.5"
          >
            <FaSvgIcon icon="ri:user-shared-line" class="text-xs text-primary" />
            {{ $t("login.quickSelectAccount") || "快速切换预设角色" }}
          </span>
          <span class="text-[11px] text-(--el-color-primary) font-medium opacity-85"
            >点击即一键填入</span
          >
        </div>
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="account in accounts"
            :key="account.key"
            type="button"
            class="role-select-chip flex flex-col items-center justify-center py-2 px-1.5 rounded-xl border text-xs font-medium transition-all duration-200 outline-none select-none cursor-pointer"
            :class="
              demoAccountKey === account.key
                ? 'role-select-chip--active'
                : 'role-select-chip--inactive'
            "
            @click="$emit('setupAccount', account.key)"
          >
            <div class="flex items-center gap-1">
              <FaSvgIcon
                :icon="
                  account.key === 'super'
                    ? 'ri:shield-user-fill'
                    : account.key === 'admin'
                      ? 'ri:user-settings-fill'
                      : 'ri:user-3-fill'
                "
                class="text-xs"
              />
              <span class="truncate font-semibold">{{ account.label }}</span>
            </div>
            <span class="text-[10px] opacity-70 font-mono mt-0.5">{{ account.username }}</span>
          </button>
        </div>
      </div>

      <!-- 用户名输入框 -->
      <ElFormItem prop="username">
        <ElInput
          class="custom-height"
          v-model.trim="loginForm.username"
          autocomplete="username"
          clearable
          :placeholder="$t('login.placeholder.username')"
        >
          <template #prefix>
            <FaSvgIcon icon="ri:user-line" class="text-base text-(--el-text-color-placeholder)" />
          </template>
        </ElInput>
      </ElFormItem>

      <!-- 密码输入框 -->
      <ElTooltip :visible="isCapsLock" :content="$t('login.capsLock')" placement="right">
        <ElFormItem prop="password">
          <ElInput
            class="custom-height"
            v-model.trim="loginForm.password"
            type="password"
            autocomplete="current-password"
            show-password
            clearable
            :placeholder="$t('login.placeholder.password')"
            @keyup="onPasswordKeyup"
          >
            <template #prefix>
              <FaSvgIcon
                icon="ri:lock-password-line"
                class="text-base text-(--el-text-color-placeholder)"
              />
            </template>
          </ElInput>
        </ElFormItem>
      </ElTooltip>

      <div class="login-form-tail flex flex-col gap-3.5">
        <!-- 滑块人机验证 -->
        <div class="relative pb-2">
          <div
            class="relative z-2 overflow-hidden select-none rounded-xl border border-transparent transition duration-300"
            :class="{ 'border-[#FF4E4F]!': !isPassing && isClickPass }"
          >
            <FaDragVerify
              ref="dragVerifyRef"
              v-model:value="isPassing"
              :text="$t('login.sliderText')"
              :text-color="dragVerifyTextColor"
              :success-text="$t('login.sliderSuccessText')"
              progress-bar-bg="var(--el-color-success)"
              :background="isDark ? '#232733' : 'var(--el-fill-color-light)'"
              handler-bg="var(--default-box-color)"
            />
          </div>
          <p
            class="absolute top-0 z-1 mt-1 px-1 text-xs text-[#f56c6c] transition duration-300"
            :class="{ 'translate-y-10': !isPassing && isClickPass }"
          >
            {{ $t("login.placeholder.slider") }}
          </p>
        </div>

        <!-- 记住我 与 忘记密码 -->
        <div class="login-options-row flex items-center justify-between text-sm pt-0.5">
          <ElCheckbox v-model="loginForm.remember" class="login-remember">
            {{ $t("login.rememberPwd") }}
          </ElCheckbox>
          <ElLink
            type="primary"
            underline="never"
            class="inline-flex items-center text-sm font-medium leading-[inherit]! transition-opacity hover:opacity-85"
            @click="$emit('forget')"
          >
            {{ $t("login.forgetPwd") }}
          </ElLink>
        </div>

        <!-- 登录主操作按钮 -->
        <div>
          <ElButton
            class="login-submit-btn h-11 w-full rounded-xl! text-base font-semibold shadow-sm transition-all duration-200"
            type="primary"
            :loading="loading"
            v-ripple
            @click="$emit('submit')"
          >
            <span class="flex items-center justify-center gap-2">
              <span>{{ $t("login.btnText") }}</span>
              <FaSvgIcon icon="ri:arrow-right-line" class="text-base" />
            </span>
          </ElButton>
        </div>

        <!-- 辅助登录方式（手机/扫码） -->
        <div class="login-secondary-actions grid grid-cols-2 gap-2.5">
          <ElButton
            class="login-secondary-btn flex items-center justify-center gap-1.5"
            plain
            @click="$emit('openMobile')"
          >
            <FaSvgIcon icon="ri:smartphone-line" class="text-sm" />
            <span>{{ $t("login.mobileLogin") }}</span>
          </ElButton>
          <ElButton
            class="login-secondary-btn flex items-center justify-center gap-1.5"
            plain
            @click="$emit('openQr')"
          >
            <FaSvgIcon icon="ri:qr-code-line" class="text-sm" />
            <span>{{ $t("login.qrLogin") }}</span>
          </ElButton>
        </div>
      </div>
    </ElForm>

    <FaLoginThirdPartySection @oauth="$emit('oauth', $event)" />

    <FaLoginAuthLinkRow
      :hint="$t('login.noAccount')"
      :link-text="$t('login.register')"
      @link="$emit('register')"
    />
  </div>
</template>

<script setup lang="ts">
import type { CaptchaInfo, LoginFormData } from "@/api/module_system/auth";
import type { FormRules } from "element-plus";
import type { Account, AccountKey } from "@views/module_system/auth/login/types";

const loginForm = defineModel<LoginFormData>("loginForm", { required: true });

defineOptions({ name: "FaLoginAccountForm" });

interface Props {
  rules: FormRules;
  captchaState: CaptchaInfo;
  codeLoading: boolean;
  demoAccountKey: AccountKey;
  accounts: Account[];
  formKey: number | string;
  isDark: boolean;
  dragVerifyTextColor: string;
  loading: boolean;
}

withDefaults(defineProps<Props>(), {});

const isPassing = defineModel<boolean>("isPassing", { required: true });
const isClickPass = defineModel<boolean>("isClickPass", { required: true });

interface Emits {
  submit: [];
  setupAccount: [key: AccountKey];
  getCaptcha: [];
  openMobile: [];
  openQr: [];
  forget: [];
  register: [];
  oauth: [provider: "wechat" | "qq" | "github" | "gitee"];
}

const emit = defineEmits<Emits>();

const formRef = ref();
const dragVerifyRef = ref<{ reset?: () => void } | null>(null);
const isCapsLock = ref(false);

function onPasswordKeyup(event: KeyboardEvent) {
  if (event instanceof KeyboardEvent) {
    isCapsLock.value = event.getModifierState("CapsLock");
    if (event.key === "Enter") {
      emit("submit");
    }
  }
}

defineExpose({
  validate: () => formRef.value?.validate?.(),
  clearValidate: () => formRef.value?.clearValidate?.(),
  resetDragVerify: () => dragVerifyRef.value?.reset?.(),
});
</script>

<style scoped lang="scss">
.role-select-chip--active {
  color: var(--el-color-primary);
  background-color: color-mix(in srgb, var(--el-color-primary) 12%, transparent);
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--el-color-primary) 30%, transparent);
}

.role-select-chip--inactive {
  color: var(--el-text-color-regular);
  background-color: var(--el-fill-color-light);
  border-color: var(--el-border-color-lighter);

  &:hover {
    color: var(--el-color-primary);
    background-color: color-mix(in srgb, var(--el-color-primary) 6%, transparent);
    border-color: var(--el-color-primary-light-5);
  }
}

html.dark {
  .role-select-chip--active {
    background-color: color-mix(in srgb, var(--el-color-primary) 22%, transparent);
  }

  .role-select-chip--inactive {
    background-color: rgb(255 255 255 / 4%);
    border-color: rgb(255 255 255 / 10%);

    &:hover {
      background-color: rgb(255 255 255 / 8%);
    }
  }
}
</style>
