<!-- 登录、注册、忘记密码左侧品牌与智能制造协同展示区 -->
<template>
  <div
    class="login-left-view flex h-full w-full flex-col justify-between overflow-hidden relative p-8 xl:p-12 select-none"
  >
    <!-- 背景流光与科技网格氛围 -->
    <div class="ambient-glow ambient-glow--1" aria-hidden="true" />
    <div class="ambient-glow ambient-glow--2" aria-hidden="true" />
    <div class="ambient-grid-overlay" aria-hidden="true" />

    <!-- 顶部品牌栏（当未由顶栏接管时展示） -->
    <div v-if="!hideTopBranding" class="logo relative z-10 flex items-center gap-3">
      <FaLogo class="icon shrink-0" size="44" :src="webLogoSrc" />
      <div class="logo-title-wrap min-w-0">
        <div class="logo-title-inline flex items-center gap-2">
          <h1
            class="title font-bold text-lg xl:text-xl tracking-tight text-(--el-text-color-primary)"
          >
            {{ siteTitle }}
          </h1>
          <ElTooltip :content="displayVersion" placement="bottom">
            <div class="logo-version-badge shrink-0">
              <span class="logo-version-pill text-xs font-semibold px-2 py-0.5 rounded-full">{{
                displayVersion
              }}</span>
            </div>
          </ElTooltip>
        </div>
      </div>
    </div>
    <div v-else class="h-6" />

    <!-- 中部：品牌标语 + 工业级智能 CNC 自动比价看板演示卡片 -->
    <div class="hero-content relative z-10 my-auto flex flex-col justify-center max-w-2xl">
      <!-- 标语胶囊 -->
      <div
        class="hero-badge inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium mb-4 backdrop-blur-md w-fit"
      >
        <span class="relative flex h-2 w-2">
          <span
            class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"
          ></span>
          <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        <span class="hero-badge__text font-medium tracking-wide">智能工业制造 · 协同报价中枢</span>
      </div>

      <!-- 主标题与副标题 -->
      <h2 class="hero-title text-2xl xl:text-4xl font-extrabold tracking-tight leading-tight mb-3">
        {{
          configStore.configData?.login_title?.config_value || "工业级智能 CNC 自动比价与协同系统"
        }}
      </h2>
      <p class="hero-subtitle text-sm xl:text-base leading-relaxed mb-6 opacity-85">
        {{
          configStore.configData?.login_subtitle?.config_value ||
          "秒级几何特征识别 · 多源制造平台实时比价 · 工程决策敏捷落地"
        }}
      </p>

      <!-- 拟真工业工程卡片 (Glassmorphism Mockup) -->
      <div
        class="tech-mockup-card rounded-2xl p-4 xl:p-5 backdrop-blur-xl border transition-all duration-300"
      >
        <!-- 卡片顶栏状态 -->
        <div
          class="flex items-center justify-between pb-3 border-b border-(--el-border-color-lighter) text-xs"
        >
          <div class="flex items-center gap-2 font-medium">
            <FaSvgIcon icon="ri:cpu-line" class="text-base text-primary" />
            <span class="font-mono text-xs">CAD / STEP 3D 几何特征实时解析引擎</span>
          </div>
          <span
            class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
          >
            <span class="size-1.5 rounded-full bg-emerald-500"></span>
            就绪 · 在线处理
          </span>
        </div>

        <!-- 零件加工解析矩阵 -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 my-3 text-xs">
          <div class="spec-cell rounded-lg p-2.5 bg-(--el-fill-color-light)">
            <div class="spec-cell__label text-[11px] text-(--el-text-color-secondary)">
              材料选型
            </div>
            <div class="spec-cell__val font-semibold mt-0.5 text-(--el-text-color-primary)">
              AL 6061-T6
            </div>
          </div>
          <div class="spec-cell rounded-lg p-2.5 bg-(--el-fill-color-light)">
            <div class="spec-cell__label text-[11px] text-(--el-text-color-secondary)">
              尺寸包络
            </div>
            <div class="spec-cell__val font-semibold mt-0.5 text-(--el-text-color-primary)">
              120 × 85 × 24
            </div>
          </div>
          <div class="spec-cell rounded-lg p-2.5 bg-(--el-fill-color-light)">
            <div class="spec-cell__label text-[11px] text-(--el-text-color-secondary)">
              特征检测
            </div>
            <div class="spec-cell__val font-semibold mt-0.5 text-(--el-text-color-primary)">
              14孔 · 2槽 · ±0.02
            </div>
          </div>
          <div class="spec-cell rounded-lg p-2.5 bg-(--el-fill-color-light)">
            <div class="spec-cell__label text-[11px] text-(--el-text-color-secondary)">
              表面工艺
            </div>
            <div class="spec-cell__val font-semibold mt-0.5 text-(--el-text-color-primary)">
              阳极氧化本色
            </div>
          </div>
        </div>

        <!-- 多平台比对模拟结果 -->
        <div class="space-y-2">
          <!-- 嘉立创 -->
          <div
            class="platform-row flex items-center justify-between p-2.5 rounded-xl border border-(--el-border-color-lighter) bg-(--el-bg-color)"
          >
            <div class="flex items-center gap-2.5">
              <div
                class="size-7 rounded-lg flex items-center justify-center font-bold text-xs bg-blue-500/10 text-blue-600 dark:text-blue-400"
              >
                JLC
              </div>
              <div>
                <div class="text-xs font-semibold text-(--el-text-color-primary)">嘉立创 CNC</div>
                <div class="text-[11px] text-(--el-text-color-secondary)">标准制造 · 3工作日</div>
              </div>
            </div>
            <div class="text-right">
              <div class="text-xs font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                ¥ 142.50
              </div>
              <div class="text-[10px] text-emerald-500 font-medium">推荐最优单价</div>
            </div>
          </div>

          <!-- Xometry -->
          <div
            class="platform-row flex items-center justify-between p-2.5 rounded-xl border border-(--el-border-color-lighter) bg-(--el-bg-color)"
          >
            <div class="flex items-center gap-2.5">
              <div
                class="size-7 rounded-lg flex items-center justify-center font-bold text-xs bg-orange-500/10 text-orange-600 dark:text-orange-400"
              >
                XM
              </div>
              <div>
                <div class="text-xs font-semibold text-(--el-text-color-primary)">
                  索玛特 Xometry
                </div>
                <div class="text-[11px] text-(--el-text-color-secondary)">高精工件 · 5工作日</div>
              </div>
            </div>
            <div class="text-right">
              <div class="text-xs font-bold text-(--el-text-color-primary) font-mono">¥ 198.00</div>
              <div class="text-[10px] text-(--el-text-color-secondary)">认证工艺池</div>
            </div>
          </div>
        </div>

        <!-- 底部数据提效指标 -->
        <div
          class="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-(--el-border-color-lighter) text-center"
        >
          <div>
            <div class="text-xs xl:text-sm font-extrabold text-primary font-mono">+320%</div>
            <div class="text-[10px] text-(--el-text-color-secondary)">核价提效</div>
          </div>
          <div>
            <div class="text-xs xl:text-sm font-extrabold text-emerald-500 font-mono">99.9%</div>
            <div class="text-[10px] text-(--el-text-color-secondary)">公差识别率</div>
          </div>
          <div>
            <div class="text-xs xl:text-sm font-extrabold text-orange-500 font-mono">-24.8%</div>
            <div class="text-[10px] text-(--el-text-color-secondary)">平均降本</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：三项核心价值要点 -->
    <div
      class="hero-pillars relative z-10 grid grid-cols-3 gap-3 pt-4 border-t border-(--el-border-color-lighter)/60"
    >
      <div class="flex items-center gap-2">
        <div
          class="size-8 rounded-lg flex items-center justify-center bg-primary/10 text-primary shrink-0"
        >
          <FaSvgIcon icon="ri:flashlight-line" class="text-base" />
        </div>
        <div class="min-w-0">
          <div class="text-xs font-semibold text-(--el-text-color-primary) truncate">毫秒解析</div>
          <div class="text-[11px] text-(--el-text-color-secondary) truncate">图纸特征即时提取</div>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <div
          class="size-8 rounded-lg flex items-center justify-center bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 shrink-0"
        >
          <FaSvgIcon icon="ri:scales-3-line" class="text-base" />
        </div>
        <div class="min-w-0">
          <div class="text-xs font-semibold text-(--el-text-color-primary) truncate">多源比价</div>
          <div class="text-[11px] text-(--el-text-color-secondary) truncate">多厂梯度阶梯报价</div>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <div
          class="size-8 rounded-lg flex items-center justify-center bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 shrink-0"
        >
          <FaSvgIcon icon="ri:shield-check-line" class="text-base" />
        </div>
        <div class="min-w-0">
          <div class="text-xs font-semibold text-(--el-text-color-primary) truncate">工程隔离</div>
          <div class="text-[11px] text-(--el-text-color-secondary) truncate">图纸资产沙箱防护</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppConfig from "@/config";
