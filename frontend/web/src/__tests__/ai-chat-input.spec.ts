import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/api/module_ai/chat", () => ({
  default: {
    getModelConfig: vi
      .fn()
      .mockResolvedValue({ data: { code: 0, data: { items: [], active_id: null } } }),
  },
}));

import ChatInput from "@/views/module_ai/chat/components/FaChatInput.vue";

const Input = defineComponent({
  name: "ElInput",
  props: ["modelValue"],
  emits: ["update:modelValue"],
  template:
    "<textarea :value='modelValue' @input=\"$emit('update:modelValue', $event.target.value)\" />",
});
const Button = defineComponent({ name: "ElButton", template: "<button><slot /></button>" });

describe("聊天输入草稿", () => {
  it("直到发送被接收才清空文本", async () => {
    const wrapper = mount(ChatInput, {
      global: {
        stubs: {
          ElInput: Input,
          ElButton: Button,
          ElForm: { template: "<div><slot /></div>" },
          ElUpload: { template: "<div><slot /></div>" },
          ElDropdown: { template: "<div><slot /></div>" },
          ElTooltip: { template: "<span><slot /></span>" },
          ElIcon: { template: "<span><slot /></span>" },
        },
      },
    });
    await flushPromises();
    await wrapper.get("textarea").setValue("保留的草稿");
    await wrapper.get('[aria-label="发送消息"]').trigger("click");
    const sent = wrapper.emitted("send")?.[0];
    expect(sent?.[0]).toBe("保留的草稿");
    expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe("保留的草稿");
    (sent?.[2] as () => void)();
    await nextTick();
    expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe("");
    wrapper.unmount();
  });
});
