# 教务管理系统 UI 重构设计方案

> 状态：讨论定稿 · 日期：2026-08-02
> 决策：用户认可 6 大域架构 + 配置驱动 + 桌面/Web 同步
> 平台：最终运行于 **Windows**（Mint/RDP 仅开发调试用）
> 原型：`docs/ui_redesign_preview_v2.html` · 配置样例：`docs/ui_config.example.json` · 加载器草案：`docs/ui_config_loader_draft.py`
> 已采纳：业界全部模式（权限过滤菜单/图标系统/空状态/批量操作条/确认撤销/命令面板/最近访问/列持久化/主题密度/热键）

---

## 0. 业界模式采纳清单（2026-08-02 全部确认）

| 模式 | 说明 | 优先级 | 落地位置 |
|------|------|--------|---------|
| 权限过滤菜单 | 按角色过滤可见域/页签（管理员全量，教务员学生/成绩，教师成绩录入/查分） | 必做 | `ui_config` `permissions[]` + 登录态注入 |
| 图标系统 | 统一 SVG 图标库替换文字符号（◈▤▦→图标） | 必做 | `theme` + 图标组件 |
| 空状态 | 无数据显示引导插画+主操作，替代空白表格 | 必做 | 通用组件 `EmptyState` |
| 批量操作条 | 选中多行后出现批量删除/导出/锁定操作条 | 必做 | 表格组件扩展 |
| 确认/撤销 | 批量删除、覆盖导入二次确认；支持撤销 | 必做 | `ConfirmDialog` + 撤销栈 |
| 命令面板 | Ctrl+K 全局搜索/跳转跨域 | 建议 | `CommandPalette` |
| 最近访问 | 高频页面置顶（成绩录入等固定操作） | 建议 | 首页/侧栏 |
| 列配置持久化 | 列宽/顺序/显示列存本地，下次保持 | 建议 | 表格组件 |
| 主题密度切换 | compact / comfortable 两档 | 可选 | `theme.density` |
| 全局热键 | Ctrl+K 搜索 / Ctrl+E 录入 / F5 刷新 | 可选 | 主窗口 |

> 平台说明：Windows 为最终运行环境（xrdp 仅开发），布局采用标准舒适间距，不因远程桌面过度压缩；同时保留 density 配置供小屏适配。

---

## 1. 设计总纲

- **配置驱动**：导航/页签/视图路由全部数据化（`ui_config.json`），改配置即可调整 UI，桌面端（PyQt5）与 Web 端共享同一份配置。
- **单一导航**：去掉现有"侧栏按钮 + 顶部下拉菜单"双入口，只保留左侧一级导航 + 内容区顶部二级页签，双源切换改单源。
- **贴合教务工作流**：按业务主线组织 6 大域，全局"当前学期"上下文始终置顶，首页仪表盘作为工作流总入口。
- **结构化组件**：统一工具栏/表格/筛选栏/分页/对话框/消息 6 类组件的代码骨架与视觉规范。

## 2. 信息架构（6 大域）

| 域 id | 标题 | 页签 |
|-------|------|------|
| home | 首页 | 学期概览 / 快捷操作 / 待办·数据状态 |
| students | 学生管理 | 学生信息 / 新生注册 / 学籍变动 / 升留级·毕业 |
| scores | 成绩管理 | 成绩录入 / 成绩查询 / 成绩统计 / 排名分析 |
| exams | 考试管理 | 考试管理 / 考场座位 / 监考安排 / 准考证 |
| teachers | 教师管理 | 教师信息 / 任课安排 |
| system | 系统设置 | 学期设置 / 班级科目 / 教室位置 / 用户权限 / 数据维护 / 系统设置 / 初始化 |

**关键转变**：
- 成绩从"考试管理"的子 tab 提升为独立一级域（日常最高频操作）。
- 删除教师管理的冗余嵌套（原 1 工作台 + 内部双 tab → 拆成 2 个扁平页签）。
- 报表/导出归属：跟随成绩统计（`score_stats`）与各列表的"导出"动作，不设独立导航。
- 新增首页仪表盘（学期数据快照、快捷操作、待办/锁定状态）。

## 3. 配置驱动模型

`docs/ui_config.example.json` + `docs/ui_config_loader_draft.py` 定义了完整 schema：

```
UIConfig
├── app           品牌/学校名/版本号/窗口标题/页脚（全部可改，支持 {school}{name}{version} 模板变量）
├── theme         强调色 / 侧栏色 / 密度
├── topbar        学期切换 / 搜索 / 用户菜单 / 通知
├── domains[]     一级域（6 个）
│   ├── id/title/icon/order/badge_source
│   └── tabs[]    页签
│       ├── id/title/view(default)/permissions[]
└── statusbar     状态栏（左/右分栏）
```

**低耦合原则（用户明确要求）**：UI 所有可见元素单一来源 = `ui_config.json`：

| 想改什么 | 改哪里 | 是否动代码 |
|---------|--------|-----------|
| "示例学校" 学校名 | `app.school_name` | 否 |
| "教务系统" 名称 | `app.name` / `app.name_short` | 否 |
| "v2.0" 版本号 | `app.version` / `app.version_display` | 否 |
| 窗口标题/页脚 | `app.window_title` / `app.footer`（模板变量） | 否 |
| 加/删菜单（域） | `domains[]` 增删一项 | 否（新视图需注册一次） |
| 改菜单名/图标/顺序 | `title` / `icon` / `order` | 否 |
| 加/删页签 | `tabs[]` 增删一项 | 否（新视图需注册一次） |
| 改页签名/默认页 | `title` / `default` | 否 |
| 状态栏文案 | `statusbar` | 否 |
| 颜色主题 | `theme` | 否 |

**view 标识符 ↔ 实现的映射契约**（桌面与 Web 各自维护一张表）：