import { useConfigStore } from "@stores";

defineOptions({ name: "FaLoginLeftView" });

interface Props {
  hideContent?: boolean;
  /** 顶栏已展示 Logo/标题/版本时隐藏左侧重复顶栏 */
  hideTopBranding?: boolean;
}

withDefaults(defineProps<Props>(), {
  hideContent: false,
  hideTopBranding: false,
});

const configStore = useConfigStore();

/** 接口 logo_url，空则 FaLogo 内置默认图 */
const webLogoSrc = computed(
  () => configStore.configData.logo_url?.config_value?.trim() || undefined
);

const siteTitle = computed(
  () => configStore.configData.sys_name?.config_value?.trim() || AppConfig.systemInfo.name
);

const DEFAULT_APP_VERSION = "3.0.0";
const displayVersion = computed(() => {
  const raw = configStore.configData.version?.config_value?.trim();
  const ver = raw || DEFAULT_APP_VERSION;
  return ver.startsWith("v") || ver.startsWith("V") ? ver : `v${ver}`;
});
</script>

<style lang="scss" scoped>
.login-left-view {
  background: color-mix(in srgb, var(--el-color-primary-light-9) 70%, var(--default-box-color));
  transition: background-color 0.3s ease;
}

html.dark .login-left-view {
  background: color-mix(in srgb, var(--el-color-primary-light-9) 25%, #0b0f19);
}

.ambient-grid-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image: radial-gradient(
    circle,
    color-mix(in srgb, var(--el-color-primary) 12%, transparent) 1px,
    transparent 1px
  );
  background-size: 24px 24px;
  opacity: 0.8;
  mask-image: radial-gradient(ellipse at center, rgb(0 0 0 / 100%) 0%, rgb(0 0 0 / 20%) 80%);
}

