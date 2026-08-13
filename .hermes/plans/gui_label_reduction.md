# GUI 界面标签减法 + 代码瘦身 执行计划

## 目标
消除界面多重标签冗余，瘦身 GUI 代码，提升感知简洁度。

## 现状痛点
- **四层标签**：侧栏域 → 侧栏页签 → 页面内 QTabWidget → 窗口标题
- 侧栏页签 28 个，系统设置 9 个最严重
- 16 视图用 QTabWidget，与侧栏页签形成双重导航
- system_config 6 个内部 Tab = 三层标签叠加

## 执行阶段

### Phase 1：侧栏页签精简（UI 配置层，最快见效）
**文件**：`src/edu_system/config/ui_config.json`
**预期**：页签 28→19（-9，减 32%）

| 域 | 当前页签 | 合并后 |
|-----|----------|--------|
| 系统设置 | 9 | 3（基础配置/权限字典/运维监控） |
| 考试管理 | 4 | 2（考试配置/考试执行） |
| 报表工具 | 3 | 2（报表中心/模板与打印） |
| 学生管理 | 4 | 3（学生档案/学籍业务/毕业升留） |
| 图书管理 | 1 | 保持 |

**验收**：侧栏页签数 28→19，契约测试 `test_ui_config_has_10_domains` 更新为新数量。

### Phase 2：system_config 6 Tab 拍平为垂直卡片（消除三层标签）
**文件**：`src/edu_system/gui/views/system_config.py`
**策略**：
- 移除 `QTabWidget`，改单 `QScrollArea` + 垂直布局
- 6 个 `_create_xxx_tab` → 6 个 `_create_xxx_section`（返回 QWidget 卡片）
- 保持原有字段/逻辑，仅容器变化
- 预估：1061 行 → 800 行左右

**验收**：进入"系统设置"页面，单页滚动查看 6 个配置区块，无内部 Tab。

### Phase 3：system_ext 3 Tab 拍平（同理）
**文件**：`src/edu_system/gui/views/system_ext.py`
**策略**：3 Tab → 3 卡片区块垂直堆叠

### Phase 4：考试管理 4 Tab → 步骤条/向导
**文件**：`src/edu_system/gui/views/exam.py`
**策略**：线性流程（配置→分考场→监考→准考证）改为 `QWizard` 或顶部步骤条 + 内容区切换。

### Phase 5：契约测试同步
- `test_ui_config.py`：页签数量断言更新
- `test_web_pages.py`：域/页签结构断言更新

## 风险控制
- 只改 UI 容器，不改业务逻辑/字段/信号
- 每阶段跑 GUI 测试 + 全量回归
- 保留 git 历史可随时回滚

## 里程碑
| 阶段 | 预估时间 | 产出 |
|------|----------|------|
| Phase 1 | 30 min | ui_config.json + 契约更新 |
| Phase 2 | 60 min | system_config.py 重构 |
| Phase 3 | 30 min | system_ext.py 重构 |
| Phase 4 | 60 min | exam.py 重构 |
| Phase 5 | 20 min | 契约同步 + 全量回归 |

## 开始执行
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5，每阶段验收通过后进入下一阶段。