```python
# 桌面：gui/views/registry.py
VIEW_REGISTRY = {
    "student_list": build_student_view,
    "score_entry":  build_score_entry_view,
    # ...
}
# Web：api/views_registry.py
WEB_VIEWS = {
    "student_list": "student_list.html",
    # ...
}
```

改菜单/页签/顺序/图标 → 只改 `ui_config.json`；新增页面 → 注册一个新 view 标识符即可。

## 4. 统一组件规范

所有业务页面由以下可复用组件拼装，视觉与行为保持一致。

### 4.1 页面骨架（每个页签统一布局）

```
┌ 页头: [页面标题]                [导出▾] [刷新] [操作按钮+] ┐
├ 筛选栏: [搜索框] [下拉条件] [日期] [组合筛选] [重置]     ┤
├ 数据区: QTableView / Tabulator（虚拟滚动）               ┤
├ 底栏: [全选] [选中 x/共 y 条] …… [分页: ‹ 1 2 3 ›]        ┤
└ 状态: [最近更新 12:00] [锁定指示] ──────────────────────┘
```

- 页头：左标题（18px 加粗），右动作按钮组（主操作高亮、次操作次要）。
- 筛选栏：可收起（`toggle_filter`），搜索防抖 300ms，条件持久化到 session。
- 数据区：默认 200 行分页 + 虚拟滚动；支持列选择/冻结首列/排序/Excel 粘贴。
- 分页：首页/上一页/页码/下一页/末页 + 每页条数选择。

### 4.2 组件契约（PyQt5）

| 组件 | 类 | 关键方法 |
|------|-----|---------|
| 筛选栏 | `FilterBar` | `set_conditions`, `get_filters`, `reset`, 信号 `filters_changed` |
| 工具栏 | `Toolbar` | `add_action(id,text,icon,primary)`, 信号 `action_triggered(id)` |
| 分页器 | `PaginationBar` | `set_total`, `set_page`, 信号 `page_changed` |
| 状态徽标 | `StatusBadge` | `set_state(ok/warn/error/draft/locked)` |
| 列选择 | `ColumnSelectorDialog` | `get_selected`, 全选/全不选 |
| 消息 | `Toast` / `MessageBox` | 成功/警告/错误/信息，非阻塞 Toast |

### 4.3 视觉规范（见 `theme.py` 扩展）

- 间距栅格：4/8/12/16/24px。
- 强调色 `#3498DB` 用于选中态/hover/主按钮；成功 `#27AE60`；警告 `#E67E22`；危险 `#E74C3C`。
- 表格斑马纹 `#EBF5FB`；表头底 `#D9E1F2`；内容区背景 `#F5F6FA`。
- 密度 `compact`（窄行距，适配远程桌面低分辨率）。

## 6. 桌面端重构（PyQt5 / main_window.py）

当前 `main_window.py`(509 行) 的双导航（`CollapsibleSidebar`+`TopModuleBar`）重构目标：

1. **单导航源**：删除顶部 `module_btn` 下拉菜单与 `module_changed` 信号，统一由侧栏 `workbench_selected` 驱动；面包屑改由当前"域/页签"派生，减少手写同步。
2. **配置驱动装配**：`WORKBENCH_CONFIGS`（硬编码）改为从 `ui_config.json` 加载，布局扫描 `UIConfig.domains` 生成侧栏/页签/视图工厂调用。
3. **重构 `WorkbenchWidget`**：从"载配置内联"改为 "`render(config)`"，逐页签懒加载，`view` 标识符经 `VIEW_REGISTRY` 路由。
4. **新增 `DashboardView`**：首页仪表盘，读学期统计缓存 + 待办 + 学期进度。
5. **顶层结构**：`MainWindow` 保留快速骨架 + 后台 DB 线程，仅替换导航装配部分；主题色沿用 `theme.py`。

风险控制：采用"配置驱动正则否定式"——不动 9 个具体业务视图源码（`StudentView` 等），只改装配层（`main_window.py` + `views/__init__.py` + 新增 registry + config 加载）。故回归成本低、可逐页签验收。

## 7. Web 端同步

Web 端（FastAPI + Jinja2 + Tabulator 6.x CDN）共用同一 `ui_config.json`；`base.html` 顶部渲染域导航（唯一），内容按 `view` 标识符加载对应模板。桌面与 Web 的"页签/域/图标/排序"天然一致。

## 8. 实施路线（小任务拆分）

| # | 任务 | 产出 | 验收 |
|---|------|------|------|
| 1 | config 加载器接入：`src/edu_system/config/ui.py` + `config/ui_config.json` | 加载器 + 配置 | 单元测试 |
| 2 | 桌面装配重构：`main_window.py` 单导航 + 数据驱动 | 布局无回归 | GUI 截图 |
| 3 | `WorkbenchWidget` 数据驱动 + view registry | 页签懒载 | 分组截图 |
| 4 | 首页 `DashboardView` | 学期概览 | 数据正确 |
| 5 | 结构组件抽离（FilterBar/Toolbar/分页） | 复用组件 + 测试 | 组件测试 |
| 6 | HTML 原型交互化 + Web 模板接入 | base.html 统一 | 浏览器验收 |
| 7 | DEV_PLAN 勾 ✅ / 文档归档 | DEV_PLAN | — |

## 9. 待确认/风险

- 成绩域"排名分析/成绩统计"是否复用现有 StatisticsService（有缓存）；录入页是否要 Excel 粘贴高级模式（见 4.6.1）。
- 主题：用户当前若已习惯旧深色侧栏配色，重构保留深色侧栏 + 浅色内容区（不引入激进换肤），避免改动过大。
- 迁移：受保护 master 分支 + PR 合规；小步多 PR 保持可回归。