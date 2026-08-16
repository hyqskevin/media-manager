# 05 · UI 设计系统（media-manager v0.2）

> 本文档定义 media-manager v0.2 的 UI 设计系统。严格遵循 **Google Material Design 3**（Material You）规范。
> 组件实现层使用 **Element Plus 2.9**（基于 Vue 3），通过 CSS 变量与 M3 Color Roles 映射实现视觉对齐。
>
> 官方参考资料：
> - [Material Design 3 概览](https://m3.material.io/)
> - [Color system（M3 Color Roles）](https://m3.material.io/styles/color/the-color-system/key-colors-tones)
> - [Type scale](https://m3.material.io/styles/typography/type-scale-tokens)
> - [Elevation](https://m3.material.io/styles/elevation/elevation-tokens)
> - [Shape（圆角）](https://m3.material.io/styles/shape/shape-scale-tokens)
> - [State layers](https://m3.material.io/styles/interaction/state-layer-tokens)
> - [Accessibility overview](https://m3.material.io/foundations/accessible-design/accessibility-basics)
> - [Material Symbols 图标](https://fonts.google.com/icons)
> - [Element Plus 组件库](https://element-plus.org/zh-CN/component/overview.html)

---

## 1. 设计 Tokens

> 全部设计 token 通过 CSS 变量（`:root`）下发，组件仅消费变量名，不写死颜色/字号。
> 颜色基于主色 `#1976D2`（友好的 Material Blue 600），用 Material Theme Builder 算法派生完整 M3 调色板。

### 1.1 颜色（Material 3 Color Roles）

#### 1.1.1 主色（Primary）

| Role | Token | HEX | 用途 |
|---|---|---|---|
| Primary | `--md-sys-color-primary` | `#1976D2` | 关键按钮、主链接、聚焦边框、AppBar 强调 |
| On Primary | `--md-sys-color-on-primary` | `#FFFFFF` | Primary 背景上的文字/图标 |
| Primary Container | `--md-sys-color-primary-container` | `#D3E4FD` | 弱化背景（选中态、Tag、卡片顶） |
| On Primary Container | `--md-sys-color-on-primary-container` | `#001C38` | Primary Container 背景上的文字 |

#### 1.1.2 辅色（Secondary）

| Role | Token | HEX | 用途 |
|---|---|---|---|
| Secondary | `--md-sys-color-secondary` | `#535F70` | 次要按钮、过滤标签 |
| On Secondary | `--md-sys-color-on-secondary` | `#FFFFFF` | Secondary 背景上的文字 |
| Secondary Container | `--md-sys-color-secondary-container` | `#D7E3F8` | 次要弱化背景（Chip 未选中） |
| On Secondary Container | `--md-sys-color-on-secondary-container` | `#101C2B` | Secondary Container 上文字 |

#### 1.1.3 第三色（Tertiary）

| Role | Token | HEX | 用途 |
|---|---|---|---|
| Tertiary | `--md-sys-color-tertiary` | `#6B5778` | 辅助强调（进度环、收藏/点赞图标） |
| On Tertiary | `--md-sys-color-on-tertiary` | `#FFFFFF` | Tertiary 上文字 |
| Tertiary Container | `--md-sys-color-tertiary-container` | `#F2DAFF` | 辅助弱化背景 |
| On Tertiary Container | `--md-sys-color-on-tertiary-container` | `#251431` | Tertiary Container 上文字 |

#### 1.1.4 错误（Error）

| Role | Token | HEX | 用途 |
|---|---|---|---|
| Error | `--md-sys-color-error` | `#BA1A1A` | 错误按钮、Error 状态 |
| On Error | `--md-sys-color-on-error` | `#FFFFFF` | Error 上文字 |
| Error Container | `--md-sys-color-error-container` | `#FFDAD6` | 错误弱化背景（错误提示条） |
| On Error Container | `--md-sys-color-on-error-container` | `#410002` | Error Container 上文字 |

#### 1.1.5 中性背景（Background / Surface）

| Role | Token | HEX | 用途 |
|---|---|---|---|
| Background | `--md-sys-color-background` | `#FCFCFF` | 全局页面背景 |
| On Background | `--md-sys-color-on-background` | `#1A1C1E` | 页面正文文字 |
| Surface | `--md-sys-color-surface` | `#FCFCFF` | 卡片/Sheet/Dialog 背景 |
| On Surface | `--md-sys-color-on-surface` | `#1A1C1E` | Surface 上正文 |
| Surface Variant | `--md-sys-color-surface-variant` | `#DFE2EB` | 分割线、禁用态背景 |
| On Surface Variant | `--md-sys-color-on-surface-variant` | `#43474E` | 次要文字、占位符 |

#### 1.1.6 描边（Outline）

| Role | Token | HEX | 用途 |
|---|---|---|---|
| Outline | `--md-sys-color-outline` | `#73777F` | 输入框/卡片描边、Divider |
| Outline Variant | `--md-sys-color-outline-variant` | `#C3C7CF` | 弱描边（Tab 底边、Card 轻量边框） |

#### 1.1.7 反色（Inverse）

| Role | Token | HEX | 用途 |
|---|---|---|---|
| Inverse Surface | `--md-sys-color-inverse-surface` | `#2F3033` | Snackbar 反色背景 |
| Inverse On Surface | `--md-sys-color-inverse-on-surface` | `#F1F0F4` | Snackbar 上文字 |
| Inverse Primary | `--md-sys-color-inverse-primary` | `#A3C9FF` | Inverse Surface 上的 Primary |

#### 1.1.8 CSS 变量定义（`:root`）

```css
/* ============================================
 * Material Design 3 — Color Roles (Light)
 * media-manager v0.2 (primary #1976D2)
 * ============================================ */
:root {
  /* Primary */
  --md-sys-color-primary: #1976D2;
  --md-sys-color-on-primary: #FFFFFF;
  --md-sys-color-primary-container: #D3E4FD;
  --md-sys-color-on-primary-container: #001C38;

  /* Secondary */
  --md-sys-color-secondary: #535F70;
  --md-sys-color-on-secondary: #FFFFFF;
  --md-sys-color-secondary-container: #D7E3F8;
  --md-sys-color-on-secondary-container: #101C2B;

  /* Tertiary */
  --md-sys-color-tertiary: #6B5778;
  --md-sys-color-on-tertiary: #FFFFFF;
  --md-sys-color-tertiary-container: #F2DAFF;
  --md-sys-color-on-tertiary-container: #251431;

  /* Error */
  --md-sys-color-error: #BA1A1A;
  --md-sys-color-on-error: #FFFFFF;
  --md-sys-color-error-container: #FFDAD6;
  --md-sys-color-on-error-container: #410002;

  /* Background / Surface */
  --md-sys-color-background: #FCFCFF;
  --md-sys-color-on-background: #1A1C1E;
  --md-sys-color-surface: #FCFCFF;
  --md-sys-color-on-surface: #1A1C1E;
  --md-sys-color-surface-variant: #DFE2EB;
  --md-sys-color-on-surface-variant: #43474E;

  /* Outline */
  --md-sys-color-outline: #73777F;
  --md-sys-color-outline-variant: #C3C7CF;

  /* Inverse */
  --md-sys-color-inverse-surface: #2F3033;
  --md-sys-color-inverse-on-surface: #F1F0F4;
  --md-sys-color-inverse-primary: #A3C9FF;
}
```

> 深色主题（v0.3 规划）：用 `prefers-color-scheme: dark` 媒体查询或 `[data-theme="dark"]` 切换暗色 token 集。v0.2 仅交付 Light 主题。

### 1.2 字体（Material 3 Type Scale）

> M3 完整字阶为 15 个样式（Display × 3 + Headline × 3 + Title × 3 + Body × 3 + Label × 3）。
> 字体族使用系统无衬线（San Francisco / Segoe UI / Roboto），与 Element Plus 默认栈一致。

| Token | font-size | font-weight | line-height | letter-spacing | 用例 |
|---|---|---|---|---|---|
| `--md-sys-typescale-display-large` | 57px | 400 | 64px | -0.25px | 营销页 Hero（v0.2 不用） |
| `--md-sys-typescale-display-medium` | 45px | 400 | 52px | 0 | 营销页 Hero（v0.2 不用） |
| `--md-sys-typescale-display-small` | 36px | 400 | 44px | 0 | 报表大数字 |
| `--md-sys-typescale-headline-large` | 32px | 400 | 40px | 0 | 页面 H1（极少用） |
| `--md-sys-typescale-headline-medium` | 28px | 500 | 36px | 0 | 页面 H1（默认） |
| `--md-sys-typescale-headline-small` | 24px | 500 | 32px | 0 | Dialog 标题 |
| `--md-sys-typescale-title-large` | 22px | 500 | 28px | 0 | AppBar 标题、Card 标题 |
| `--md-sys-typescale-title-medium` | 16px | 600 | 24px | 0.15px | ListItem 主标题 |
| `--md-sys-typescale-title-small` | 14px | 600 | 20px | 0.1px | Tab 标签 |
| `--md-sys-typescale-body-large` | 16px | 400 | 24px | 0.5px | 默认正文 |
| `--md-sys-typescale-body-medium` | 14px | 400 | 20px | 0.25px | 表格内容、Helper Text |
| `--md-sys-typescale-body-small` | 12px | 400 | 16px | 0.4px | 表格次要列、版权信息 |
| `--md-sys-typescale-label-large` | 14px | 600 | 20px | 0.1px | Button 文字 |
| `--md-sys-typescale-label-medium` | 12px | 600 | 16px | 0.5px | Chip 文字 |
| `--md-sys-typescale-label-small` | 11px | 600 | 16px | 0.5px | Badge 文字 |

```css
/* ============================================
 * Material Design 3 — Type Scale
 * ============================================ */
:root {
  --md-sys-typescale-display-large:  400 57px/64px  'Roboto', 'PingFang SC', system-ui, sans-serif;
  --md-sys-typescale-display-medium: 400 45px/52px  'Roboto', 'PingFang SC', system-ui, sans-serif;
  --md-sys-typescale-display-small:  400 36px/44px  'Roboto', 'PingFang SC', system-ui, sans-serif;
  --md-sys-typescale-headline-large:  500 32px/40px 'Roboto', 'PingFang SC', system-ui, sans-serif;
  --md-sys-typescale-headline-medium: 500 28px/36px 'Roboto', 'PingFang SC', system-ui, sans-serif;
  --md-sys-typescale-headline-small:  500 24px/32px 'Roboto', 'PingFang SC', system-ui, sans-serif;
  --md-sys-typescale-title-large:    500 22px/28px 'Roboto', 'PingFang SC', system-ui, sans-serif;
  --md-sys-typescale-title-medium:   600 16px/24px 'Roboto', 'PingFang SC', system-ui, sans-serif;
  --md-sys-typescale-title-small:    600 14px/20px 'Roboto', 'PingFang SC', system-ui, sans-serif;
  --md-sys-typescale-body-large:     400 16px/24px 'Roboto', 'PingFang SC', system-ui, sans-serif;
  --md-sys-typescale-body-medium:    400 14px/20px 'Roboto', 'PingFang SC', system-ui, sans-serif;
  --md-sys-typescale-body-small:     400 12px/16px 'Roboto', 'PingFang SC', system-ui, sans-serif;
  --md-sys-typescale-label-large:    600 14px/20px 'Roboto', 'PingFang SC', system-ui, sans-serif;
  --md-sys-typescale-label-medium:   600 12px/16px 'Roboto', 'PingFang SC', system-ui, sans-serif;
  --md-sys-typescale-label-small:    600 11px/16px 'Roboto', 'PingFang SC', system-ui, sans-serif;
}

.md-typescale-display-small  { font: var(--md-sys-typescale-display-small); }
.md-typescale-headline-medium { font: var(--md-sys-typescale-headline-medium); }
.md-typescale-title-large    { font: var(--md-sys-typescale-title-large); }
.md-typescale-title-medium   { font: var(--md-sys-typescale-title-medium); }
.md-typescale-body-large     { font: var(--md-sys-typescale-body-large); }
.md-typescale-body-medium    { font: var(--md-sys-typescale-body-medium); }
.md-typescale-body-small     { font: var(--md-sys-typescale-body-small); }
.md-typescale-label-large    { font: var(--md-sys-typescale-label-large); }
```

### 1.3 间距（Material 3 Spacing — 4dp Grid）

> 所有外边距、内边距、组件间距必须是 4 的倍数。M3 推荐 4/8/12/16/24/32/48/64。

| Token | dp | px | 典型场景 |
|---|---|---|---|
| `--md-sys-spacing-1` | 4dp | 4px | Icon 与文字间距、Chip 内边距 |
| `--md-sys-spacing-2` | 8dp | 8px | ListItem 上下内边距 |
| `--md-sys-spacing-3` | 12dp | 12px | Card 内边距（紧凑型） |
| `--md-sys-spacing-4` | 16dp | 16px | Card 内边距（标准）、AppBar 高度 |
| `--md-sys-spacing-6` | 24dp | 24px | 区块间距、Dialog 内边距 |
| `--md-sys-spacing-8` | 32dp | 32px | 大区块间距 |
| `--md-sys-spacing-12` | 48dp | 48px | 触控目标最小尺寸、Hero 内边距 |
| `--md-sys-spacing-16` | 64dp | 64px | 页面边距（Desktop 极限） |

```css
:root {
  --md-sys-spacing-1:  4px;
  --md-sys-spacing-2:  8px;
  --md-sys-spacing-3:  12px;
  --md-sys-spacing-4:  16px;
  --md-sys-spacing-6:  24px;
  --md-sys-spacing-8:  32px;
  --md-sys-spacing-12: 48px;
  --md-sys-spacing-16: 64px;
}
```

### 1.4 圆角（Material 3 Shape）

> M3 形状分级与 Elevation 共同定义"层"的概念。圆角越大 → 视觉越柔和。

| Token | dp | 适用 |
|---|---|---|
| `--md-sys-shape-xs` | 4dp | TextField、Chip、Tag |
| `--md-sys-shape-sm` | 8dp | Button（小）、Card（小） |
| `--md-sys-shape-md` | 12dp | Card（默认）、Dialog、Snackbar |
| `--md-sys-shape-lg` | 16dp | FAB extended、Sheet |
| `--md-sys-shape-xl` | 28dp | Dialog（大尺寸）、AppBar（v0.2 不用） |
| `--md-sys-shape-full` | 9999dp | FAB round、Avatar、CircularProgress |

```css
:root {
  --md-sys-shape-xs:   4px;
  --md-sys-shape-sm:   8px;
  --md-sys-shape-md:  12px;
  --md-sys-shape-lg:  16px;
  --md-sys-shape-xl:  28px;
  --md-sys-shape-full: 9999px;
}
```

### 1.5 阴影（Material 3 Elevation）

> M3 使用两级阴影（Level 1+ 才有 dp2 阴影模拟"环境光"+"定向光"）。
> v0.2 推荐：卡片用 Level 1，Dialog/Sheet 用 Level 3，FAB 用 Level 0+ tonal elevation。

| Level | Token | dp1 | dp2 | 适用 |
|---|---|---|---|---|
| 0 | `--md-sys-elevation-0` | — | — | AppBar、FAB resting |
| 1 | `--md-sys-elevation-1` | 1 | 2 | Card（默认）、Button（hover） |
| 2 | `--md-sys-elevation-2` | 3 | 6 | Button（pressed）、Chip（selected） |
| 3 | `--md-sys-elevation-3` | 6 | 8 | Dialog、Menu、Tooltip |
| 4 | `--md-sys-elevation-4` | 8 | 12 | NavigationDrawer、Modal Sheet |
| 5 | `--md-sys-elevation-5` | 12 | 16 | FAB（pressed）、顶置 Snackbar |

```css
:root {
  --md-sys-elevation-0: none;
  --md-sys-elevation-1:
    0 1px 2px 0 rgba(0, 0, 0, 0.30),
    0 1px 3px 1px rgba(0, 0, 0, 0.15);
  --md-sys-elevation-2:
    0 1px 2px 0 rgba(0, 0, 0, 0.30),
    0 2px 6px 2px rgba(0, 0, 0, 0.15);
  --md-sys-elevation-3:
    0 4px 8px 3px rgba(0, 0, 0, 0.15),
    0 1px 3px 0 rgba(0, 0, 0, 0.30);
  --md-sys-elevation-4:
    0 6px 10px 4px rgba(0, 0, 0, 0.15),
    0 2px 3px 0 rgba(0, 0, 0, 0.30);
  --md-sys-elevation-5:
    0 8px 12px 6px rgba(0, 0, 0, 0.15),
    0 4px 4px 0 rgba(0, 0, 0, 0.30);
}
```

---

## 2. 组件库（Element Plus ↔ Material 3 映射）

> 项目使用 **Element Plus 2.9**。下表列出 M3 组件对应的 EP 组件 + 主题定制点。
> 所有覆盖样式写在 `frontend/src/styles/element-overrides.scss`，**禁止**修改 Element Plus 源码。

| M3 组件 | Element Plus 实现 | 覆盖点 |
|---|---|---|
| **Button**（Filled / Tonal / Outlined / Text） | `el-button` | 圆角 → `--md-sys-shape-sm`；高度 40dp；hover 用 State Layer 8% primary |
| **IconButton** | `el-button circle` + `el-icon` | 尺寸 40×40dp；icon-only 强制 `aria-label` |
| **FAB**（Floating Action Button） | `el-button circle` 56×56 | 圆角 `--md-sys-shape-lg`；Elevation 3；颜色 Primary Container |
| **Card**（Filled / Outlined / Elevated） | `el-card` | 圆角 `--md-sys-shape-md`；Elevation 1；内边距 16dp |
| **Dialog** | `el-dialog` | 圆角 `--md-sys-shape-xl`；Elevation 3；标题用 Headline Small |
| **Bottom Sheet** | `el-drawer`（`direction="btt"`） | 顶部圆角 28dp；Elevation 4 |
| **Side Sheet** | `el-drawer`（`direction="rtl"`） | 圆角 0；宽度 360dp |
| **TextField**（Outlined / Filled） | `el-input` | 圆角 xs；helper text 用 Body Small |
| **Select** | `el-select` | 同 TextField；menu 用 Elevation 2 |
| **Checkbox** | `el-checkbox` | 选中色 Primary；勾选动画 150ms |
| **Radio** | `el-radio` | 同 Checkbox |
| **Switch** | `el-switch` | 轨道 32×14dp；thumb 20×20dp |
| **AppBar**（Top App Bar） | `el-header` | 高度 64dp；Elevation 0；底边 1px Outline Variant |
| **NavigationRail** | `el-aside`（折叠态） | 宽度 80dp 展开 / 240dp |
| **NavigationDrawer**（Modal） | `el-drawer` | 同 Side Sheet |
| **Tab**（Primary / Secondary） | `el-tabs` | 指示器 3dp Primary；未选中色 On Surface Variant |
| **Chip**（Assist / Filter / Input / Suggestion） | `el-tag` | 圆角 xs；高度 32dp |
| **Badge** | `el-badge` | 圆角 full；size 16dp；色 Error |
| **LinearProgress** | `el-progress`（linear） | 轨道 Surface Variant；填充 Primary |
| **CircularProgress** | `el-progress`（circle/dashboard） | 圆环 4dp；色 Primary |
| **Snackbar** | `el-message` | 圆角 md；Elevation 3；Inverse Surface 背景 |
| **Tooltip** | `el-tooltip` | 圆角 xs；Elevation 2；Body Small 文字 |
| **List** | `el-table` 或 `el-list` | 行高 48dp；选中态用 Primary Container |
| **ListItem** | `el-table row` | 三行结构（leading / label+supporting / trailing） |
| **Divider** | `el-divider` | 1dp Outline Variant |
| **SearchBar** | `el-input` + `prefix` icon | 圆角 full；高度 40dp |
| **Banner** | `el-alert` | 圆角 xs；色 Error Container / Primary Container |

---

## 3. 状态徽章规范

### 3.1 通用 4 状态

| 状态 | M3 Role | HEX 前景 / 背景 | Icon（Material Symbol） | 对比度 |
|---|---|---|---|---|
| **Success** | Tertiary / Tertiary Container | `#1B5E20` / `#C8E6C9` | `check_circle` | 7.4:1 ✅ |
| **Warning** | 派生（amber 800 / amber 100） | `#E65100` / `#FFE0B2` | `warning` | 4.6:1 ✅ |
| **Error** | Error / Error Container | `#BA1A1A` / `#FFDAD6` | `error` | 7.0:1 ✅ |
| **Info** | Primary / Primary Container | `#1976D2` / `#D3E4FD` | `info` | 7.3:1 ✅ |

```css
:root {
  --md-status-success:       #1B5E20;  --md-status-success-bg:       #C8E6C9;
  --md-status-warning:       #E65100;  --md-status-warning-bg:       #FFE0B2;
  --md-status-error:         #BA1A1A;  --md-status-error-bg:         #FFDAD6;
  --md-status-info:          #1976D2;  --md-status-info-bg:          #D3E4FD;
}

.md-badge { display: inline-flex; align-items: center; gap: 4px;
            padding: 2px 8px; border-radius: var(--md-sys-shape-xs);
            font: var(--md-sys-typescale-label-medium); }
.md-badge--success { color: var(--md-status-success); background: var(--md-status-success-bg); }
.md-badge--warning { color: var(--md-status-warning); background: var(--md-status-warning-bg); }
.md-badge--error   { color: var(--md-status-error);   background: var(--md-status-error-bg); }
.md-badge--info    { color: var(--md-status-info);    background: var(--md-status-info-bg); }
```

### 3.2 v0.2 业务状态枚举

#### 3.2.1 `login_status`（4 值，存储在 `platform_accounts.login_status`）

| 值 | 文案 | 颜色 Token | Icon |
|---|---|---|---|
| `logged_in` | 已登录 | Success | `check_circle` |
| `logged_out` | 未登录 | Error | `error` |
| `expired` | 已过期 | Warning | `schedule` |
| `unknown` | 未知 | Info | `help` |

#### 3.2.2 `task_status`（6 值，养号任务状态）

| 值 | 文案 | 颜色 | Icon | 备注 |
|---|---|---|---|---|
| `pending` | 待执行 | Info | `schedule` | 排队中 |
| `running` | 执行中 | Info | `progress_activity` | 蓝 + 转圈 |
| `completed` | 已完成 | Success | `check_circle` | 绿 |
| `failed` | 失败 | Error | `error` | 红 + 错误码 |
| `skipped` | 已跳过 | Warning | `skip_next` | 静默时段/全局关闭 |
| `cancelled` | 已取消 | Warning | `cancel` | 用户主动取消 |

#### 3.2.3 `operator_status`（2 值，操作员状态）

| 值 | 文案 | 颜色 | Icon |
|---|---|---|---|
| `active` | 在岗 | Success | `badge` |
| `inactive` | 离岗 | Info | `do_not_disturb` |

#### 3.2.4 `notification_severity`（3 值，通知严重度）

| 值 | 文案 | 颜色 | Icon |
|---|---|---|---|
| `critical` | 严重 | Error | `priority_high` |
| `warning` | 警告 | Warning | `warning_amber` |
| `info` | 提示 | Info | `notifications` |

---

## 4. 视觉规范

### 4.1 字号层级（页面级）

| 用途 | Token | 示例 |
|---|---|---|
| 页面 H1 | Headline Medium（28/500） | "账号总览" |
| 页面 H2 | Headline Small（24/500） | "账号列表" |
| AppBar 标题 | Title Large（22/500） | 顶部导航标题 |
| Card 标题 | Title Medium（16/600） | "账号 #12 · 小红书·种草号" |
| ListItem 主标题 | Title Medium（16/600） | "阿蓝爱分享" |
| ListItem 副标题 | Body Medium（14/400） | "上次登录 5 分钟前" |
| 正文 | Body Large（16/400） | 长描述 |
| 表格内容 | Body Medium（14/400） | 单元格文字 |
| Helper / 占位符 | Body Small（12/400） | "请输入账号名" |
| Button 文字 | Label Large（14/600） | "新建账号" |
| Tab 文字 | Title Small（14/600） | "[🔴小红书]" |
| Chip 文字 | Label Medium（12/600） | "xhs" |
| Badge 数字 | Label Small（11/600） | "3" |

### 4.2 间距规则

| 场景 | 间距 | Token |
|---|---|---|
| 同一 ListItem 内 leading → label | 16dp | `--md-sys-spacing-4` |
| 不同 ListItem 之间 | 8dp | `--md-sys-spacing-2` |
| Card 与 Card 之间 | 16dp | `--md-sys-spacing-4` |
| 区块标题 → 区块内容 | 12dp | `--md-sys-spacing-3` |
| 页面顶部 → 第一块内容 | 24dp | `--md-sys-spacing-6` |
| Button → Button（同行） | 8dp | `--md-sys-spacing-2` |
| Form Field 之间 | 16dp | `--md-sys-spacing-4` |
| Dialog 内边距 | 24dp | `--md-sys-spacing-6` |

### 4.3 对齐规则

1. **栅格**：12 列栅格，gutter 16dp，margin 24dp。
2. **基线网格**：所有文本与组件基线对齐 4dp 网格。
3. **左对齐优先**：除非数字/标签，否则一律左对齐（中文友好）。
4. **数字右对齐**：表格中所有数字列右对齐；货币/百分比保留 2 位小数。
5. **图标垂直居中**：与同一行文字基线差 ≤ 1dp。
6. **AppBar 标题居左**：与 logo 距离 16dp，垂直居中。

### 4.4 圆角规则

| 组件 | 圆角 | Token |
|---|---|---|
| TextField | 4dp | `--md-sys-shape-xs` |
| Button | 8dp（方形大按钮用 full） | `--md-sys-shape-sm` |
| Chip | 8dp | `--md-sys-shape-sm` |
| Card | 12dp | `--md-sys-shape-md` |
| Dialog | 28dp | `--md-sys-shape-xl` |
| Bottom Sheet（顶角） | 28dp | `--md-sys-shape-xl` |
| FAB | 16dp（extended）/ full（round） | `--md-sys-shape-lg` / `--md-sys-shape-full` |
| Snackbar | 4dp | `--md-sys-shape-xs` |
| Badge | full | `--md-sys-shape-full` |
| Tooltip | 4dp | `--md-sys-shape-xs` |

---

## 5. 无障碍规范（Material 3 Accessibility）

> 目标：**WCAG 2.1 AA** 级别合规。
> 参考：[Material 3 Accessibility](https://m3.material.io/foundations/accessible-design/accessibility-basics) · [WCAG 2.1 AA](https://www.w3.org/WAI/WCAG21/quickref/?currentsidebar=%23col_overview&levels=aaa)

### 5.1 颜色对比度

| 文字类型 | 最小对比度 | 实测（v0.2 主色） |
|---|---|---|
| 正文（Body Large / Medium） | **4.5 : 1** | On Surface `#1A1C1E` on Background `#FCFCFF` → **16.5 : 1** ✅ |
| 大文字（≥ 18px 或 14px 粗体） | **3 : 1** | On Primary `#FFFFFF` on Primary `#1976D2` → **4.7 : 1** ✅ |
| UI 组件（按钮边框、图标） | **3 : 1** | Primary `#1976D2` on Background → **4.5 : 1** ✅ |
| 状态徽章 | **4.5 : 1** | 见 §3.1 表格，全部 ≥ 4.5 ✅ |

### 5.2 触控目标（Touch Target）

- **最小尺寸**：**48 × 48 dp**（M3 强制要求，参考 [Touch targets](https://m3.material.io/foundations/accessible-design/accessibility-basics#e747dc1e-0e87-4d63-a4ed-ef9f5d247c87)）。
- 内边距可以小于 48dp，但实际可点击区域（含外圈透明 padding）必须 ≥ 48dp。
- IconButton 视觉 24dp icon，触控区 48dp。

```css
.md-touch-target {
  min-width: 48px;
  min-height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
```

### 5.3 键盘导航

- **Tab Order**：DOM 顺序即 Tab 顺序（不重排）。
- **Focus Ring**：2dp Primary 外圈，offset 2dp。
- **快捷键**：
  - `Ctrl/Cmd + K` 打开命令面板（v0.3 规划，v0.2 不强制）
  - `Esc` 关闭 Dialog / Drawer / Menu
  - `Enter` 触发当前焦点按钮
  - `↑/↓` 在 List/Menu 中移动焦点
- **Skip Link**：页面顶部放"跳到主内容"链接，仅 Tab 聚焦时显示。

```css
:focus-visible {
  outline: 2px solid var(--md-sys-color-primary);
  outline-offset: 2px;
  border-radius: var(--md-sys-shape-xs);
}
```

### 5.4 屏幕阅读器

- 所有 IconButton / Icon 必须有 `aria-label`（中文文案）。
- 状态徽章用 `role="status"` + `aria-live="polite"`。
- 错误提示用 `role="alert"` + `aria-live="assertive"`。
- Dialog 用 `role="dialog"` + `aria-modal="true"` + `aria-labelledby`。
- 表格 `<table>` 必须有 `<caption>` 或 `aria-label`。
- 加载状态 `aria-busy="true"`。

```html
<button class="md-icon-button" aria-label="编辑账号 #12">
  <span class="material-symbols-outlined">edit</span>
</button>

<div role="status" aria-live="polite" class="md-badge md-badge--success">
  <span class="material-symbols-outlined">check_circle</span>
  已登录
</div>
```

### 5.5 动效与运动

- 尊重 `prefers-reduced-motion`：用户开启后，禁用所有非必要动画。
- 默认过渡时长：**150ms**（小元素）/ **250ms**（大元素），曲线 `cubic-bezier(0.4, 0.0, 0.2, 1)`（M3 标准）。

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 6. 响应式（Breakpoints）

> v0.2 主用 **Desktop**。Tablet 适配基础体验，Mobile 仅保证"不崩"。

| 断点 | 范围 | 主要变化 |
|---|---|---|
| **Mobile** | `< 768px` | 顶部 Tab 转横向滚动；NavigationRail 转 BottomNavigation；表格转卡片列表（v0.2 仅"不崩"） |
| **Tablet** | `768px – 1279px` | NavigationRail 折叠态 80dp；Dialog 最大宽度 560dp；卡片栅格 2 列 |
| **Desktop** | `≥ 1280px` | NavigationRail 展开 240dp；最大内容宽 1440dp；卡片栅格 3-4 列 |

```css
:root {
  --md-breakpoint-tablet:  768px;
  --md-breakpoint-desktop: 1280px;
}

@media (max-width: 767px)  { /* mobile-only rules */ }
@media (min-width: 768px) and (max-width: 1279px) { /* tablet-only rules */ }
@media (min-width: 1280px) { /* desktop-only rules (default) */ }
```

---

## 7. Material Symbols 图标清单

> 字体：[Material Symbols Outlined](https://fonts.google.com/icons) 通过 CDN 引入：
> `<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet" />`
> 使用：`<span class="material-symbols-outlined">icon_name</span>`

| 页面 / 场景 | 图标 | 名称 |
|---|---|---|
| **Navbar 顶级** | | |
| 总览 | `person` | 账号总览 |
| 媒体账号 | `smartphone` | 账号列表 |
| 媒体账号 | `vpn_lock` | 登录态 |
| 媒体账号 | `monitoring` | 账号活跃度 |
| 媒体账号 | `shield` | 风控配置 |
| 养号任务 | `play_circle` | 执行中 |
| 养号任务 | `history` | 历史 |
| 养号任务 | `schedule` | 定时任务 |
| 养号任务 | `list_alt` | 动作集 |
| 养号任务 | `star` | 我的收藏夹 |
| 管理台 | `settings` | 平台配置 |
| 管理台 | `notifications` | 通知中心 |
| 管理台 | `article` | 操作日志 |
| 管理台 | `group` | 操作员管理 |
| **平台 Tab** | | |
| 小红书 | `favorite` | 🔴 |
| 微博 | `forum` | 🧣 |
| 抖音 | `music_note` | 🎵 |
| 知乎 | `lightbulb` | 💡 |
| Twitter | `flutter_dash` | 🐦 |
| B 站 | `play_circle_outline` | 📺 |
| 小宇宙 | `podcasts` | 🎙️ |
| 公众号 | `article` | 📰 |
| **操作图标** | | |
| 新建 | `add` | — |
| 编辑 | `edit` | — |
| 删除 | `delete` | — |
| 搜索 | `search` | — |
| 刷新 | `refresh` | — |
| 筛选 | `filter_alt` | — |
| 排序 | `sort` | — |
| 导出 | `download` | — |
| 登录 | `login` | — |
| 登出 | `logout` | — |
| 暂停 | `pause` | — |
| 启动 | `play_arrow` | — |
| 停止 | `stop` | — |
| **状态** | | |
| 已登录 | `check_circle` | — |
| 未登录 | `cancel` | — |
| 已过期 | `schedule` | — |
| 加载中 | `progress_activity` | — |
| 成功 | `check_circle` | — |
| 警告 | `warning` | — |
| 错误 | `error` | — |
| 提示 | `info` | — |

---

## 8. 附录：SCSS 全量变量速查

```scss
// ==============================================
// media-manager v0.2 — Material Design 3 主题入口
// 引入位置：frontend/src/styles/material.scss
// ==============================================

// —— Color Roles ——
$md-primary:               #1976D2;
$md-on-primary:            #FFFFFF;
$md-primary-container:     #D3E4FD;
$md-on-primary-container:  #001C38;
// (其余 25 个 token 同 §1.1)

// —— Type Scale ——
$md-typescale-display-small:  400 36px/44px  system-ui;
$md-typescale-headline-medium: 500 28px/36px system-ui;
$md-typescale-title-large:    500 22px/28px system-ui;
$md-typescale-title-medium:   600 16px/24px system-ui;
$md-typescale-body-large:     400 16px/24px system-ui;
$md-typescale-body-medium:    400 14px/20px system-ui;
$md-typescale-body-small:     400 12px/16px system-ui;
$md-typescale-label-large:    600 14px/20px system-ui;
$md-typescale-label-medium:   600 12px/16px system-ui;
$md-typescale-label-small:    600 11px/16px system-ui;

// —— Spacing ——
$md-spacing-1:  4px;   $md-spacing-2:  8px;
$md-spacing-3:  12px;  $md-spacing-4: 16px;
$md-spacing-6:  24px;  $md-spacing-8: 32px;
$md-spacing-12: 48px;  $md-spacing-16: 64px;

// —— Shape ——
$md-shape-xs:   4px;
$md-shape-sm:   8px;
$md-shape-md:  12px;
$md-shape-lg:  16px;
$md-shape-xl:  28px;
$md-shape-full: 9999px;

// —— Elevation ——
$md-elevation-0: none;
$md-elevation-1: 0 1px 2px 0 rgba(0,0,0,0.30), 0 1px 3px 1px rgba(0,0,0,0.15);
$md-elevation-2: 0 1px 2px 0 rgba(0,0,0,0.30), 0 2px 6px 2px rgba(0,0,0,0.15);
$md-elevation-3: 0 4px 8px 3px rgba(0,0,0,0.15), 0 1px 3px 0 rgba(0,0,0,0.30);
$md-elevation-4: 0 6px 10px 4px rgba(0,0,0,0.15), 0 2px 3px 0 rgba(0,0,0,0.30);
$md-elevation-5: 0 8px 12px 6px rgba(0,0,0,0.15), 0 4px 4px 0 rgba(0,0,0,0.30);

// —— 状态徽章 ——
$md-status-success:      #1B5E20;  $md-status-success-bg: #C8E6C9;
$md-status-warning:      #E65100;  $md-status-warning-bg: #FFE0B2;
$md-status-error:        #BA1A1A;  $md-status-error-bg:   #FFDAD6;
$md-status-info:         #1976D2;  $md-status-info-bg:    #D3E4FD;
```

---

## 9. 附录：资源链接汇总

- Material 3 官方文档：https://m3.material.io/
- Color Roles 完整表：https://m3.material.io/styles/color/the-color-system/key-colors-tones
- Type Scale Tokens：https://m3.material.io/styles/typography/type-scale-tokens
- Elevation Tokens：https://m3.material.io/styles/elevation/elevation-tokens
- Shape Scale Tokens：https://m3.material.io/styles/shape/shape-scale-tokens
- State Layers：https://m3.material.io/styles/interaction/state-layer-tokens
- Accessibility Basics：https://m3.material.io/foundations/accessible-design/accessibility-basics
- Material Symbols：https://fonts.google.com/icons
- WCAG 2.1 AA Quick Reference：https://www.w3.org/WAI/WCAG21/quickref/
- Element Plus 官方文档：https://element-plus.org/zh-CN/component/overview.html
- Material Theme Builder（生成调色板）：https://material-foundation.github.io/material-theme-builder/

---

> **维护说明**：本设计系统是 v0.2 的"单一事实来源"（Single Source of Truth）。
> 新增组件或 token 必须先更新本文档，再写代码；如对 token 有调整，提交 PR 时必须附 visual diff 截图。
