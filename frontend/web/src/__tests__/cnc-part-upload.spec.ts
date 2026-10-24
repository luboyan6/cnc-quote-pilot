import { flushPromises, mount } from "@vue/test-utils";
import { computed, defineComponent, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useCrudDialog } from "@/hooks/core/useCrudDialog";
import type { CncPartForm } from "@/api/module_cnc/cnc_part";

const mocks = vi.hoisted(() => ({
  post: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  detail: vi.fn(),
  download: vi.fn(),
  checkPerm: vi.fn(),
}));
vi.mock("@utils", async () => {
  const { h, ref } = await import("vue");
  return {
    request: { post: mocks.post },
    renderTableOperationCell: (actions: { key: string; run: () => void }[]) =>
      h("button", { class: "edit", onClick: actions.find((a) => a.key === "edit")?.run }, "编辑"),
    resolveStatusColumns: (factory: unknown) => factory,
    stripPaginationParams: () => ({}),
    toCrudCols: () => ref([]),
  };
});
vi.mock("@/utils/checkPerm", () => ({ checkPerm: mocks.checkPerm }));
vi.mock("@/utils/download", () => ({ default: { name: mocks.download } }));
vi.mock("@/api/module_cnc/cnc_part", () => ({
  default: {
    createCncPart: mocks.create,
    updateCncPart: mocks.update,
    detailCncPart: mocks.detail,
  },
}));
vi.mock("@/components/forms/fa-form/index.vue", async () => {
  const { defineComponent, h } = await import("vue");
  return {
    default: defineComponent({
      name: "FaForm",
      props: ["modelValue"],
      setup(_props, { slots, expose }) {
        expose({ validate: async () => true, resetFields: () => {}, clearValidate: () => {} });
        return () => h("div", slots.upload_step?.());
      },
    }),
  };
});
vi.mock("@/components/display/fa-descriptions/index.vue", () => ({ default: {} }));
vi.mock("@/components/tables/fa-table-header/index.vue", () => ({
  default: { template: "<div><slot name='left' /></div>" },
}));

import PartPage from "@/views/module_cnc/cnc_part/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";

