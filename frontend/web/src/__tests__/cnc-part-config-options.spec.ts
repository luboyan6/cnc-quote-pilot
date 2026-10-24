import { flushPromises, mount } from "@vue/test-utils";
import ElementPlus, { ElOption, ElSelect } from "element-plus";
import { computed, defineComponent, h, reactive, ref, toRefs, useTemplateRef } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useCrudDialog } from "@/hooks/core/useCrudDialog";
import type { CncPartConfigForm } from "@/api/module_cnc/cnc_part_config";

const mocks = vi.hoisted(() => ({
  listPlatforms: vi.fn(),
  listParts: vi.fn(),
  detail: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  quoteAccounts: vi.fn(),
  checkPerm: vi.fn(),
  renderOperations: vi.fn(),
}));
vi.mock("@/api/module_cnc/cnc_platform", () => ({
  default: { listCncPlatform: mocks.listPlatforms },
}));
vi.mock("@/api/module_cnc/cnc_part", () => ({ default: { listCncPart: mocks.listParts } }));
vi.mock("@/api/module_cnc/cnc_part_config", () => ({
  default: {
    detailCncPartConfig: mocks.detail,
    createCncPartConfig: mocks.create,
    updateCncPartConfig: mocks.update,
    quoteAccounts: mocks.quoteAccounts,
  },
}));
vi.mock("@/utils/checkPerm", () => ({ checkPerm: mocks.checkPerm }));
vi.mock("@utils", async () => {
  const { h, ref } = await import("vue");
  return {
    renderTableOperationCell: (actions: { key: string; label: string; run: () => void }[]) => {
      mocks.renderOperations(actions);
      return h(
        "div",
        actions
          .filter((action) => action.key !== "delete")
          .map((action) => h("button", { class: action.key, onClick: action.run }, action.label))
      );
    },
    resolveStatusColumns: (factory: unknown) => factory,
    stripPaginationParams: () => ({}),
    toCrudCols: () => ref([]),
    calculateResponsiveSpan: (itemSpan: number | undefined, span: number) => itemSpan ?? span,
  };
});
vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock("@/components/forms/fa-search-bar/FaDatePicker.vue", () => ({ default: {} }));
vi.mock("@/components/forms/fa-file-upload/index.vue", () => ({ default: {} }));
vi.mock("@/components/actions/fa-upload/index.vue", () => ({ default: {} }));
vi.mock("@/components/forms/fa-wang-editor/index.vue", () => ({ default: {} }));
vi.mock("@/components/tables/fa-table-header/index.vue", () => ({
  default: { template: "<div><slot name='left' /></div>" },
}));

import ConfigPage from "@/views/module_cnc/cnc_part_config/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";

