# 第四阶段（A）方案：桌面端体验精修

> 2026-08-09 · 基于实机盘点（桌面 1 万行 / 16 视图 / 162 消息框）

---

## 一、为什么做桌面体验精修

**用户原始诉求**（第三阶段起点）："桌面端各菜单功能区使用上不够满意"。前几阶段解决了**信息架构**（8域重组）、**功能对等**（CRUD）、**可视化**（看板），但**桌面端"手感"短板未系统处理**。

### 实机盘点（短板清单）
| # | 短板 | 现状 | 影响 |
|---|------|------|------|
| E1 | **无加载反馈** | 全仓无 WaitCursor/QProgressDialog（导入除外） | 大表操作时界面"卡死感"，用户不知在运行 |
| E2 | **表格无双击快捷** | 仅 classroom 有 cellDoubleClicked | 查详情/编辑需找按钮，操作路径长 |
| E3 | **无分页** | score/exam/teacher 全量 setRowCount | 几百行学生/成绩渲染卡顿 |
| E4 | **部分视图无滚动** | 仅 base/student 有 QScrollArea | 小窗口/高分屏内容截断 |
| E5 | **空状态缺失** | 仅 dashboard 有"暂无" | 空数据白屏无引导 |
| E6 | **列宽不统一** | 29 处分散 Stretch/ResizeToContents | 表格忽宽忽窄观感差 |

### 为什么风险低、价值高
- 全部是**展示层增强**（不碰业务逻辑/数据层）
- 方案有现成范式（student.py 已是标杆：ResizeToContents + ScrollArea + 空状态）
- 直接回应"使用不满意"，桌面端立即可感

---

## 二、方案（按性价比排序）

### E1 全局加载反馈（最高价值）
- `base.py` 加 `wait_cursor()` 上下文管理器（QApplication.setOverrideCursor）
- 数据加载类方法（load_data/_refresh/查询）包裹
- 复用 QProgressDialog 于导入/导出类长任务（已有 import_wizard 范式）

### E3 表格分页 + E6 列宽统一（中高价值）
- 新增 `base.py` 的 `PagedTable` 组件：setRowCount 全量 → 分页加载（每页 100，底部页码）
- 统一表格列策略：数据表 `ResizeToContents` + 末列 `Stretch`（对齐 student.py 标杆）
- 覆盖：score/teacher/exam 主表

### E2 双击快捷（中价值）
- 主表加 `cellDoubleClicked`：学生→编辑档案、成绩→编辑分数、教师→编辑档案、考试→详情
- 复用各视图已有编辑对话框/方法

### E4 滚动 + E5 空状态（低风险补全）
- 无 QScrollArea 的视图（score/teacher/exam/report）内容区包 QScrollArea
- 空列表统一显示"暂无数据，点击xx新建"引导文案（对齐 dashboard 范式）

---

## 三、范围与验收

| 项 | 内容 |
|----|------|
| E1 | base.wait_cursor + 加载类方法包裹（全局） |
| E3+E6 | base.PagedTable 分页组件 + 3 视图接入 + 列宽统一 |
| E2 | 4 视图主表双击快捷（学生/成绩/教师/考试） |
| E4+E5 | 滚动容器补全 + 空状态引导（4 视图） |
| 验收 | GUI 测试 + 全量不降 + 手动 offscreen 渲染验证 + ruff 全绿 |

### 非目标
- 不改业务逻辑、不动数据层、不做样式大改（令牌已统一）
- 不做 Web 端（Web 已是响应式 + 分页）

---

## 四、交付
- v3.6.0（桌面端体验精修）
- 全量 612 基线不降，tag v3.6.0

**确认后按 E1→E4 执行。**