# 第四阶段（续）方案：报表打印闭环 Web 化

> 2026-08-09 · 基于实机盘点（report 页签空白 / reports API / 报表服务 / 桌面 ReportView）

---

## 一、为什么选报表打印闭环（实机依据）

| 现状 | 实证据 |
|------|--------|
| ❌ **Web report 页签空白** | ui_config view=report 映射 report.html，但 templates/ 无该文件 → pages.py 回退 index.html 占位；`/page/system/report` 打开是空页 |
| ✅ 后端 endpoints 已就绪 | reports.py 全套：`/types`(报表类型) `/generate`(生成下载) `/printers`(打印机) `/print`(打印) |
| ✅ 报表服务已完备 | report.py：exam/change/成绩单(Word/Excel)/证书(generate_certificate) 全套生成 |
| ✅ 桌面有成型参照 | ReportView 已实现：报表类型选择、批量生成+ZIP、证书打印 |
| ⚠️ Web 仅部分 | 只有 score_entry 加了考试报表下载按钮，无独立报表管理页、无打印 |

→ **后端+桌面全就绪，只差 Web 报表页**。补上即形成「报表模板→生成→下载→打印」完整闭环，且**顺带修复 report 页签空白 bug**。

---

## 二、方案：Web 报表打印页（report.html）

### 页面结构（对齐桌面 ReportView 能力，复用既有 endpoints）
| 区块 | 功能 | 复用端点 |
|------|------|---------|
| 1. 报表类型选择 | 下拉（考试报表/学籍变动/成绩单/证书） | GET /api/reports/types |
| 2. 参数区 | 考试下拉/学期下拉（按类型显示） | /api/exam, /api/semester |
| 3. 生成预览 | 点生成 → 获取文件 | POST /api/reports/generate |
| 4. 下载 | 浏览器下载生成文件 | 同上（StreamingResponse） |
| 5. 打印 | 选打印机 → 打印 | GET /printers + POST /print |

### 后端补充（小）
- `report.html` 模板（Alpine + ECharts 不涉及，纯表单+下载）
- 若 `generate` 需按格式分（excel/word/pdf）已支持（GenerateRequest.format）
- **新端点**: 复用现有，无需新增；仅需确认 `print` 端点参数（files/path）

### 桌面对齐（可选）
- Web report.html 建好后，与桌面 ReportView 同名功能对齐（比对 5 类报表两端覆盖度）

---

## 三、范围与验收

| 项 | 内容 |
|----|------|
| B1 | `report.html` 模板：类型选择 + 参数 + 生成下载 + 打印 |
| B2 | 后端补齐：确认/测试 /print、/generate 各类型契约 |
| B3 | 修复 report 页签空白（view=report → report.html 生效） |
| B4 | 验收：页面渲染 → 各类型生成下载 200 → 契约/页面测试 +ruff → 全量不降 |

### 非目标
- 不加 PDF 服务（当前 docx/xlsx 下载已够，PDF 另议）
- 不做 Web 端批量 ZIP（桌面已有，Web 本期单文件下载）

---

## 四、交付
- v3.5.0（报表打印闭环 Web 化）
- 全量 607 基线不降，tag v3.5.0

**确认后按 B1→B4 执行。**