const Dialog = defineComponent({
  props: ["modelValue", "confirmLoading"],
  emits: ["confirm", "cancel"],
  template: `<section v-if="modelValue"><slot />
    <button class="confirm" @click="$emit('confirm')">确定</button>
    <button class="cancel" @click="$emit('cancel')">取消</button>
  </section>`,
});
const Table = defineComponent({
  props: ["columns"],
  setup(props) {
    return () =>
      props.columns.find((c: { prop?: string }) => c.prop === "operation").formatter({ id: 7 });
  },
});
const mounted: ReturnType<typeof mount>[] = [];
function mountPage() {
  const wrapper = mount(PartPage, {
    global: {
      stubs: {
        FaSearchBar: true,
        FaTableHeaderLeft: { template: `<button class="add" @click="$emit('add')">新增</button>` },
        FaTable: Table,
        FaDialog: Dialog,
        FaImportDialog: true,
        FaExportDialog: true,
        ElCard: { template: "<div><slot /></div>" },
        ElButton: { template: "<button><slot /></button>" },
        ElIcon: { template: "<span><slot /></span>" },
        ElTag: { template: "<span><slot /></span>" },
      },
    },
  });
  mounted.push(wrapper);
  return wrapper;
}
function uploadResponse(path = "E:\\uploads\\part.step") {
  return { data: { code: 0, data: { file_path: path, origin_name: "零件.STEP" } } };
}
async function selectFile(wrapper: ReturnType<typeof mount>, file: File) {
  const input = wrapper.get<HTMLInputElement>('input[type="file"]');
  Object.defineProperty(input.element, "files", { configurable: true, value: [file] });
  await input.trigger("change");
}
function form(wrapper: ReturnType<typeof mount>) {
  return wrapper.findComponent(FaForm).props("modelValue") as CncPartForm;
}
beforeEach(() => {
  Object.values(mocks).forEach((mock) => mock.mockReset());
  mocks.checkPerm.mockReturnValue(true);
  mocks.post.mockResolvedValue(uploadResponse());
  mocks.create.mockResolvedValue({});
  mocks.update.mockResolvedValue({});
  mocks.detail.mockResolvedValue({
    data: {
      data: {
        id: 7,
        file_name: "旧图纸.stp",
        file_path: "E:/uploads/old.stp",
        validation_status: "HEADER_VALID",
        upload_authorized: true,
        declared_unit: "mm",
        file_type: 1,
      },
    },
  });
  vi.spyOn(ElMessage, "success").mockImplementation(() => ({ close: vi.fn() }));
  vi.spyOn(ElMessage, "warning").mockImplementation(() => ({ close: vi.fn() }));
  vi.spyOn(ElMessage, "error").mockImplementation(() => ({ close: vi.fn() }));
  vi.spyOn(console, "error").mockImplementation(() => {});
  for (const [name, value] of Object.entries({ computed, reactive, ref, useCrudDialog })) {
    vi.stubGlobal(name, value);
  }
  vi.stubGlobal("useTableSelection", () => ({
    selectedRows: ref([]),
    selectedIds: ref([]),
    batchDeleting: ref(false),
    onTableSelectionChange: vi.fn(),
  }));
  vi.stubGlobal("useTable", (options: { core: { columnsFactory: () => unknown[] } }) => ({
    columns: ref(options.core.columnsFactory()),
    columnChecks: ref([]),
    data: ref([]),
    loading: ref(false),
    pagination: {},
    searchParams: {},
    refreshCreate: vi.fn(),
    refreshUpdate: vi.fn(),
  }));
  vi.stubGlobal("useImportExport", () => ({
    importVisible: ref(false),
    exportVisible: ref(false),
    openImport: vi.fn(),
    openExport: vi.fn(),
  }));
});
afterEach(() => {
  mounted.splice(0).forEach((wrapper) => wrapper.unmount());
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("图纸新增和修改上传", () => {
  it.each(["part.step", "part.STP", "part.setp"])(
    "支持 %s 并在缺少原名时使用选中文件名",
    async (name) => {
      mocks.post.mockResolvedValueOnce({
        data: { code: 0, data: { file_path: "static/upload/part.step" } },
      });
      const wrapper = mountPage();
      await wrapper.get(".add").trigger("click");
      await selectFile(wrapper, new File(["data"], name));
      await flushPromises();
      expect(form(wrapper).file_name).toBe(name);
      expect(form(wrapper).extension).toBe(name.split(".").pop()?.toLowerCase());
    }
  );

  it("移除图纸同时清除旧单位、类型和第三方授权", async () => {
    const wrapper = mountPage();
    await wrapper.get(".edit").trigger("click");
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((button) => button.text() === "移除")!
      .trigger("click");
    expect(form(wrapper)).toMatchObject({ upload_authorized: false, declared_unit: "" });
    for (const field of [
      "file_name",
      "file_path",
      "extension",
      "size_bytes",
      "validation_status",
      "file_type",
    ] as const) {
      expect(form(wrapper)[field]).toBeUndefined();
    }
  });

  it("没有文件上传或下载权限时禁用控件且不调用接口", async () => {
    mocks.checkPerm.mockReturnValue(false);
    const wrapper = mountPage();
    await wrapper.get(".edit").trigger("click");
    await flushPromises();
    expect(wrapper.get('input[type="file"]').attributes("disabled")).toBeDefined();
    for (const label of ["重新上传", "下载"]) {
      expect(
        wrapper
          .findAll("button")
          .find((button) => button.text() === label)!
          .attributes("disabled")
      ).toBeDefined();
    }
    await selectFile(wrapper, new File(["data"], "denied.step"));
    expect(mocks.post).not.toHaveBeenCalled();
    expect(mocks.download).not.toHaveBeenCalled();
    expect(form(wrapper).file_path).toBe("E:/uploads/old.stp");
  });

  it("卸载页面时中止上传并忽略迟到结果", async () => {
    let resolveUpload!: (value: ReturnType<typeof uploadResponse>) => void;
    mocks.post.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveUpload = resolve;
      })
    );
    const wrapper = mountPage();
    await wrapper.get(".add").trigger("click");
    await selectFile(wrapper, new File(["data"], "part.step"));
    const signal = mocks.post.mock.calls[0]![2].signal as AbortSignal;
    wrapper.unmount();
    expect(signal.aborted).toBe(true);
    resolveUpload(uploadResponse());
    await flushPromises();
    expect(ElMessage.error).not.toHaveBeenCalled();
  });

  it("上传后填充原名、本地路径、扩展名和字节大小，并随新增表单保存", async () => {
    let createdForm: CncPartForm | undefined;
    mocks.create.mockImplementationOnce(async (data: CncPartForm) => {
      createdForm = { ...data };
    });
    const wrapper = mountPage();
    await wrapper.get(".add").trigger("click");
    await selectFile(wrapper, new File(["STEP data"], "零件.STEP"));
    await flushPromises();
    expect(mocks.post).toHaveBeenCalledTimes(1);
    const uploadCall = mocks.post.mock.calls[0]!;
    expect(uploadCall[0]).toBe("/common/file/upload");
    expect(uploadCall[1].get("file").name).toBe("零件.STEP");
    expect(uploadCall[2].params).toEqual({ upload_type: "file" });
    expect(form(wrapper)).toMatchObject({
      file_name: "零件.STEP",
      file_path: "E:/uploads/part.step",
      extension: "step",
      size_bytes: 9,
      validation_status: "PENDING",
      upload_authorized: false,
    });
    expect(form(wrapper).declared_unit).toBe("");
    await wrapper.get(".confirm").trigger("click");
    await flushPromises();
    expect(createdForm).toMatchObject({ file_path: "E:/uploads/part.step" });
  });

  it("修改时回显旧文件，替换后保存新路径并重置校验状态", async () => {
    const wrapper = mountPage();
    await wrapper.get(".edit").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("旧图纸.stp");
    const downloadButton = wrapper.findAll("button").find((button) => button.text() === "下载")!;
    await downloadButton.trigger("click");
    expect(mocks.download).toHaveBeenCalledWith("E:/uploads/old.stp", false);
    await selectFile(wrapper, new File(["new part"], "new.setp"));
    await flushPromises();
    expect(form(wrapper)).toMatchObject({
      extension: "setp",
      validation_status: "PENDING",
      upload_authorized: false,
    });
    expect(form(wrapper).declared_unit).toBe("");
    expect(form(wrapper).file_type).toBeUndefined();
    await wrapper.get(".confirm").trigger("click");
    await flushPromises();
    expect(mocks.update).toHaveBeenCalledWith(
      7,
      expect.objectContaining({
        file_path: "E:/uploads/part.step",
        declared_unit: "",
        upload_authorized: false,
      })
    );
  });

  it("拒绝其他格式、空文件和超过 50MB 的文件", async () => {
    const wrapper = mountPage();
    await wrapper.get(".add").trigger("click");
    await selectFile(wrapper, new File(["text"], "part.txt"));
    await selectFile(wrapper, new File([], "empty.stp"));
    const oversized = new File(["data"], "big.step");
    Object.defineProperty(oversized, "size", { value: 50 * 1024 * 1024 + 1 });
    await selectFile(wrapper, oversized);
    expect(mocks.post).not.toHaveBeenCalled();
    expect(ElMessage.warning).toHaveBeenCalledTimes(3);
  });

  it.each(["网络失败", "缺少存储路径"])("%s 时保留修改前的图纸", async (failure) => {
    const wrapper = mountPage();
    await wrapper.get(".edit").trigger("click");
    await flushPromises();
    if (failure === "网络失败") mocks.post.mockRejectedValueOnce(new Error("网络失败"));
    else mocks.post.mockResolvedValueOnce({ data: { code: 0, data: { file_url: "/part.step" } } });
    await selectFile(wrapper, new File(["data"], "new.step"));
    await flushPromises();
    expect(form(wrapper).file_path).toBe("E:/uploads/old.stp");
    expect(form(wrapper).file_name).toBe("旧图纸.stp");
    expect(form(wrapper).upload_authorized).toBe(true);
    expect(form(wrapper).declared_unit).toBe("mm");
    expect(ElMessage.error).toHaveBeenCalled();
  });

  it("上传中阻止保存及重复上传，关闭后忽略旧请求的结果", async () => {
    let resolveUpload!: (value: ReturnType<typeof uploadResponse>) => void;
    mocks.post.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveUpload = resolve;
      })
    );
    const wrapper = mountPage();
    await wrapper.get(".add").trigger("click");
    await selectFile(wrapper, new File(["data"], "first.stp"));
    await selectFile(wrapper, new File(["data"], "second.stp"));
    await wrapper.get(".confirm").trigger("click");
    expect(mocks.post).toHaveBeenCalledTimes(1);
    expect(mocks.create).not.toHaveBeenCalled();
    expect(wrapper.findComponent(Dialog).props("confirmLoading")).toBe(true);
    const signal = mocks.post.mock.calls[0]![2].signal as AbortSignal;
    await wrapper.get(".cancel").trigger("click");
    expect(signal.aborted).toBe(true);
    await wrapper.get(".add").trigger("click");
    resolveUpload(uploadResponse());
    await flushPromises();
    expect(form(wrapper).file_path).toBeUndefined();
    expect(ElMessage.success).not.toHaveBeenCalled();
  });
});
