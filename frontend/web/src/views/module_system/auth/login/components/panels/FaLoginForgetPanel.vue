<!-- 重置密码 / 忘记密码 -->
<template>
  <div>
    <ElForm
      ref="formRef"
      :model="forgetForm"
      :rules="forgetRules"
      :key="formKey"
      class="login-page-form"
      @keyup.enter="$emit('submit')"
    >
      <ElFormItem prop="username">
        <ElInput
          v-model.trim="forgetForm.username"
          class="custom-height"
          autocomplete="username"
          clearable
          :placeholder="$t('login.placeholder.username')"
          @keyup.enter="$emit('submit')"
        >
          <template #prefix>
            <FaSvgIcon icon="ri:user-line" class="text-base text-(--el-text-color-placeholder)" />
          </template>
        </ElInput>
      </ElFormItem>

      <div class="mt-6">
        <ElButton
          class="login-submit-btn h-11 w-full min-w-0 rounded-xl! text-base font-semibold shadow-sm transition-all duration-200"
          type="primary"
          :loading="forgetLoading"
          v-ripple
          @click="$emit('submit')"
        >
          <span class="flex items-center justify-center gap-2">
            <span>{{ $t("common.confirm") }}</span>
            <FaSvgIcon icon="ri:check-line" class="text-base" />
          </span>
        </ElButton>
      </div>
    </ElForm>

    <FaLoginAuthLinkRow
      :hint="$t('login.thinkOfPasswd')"
      :link-text="$t('login.backLoginBtnText')"
      @link="$emit('toLogin')"
    />
  </div>
</template>

<script setup lang="ts">
import type { ForgetPasswordForm } from "@/api/module_system/user";
import type { FormRules } from "element-plus";

const forgetForm = defineModel<ForgetPasswordForm>("forgetForm", { required: true });

defineOptions({ name: "FaLoginForgetPanel" });

interface Props {
  forgetRules: FormRules<ForgetPasswordForm>;
  formKey: number | string;
  forgetLoading: boolean;
}

withDefaults(defineProps<Props>(), {});

interface Emits {
  submit: [];
  toLogin: [];
}

defineEmits<Emits>();

const formRef = ref();

defineExpose({
  validate: () => formRef.value?.validate?.(),
  clearValidate: () => formRef.value?.clearValidate?.(),
});
</script>
