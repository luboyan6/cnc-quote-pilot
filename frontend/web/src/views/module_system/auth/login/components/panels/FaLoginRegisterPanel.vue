<!-- 注册表单组件 -->
<template>
  <div>
    <ElForm
      ref="formRef"
      :model="registerForm"
      :rules="registerRules"
      :key="formKey"
      class="login-page-form"
      @keyup.enter="$emit('submit')"
    >
      <!-- 用户名 -->
      <ElFormItem prop="username">
        <ElInput
          class="custom-height"
          v-model.trim="registerForm.username"
          autocomplete="username"
          clearable
          :placeholder="$t('login.placeholder.username')"
        >
          <template #prefix>
            <FaSvgIcon icon="ri:user-line" class="text-base text-(--el-text-color-placeholder)" />
          </template>
        </ElInput>
      </ElFormItem>

      <!-- 姓名 / 昵称 -->
      <ElFormItem prop="name">
        <ElInput
          class="custom-height"
          v-model.trim="registerForm.name"
          clearable
          :placeholder="$t('register.placeholder.name')"
        >
          <template #prefix>
            <FaSvgIcon icon="ri:badge-line" class="text-base text-(--el-text-color-placeholder)" />
          </template>
        </ElInput>
      </ElFormItem>

      <!-- 登录密码 -->
      <ElTooltip :visible="isCapsLock" :content="$t('login.capsLock')" placement="right">
        <ElFormItem prop="password">
          <ElInput
            class="custom-height"
            v-model.trim="registerForm.password"
            type="password"
            autocomplete="new-password"
            show-password
            clearable
            :placeholder="$t('login.placeholder.password')"
            @keyup="checkCapsLock"
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

      <!-- 确认密码 -->
      <ElTooltip :visible="isCapsLock" :content="$t('login.capsLock')" placement="right">
        <ElFormItem prop="confirmPassword">
          <ElInput
            class="custom-height"
            v-model.trim="registerForm.confirmPassword"
            type="password"
            autocomplete="new-password"
            show-password
            clearable
            :placeholder="$t('login.message.password.confirm')"
            @keyup="checkCapsLock"
          >
            <template #prefix>
              <FaSvgIcon
                icon="ri:lock-check-line"
                class="text-base text-(--el-text-color-placeholder)"
              />
            </template>
          </ElInput>
        </ElFormItem>
      </ElTooltip>

      <!-- 用户服务与隐私条款 -->
      <ElFormItem class="!mb-3">
        <div class="flex flex-wrap items-center gap-1.5 text-sm pt-0.5">
          <ElCheckbox v-model="registerAgreementReadModel" class="login-remember">
            {{ $t("login.agree") }}
          </ElCheckbox>
          <ElLink
            type="primary"
            underline="never"
            class="text-sm font-medium transition-opacity hover:opacity-85"
            :href="userAgreementHref"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ $t("login.userAgreement") }}
          </ElLink>
        </div>
      </ElFormItem>

      <!-- 注册提交按钮 -->
      <div class="mt-4">
        <ElButton
          class="login-submit-btn h-11 w-full rounded-xl! text-base font-semibold shadow-sm transition-all duration-200"
          type="primary"
          :loading="registerLoading"
          v-ripple
          @click="$emit('submit')"
        >
          <span class="flex items-center justify-center gap-2">
            <span>{{ $t("login.register") }}</span>
            <FaSvgIcon icon="ri:user-add-line" class="text-base" />
          </span>
        </ElButton>
      </div>
    </ElForm>

    <FaLoginAuthLinkRow
      :hint="$t('login.haveAccount')"
      :link-text="$t('login.backLoginBtnText')"
      @link="$emit('toLogin')"
    />
  </div>
</template>

<script setup lang="ts">
import type { RegisterForm } from "@/api/module_system/user";
import type { FormRules } from "element-plus";

const registerForm = defineModel<RegisterForm>("registerForm", { required: true });

defineOptions({ name: "FaLoginRegisterPanel" });

interface Props {
  registerRules: FormRules<RegisterForm>;
  formKey: number | string;
  registerLoading: boolean;
  userAgreementHref: string;
}

withDefaults(defineProps<Props>(), {});

const registerAgreementReadModel = defineModel<boolean>("registerAgreementRead", {
  required: true,
});

interface Emits {
  submit: [];
  toLogin: [];
}

const emit = defineEmits<Emits>();

const formRef = ref();
const isCapsLock = ref(false);

function checkCapsLock(event: KeyboardEvent) {
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
  validateField: (prop: string | string[]) => formRef.value?.validateField?.(prop),
});
</script>