.ambient-glow {
  position: absolute;
  pointer-events: none;
  border-radius: 9999px;
  opacity: 0.45;
  filter: blur(80px);
  transition: all 0.5s ease;
}

.ambient-glow--1 {
  top: 10%;
  left: 5%;
  width: 380px;
  height: 380px;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--el-color-primary) 40%, transparent) 0%,
    transparent 70%
  );
}

.ambient-glow--2 {
  right: 5%;
  bottom: 12%;
  width: 320px;
  height: 320px;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--el-color-success) 30%, transparent) 0%,
    transparent 70%
  );
}

html.dark .ambient-glow {
  opacity: 0.25;
}

.hero-badge {
  color: var(--el-color-primary);
  background: color-mix(in srgb, var(--el-color-primary) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--el-color-primary) 25%, transparent);
}

.hero-title {
  color: var(--el-text-color-primary);
  letter-spacing: -0.025em;
}

.hero-subtitle {
  color: var(--el-text-color-secondary);
}

.tech-mockup-card {
  background: color-mix(in srgb, var(--el-bg-color) 80%, transparent);
  border-color: color-mix(in srgb, var(--el-border-color-lighter) 80%, transparent);
  box-shadow:
    0 10px 30px -10px color-mix(in srgb, var(--el-color-primary) 8%, transparent),
    0 1px 3px rgb(0 0 0 / 5%);
}

html.dark .tech-mockup-card {
  background: color-mix(in srgb, #111827 75%, transparent);
  border-color: rgb(255 255 255 / 8%);
  box-shadow:
    0 15px 35px -10px rgb(0 0 0 / 60%),
    0 0 1px rgb(255 255 255 / 10%) inset;
}

.logo-version-pill {
  color: var(--el-color-primary);
  background: color-mix(in srgb, var(--el-color-primary) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--el-color-primary) 25%, transparent);
}
</style>
