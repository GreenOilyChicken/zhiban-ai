<template>
  <router-view />
</template>

<script setup>
</script>

<style>
/* =========================================================
   设计 Token —— 知伴AI
   方向：沉静墨青色系（政务/银发/文旅），单一强调色，去 AI 紫蓝渐变
   灰阶统一为冷调（带一丝青），阴影带背景色相，圆角分级
   ========================================================= */
:root {
  /* —— 中性灰阶（冷调，统一青相）—— */
  --zb-bg:           #f6f7f9;   /* 页面底色，微冷 */
  --zb-surface:      #ffffff;   /* 卡片/面板表面 */
  --zb-surface-2:    #fbfcfd;   /* 次级表面 */
  --zb-border:       #e4e7ec;   /* 分隔线/边框 */
  --zb-border-strong:#d0d5dd;

  /* —— 文字色阶 —— */
  --zb-text:         #1a2330;   /* 主文字，近黑带青 */
  --zb-text-2:       #455163;   /* 次级文字 */
  --zb-text-3:       #7a8493;   /* 辅助文字 */
  --zb-text-on-accent: #ffffff;

  /* —— 强调色：单一墨青 —— */
  --zb-accent:       #2b6a77;   /* 墨青，饱和度克制 */
  --zb-accent-hover: #245964;
  --zb-accent-soft:  #e8f1f3;   /* 强调色浅底 */
  --zb-accent-border:#cfe0e4;

  /* —— 语义色（去饱和，融入中性）—— */
  --zb-success:      #3f7a55;
  --zb-success-soft: #eaf3ee;
  --zb-warning:      #b07a1e;
  --zb-warning-soft: #f7f0e2;
  --zb-danger:       #b5453b;
  --zb-danger-soft:  #f7eae8;

  /* —— 圆角分级 —— */
  --zb-radius-sm: 6px;
  --zb-radius:    10px;
  --zb-radius-lg: 14px;
  --zb-radius-pill: 999px;

  /* —— 阴影（带背景色相，非纯黑）—— */
  --zb-shadow-xs: 0 1px 2px rgba(26, 35, 48, 0.04);
  --zb-shadow-sm: 0 1px 3px rgba(26, 35, 48, 0.06), 0 1px 2px rgba(26, 35, 48, 0.04);
  --zb-shadow-md: 0 4px 12px rgba(26, 35, 48, 0.08), 0 2px 4px rgba(26, 35, 48, 0.04);
  --zb-shadow-lg: 0 12px 32px rgba(26, 35, 48, 0.10), 0 4px 8px rgba(26, 35, 48, 0.05);

  /* —— 间距尺度（4px 基准）—— */
  --zb-space-1: 4px;
  --zb-space-2: 8px;
  --zb-space-3: 12px;
  --zb-space-4: 16px;
  --zb-space-5: 20px;
  --zb-space-6: 24px;
  --zb-space-8: 32px;
  --zb-space-10: 40px;
  --zb-space-12: 48px;

  /* —— 容器宽度 —— */
  --zb-container: 1200px;

  /* —— 字体：中文优先 PingFang/微软雅黑，西文用更具质感的栈 —— */
  --zb-font: 'Inter', 'Helvetica Neue', 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', system-ui, -apple-system, sans-serif;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
}

html {
  scroll-behavior: smooth;
}

body {
  font-family: var(--zb-font);
  color: var(--zb-text);
  background-color: var(--zb-bg);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-variant-numeric: tabular-nums;
  line-height: 1.6;
}

/* 让 Element Plus 的 primary 跟随我们的强调色，避免蓝紫默认 */
:root {
  --el-color-primary: #2b6a77;
  --el-color-primary-light-3: #5b8d96;
  --el-color-primary-light-5: #8aafb5;
  --el-color-primary-light-7: #bad2d6;
  --el-color-primary-light-8: #d2e2e5;
  --el-color-primary-light-9: #e8f1f3;
  --el-color-primary-dark-2: #245964;
  --el-border-radius-base: 8px;
  --el-box-shadow-light: 0 1px 3px rgba(26, 35, 48, 0.06), 0 1px 2px rgba(26, 35, 48, 0.04);
}

/* 全局：卡片 body 不要默认 overflow:auto（修复方向卡片滚动条根因）。
   el-card__body 默认 { flex-grow:1; overflow:auto }，在等高列布局里会触发滚动条。
   需要滚动的真正长内容区（表格/列表）自行声明 overflow。 */
.el-card__body {
  overflow: visible;
}

/* 焦点可见性（可访问性 WCAG 2.1 AA） */
:focus-visible {
  outline: 2px solid var(--zb-accent);
  outline-offset: 2px;
  border-radius: 4px;
}

/* 跳过到主内容（键盘可访问性） */
.skip-link {
  position: absolute;
  left: -9999px;
  top: 0;
  z-index: 2000;
  background: var(--zb-accent);
  color: var(--zb-text-on-accent);
  padding: 8px 16px;
  border-radius: 0 0 8px 0;
}
.skip-link:focus {
  left: 0;
}

@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
</style>
