import { flushPromises, mount } from "@vue/test-utils";
import ElementPlus, { ElOption, ElSelect } from "element-plus";
import { computed, defineComponent, h, reactive, ref, toRefs, useTemplateRef } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useCrudDialog } from "@/hooks/core/useCrudDialog";

const mocks = vi.hoisted(() => ({
  listPlatforms: vi.fn(),
  login: vi.fn(),
  closeLogin: vi.fn(),
  checkPerm: vi.fn(() => true),
}));

vi.mock("@/api/module_cnc/cnc_platform", () => ({
  default: { listCncPlatform: mocks.listPlatforms },
}));
vi.mock("@/api/module_cnc/cnc_account", () => ({
  default: { login: mocks.login, closeLogin: mocks.closeLogin },
}));
vi.mock("@/utils/checkPerm", () => ({ checkPerm: mocks.checkPerm }));
vi.mock("@utils", async () => {
  const { ref } = await import("vue");
  return {
    renderTableOperationCell: vi.fn(),
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
vi.mock("@/components/display/fa-descriptions/index.vue", () => ({ default: {} }));
vi.mock("@/components/tables/fa-table-header/index.vue", () => ({
  default: { template: "<div><slot name='left' /></div>" },
}));

import AccountPage from "@/views/module_cnc/cnc_account/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";

const AddButton = defineComponent({
  emits: ["add"],
  template: "<button data-test='add' @click='$emit(\"add\")'>新增</button>",
});
const Dialog = defineComponent({
  props: ["modelValue"],
  emits: ["cancel"],
  template: "<section v-if='modelValue'><slot /></section>",
});
const Table = defineComponent({
  props: ["columns"],
  setup(props) {
    return () =>
      h(
        "div",
        props.columns
          .filter((column: { prop?: string }) => column.prop === "operation")
          .map((column: { formatter: (row: unknown) => unknown }) =>
            column.formatter({ id: 3, enabled: true, platform_name: "平台甲" })
          )
      );
  },
});

function page(items: { id: number; name: string }[], hasNext = false) {
  return { data: { data: { items, has_next: hasNext } } };
}

function mountPage() {
  // 使用真实 FaForm 和 Element Plus，验证 API 数据确实渲染为选项，而非只断言配置数组。
  return mount(AccountPage, {
    global: {
      plugins: [ElementPlus],
      stubs: {
        FaSearchBar: true,
        FaTableHeaderLeft: AddButton,
        FaTable: Table,
        FaDialog: Dialog,
        FaImportDialog: true,
        FaExportDialog: true,
      },
      directives: { ripple: {} },
    },
  });
}

beforeEach(() => {
  mocks.listPlatforms.mockReset();
  mocks.login.mockReset();
  mocks.closeLogin.mockResolvedValue({ data: { code: 0 } });
  mocks.checkPerm.mockReturnValue(true);
  // Vitest 不运行应用的自动导入插件，为真实页面及表单补齐 Vue/业务 hook 全局。
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
  }));
  vi.stubGlobal("useImportExport", () => ({
    importVisible: ref(false),
    exportVisible: ref(false),
    openImport: vi.fn(),
    openExport: vi.fn(),
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("账号新增的平台下拉框", () => {
  it("将平台接口的数据渲染为真实选项，并保留数字平台 ID", async () => {
    mocks.listPlatforms.mockResolvedValue(
      page([
        { id: 7, name: "平台甲" },
        { id: 12, name: "平台乙" },
      ])
    );
    const wrapper = mountPage();
    try {
      await flushPromises();
      await wrapper.get("[data-test=add]").trigger("click");
      await flushPromises();

      const select = wrapper.findComponent(ElSelect);
      expect(select.exists()).toBe(true);
      expect(select.findAllComponents(ElOption).map((option) => option.props("label"))).toEqual([
        "平台甲",
        "平台乙",
      ]);
      select.vm.$emit("update:modelValue", 12);
      await flushPromises();
      expect(wrapper.findComponent(FaForm).props("modelValue")?.platform_id).toBe(12);
      expect(mocks.listPlatforms).toHaveBeenLastCalledWith({ page_no: 1, page_size: 100 });
    } finally {
      wrapper.unmount();
    }
  });

  it("每次打开新增弹窗时更新平台列表，能选择后来新增的平台", async () => {
    mocks.listPlatforms.mockResolvedValue(page([{ id: 7, name: "平台甲" }]));
    const wrapper = mountPage();
    try {
      await flushPromises();
      await wrapper.get("[data-test=add]").trigger("click");
      await flushPromises();
      wrapper.findComponent(Dialog).vm.$emit("cancel");
      await flushPromises();

      mocks.listPlatforms.mockResolvedValue(
        page([
          { id: 7, name: "平台甲" },
          { id: 12, name: "新平台" },
        ])
      );
      await wrapper.get("[data-test=add]").trigger("click");
      await flushPromises();

      expect(mocks.listPlatforms).toHaveBeenCalledTimes(3);
      expect(
        wrapper
          .findComponent(ElSelect)
          .findAllComponents(ElOption)
          .map((option) => option.props("label"))
      ).toContain("新平台");
    } finally {
      wrapper.unmount();
    }
  });

  it("初始请求未结束时打开弹窗，显示加载状态并在返回后渲染选项", async () => {
    let resolveRequest!: (response: ReturnType<typeof page>) => void;
    mocks.listPlatforms.mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve;
      })
    );
    const wrapper = mountPage();
    try {
      await wrapper.get("[data-test=add]").trigger("click");
      await flushPromises();
      expect(wrapper.findComponent(ElSelect).props("loading")).toBe(true);
      expect(mocks.listPlatforms).toHaveBeenCalledTimes(1);

      resolveRequest(page([{ id: 7, name: "平台甲" }]));
      await flushPromises();
      expect(wrapper.findComponent(ElSelect).props("loading")).toBe(false);
      expect(wrapper.findComponent(ElOption).props("label")).toBe("平台甲");
    } finally {
      wrapper.unmount();
    }
  });
});

describe("账号列表登录按钮", () => {
  it("点击实际行按钮调用登录接口，连续点击只请求一次", async () => {
    mocks.listPlatforms.mockResolvedValue(page([]));
    let finish!: (value: unknown) => void;
    mocks.login.mockReturnValue(
      new Promise((resolve) => {
        finish = resolve;
      })
    );
    const wrapper = mountPage();
    try {
      const button = wrapper.findAll("button").find((item) => item.text() === "登录");
      expect(button).toBeDefined();
      await button!.trigger("click");
      await button!.trigger("click");
      expect(mocks.login).toHaveBeenCalledTimes(1);
      expect(mocks.login).toHaveBeenCalledWith(3);
      expect(button!.classes()).toContain("is-loading");
      finish({
        data: {
          code: 0,
          data: {
            account_id: 3,
            session_id: "s3",
            status: "WAITING_HUMAN",
            viewport: { width: 1280, height: 720 },
            reason: "PROVIDER_VERIFICATION_REQUIRED",
          },
        },
      });
      await flushPromises();
      expect(button!.classes()).not.toContain("is-loading");
    } finally {
      wrapper.unmount();
    }
  });

  it("无账号修改权限时隐藏登录按钮", async () => {
    mocks.listPlatforms.mockResolvedValue(page([]));
    mocks.checkPerm.mockReturnValue(false);
    const wrapper = mountPage();
    try {
      await flushPromises();
      expect(wrapper.findAll("button").some((button) => button.text() === "登录")).toBe(false);
      expect(mocks.login).not.toHaveBeenCalled();
    } finally {
      wrapper.unmount();
    }
  });
});

describe("账号列表与详情的平台页面展示", () => {
  it("在启用状态后展示登录页面与报价页面，并隐藏更新时间列", async () => {
    mocks.listPlatforms.mockResolvedValue(
      page([
        {
          id: 5,
          name: "平台A",
          login_url: "https://login.a.com",
          quote_entry_url: "https://quote.a.com",
        } as any,
      ])
    );
    const wrapper = mountPage();
    try {
      await flushPromises();
      const table = wrapper.findComponent(Table);
      expect(table.exists()).toBe(true);

      const columns = table.props("columns") as Array<{
        prop?: string;
        label?: string;
        visible?: boolean;
        formatter?: (row: unknown) => unknown;
      }>;

      const enabledIdx = columns.findIndex((c) => c.prop === "enabled");
      const loginUrlIdx = columns.findIndex((c) => c.prop === "platform_login_url");
      const quoteUrlIdx = columns.findIndex((c) => c.prop === "platform_quote_entry_url");
      const updatedTimeCol = columns.find((c) => c.prop === "updated_time");

      expect(enabledIdx).toBeGreaterThan(-1);
      expect(loginUrlIdx).toBe(enabledIdx + 1);
      expect(quoteUrlIdx).toBe(enabledIdx + 2);

      const loginCol = columns[loginUrlIdx]!;
      const quoteCol = columns[quoteUrlIdx]!;

      expect(loginCol.label).toBe("登录页面");
      expect(quoteCol.label).toBe("报价页面");
      expect(updatedTimeCol?.visible).toBe(false);

      // 测试 formatter：优先使用 row 上的平台地址
      const rowWithUrls = {
        platform_id: 5,
        platform_login_url: "https://override.login.com",
        platform_quote_entry_url: "https://override.quote.com",
      };
      expect(loginCol.formatter!(rowWithUrls)).toBe("https://override.login.com");
      expect(quoteCol.formatter!(rowWithUrls)).toBe("https://override.quote.com");

      // 测试 formatter：row 缺少地址时，从已加载的平台数据源中回退获取
      const rowFallback = { platform_id: 5 };
      expect(loginCol.formatter!(rowFallback)).toBe("https://login.a.com");
      expect(quoteCol.formatter!(rowFallback)).toBe("https://quote.a.com");

      // 测试 formatter：无对应平台时兜底返回 "-"
      const rowEmpty = { platform_id: 999 };
      expect(loginCol.formatter!(rowEmpty)).toBe("-");
      expect(quoteCol.formatter!(rowEmpty)).toBe("-");
    } finally {
      wrapper.unmount();
    }
  });
});