const Dialog = defineComponent({
  props: ["modelValue"],
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
      h("div", [
        h(
          "span",
          { class: "part-name" },
          props.columns
            .find((c: { prop?: string }) => c.prop === "part_id")
            .formatter({ part_id: 205 })
        ),
        h(
          "span",
          { class: "platform-name" },
          props.columns
            .find((c: { prop?: string }) => c.prop === "site_type")
            .formatter({ site_type: 1 })
        ),
        props.columns
          .find((c: { prop?: string }) => c.prop === "operation")
          .formatter({ id: 4, part_id: 205, enabled: true }),
      ]);
  },
});
const mounted: ReturnType<typeof mount>[] = [];
function mountPage() {
  const wrapper = mount(ConfigPage, {
    global: {
      plugins: [ElementPlus],
      stubs: {
        FaSearchBar: true,
        FaTableHeaderLeft: { template: `<button class="add" @click="$emit('add')">新增</button>` },
        FaTable: Table,
        FaDialog: Dialog,
        FaImportDialog: true,
        FaExportDialog: true,
        FaJsonPretty: true,
        AutoQuoteDialog: true,
      },
      directives: { ripple: {} },
    },
  });
  mounted.push(wrapper);
  return wrapper;
}
function page<T>(items: T[], hasNext = false) {
  return { data: { data: { items, has_next: hasNext } } };
}
function platformSelect(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAllComponents(ElSelect)[0]!;
}
function partSelect(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAllComponents(ElSelect)[1]!;
}
beforeEach(() => {
  Object.values(mocks).forEach((mock) => mock.mockReset());
  mocks.checkPerm.mockReturnValue(true);
  mocks.quoteAccounts.mockResolvedValue({ data: { code: 0, data: [] } });
  mocks.listPlatforms.mockResolvedValue(
    page([
      { id: 1, name: "Xometry" },
      { id: 2, name: "嘉立创" },
    ])
  );
  mocks.listParts.mockResolvedValue(page([{ id: 205, file_name: "装配图.step" }]));
  mocks.detail.mockResolvedValue({
    data: {
      data: {
        id: 4,
        name: "测试配置",
        site_type: 1,
        material: "铝合金",
        quantity: 1,
        part_id: 205,
      },
    },
  });
  mocks.create.mockResolvedValue({});
  mocks.update.mockResolvedValue({});
  vi.spyOn(console, "error").mockImplementation(() => {});
  for (const [name, value] of Object.entries({
    computed,
    reactive,
    ref,
    toRefs,
    useTemplateRef,
    useCrudDialog,
  })) {
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
  document.body.innerHTML = "";
});

describe("配置关联竞价平台与图纸选择", () => {
  it("每行操作包含自动报价，点击按当前配置请求账号；缺少账号操作权限时隐藏入口", async () => {
    const wrapper = mountPage();
    await flushPromises();
    const latestActions = mocks.renderOperations.mock.calls.at(-1)?.[0] as {
      key: string;
      label: string;
      artType: string;
      icon?: string;
    }[];
    const quoteAction = latestActions?.find((a) => a.key === "quote");
    expect(quoteAction).toMatchObject({
      key: "quote",
      label: "自动报价",
      artType: "more",
      icon: "ri:money-cny-circle-line",
    });
    const button = wrapper.findAll("button").find((item) => item.text() === "自动报价");
    expect(button).toBeDefined();
    await button!.trigger("click");
    await flushPromises();
    expect(mocks.quoteAccounts).toHaveBeenCalledWith(4, expect.any(AbortSignal));
    expect(wrapper.getComponent({ name: "AutoQuoteDialog" }).props("error")).toContain(
      "没有可用账号"
    );
    mocks.checkPerm.mockImplementation(
      (permission: string) => permission !== "module_cnc:cnc_account:update"
    );
    const denied = mountPage();
    await flushPromises();
    expect(denied.findAll("button").some((item) => item.text() === "自动报价")).toBe(false);
  });

  it("加载平台接口并渲染下拉选项，新增时提交选中平台 ID", async () => {
    let created: CncPartConfigForm | undefined;
    mocks.create.mockImplementation(async (data: CncPartConfigForm) => {
      created = { ...data };
    });
    const wrapper = mountPage();
    await flushPromises();
    await wrapper.get(".add").trigger("click");
    await flushPromises();

    const pSelect = platformSelect(wrapper);
    expect(pSelect.findAllComponents(ElOption).map((opt) => opt.props("label"))).toEqual([
      "Xometry",
      "嘉立创",
    ]);

    pSelect.vm.$emit("update:modelValue", 2);
    partSelect(wrapper).vm.$emit("update:modelValue", 205);
    await wrapper.get('input[placeholder="请输入配置名称（最多6个字）"]').setValue("新配置");
    await wrapper.get('input[placeholder="请输入加工材料，例如：铝合金 6061"]').setValue("铝合金");
    await wrapper.get(".confirm").trigger("click");
    await flushPromises();

    expect(created).toMatchObject({ site_type: 2, part_id: 205 });
  });

  it("图纸下拉只展示名称无需展示ID，新增时提交数字图纸 ID", async () => {
    let created: CncPartConfigForm | undefined;
    mocks.create.mockImplementation(async (data: CncPartConfigForm) => {
      created = { ...data };
    });
    mocks.listParts.mockImplementation(({ page_no }: { page_no: number }) =>
      Promise.resolve(
        page_no === 1
          ? page([{ id: 101, file_name: "零件A.step" }], true)
          : page([{ id: 205, file_name: "零件B.step" }])
      )
    );
    const wrapper = mountPage();
    await flushPromises();
    await wrapper.get(".add").trigger("click");
    await flushPromises();
    const select = partSelect(wrapper);
    expect(select.findAllComponents(ElOption).map((option) => option.props("label"))).toEqual([
      "零件A.step",
      "零件B.step",
    ]);
    expect(mocks.listParts).toHaveBeenCalledWith({ page_no: 2, page_size: 100 });
    select.vm.$emit("update:modelValue", 205);
    await wrapper.get('input[placeholder="请输入配置名称（最多6个字）"]').setValue("新配置");
    await wrapper.get('input[placeholder="请输入加工材料，例如：铝合金 6061"]').setValue("铝合金");
    platformSelect(wrapper).vm.$emit("update:modelValue", 1);
    await wrapper.get(".confirm").trigger("click");
    await flushPromises();
    expect(created).toMatchObject({ part_id: 205 });
  });

  it("列表显示图纸名称与平台名称，修改时按 ID 回显并可更换图纸", async () => {
    mocks.listParts.mockResolvedValue(
      page([
        { id: 205, file_name: "装配图.step" },
        { id: 301, file_name: "新图纸.stp" },
      ])
    );
    const wrapper = mountPage();
    await flushPromises();
    expect(wrapper.get(".part-name").text()).toBe("装配图.step");
    expect(wrapper.get(".platform-name").text()).toBe("Xometry");
    await wrapper.get(".edit").trigger("click");
    await flushPromises();
    const select = partSelect(wrapper);
    expect(select.props("modelValue")).toBe(205);
    expect(select.text()).toContain("装配图.step");
    select.vm.$emit("update:modelValue", 301);
    await wrapper.get(".confirm").trigger("click");
    await flushPromises();
    expect(mocks.update).toHaveBeenCalledWith(4, expect.objectContaining({ part_id: 301 }));
  });

  it("详情展示关联图纸名称与报价平台名称", async () => {
    const wrapper = mountPage();
    await flushPromises();
    await wrapper.get(".detail").trigger("click");
    await flushPromises();
    const dialogText = wrapper.findComponent(Dialog).text();
    expect(dialogText).toContain("装配图.step");
    expect(dialogText).toContain("Xometry");
  });

  it("重新打开表单时更新图纸和平台列表", async () => {
    const wrapper = mountPage();
    await flushPromises();
    await wrapper.get(".add").trigger("click");
    await flushPromises();
    await wrapper.get(".cancel").trigger("click");
    mocks.listParts.mockResolvedValue(page([{ id: 301, file_name: "后来上传.setp" }]));
    mocks.listPlatforms.mockResolvedValue(page([{ id: 3, name: "新竞价平台" }]));
    await wrapper.get(".add").trigger("click");
    await flushPromises();
    expect(partSelect(wrapper).findComponent(ElOption).props("label")).toBe("后来上传.setp");
    expect(platformSelect(wrapper).findComponent(ElOption).props("label")).toBe("新竞价平台");
  });

  it("图纸初次请求未完成时显示加载状态，打开表单不会重复请求", async () => {
    let resolveParts!: (response: ReturnType<typeof page>) => void;
    mocks.listParts.mockReturnValue(
      new Promise((resolve) => {
        resolveParts = resolve;
      })
    );
    const wrapper = mountPage();
    await wrapper.get(".add").trigger("click");
    expect(partSelect(wrapper).props("loading")).toBe(true);
    expect(mocks.listParts).toHaveBeenCalledTimes(1);
    resolveParts(page([{ id: 205, file_name: "装配图.step" }]));
    await flushPromises();
    expect(partSelect(wrapper).props("loading")).toBe(false);
    expect(partSelect(wrapper).findAllComponents(ElOption)).toHaveLength(1);
  });

  it("图纸加载失败时保留原关联 ID，重新打开下拉框可以重试", async () => {
    mocks.listParts.mockRejectedValue(new Error("加载失败"));
    const wrapper = mountPage();
    await flushPromises();
    await wrapper.get(".edit").trigger("click");
    await flushPromises();
    const select = partSelect(wrapper);
    expect(select.props("modelValue")).toBe(205);
    expect(select.findComponent(ElOption).props()).toMatchObject({
      label: "图纸#205",
      disabled: true,
    });
    expect(select.props("noDataText")).toContain("加载失败");
    mocks.listParts.mockResolvedValue(page([{ id: 205, file_name: "装配图.step" }]));
    select.vm.$emit("visible-change", true);
    await flushPromises();
    expect(select.findComponent(ElOption).props()).toMatchObject({
      label: "装配图.step",
      disabled: false,
    });
    expect(wrapper.findComponent(FaForm).props("modelValue")?.part_id).toBe(205);
  });
});
