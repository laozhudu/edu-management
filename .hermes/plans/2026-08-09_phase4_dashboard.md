# 第四阶段方案：数据看板（Dashboard）双端可视化

> 2026-08-09 · 基于实机盘点（Desktop dashboard / Web overview / stats API / 图表库可用性）

---

## 一、为什么选数据看板（实机依据）

| 现状缺口 | 实证据 |
|---------|--------|
| 桌面 dashboard **无任何图表** | dashboard.py 420 行仅 KPI 卡片/学期进度/快捷操作/最近访问/待办表，图表区为空 |
| Web overview **ECharts 已引未用** | base.html 已加载 echarts@5.5.0 CDN，但 overview.html 只 fetch 数字 |
| 统计指标**已有但未展示** | stats summary API 返回 9 指标（男女/平均分/及格率等），overview 只用 4 个 |
| 数据层**已就绪** | stats.py 缓存预计算齐全（student/class/teacher/subject/score_avg/pass_rate） |
| 图表库**两端就位** | 桌面 QtCharts（score.py 5 种图成熟范式）；Web ECharts CDN |

→ **双端同一缺口、数据层零改动、图表库现成：一次做两端，见效快、风险低**。

---

## 二、方案：Dashboard 双端图表区补全

### 桌面端（dashboard.py，复用 score.py QtCharts 范式）
在 KPI 行下方加图表区（QChartView），数据源 = stats summary API 或 direct DB：

| 图表 | 类型 | 数据 |
|------|------|------|
| 1. 学生性别构成 | 🍰 饼图 | male / female（metrics） |
| 2. 班级-科目统计 | 📊 柱状图 | class_count / subject_count |
| 3. 成绩质量 | 📈 仪表/柱状 | score_avg / score_pass_rate |

数据获取：`/api/stats/semester/{id}/summary`（已有），或复用 dashboard.load_data 的本地 session 查询。推荐走 API 与 Web 统一。

### Web 端（overview.html，用已加载的 ECharts）
在 KPI 卡片下方加 2 个图表卡片：

| 图表 | ECharts 类型 | 数据 |
|------|-------------|------|
| 1. 性别构成 | pie | student_male/female |
| 2. 成绩概览 | bar/gauge | score_avg、score_pass_rate |

通过新增 `x-data` 图表初始化 + `fetch summary` 填充，复用现有 stats API。

### 统一后端（可选，推荐）
新增 `GET /api/stats/dashboard` 聚合端点，打包：性别构成、成绩概览、班级科目、多时点趋势（若数据够）→ 桌面 + Web 都调它，**单一数据源**。

---

## 三、范围与验收

| 项 | 内容 |
|----|------|
| D1 | 后端 `GET /api/stats/dashboard` 聚合端点（契约测试） |
| D2 | 桌面 dashboard.py 加 QtCharts 图表区（性别饼 + 成绩柱） |
| D3 | Web overview.html 用 ECharts 渲染同样图表 |
| D4 | 验收：D 显示正确绘图 → 契约/弹 GUI 测试 +ruff 全绿 → commit+push |

### 非目标
- 不加新图表库（复用现有）
- 不改 stats 缓存模型（只是消费端）
- 不做深钻交互（本期只读看板）

---

## 四、交付
- v3.4.0（数据看板双端）
- 全量回归不降（605 → 新增 D1 契约 + GUI）
- tag v3.4.0

**确认后按 D1→D4 执行。**