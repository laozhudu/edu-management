# 教务管理系统开发计划（v2.0 对齐版）

> **核心原则**：教务员不加班，系统才算合格
> **架构演进**：PyQt5 单机 → PyQt5 + 嵌入 FastAPI（局域网协作） → Windows 原生部署
> **时间分界**：学年/学期为核心上下文，所有业务数据、配置、权限随学期隔离
> **性能策略**：预计算统计 + 学期配置继承 + 分级缓存 + 数据锁定 + 服务级权限
> **数据模型**：主数据 + 学期快照 + 变动流水三层结构；**各数据表支持字段动态增删（JSON 扩展列 + 字段注册表），灵活度高、耦合低**
> **开发方法论**：零部件优先 + AI 模拟人工验收 + TDD 轻量化
> - **零部件优先**：每个任务开始前先搜索成熟开源组件/库/方案，有成熟可用的优先集成，仅填补业务缺口
> - **AI 模拟人工验收**：验收由 AI 代理模拟真实用户（教务主任/教师/学生/家长/运维）操作路径、点击流、异常处理、边界探索
> - **TDD 轻量化**：`tests/contract/` 先行、`TestClient` + `sqlite3 :memory:`，新增 API 必先有契约测试
> - **根因修复**：只做根因级修复，拒绝表面补丁（用户硬性要求）

---

## 📋 总体路线图（v2.0 对齐）

| Sprint | 主题 | 周期 | 状态 | 完成时间 | 关键零部件 |
|--------|------|------|------|----------|-----------|
| 0 | 基础设施（权限/审计/冒烟测试） | 3/2h | ✅ 已完成 | 2025-07-29 | SQLAlchemy 权限模型、审计监听器 |
| 1 | 学生档案核心（导入/列表/详情/编辑） | 1周 | ✅ 已完成 | 2025-07-30 | pandas 导入、照片处理、表格/向导 |
| 2 | 学籍变动闭环（转班/休学/升年级） | 1周 | ✅ 已完成 | 2025-07-30 | 状态机、向导组件、批量操作 |
| 3 | 成绩管理闭环（录入/统计/成绩单） | 1.5周 | ✅ 已完成 | 2025-07-31 | Tabulator 思路、ECharts、python-docx 报表 |
| 3.1 | 学年/学期上下文重构 | 1周 | 🟡 模型层✅ UI/迁移收尾⬜ | 2025-08-01 | Semester/AcademicYear/SemesterConfig/GlobalSetting 模型已建；before_compile/切换器收尾 |
| 3.2 | 统计预计算与缓存层 | 0.5周 | 🟡 模型层✅ | 2025-08-01 | SemesterStatsCache/statistics.py 已建；Worker/API 收尾 |
| 3.3 | 学期配置继承与数据锁定 | 0.5周 | 🟡 模型层✅ | 2025-08-01 | DataLock/locks.py/semester_config.py 已建；继承向导 UI 待做 |
| 3.4 | 基础设施补强 | 1周 | 🟡 大部分✅ | 2025-08-01 | logging/monitoring/versions/middleware/storage/scheduler 已建；离线同步/无障碍待做 |
| 3.5 | 测试数据管理与验收体系 | 1周 | ⬜ 待开始 | - | Faker、factory_boy、Playwright |
| 3.6 | 底座补强极简版 | 0.5天 | ✅ 已完成 | 2026-08-02 | 幂等性中间件 / Outbox 事件总线 / Feature Flag |
| 3.7 | **数据模型重构与优化（含字段动态增删）** | 1周 | ⬜ 待开始 | - | 主数据+快照+流水、宽表、字段注册表、RLS、归档分区 |
| 3.8 | **打磨准备（迁移基线/功能清单/变更日志）** | 1天 | 🟡 迁移✅ 清单/日志⬜ | - | alembic 对齐迁移 + CI 门禁已建；feature_inventory/TODO/CHANGELOG 待做 |
| 4 | PyQt5 + FastAPI 嵌入式 + UI 设计系统 | 3周 | 🟡 4.5/4.10 已完成 | 2026-08 进行中 | PyQt-Fluent-Widgets、Tabulator、Alpine.js、JWT、pydantic |
| 5 | 考试管理 + 排课引擎 | 1.5周 | ⬜ 待开始 | - | OR-Tools CP-SAT、WeasyPrint、WebSocket、docxtpl |
| 6 | 基础配置/家校报表/教师人事 + 报表引擎 | 1.5周 | ⬜ 待开始 | - | docxtpl+WeasyPrint、多通道推送、PDF 批量 |
| 7 | 打包/签名/自动更新/无障碍 + 通用工具包 | 1周 | ⬜ 待开始 | - | Nuitka、codesign、NSIS、axe-core、内部 PyPI |

---

## ✅ 已完成基线（2026-08-03 对齐确认）

| 项 | 状态 | 证据 |
|----|------|------|
| Sprint 0-3 基础业务 | ✅ | 学生/成绩/学籍闭环可用，共享 test_data/ |
| 学期上下文模型层 | ✅ | `models/__init__.py` 41 个模型：Semester/AcademicYear/SemesterConfig/GlobalSetting/DataLock/OutboxEvent/IdempotencyKey/DeviceTrust/School/ServiceConfig/SemesterStatsCache/Exam 扩展(ExamRoom/ExamSeat/Invigilation/AdmitCard/ExamSubjectSetting) |
| 统计缓存模型 | ✅ | `SemesterStatsCache` + `services/statistics.py` `stats.py` `cache.py` |
| 锁定与配置继承 | ✅ | `DataLock` + `core/locks.py` `services/locks.py` `services/semester_config.py` |
| 基础设施 | ✅ | `api/logging.py` `monitoring.py` `versions.py` `middleware/` `services/storage.py` `scheduler.py` `core/audit.py` `core/context.py` `core/event_bus.py` |
| 底座补强 | ✅ | 幂等性(5 单测) + Outbox(5 单测) + Feature Flag(13 单测) |
| 数据质量四件套 | ✅ | `services/export.py` `data_quality.py` `data_cleaning.py` `import_export.py`（PR #14-17） |
| UI 配置驱动 | ✅ | `config/ui_config.py` + `ui_config.json` + 12 单测（PR #19） |
| 桌面装配重构 | ✅ | `main_window.py` 单导航 + view registry（PR #20） |
| 通用组件库 | ✅ | `components.py`：FilterBar/Toolbar/PaginationBar/StatusBadge/EmptyState/ConfirmDialog/BatchActionBar/CommandPalette（PR #21） |
| 首页仪表盘 | ✅ | `DashboardView` + 最近访问 + 命令面板（PR #22-24） |
| 视图注册 + Web 模板 | ✅ | `views/registry.py` 26 视图 + `templates/base.html` + `static/css/base.css` + `static/js/base.js`（PR #25） |
| 测试基线 | ✅ | 125 passed, 2 warnings（`./venv/bin/pytest`） |
| **认证/会话 API** | ✅ | `api/routes/auth.py` 7 端点：login/logout/refresh/me/device/trust（JWT + HttpOnly + 设备信任）+ 9 契约测试 `tests/contract/test_auth.py` |
| **核心业务 API 路由** | ✅ | `api/routes/` 6 个：attendance(9测试)/auth(9)/exam(9)/score(10)/stats/scheduler，已注册进 `api/main.py`（8 处 include_router） |
| **API 中间件** | ✅ | `api/middleware/gateway.py` + `security.py`；`api/deps.py` 含 require_permission/get_current_user/get_current_semester |
| **嵌入式服务端** | ✅ | `gui/server_thread.py` 已建（QThread + uvicorn） |
| **备份/归档/迁移脚本** | ✅ | `scripts/` 7 个：backup.py / archive_semester.py / audit_cleaner.py / migrate_semester_context.py / migrate_exam_extension.py |
| **alembic 配置** | 🟡 | `alembic.ini` 已建（script_location=alembic），`migrations/` 目录待 `alembic init` |

**待办缺口**：alembic `migrations/` 初始化、PyQt5 LoginDialog、导入向导 UI、列持久化/密度切换、Sprint 4.10.5 剩余验收、报表服务四件套（report_excel/certificate/print_service/factory）、主题切换 manager。各 Sprint 详情见下表，状态已按 2026-08-03 代码核查更新。

---
## 🎯 Sprint 3.1：学年/学期上下文重构（1 周）

> 目标：建立「学年-学期」为核心的上下文模型，所有业务表、配置、权限按学期强隔离。模型层已完成，收尾注入与 UI。

### 3.1.1 收尾任务（模型已建）

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 3.1.1 | `Session` 级上下文管理器：`set_active_semester(sem_id)` / `get_active_semester()` | `database.py` | ⬜ | 线程局部存储 + 请求级绑定 |
| 3.1.2 | SQLAlchemy `before_compile` 事件：自动注入 `WHERE semester_id = :active` | `database.py` | ⬜ | 排除系统表、跨学期报表、管理员全局视图 |
| 3.1.3 | FastAPI 依赖注入：`Depends(get_current_semester)` → 绑定 request.state | `api/deps.py` | ⬜ | Web 端复用同一套逻辑 |
| 3.1.4 | PyQt5 顶部栏「学年/学期切换器」：切换即写配置 + 广播刷新 | `gui/views/semester.py` + `main_window.py` | ⬜ | 现有 SemesterView 复用增强 |
| 3.1.5 | 角色权限增加学期维度：`Permission.SCORE_ENTRY_SEMESTER` 等细粒度 | `core/permissions.py` | ⬜ | 教师仅操作自己班级当前学期数据 |
| 3.1.6 | 审计日志自动记录 `semester_id`，跨学期操作留痕 | `core/audit.py` | ⬜ | 现有 `before_flush` 扩展 |

### 3.1.2 验收基线

| # | 验收项 | 通过标准 |
|---|--------|----------|
| 3.1.7 | 切换学期后，学生列表/成绩录入/考试管理/报表**零代码改动**自动过滤 | 100% 业务页面通过 |
| 3.1.8 | 新建学年/学期向导：一键复制上学期配置（评分线、课程、班级结构） | 5 分钟完成新学期初始化 |
| 3.1.9 | 历史学期只读模式：`is_active=False` 的学期禁止写入，仅查询/导出 | 审计日志可追溯 |

---

## 🎯 Sprint 3.2：统计预计算与缓存层（0.5 周）

> 目标：界面统计（学生数/均分/及格率/排名）全部**预计算落表**，页面查询只读缓存，毫秒级响应。模型已建，收尾 Worker 与 API。

### 3.2.1 收尾任务

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 3.2.1 | 核心指标清单：学生数/班级数/教师数、各科均分/及格率/优秀率/分段分布、班级/年级排名、考试整体统计 | `services/statistics.py` | ⬜ | 约 30 个核心指标 |
| 3.2.2 | 增量刷新触发器：成绩变更/学生变动/班级调整 → 标记脏位 → 后台重算 | `services/statistics.py` + `core/events.py` | ⬜ | 事件驱动，避免全量重算 |
| 3.2.3 | 后台计算 Worker：`QThread` 跑统计任务，进度条可视，支持取消/重试 | `services/statistics_worker.py` | ⬜ | 复用现有 DB 连接池 |
| 3.2.4 | 手动触发入口：PyQt5「系统维护 → 统计刷新」/ Web「管理员 → 重算统计」 | `gui/views/system_config.py` + `api/routes/admin.py` | ⬜ | 幂等操作 |
| 3.2.5 | 缓存读取 API：`GET /api/stats/semester/{id}` → 直接返回预计算值 | `api/routes/stats.py` | ⬜ | 无实时聚合查询 |
| 3.2.6 | 版本控制：每次重算 `version++`，前端携带版本号，不变则 304 | `models/__init__.py` | ⬜ | 减少传输 |

### 3.2.2 验收基线

| # | 验收项 | 通过标准 |
|---|--------|----------|
| 3.2.7 | 学生列表页（2000+ 行）含统计列，首屏 < 200ms | 无实时 COUNT/SUM |
| 3.2.8 | 成绩录入保存后，相关统计 5 秒内自动刷新 | 事件驱动增量 |
| 3.2.9 | 切换学期，统计数据瞬间切换 | 读缓存表 |

---

## 🎯 Sprint 3.3：学期配置继承与数据锁定（0.5 周）

> 目标：新学期「一键继承」上学期配置，仅改差异；关键数据可锁定需权限解锁。模型已建，收尾 UI。

### 3.3.1 收尾任务

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 3.3.1 | 继承向导 UI：选择源学期 → 预览差异 → 确认执行 → 审计记录 | `gui/views/semester.py` | ⬜ | 四色高亮：绿新增/蓝修改/灰保留/红冲突 |
| 3.3.2 | 版本回滚：`SemesterConfig` 保留历史版本，支持「恢复到上一版」 | `models/__init__.py` | ⬜ | 软删除 + version 字段 |
| 3.3.3 | PyQt5/Web 统一锁定 UI：工具栏锁定/解锁、行内锁图标、批量锁定、理由必填 | `gui/views/base.py` + `templates/` | ⬜ | 权限控制按钮显隐 |
| 3.3.4 | 典型锁定场景：成绩发布后锁定、学籍变动审核通过锁定、考号生成后锁定、学期归档锁定 | `services/score.py` `services/enrollment.py` | ⬜ | 业务流程自动加锁 |

### 3.3.2 验收基线

| # | 验收项 | 通过标准 |
|---|--------|----------|
| 3.3.5 | 新建学期 → 继承上学期配置 → 仅改评分线 → 保存 → 生效 | < 3 分钟 |
| 3.3.6 | 成绩发布 → 自动 hard 锁 → 教师不可改 → 主任解锁 → 可改 → 审计 | 全流程通过 |
| 3.3.7 | 学期归档 → 全表 hard 锁 → 仅导出/查询 | 只读生效 |

---

## 🎯 Sprint 3.4：基础设施补强（1 周）

> 目标：补齐迁移回滚、备份归档、审计清理、定时调度、多校区、API 版本、文件存储、可观测性、安全、离线同步、无障碍。大部分已建，收尾离线与无障碍。

### 3.4.1 收尾任务

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 3.4.1 | **alembic 初始化**：`migrations/` 目录 + `alembic init` + 基线迁移 + CI 门禁 (upgrade/downgrade/checksum) | `migrations/` + `.github/workflows/ci.yml` | ⬜ | 当前为手写 SQL，改为版本化迁移 |
| 3.4.2 | 迁移脚本 dry-run + 校验和对比 + 自动回滚脚本 | `scripts/verify_migration.py` `scripts/rollback_migration.py` | ⬜ | 预演环境跑 3 次 |
| 3.4.3 | 备份/归档：每日增量 + 学期全量 + SHA256；审计分表 + 清理 Worker | `scripts/backup.py` `services/audit_cleaner.py` | ⬜ | 保留 30 天增量 + 3 年全量 |
| 3.4.4 | 定时任务可视化：列表、启停、手动触发、执行历史、下次运行时间 | `gui/views/system_config.py` | ⬜ | APScheduler 已建 |
| 3.4.5 | 离线同步：IndexedDB 队列 + 冲突合并 + Service Worker | `static/js/offline.js` `static/sw.js` `api/routes/sync.py` | ⬜ | 考勤/录分优先 |
| 3.4.6 | 无障碍适配：语义化 HTML、ARIA、焦点管理、高对比度、字号缩放、键盘可达 | `templates/base.html` + `static/css/a11y.css` | ⬜ | WCAG 2.1 AA 自测 |
| 3.4.7 | 跨库只读视图：多校区 `UNION ALL` 汇总视图 | `scripts/create_cross_school_views.py` | ⬜ | 教育局汇总用 |

### 3.4.2 验收基线

| # | 验收项 | 通过标准 |
|---|--------|----------|
| 3.4.8 | 迁移演练：预演环境跑 3 次全量迁移+回滚，零丢失零报错 | 100% 通过 |
| 3.4.9 | 备份恢复：任意时间点备份 → 空库恢复 → 校验和一致 | < 10 分钟 |
| 3.4.10 | 离线同步：断网 30 分钟操作 → 恢复自动合并 → 冲突可复核 | 端到端通过 |
| 3.4.11 | 无障碍：axe-core 0 违规、键盘全流程可达 | 合规通过 |
| 3.4.12 | 安全：OWASP Top 10 扫描 0 高危、速率限制生效 | 安全扫描通过 |

---

## 🎯 Sprint 3.5：测试数据管理与验收体系（1 周）

> 目标：真实共享测试数据集 + 人工验收测试规范 + 全链路验收清单，以真实业务数据为基准、人类操作为验收视角。

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 3.5.1 | 标准测试数据集 Schema：3 学年 × 2 学期 × 3 年级 × 12 班 × 50 人 = 10,800 学生全维度 | `test_data/schema.md` | ⬜ | 全实体覆盖 |
| 3.5.2 | 生成基准数据集：典型场景（新生/转班/休学/升年级/毕业/补考/缺考/转学/复学） | `test_data/generate.py` | ⬜ | Faker + 业务规则，含边界/异常值 |
| 3.5.3 | 数据版本库：`v1.0/` `v1.1/`，每版本含 manifest.json（指纹/时间/场景/校验和） | `test_data/versions/` | ⬜ | Git LFS 管理 |
| 3.5.4 | 加载/重置工具：`load_test_data.py --version --scenario`，dry-run/verify-only/进度条 | `test_data/loader.py` | ⬜ | 并发加载 |
| 3.5.5 | 敏感数据脱敏：身份证/手机/住址/监护人，保留格式校验 | `test_data/masker.py` | ⬜ | 符合《个保法》 |
| 3.5.6 | 数据完整性自检：外键闭环/唯一约束/业务规则，生成 HTML 报告 | `test_data/validator.py` | ⬜ | 红/黄/绿三色 |
| 3.5.7 | 《验收测试规范》：角色/环境/数据版本/通过标准/缺陷分级/签收 | `docs/acceptance_testing_spec.md` | ⬜ | 参考 IEEE 829 / ISO 29119 |
| 3.5.8 | 核心业务用例集（覆盖率 ≥ 90%）：学生全生命周期/成绩全闭环/考试全流程/考勤闭环/学期管理/权限服务锁定 | `test_cases/core_business/` | ⬜ | 每用例含步骤/预期/审计 |
| 3.5.9 | UAT 执行工具：`uat_runner.py`（加载数据→执行→录屏→对比→报告） | `tools/uat/` | ⬜ | Playwright + FFmpeg |
| 3.5.10 | 定义 DoD 判据：核心用例 100%、边界 ≥ 90%、0 个 P0/P1、性能达标 | `docs/definition_of_done.md` | ⬜ | 双人复核 |

---

## 🎯 Sprint 3.6：底座补强极简版（0.5 天）✅ 已完成

| # | 子任务 | 产出 | 状态 |
|---|--------|------|------|
| 3.6.1 | **幂等性中间件**：`Idempotency-Key` + `idempotency_keys` 表（唯一索引 + TTL 1 天） | `core/idempotency.py` | ✅ 已接入 + 5 单测 |
| 3.6.2 | **Outbox 事件总线**：`outbox_events` 表 + APScheduler 轮询（10s、重试 3、死信） | `core/event_bus.py` | ✅ 已注册 + 5 单测 |
| 3.6.3 | **Feature Flag**：`features.json` + 热加载 + `@feature_flag` 装饰器 | `core/features.py` | ✅ 已建 + 13 单测 |

---

## 🎯 Sprint 3.7：数据模型重构与优化（1 周）⭐ 新增

> **背景**：当前模型将「不变属性」与「学期级快照」混在同表（Student/Teacher/Class 直接挂 semester_id），跨学期流转（升级/留级/转学/调课）需复杂迁移、历史关联易断裂。业界成熟教务系统普遍采用 **主数据表 + 学期快照表 + 变动流水表** 三层结构。
> **目标**：拆分核心实体生命周期，建立主数据管理(MDM)基础 + **字段动态增删机制**，为排课、跨学年统计、档案管理扫清结构性障碍。

### 3.7.1 核心实体拆分（主数据 + 学期快照）

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 3.7.1 | ~~**Student 拆分** Profile+Enrollment~~ → **简化** | `models/` | ❌ 简化跳过 | 2026-08-03 用户决策；现有 Student 已含 semester_id/status/ext_json 满足学期快照，拆双表纯结构重构无增益 |
| 3.7.2 | ~~**Teacher 拆分**~~ → **简化** | `models/` | ❌ 简化跳过 | 2026-08-03 用户决策；Teacher 已含 semester_id 满足学期归属，一教师多角色由 ClassSubject 承担 |
| 3.7.3 | ~~**Class 拆分** AdminClass+ClassSemester~~ → **简化** | `models/` | ❌ 简化跳过 | 2026-08-03 用户决策；Class 已含 semester_id+唯一约束(grade,semester,name) 满足跨学期稳定 |
| 3.7.4 | **学籍变动流水增强**：`StudentMovement` 补 `movement_category`(升级/留级/转班/休学/复学/转入/转出/毕业) | `models/` + `repository/movement.py` | ✅ 已完成 | 2026-08-03 PR #60；movement_category+create_movement 自动分类+list_by_category+8 测试 |
| 3.7.5 | ~~**教师任课计划** TeachingPlan~~ → **简化** | `models/` | ❌ 简化跳过 | 2026-08-03 用户决策；ClassSubject(班级-科目-教师) 已承担任课关系，无需新建 |

### 3.7.2 字段动态增删机制（用户核心需求：灵活度高、耦合低）⭐

> 目标：**各数据表允许增删字段，无需改代码、无需改表结构**。核心表结构保持稳定，扩展字段走 JSON 列 + 字段注册表。

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 3.7.6 | **通用扩展列**：所有核心业务表加 `ext_json` (Text/JSON) 列，存自定义字段 | `models/` | ⬜ | SQLite JSON1 支持，查询用 `json_extract` |
| 3.7.7 | **字段注册表**：`FieldDefinition` 表(entity_type, field_key, label, field_type[string/int/float/date/enum/select], options, required, sort_order, is_system, created_by) | `models/` | ⬜ | 系统字段 is_system=1 不可删，自定义字段可增删 |
| 3.7.8 | **字段元数据 API**：`GET /api/meta/fields?entity=student` `POST /api/meta/fields`（增删改查字段定义） | `api/routes/meta.py` | ✅ 已完成 | 2026-08-03 PR #42；含实体值写入端点+13 契约测试 |
| 3.7.9 | **动态表单渲染器**：根据 FieldDefinition 生成编辑表单（PyQt5 `QFormLayout` 动态构建 + Web 动态渲染） | `gui/widgets/dynamic_form.py` + `static/js/dynamic_form.js` | 🟡 PyQt5✅ Web待做 | 2026-08-03 PR #44；PyQt5 DynamicFormWidget+11测试；Web 端 dynamic_form.js 待做 |
| 3.7.10 | **动态表格列**：列表页/导出根据字段注册表动态生成列，列配置可持久化（用户偏好） | `gui/widgets/table_columns.py` | ✅ 已完成 | 2026-08-03 PR #46；TableColumnManager（合并列+QSettings持久化）+8 测试 |
| 3.7.11 | **导入导出联动**：字段增删后，导入向导/导出模板自动识别新字段 | `services/export.py` | ✅ 已完成 | 2026-08-03 PR #48；template_for 动态追加自定义字段（系统字段排除）+2 测试 |
| 3.7.12 | **索引与查询**：`json_extract` 查询优化、高频自定义字段可提升为真实列（`ALTER TABLE ADD COLUMN` 由迁移脚本执行） | `services/meta.py` | ✅ 已完成 | 2026-08-03 PR #50；query_by_field 按自定义字段查询（json_extract）+3 测试 |

**设计要点**：
- 系统核心字段（姓名/学籍号/成绩等）仍为真实列，保证完整性约束与索引性能
- 学校自定义字段（如「是否留守儿童」「特长」「校车线路」）走 ext_json + FieldDefinition
- 字段增删**零代码**：教务员在「基础配置 → 自定义字段」界面操作，PyQt5/Web 双端同步生效
- 导出/导入/报表/打印模板自动识别新字段，无需改代码
- 权限：字段级权限 `field_visible_roles[]` 可控制字段对角色可见性

### 3.7.3 课程体系补全 + 成绩优化

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 3.7.13 | ~~`Course` 课程目录~~ | — | ❌ 取消 | 2026-08-03 用户决策：学科简单化，学分/课程/教材/三级分类均不需要；保留现有 `Subject` 表即可，留扩展空间 |
| 3.7.14 | ~~`CourseOffering` 开课计划~~ | — | ❌ 取消 | 2026-08-03 依赖 3.7.13 一并取消；开课沿用现有 `ClassSubject`（班级-科目-教师） |
| 3.7.15 | ~~**成绩宽表物化视图**~~ `StudentExamScoreWide`（各科分/等级/总分/排名/及格率） | — | ❌ 取消 | 2026-08-03 用户决策"原始分+折算分即可，不需要复杂统计"；报表按需即时计算，不做物化宽表 |
| 3.7.16 | ~~`ExamSubjectSetting` 补 `grading_scheme`+`weight` 加权~~ → **简化：成绩补折算分** | `models/` + `services/score.py` | ✅ 已完成 | 2026-08-03 PR #54；用户决策"原始分+折算分即可"，Score 补 converted_score，convert_scores 按满分折 100 制+5 测试 |

### 3.7.4 权限数据库层强制 + 归档

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 3.7.17 | `RolePermission(role_id, permission_code)` 规范化权限表替代逗号字符串 | `models/` + `services/permissions.py` | ✅ 已完成 | 2026-08-03 PR #57；读写双轨兼容（新表优先回退旧列）+8 测试 |
| 3.7.18 | `RowLevelPolicy(role_id, entity_type, predicate_sql)` + 数据作用域视图（教师任课班/班主任全班/教务全校） | `core/rls.py` | ✅ 已完成 | 2026-08-03 PR #58；scope: all/none/own_class/own_classes，DB策略优先回退默认，apply_scope 拦截+14 测试 |
| 3.7.19 | 学期分区 + 归档自动化：archived 学期 → 只读副本 `school_archive_YYYY_N.db` | `scripts/archive_semester.py` | ✅ 已完成 | 2026-08-03 PR #59；脚本已有实现，补 7 项测试（verify/list/完整流程/异常） |

### 3.7.5 迁移与验收

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 3.7.20 | **全量迁移脚本** `scripts/migrate_data_model_v2.py`：幂等/可回滚/dry-run/校验和/进度条 | `scripts/` | ✅ 已完成 | 2026-08-03 PR #61；MigrationScript 框架(dry-run/checksum/rollback)补 8 测试 |
| 3.7.21 | ~~**双写过渡期**~~ | — | ❌ 取消 | 2026-08-03 依赖 3.7.1 拆分（已简化跳过），无新旧表切换场景 |
| 3.7.22 | **验收基线**：<br>• ~~学生跨学期升级 ~~ (已简化，semester_id 快照)<br>• ~~教师跨学期任课~~ (ClassSubject 已承担)<br>• ~~班级跨学期连续~~ (Class 已含 semester_id 唯一约束)<br>• ~~成绩宽表~~ (用户取消，按需计算)<br>• **字段增删：新增自定义字段后，表单/表格/导入/导出即时识别，零代码改动**<br>• **权限视图：教师任课班/班主任全班/教务全校** | — | 🟡 基本达成 | 2026-08-03；字段增删即时识别（3.7.8-3.7.12 实现）+ RLS 作用域（3.7.18 实现）均完成；实体拆分类验收项随简化取消 |

---

## 🎯 Sprint 3.8：打磨准备（1 天，逐项打磨前置）⭐ 新增

> **背景**：用户将进入「逐项打磨各功能」阶段（2026-08-03 定案）。打磨必然伴随表结构变更、频繁提交、功能级验收，需要先补齐基础设施与工程规范。
> **目标**：alembic 迁移基线、功能清单、待办跟踪、变更日志、远端清理五项就绪，使「改表→开发→测试→提交→发布」全链路符合业界标准。

### 3.8.1 数据库迁移基线

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 3.8.1 | alembic 初始化：`alembic/` + env.py 接入 Base.metadata | `alembic/` | ✅ | 8月2日已建（script_location=alembic，env.py 正确） |
| 3.8.2 | 基线迁移对齐：修复 script.py.mako 模板损坏 + 生成 `c21cf1753802` 对齐迁移（补齐 20 张缺失表） | `alembic/versions/c21cf1753802_*.py` | ✅ | 空库 upgrade head = 35 表，与现有库完全一致 |
| 3.8.3 | 现有库 stamp：187MB 库标记 head（c21cf1753802），数据零改动 | `data/school_data.db` | ✅ | students=3, scores=2 数据完好 |
| 3.8.4 | CI 门禁：ci.yml 新增 `db-migrate` job（upgrade head 校验表数 + downgrade base 回滚演练） | `.github/workflows/ci.yml` | ✅ | 待推送验证 |
| 3.8.5 | 打磨约定：表结构变更一律走 alembic revision（禁止手写 ALTER） | 本文档附录 | ✅ | 2026-08-03 附录「打磨约定」已落文；CI db-migrate 门禁多 PR 全绿验证 |

### 3.8.2 功能清单与待办跟踪

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 3.8.6 | **功能清单 `docs/feature_inventory.md`**：全功能粒度登记（现状/代码位置/测试数/待打磨点/验收标准） | `docs/feature_inventory.md` | ⬜ | 逐项打磨的唯一索引 |
| 3.8.7 | **待办缺口 `TODO.md`**：LoginDialog / 导入向导 UI / 列持久化 / 报表四件套 / 主题切换 / 4.10.5 剩余验收 | `TODO.md` | ⬜ | 完成一项划一项 |

### 3.8.3 变更日志与远端整洁

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 3.8.8 | git-cliff 配置 `cliff.toml` + `CHANGELOG.md` 初始化 | `cliff.toml` + `CHANGELOG.md` | ⬜ | conventional commits 分组 |
| 3.8.9 | 清理远端已合并分支（8 个旧 feat/docs 分支） | 远端 | ⬜ | 保持整洁 |

### 3.8.4 验收基线

| # | 验收项 | 通过标准 |
|---|--------|----------|
| 3.8.10 | 空库 `alembic upgrade head` = 35 表与模型一致；`downgrade base` 可回滚 | CI 全绿 |
| 3.8.11 | feature_inventory.md 覆盖全部 26 视图 + 18 服务 + 6 路由 | 可检索可勾选 |
| 3.8.12 | TODO.md 待办缺口完整，与 DEV_PLAN 状态一致 | 无遗漏 |
| 3.8.13 | 远端仅剩 master + 活跃分支 | `gh pr list --state merged` 为空 |

---

## 🎯 Sprint 4：PyQt5 + FastAPI 嵌入式 + UI 设计系统（3 周）

> 目标：PyQt5 主进程内跑 uvicorn+FastAPI，局域网设备用浏览器协作，服务粒度可配置暴露；**全面复用成熟零部件**，建立 **UI 设计系统**（配置驱动，已定案）。
> **已完成**：4.5 数据质量四件套（PR #14-17）、4.10 UI 重构主体（PR #19-25）。以下为剩余任务。

### 4.0 零部件复用清单（Sprint 4 引入的成熟库）

| 功能域 | 选用库 | 版本/安装 | 关键能力 | 替代目标 |
|--------|--------|-----------|----------|----------|
| **UI 组件库** | **PyQt-Fluent-Widgets** | `pip install "PyQt-Fluent-Widgets[full]==1.8.0"` | FluentWindow、NavigationInterface、CardWidget、InfoBar、TeachingTip、Flyout、AcrylicLabel、ProgressRing、SwitchButton、ComboBox、DatePicker、AvatarWidget、TableView、SettingCard 系列 | 现有 main_window.py 侧栏/顶栏/卡片 |
| **Web 表格** | **Tabulator 6.x** | CDN `tabulator-tables@6` | 虚拟滚动、Excel 粘贴、排序/筛选/分组、PDF/Excel 导出 | 学生列表/成绩录入/考勤表 |
| **Web 响应式** | **Alpine.js 3.x** | CDN `alpinejs@3` | x-data/x-show/x-for/x-model、$dispatch 事件总线 | 所有 Web 页面交互 |
| **图表可视化** | **ECharts 5.x** / Qt Charts / PyQtGraph | CDN / 内置 / `pip install pyqtgraph` | 趋势/分段/雷达/箱线图 | 成绩趋势/班级对比 |
| **认证授权** | **python-jose[cryptography]** / **passlib[bcrypt]** | pip | JWT 签发/校验、Access+Refresh 旋转、bcrypt、设备信任 | 手写 JWT/登录 |
| **数据校验** | **pydantic v2** / **Pandera** | pip | 模型定义、序列化、DataFrame Schema | 手写参数校验 |
| **数据清洗/入库** | **tablib** / **dlt** / **Great Expectations** | pip | 统一格式、增量加载、期望套件 | 手写导入向导 |
| **报表生成** | **docxtpl** / **WeasyPrint** | pip | Word 模板→docx/pdf、HTML→PDF | 手写 XML/ReportLab |
| **任务调度** | **APScheduler** (SQLiteJobStore) | pip | 持久化作业、Cron/Interval、Web 管理 | 手写调度器 |
| **结构化日志** | **structlog** + **orjson** | pip | JSON 输出、上下文绑定、ELK 直连 | print/logging |
| **配置管理** | **pydantic-settings** | pip | 多源配置、类型校验、热重载 | 硬编码配置 |
| **API 文档** | **FastAPI 内置** + **scalar** | 内置 | OpenAPI 3.1、交互式试用 | 手写文档 |
| **测试** | **pytest** + **pytest-asyncio** + **pytest-cov** + **pytest-mock** | pip | 固件/参数化/异步/覆盖率/Mock | 无自动化测试 |
| **打包分发** | **Nuitka** (首选) / **PyInstaller** | pip | 单文件/目录、加速启动、源码加密、签名 | 无分发制品 |
| **命令面板** | **自研 + QFuzzySearch** | QCompleter + 快捷键 | ⌘K 唤起、模糊搜索、动作执行 | 菜单层层点击 |
| **键盘驱动** | **原生 QShortcut + QAction** | PyQt5 内置 | 全局/上下文快捷键、帮助覆盖层 | 鼠标点击菜单 |

### 4.1 基础设施（第 1-2 天）🟡 部分完成

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 4.1.1 | `requirements.txt` 增：上表所有库，版本锁定 | `requirements.txt` | ⬜ | 分组注释 |
| 4.1.2 | `api/` 包结构：`main.py` `deps.py` `routes/` `schemas/` `middleware/` | `api/` | ✅ | 已建 |
| 4.1.3 | `api/main.py`：应用工厂、CORS、静态文件、异常处理、健康检查 | `api/main.py` | ✅ | `create_app()` 单例，8 处 include_router |
| 4.1.4 | `api/deps.py`：`get_db`、`get_current_semester`、`get_current_user`、`require_permission` | `api/deps.py` | ✅ | 三个核心依赖均已实现 |
| 4.1.5 | PyQt5 `QThread` 启动 uvicorn：优雅关闭、端口冲突重试、PID 文件 | `gui/server_thread.py` | ✅ | 已建（代码核查 2026-08-03） |
| 4.1.6 | 主窗口状态栏：局域网地址 + 二维码 + 服务开关 + 端口设置 | `main_window.py` | ⬜ | `ServerThread.start()/stop()` 待接 |
| 4.1.7 | **alembic 初始化**：`migrations/` + 基线 + CI 门禁 | `migrations/` | 🟡 | alembic.ini 已建，`alembic init` 待执行 |

### 4.2 UI 设计系统（第 2-3 天）🟡 主体已完成（Sprint 4.10）

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 4.2.1 | 设计 Token 定义：颜色/间距/圆角/阴影/字体/动效 | `gui/theme/tokens.py` | 🟡 | 已有 theme.py 基础 |
| 4.2.2 | FluentWindow 窗口骨架 + NavigationInterface + TitleBar | `gui/main_window.py` | ✅ | 单导航已重构（PR #20） |
| 4.2.3 | 顶部模块栏：品牌 + 命令面板 + 学期切换 + 用户/通知/设置 | `gui/widgets/top_bar.py` | 🟡 | 命令面板已做，学期切换待接 |
| 4.2.4 | 侧边栏导航：分组/二级展开/图标切换/徽标 | `gui/widgets/sidebar.py` | ✅ | 数据驱动（PR #20） |
| 4.2.5 | 通用组件库：CardWidget/TableView/SettingCard/Flyout/TeachingTip/ProgressRing | `gui/widgets/common.py` | ✅ | components.py 已建（PR #21） |
| 4.2.6 | 暗色/亮色主题切换：系统跟随/手动/持久化/实时生效 | `gui/theme_manager.py` | ✅ | 2026-08-03 PR #65；LIGHT/DARK 25键同构+ThemeManager(singleton)+10 测试 |
| 4.2.7 | 键盘驱动体系：全局快捷键注册表、帮助覆盖层 | `gui/core/shortcuts.py` | 🟡 | 命令面板已做 |
| 4.2.8 | 工作流效率模式：批量操作/内联编辑/面包屑跳转 | `gui/core/workflow.py` | 🟡 | 部分组件已建 |
| 4.2.9 | **列配置持久化 / 主题密度切换** | `components.py` + `templates/` | ⬜ | 4.10.5 剩余项 |

### 4.3 服务级权限模型（第 3-4 天）

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 4.3.1 | 服务注册表 `ServiceRegistry` + `ServiceConfig` 表持久化 | `api/registry.py` | ✅ | 已建 |
| 4.3.2 | 默认服务清单：成绩录入/考勤/查分/家长通知/考试安排/班级名单/报表导出/管理接口/统计 | `api/registry.py` | 🟡 | 每服务独立开关/权限/限流 |
| 4.3.3 | PyQt5「系统维护 → 服务管理」：启停/权限绑定/限流/日志 | `gui/views/system_config.py` | ⬜ | 实时生效 |
| 4.3.4 | API 网关中间件：service_code → enabled → 权限 → 审计 → 转发 | `api/middleware/gateway.py` | ✅ | 已建（代码核查 2026-08-03） |

### 4.4 认证与会话（第 4-5 天）🟡 API 完成，UI 待接

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 4.4.1 | JWT 签发/校验：access 15min + refresh 7d，SQLite TokenStore | `api/routes/auth.py` | ✅ | 7 端点已实现 + 9 契约测试通过 |
| 4.4.2 | 登录页 + 登录/登出/刷新 API + HttpOnly Cookie | `api/routes/auth.py` + `templates/login.html` | 🟡 | API 完成；login.html 待建（Tailwind CDN + Alpine.js） |
| 4.4.3 | Web 权限装饰器 `@require_permission` | `api/deps.py` | ✅ | 已实现（deps.require_permission） |
| 4.4.4 | 设备信任：首次登录发指纹 Cookie，后续免密 30 天 | `api/routes/auth.py` | ✅ | /device/trust + /device/trusted + revoke 已实现 |
| 4.4.5 | 单点登出：PyQt5 踢下线 → Web token 失效 | `api/routes/auth.py` | 🟡 | logout 已实现，PyQt5 联动待接 |
| 4.4.6 | PyQt5 登录对话框：LoginDialog + 记住我/自动登录 | `gui/dialogs/login.py` | ⬜ | 键盘全流程可达 |

### 4.5 数据质量与导入导出服务（第 5-7 天）✅ 已完成（PR #14-17）

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 4.5.1 | ImportExportService：tablib + dlt + Great Expectations | `services/import_export.py` | ✅ | 解析→清洗→验证→预览/回滚→审计 |
| 4.5.2 | 导入向导 UI：拖拽上传→字段映射→规则预览→验证报告→入库 | `gui/views/import_wizard.py` | ⬜ | DropCardWidget + Flyout |
| 4.5.3 | 导出服务：Tabulator 导出 + tablib 多格式 + 模版变量 | `services/export.py` | ✅ | Excel/CSV/JSON |
| 4.5.4 | DataQualityService：Pandera Schema + GE 期望套件 | `services/data_quality.py` | ✅ | 列画像、业务规则 |
| 4.5.5 | 数据清洗管道：标准化/去重/缺失填补/错误隔离 | `services/data_cleaning.py` | ✅ | 全流程 |

### 4.6 核心业务 API（第 7-12 天）

| # | 模块 | 端点 | 关键点 | 状态 |
|---|------|------|--------|------|
| 4.6.1 | 成绩录入 | `GET/POST /api/scores` | 分页、Excel 粘贴、实时排名、补考标记、锁定检查 | 🟡 路由已建(10测试)，粘贴/排名待补 |
| 4.6.2 | 学生考勤 | `POST /api/attendance/batch` | 扫码/手工、批量、WebSocket 推送、离线队列 | 🟡 路由已建(9测试)，WebSocket/离线待补 |
| 4.6.3 | 学生查分 | `GET /api/students/me/scores` | 仅本人、趋势图、读预计算缓存 | ⬜ 待建 |
| 4.6.4 | 班级名单/详情 | `GET /api/classes/{id}/students` | 只读、搜索、导出、Tabulator | ⬜ 待建 |
| 4.6.5 | 考试/考场/监考表 | `GET /api/exams/{id}/rooms` | 移动端友好、打印 PDF、服务权限 | 🟡 路由已建(9测试)，打印 PDF 待补 |
| 4.6.6 | 统计数据 | `GET /api/stats/semester/{id}` | 读缓存、版本控制、304/ETag | 🟡 路由已建(stats.py)，304/ETag 待补 |
| 4.6.7 | 配置继承 | `POST /api/semester/{id}/inherit` | 预览差异、执行、审计、四色 | ⬜ 待建 |
| 4.6.8 | 数据锁定 | `POST/DELETE /api/locks` | 加锁/解锁、批量、理由必填 | ⬜ 待建 |
| 4.6.9 | 导入导出 | `POST /api/import` `GET /api/export` | 模版下载、字段映射、进度回调 | ⬜ 待建 |
| 4.6.10 | 字段元数据 | `GET/POST /api/meta/fields` | 动态字段增删查（Sprint 3.7 联动） | ⬜ 待建 |

> **复用策略**：所有 Service 层函数不变，API 层仅做参数校验、权限、序列化、异常映射、服务注册表检查。

### 4.7 前端页面（第 11-15 天）

| # | 页面 | 技术栈 | 状态 |
|---|------|--------|------|
| 4.7.1 | 登录页 | Jinja2 + Tailwind CDN + Alpine.js | ⬜ |
| 4.7.2 | 成绩录入表 | Alpine.js + Tabulator 6.x + Excel 粘贴 + 命令面板 + 虚拟滚动 | ⬜ |
| 4.7.3 | 学生考勤 | 原生 JS + Tabulator + WebSocket + 扫码枪/相机 + 离线队列 | ⬜ |
| 4.7.4 | 学生/家长查分页 | Vue 3 (CDN) + ECharts 趋势图 + 响应式 | ⬜ |
| 4.7.5 | 班级名单/考试安排 | Alpine.js + Tabulator + 打印样式 | ⬜ |
| 4.7.6 | 通用布局：顶部栏 + 侧栏 + 面包屑 | 共享 `base.html` | ✅ base.html 已建（PR #25） |

> **无构建工具**：全 CDN 引入。Tabulator：`virtualDom: true`、`pagination: "remote"`、`renderVertical: "virtual"` —— 10万行秒渲染。

### 4.8 报表生成服务（第 13-15 天）

| # | 子任务 | 产出文件 | 状态 | 备注 |
|---|--------|----------|------|------|
| 4.8.1 | ExcelTemplateService：openpyxl 加载模版 → 定义名称填充 → 保留样式/公式 | `services/report_excel.py` | ⬜ | 模版零侵入 |
| 4.8.2 | CertificateGenerator：docxtpl 渲染 → WeasyPrint 转 PDF → 循环/条件/图片 | `services/report_certificate.py` | ⬜ | 证书/通知书/准考证 |
| 4.8.3 | PrintService：win32print / lp 统一封装、批量队列、指定打印机 | `services/print_service.py` | ⬜ | 批量套打 |
| 4.8.4 | ReportFactory：统一入口 `gen_student_roster()` `gen_score_report()` `print_files()` | `services/report_factory.py` | ⬜ | 业务一行调用 |
| 4.8.5 | 报表模版管理 UI：上传 → 变量预览 → 测试渲染 → 版本管理 | `gui/views/report_template.py` | ⬜ | 模版制作规范 |
| 4.8.6 | 批量生成 Worker：QThread 后台、进度条、错误重试、ZIP 下载 | `services/report_worker.py` | ⬜ | 500 份 < 30 秒 |

### 4.9 集成验收（第 16-18 天）

| # | 验收项 | 通过标准 |
|---|--------|----------|
| 4.9.1 | PyQt5 启动 → 状态栏局域网地址 → 手机浏览器访问 → 登录 → 录分 → 实时刷新 | 端到端 < 3 秒 |
| 4.9.2 | 并发 20 设备录分/考勤，SQLite WAL 无锁死无丢失 | 压测通过 |
| 4.9.3 | 切换学期 → Web 端自动刷新数据范围 | 无需重新登录 |
| 4.9.4 | 关闭 PyQt5 → uvicorn 优雅停止、端口释放 | 无残留进程 |
| 4.9.5 | 服务管理：关闭成绩录入 → Web 403、PyQt5 不受影响 | 粒度生效 |
| 4.9.6 | 权限矩阵：教师仅见 score_entry/attendance/class_roster；学生仅见 score_query/exam_schedule | RBAC 正确 |
| 4.9.7 | 命令面板 ⌘K：搜索/跳转/执行、模糊匹配 | 核心操作 < 3 步 |
| 4.9.8 | 键盘驱动：不碰鼠标完成「新建学生→导入→分班→录分→发布」 | 效率提升 50%+ |
| 4.9.9 | 导入向导：Excel 拖拽→映射→验证→入库→审计，错误行可下载 | 3000 人 < 2 分钟 |
| 4.9.10 | 报表批量生成：选模版→勾选对象→后台生成→ZIP | 500 份 < 30 秒 |
| 4.9.11 | **6 域导航 + 全部页签 + 角色过滤**（4.10.5 集成验收） | 全绿 |

---

## 🎯 Sprint 5：考试管理 + 排课引擎（1.5 周）

> 考试管理天然支持：分考场按学期、排座次按班级、监考表推送教师手机、准考证批量打印。**排课引擎**基于 OR-Tools 约束求解器，参考 RosarioSIS 规则。依赖 Sprint 3.7 的 TeachingPlan/CourseOffering。

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 5.1 | 考试创建向导：学期/年级/科目/考场数/监考教师 | ⬜ | 复用 ExamView + 新 API |
| 5.2 | **自动分考场算法**：OR-Tools CP-SAT、均衡人数、同班分散、特殊生单独考场、冲突检测 | ⬜ | 最小化跨考场/最大化监考公平 |
| 5.3 | 排座次：蛇形/姓名拼音/考号，座次表 PDF（WeasyPrint） | ⬜ | 打印样式、移动端预览 |
| 5.4 | 监考表：教师端 Web 查看、导出、WebSocket 提醒、命令面板跳转 | ⬜ | 实时推送、离线缓存 |
| 5.5 | 准考证：批量 Word/PDF、学生手机查看、考场导航、二维码核验 | ⬜ | CertificateGenerator + PrintService |
| 5.6 | **排课引擎**：周课表自动生成、教师/教室/课程约束、冲突可视化、手动微调、锁定/解锁 | ⬜ | OR-Tools、周/日视图 |

---

## 🎯 Sprint 6：基础配置/家校报表/教师人事 + 报表引擎全集成（1.5 周）

| # | 任务 | 状态 |
|---|------|------|
| 6.1 | 学年/学期管理 UI：新建、复制配置、归档、切换、状态流转、命令面板入口 | ⬜ |
| 6.2 | 系统设置分级：全局 vs 学期级、配置版本回滚、继承向导、四色预览 | ⬜ |
| 6.3 | 成绩单推送：模版→对象→定时发→回执（邮件/微信/短信）、多通道模版 | ⬜ |
| 6.4 | 跨学年切换：历史只读/趋势对比/零停机迁移、命令面板快速切换 | ⬜ |
| 6.5 | 毕业生档案包：一键打包 PDF+照片+签名、批量生成 Worker | ⬜ |
| 6.6 | 教师人事档案：资质认证/合同/入离职/调动/档案/奖惩、导入导出 | ⬜ |
| 6.7 | 教师请假/考勤：多级审批/销假/代课/代班/统计/预警、工作流可视化 | ⬜ |
| 6.8 | 教师绩效考核：指标配置/过程记录/结果计算/等级/反馈/申诉、导出报表 | ⬜ |
| 6.9 | **报表模版市场**：内置常用模版（成绩单/通知/准考证/证书/档案包）、支持用户自定义上传 | ⬜ |
| 6.10 | **报表引擎全集成**：ExcelTemplateService + CertificateGenerator + PrintService + ReportFactory 全链路打通 | ⬜ |
| 6.11 | **毕业证书套打流程**：模版选择 → 批量预览 → 打印机选择 → 套打执行 → 打印日志 | ⬜ |
| 6.12 | **成绩单/名册批量打印**：班级勾选 → 模版选择 → 双面/装订 → 打印队列监控 | ⬜ |

---

## 🎯 Sprint 7：打包/签名/自动更新/无障碍 + 通用工具包发布（1 周）

| # | 任务 | 状态 |
|---|------|------|
| 7.1 | Nuitka 编译加速、单文件/目录、源码加密、跨平台构建脚本 | ⬜ |
| 7.2 | 代码签名：Windows (signtool) / Linux (GPG)、公证流程 | ⬜ |
| 7.3 | 自动更新器：GitHub Release API、增量更新、静默安装、回滚、通道 | ⬜ |
| 7.4 | 无障碍：axe-core 0 违规、键盘全流程、屏幕阅读器、高对比度、字号缩放 | ⬜ |
| 7.5 | 发布 `edu-system-common` 到内部 PyPI：Token/配置/工具类/异常/基类/装饰器 | ⬜ |
| 7.6 | 文档站：Sphinx + API 文档、用户手册、运维手册、开发指南 | ⬜ |
| 7.7 | **Windows 专项矩阵**：windows-latest CI 跑测、中文路径/编码、高 DPI、防火墙、服务注册 | ⬜ |
| 7.8 | **NSIS 安装包**：管理员权限、服务注册、防火墙、快捷方式、卸载干净 | ⬜ |
| 7.9 | **杀毒白名单**：360/火绒/Defender 官方渠道提交 | ⬜ |
## 📝 任务完成记录模板（每完成一项必填）

```markdown
## ✅ [日期] 任务编号 - 任务名
- **耗时**：X 小时
- **关键决策**：
  1. ...
  2. ...
- **踩坑/解决**：
  - 问题：...
  - 方案：...
- **后续影响**：需同步更新的文件/测试/文档
- **验收证据**：测试输出 / 截图 / 日志
```

---

## 🔄 如何恢复工作（新对话必读）

1. **打开此文件**，看「总体路线图」当前 Sprint 指向哪个任务
2. **查看 git 状态**：`git status` 确认无未提交改动；`git log --oneline -5` 看最近进度
3. **运行测试确认基线**：`export PATH="项目根目录/venv/bin:$PATH" && pytest tests/ -q`（基线 125 passed, 2 warnings）
4. **按序执行**当前 Sprint 下一项未完成任务（新功能先开分支 `feat/sprint-X.Y-*`）
5. **完成即记录**在「任务完成记录」区，CI 绿后 `gh pr merge --squash --admin`
6. **续接说法**：「继续开发 UI 重构」/「从 Sprint 4.10.1 配置加载器开始」/「从 Sprint 3.7 数据模型重构开始」

---

## 🎯 关键决策总结（去重合并）

| 决策点 | 选择 | 理由 |
|--------|------|------|
| **时间分界模型** | `AcademicYear` + `Semester` 双层，`semester_id` 强制落所有业务表 | 业界通用、查询最简单、跨学期报表 UNION |
| **配置隔离** | `GlobalSetting` + `SemesterConfig(semester_id, key, value, version, inherited_from)` | 评分线/考号规则/排课约束随学期变 |
| **上下文传播** | SQLAlchemy 事件自动注入 `WHERE semester_id = :active` + FastAPI `Depends` | 零侵入业务代码、双端复用 |
| **统计预计算** | `SemesterStatsCache` 表 + 事件驱动增量刷新 + 版本控制 | 界面零实时聚合、毫秒级响应 |
| **配置继承** | 深拷贝 + 选择性覆盖 + 四色预览 + 版本回滚 | 新学期 3 分钟初始化 |
| **数据锁定** | `DataLock` 通用表 + `before_flush` 拦截 + 四级语义(none/soft/hard/semester) | 行级/表级/学期级 |
| **数据模型** | **主数据 + 学期快照 + 变动流水** 三层结构；**ext_json + FieldDefinition 字段注册表** | 跨学期流转不断链；字段动态增删零代码、低耦合 |
| **嵌入式服务端** | PyQt5 `QThread` + `uvicorn.run(host="0.0.0.0")` + 服务注册表 | 改动最小、复用 SQLite WAL |
| **服务级权限** | `ServiceRegistry` + API 网关中间件 + 角色/权限/速率三维 | 管理员随时开关服务 |
| **前端技术栈** | Jinja2 + CDN (Alpine.js/Tabulator/Vue3/ECharts) 无构建 | 页面少、打包极简、移动端适配快 |
| **缓存策略** | 预计算表为主 + SQLite WAL/mmap/page_cache 为辅 + HTTP 304 | 无需 Redis、单机自给自足 |
| **系统上下文** | `SystemContext` 单例 + `ContextProvider` 注入 + 顶部栏唯一入口 | 一处定义、全端共享 |
| **零部件复用** | 一切可用的都拿来用，手搓仅填补业务缺口 | 节省约 60-70% 非业务代码 |
| **版本管理** | 语义化版本 + 约定式提交 + 自动化变更日志 + 标签化发布 + 回滚演练 | 5 分钟定位引入版本 |
| **目标平台** | **Windows 原生部署**（Mint/RDP 仅开发调试） | 用户 2026-08-02 定案 |
| **UI 设计** | 配置驱动 `ui_config.json` 单源，业界模式全部采纳（权限过滤/图标/空状态/批量/确认） | 改配置不改代码 |

---

## 🎯 Windows 兼容性专项规划（贯穿所有 Sprint）

> 目标：**开发环境 Linux，生产环境 Windows**，零代码修改切换。打包期在 Windows，实物打印机验收；部署期零配置，双击即用。

### 1. 核心兼容性清单

| 领域 | Linux 默认 | Windows 适配方案 | 验收标准 |
|------|-----------|------------------|----------|
| **路径分隔符** | `/` | `pathlib.Path` / `os.path.join`，禁用硬编码 `/` | 所有路径操作跨平台通过 |
| **文件编码** | UTF-8 | 显式 `encoding='utf-8'`，BOM 处理 `utf-8-sig` | 中文无乱码 |
| **换行符** | `\n` | 文本统一 `\n`，Git `core.autocrlf=input` | Git diff 无噪音 |
| **大小写敏感** | 区分 | 路径比较统一 `lower()`，SQLite `case_sensitive_like=OFF` | 查询一致 |
| **环境变量** | 区分大小写 | 读取统一 `.upper()`，`python-dotenv` | 配置加载一致 |
| **进程管理** | fork/systemd | `multiprocessing.set_start_method('spawn')`、NSSM 服务 | 后台稳定运行 |
| **文件锁** | fcntl | `portalocker`，SQLite WAL | 并发无死锁 |
| **打印** | CUPS/lp | `win32print` 封装 `PrintService` | 套打零差异 |
| **打包分发** | AppImage | **Nuitka** 单文件 `.exe` + NSIS 安装包 | 双击运行、卸载干净 |
| **代码签名** | GPG | `signtool` + 时间戳服务器、EV 证书 | SmartScreen 无警告 |
| **自动更新** | AppImageUpdate | GitHub Release API + 静默安装 + 回滚 | 用户无感 |
| **服务注册** | systemd | NSSM 注册 `uvicorn` 服务 | 开机自启、崩溃重启 |
| **权限/UAC** | sudo | `IsUserAnAdmin()` 检测、安装包请求管理员 | 自动提权 |
| **字体渲染** | 系统字体 | 内嵌 Microsoft YaHei/SimSun TTF | 无字体缺失 |
| **中文输入法** | IBus/Fcitx | Qt 原生支持 | 拼音/五笔正常 |
| **高 DPI** | Wayland/X11 | `AA_EnableHighDpiScaling` + `AA_UseHighDpiPixmaps` | 4K/150%/200% 无模糊 |
| **防火墙/端口** | iptables | `netsh advfirewall` 开放 8080/8081 | 安装包自动配置 |
| **杀毒/白名单** | 无 | 代码签名 + 360/火绒/Defender 白名单申请 | 无误报拦截 |

### 2. 平台抽象（`core/platform.py`）

```python
import os, sys, tempfile
from pathlib import Path

class Platform:
    @staticmethod
    def is_windows() -> bool:
        return sys.platform.startswith("win")

    @staticmethod
    def data_dir() -> Path:
        if Platform.is_windows():
            return Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "EduSystem"
        return Path("/var/lib/edusystem")

    @staticmethod
    def config_dir() -> Path:
        if Platform.is_windows():
            return Path(os.environ.get("APPDATA", "~")) / "EduSystem"
        return Path("/etc/edusystem")

    @staticmethod
    def default_printer() -> str:
        if Platform.is_windows():
            import win32print
            return win32print.GetDefaultPrinter()
        import subprocess
        return subprocess.check_output(["lpstat", "-d"]).decode().split(":")[-1].strip()
```

### 3. Windows CI 强制（`.github/workflows/ci.yml` 片段）

```yaml
  windows-compat:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install -r requirements.lock
      - run: pytest tests/ -x -q --tb=short
      - run: python -m pytest tests/windows_specific.py -v
      - run: python -c "from services.print_service import PrintService; PrintService.test_windows_print()"
```

### 4. Windows 验收清单（Sprint 7 完成前全绿）

| 项 | 验收方式 | 通过标准 |
|----|----------|----------|
| 双击运行 | Win10/11 裸机安装 `.exe` | 无依赖缺失、无黑框、3 秒出主界面 |
| 安装包 | NSIS 生成 `.exe` | 管理员权限、自动注册服务、配置防火墙、快捷方式 |
| 代码签名 | `signtool verify /pa /v app.exe` | 签名有效、SmartScreen 无警告 |
| 服务注册 | `sc query EduSystemAPI` | RUNNING、AUTO_START、重启拉起 |
| 套打/打印 | 实物打印机 | 偏差 < 1mm、双面/装订正确 |
| 高 DPI | 4K 150%/200% | 无模糊、控件不重叠 |
| 中文路径 | 用户名含中文安装 | 启动正常、日志/模版正常 |
| 自动更新 | 模拟新版本 | 静默下载安装、版本号变更、回滚可用 |
| 卸载干净 | 控制面板卸载 | 无残留文件/注册表/服务/防火墙规则 |
| 杀毒白名单 | 360/火绒/Defender | 无误报、无拦截 |

---

## 🎯 版本管理与复盘体系

> **目标**：每次提交、发布、回滚可追溯可复现；出问题 5 分钟内定位「哪个版本引入、哪行代码变更、哪个依赖升级」。

### 1. 版本号规范（语义化 + 构建元数据）

```
MAJOR.MINOR.PATCH-PRERELEASE+BUILD
示例：v2.1.3-rc.2+a1b2c3d.202607311430.main
```

| 字段 | 规则 |
|------|------|
| MAJOR | 不兼容变更（DB Schema 破坏、接口移除） |
| MINOR | 向后兼容功能新增 |
| PATCH | 向后兼容缺陷修复 |
| PRERELEASE | alpha/beta/rc + 序号 |
| BUILD | `git_short_sha.timestamp.branch` |

### 2. 约定式提交

`<type>(<scope>): <subject>` — feat/fix/perf/refactor/docs/chore/ci/test/revert
Scope 建议：`api` `gui` `db` `auth` `stats` `lock` `config` `sync` `deploy` `deps` `ui`

### 3. 分支策略（GitHub Flow + 发布分支）

```
main (受保护，PR 合入，CI + Review)
  ├─ feature/*  (功能分支)
  ├─ fix/*      (缺陷分支)
  ├─ release/v2.1.x (发布分支，仅 cherry-pick PATCH)
  └─ hotfix/v2.1.3  (热修复，合并回 main + release)
```

### 4. 自动化变更日志

- 工具：`git-cliff`；触发：打标签 `v*` 时 GitHub Action 自动生成 `CHANGELOG.md` + Release Notes

### 5. 复盘定位工具链

| 场景 | 命令 | 定位时间 |
|------|------|----------|
| 回归 Bug 定位 | `git bisect start v2.1.3 v2.1.0 -- scripts/test_regression.py` | < 5 分钟 |
| 某文件演变历史 | `git log --oneline --all -- gui/views/score.py` | < 1 分钟 |
| 依赖差异 | `pip list --format=freeze > v2.1.0.txt && diff ...` | < 30 秒 |
| 某行最后修改 | `git blame -L 120,150 gui/views/score.py` | < 10 秒 |
| 回滚到上一稳定版 | `git tag -d v2.1.3 && 部署 v2.1.2` | < 2 分钟 |

### 6. 发布检查清单（DoD）

```
[ ] 所有 CI 通过（单测/集成/迁移演练/安全扫描/无障碍）
[ ] CHANGELOG.md 自动生成且人工核对
[ ] 版本号语义化递增（pyproject.toml / __version__.py 同步）
[ ] Git 标签已打
[ ] 制品已构建上传（Wheel / Nuitka / Docker）
[ ] 数据库迁移已验证（正向/逆向/幂等/校验和）
[ ] 回滚演练预演环境跑通（< 30 秒）
[ ] 文档同步更新（API/用户手册/运维手册/DEV_PLAN.md）
```

---

## 🐙 GitHub 私有仓库 & 全功能启用策略

### 仓库设置（创建时一次性完成）

| 功能 | 配置 | 目的 |
|------|------|------|
| 仓库可见性 | Private | 仅授权成员 |
| 分支保护 | `main`/`release/*` 必须 PR + CI + 1 review | 防直接推送 |
| 自动合并 | Enable auto-merge (squash) | 保持历史整洁 |
| 依赖图 | Enable | 供应链可视化 |
| Dependabot | Security + Version (weekly) | 自动升级修复漏洞 |
| Code scanning | CodeQL (Python) | 静态分析 |
| Secret scanning | Push protection | 防泄露 |
| Packages | 内部 PyPI (`edu-system-common`) | 工具包分发 |
| Pages | Sphinx 文档站 | API 文档/手册 |
| Projects | Kanban (Sprint 列、Task 卡) | 可视化进度 |
| Discussions | Enable | 沉淀技术决策 |

### CI/CD 流水线（`.github/workflows/ci.yml`）

- 触发：push 到 main/master/release/* + 全部分支 PR + 夜间 schedule `0 2 * * *` + workflow_dispatch
- PYTHON_VERSION=3.12
- Job：`test`（required status check）/ contract / 代码规范检查（ruff E/F/I/W 排除存量）/ 安全扫描 / GUI 测试（xvfb）/ windows-compat
- 合并硬条件：① ≥1 write 权限 approving review；② required status check 名为 `test`
- 合并流程（当前常态）：`gh pr merge --squash --admin`（用户已放开分支保护）

### Issue/PR 模板

`bug_report.yml`（复现步骤/环境/日志/截图）、`feature_request.yml`（用户故事/验收标准/影响面）、`security_report.yml`（私密上报）、`pr_template.md`（关联 Issue/变更摘要/测试清单）

---

## 🎯 架构收敛调整（贯穿所有后续 Sprint）

| 调整项 | 具体落地 | 验收标准 |
|--------|----------|----------|
| **1. TDD 轻量化** | `tests/contract/` 先行、`TestClient` + `sqlite3 :memory:` | 新增 API 必先有契约测试、CI 门禁 |
| **2. 单一写入层** | `core/unit_of_work.py` + 所有写操作统一入口 | 无直连 `session.commit()`、事务边界显式 |
| **3. Alembic + CI 门禁** | `migrations/` + upgrade/downgrade CI 必跑 | 升降级绿、checksum 校验 |
| **4. 依赖锁定 + 供应链** | `pip-tools` 生成 `requirements.lock` + `pip-audit` 周扫 | 0 高危、可复现环境 |
| **5. 统一上下文** | `core/context.py` `SystemContext` 单例 + 依赖注入 | 无 `thread_local`/`session`/`request.state` 混用 |
| **6. GitHub 全功能** | 按上表一次性开启、CI/CD 落地 | 全绿、自动发布 |
| **7. 字段动态增删** | `ext_json` + `FieldDefinition` 注册表 + 动态表单/表格/导入导出 | 增删字段零代码、双端即时生效 |

---

## 🎯 主菜单最终版（V2 重构，配置驱动）

### 顶部全局栏（固定 64px，PyQt5/Web 同构）

| 区域 | 元素 | 交互 |
|------|------|------|
| 左·系统上下文 | 🏫 校区名 / 📅 学年学期 ▼ / 🟢 在线 | 切换 → `SystemContext.emit_change('semester_id')` |
| 中·状态聚合 | 🔒 服务 / 🔒 锁定 / 📦 离线队列 | 悬停详情，点击跳管理页 |
| 右·用户/版本 | 👤 用户 ▼ / v2.0.0·API v1·DB v12 / ⚙️ 服务管理 | 个人中心/关于/服务管理 |

### 左侧侧边栏（可折叠 200/48px，Web 抽屉式）— 由 `ui_config.json` 驱动

```
📁 学生管理    学生信息 / 学籍变动 / 新生注册 / 升年级毕业
📁 教师管理    教师档案 / 排课代课
📁 考试管理    考试列表 / 分考场排座 / 监考表 / 准考证
📁 成绩管理    成绩录入 / 成绩统计 / 成绩单生成
📁 考勤管理    日常考勤 / 请假销假 / 考勤统计
📁 学期管理    学年学期列表 / 继承向导 / 配置版本 / 激活切换
📁 统计中心    学期概览 / 考试分析 / 预设报表
📁 基础配置    年级班级科目 / 教室考场 / 评分标准 / 编号规则 / 自定义字段
📁 系统维护    服务管理 / 锁定中心 / 定时任务 / 备份归档 / 审计日志 / 系统设置
📁 家校通讯    【预留 Sprint 6】成绩单推送 / 通知模版 / 回执追踪
```

### Web 端移动布局（单列 + 底部 Tab Bar）

- 教师：首页/成绩/考勤/我；学生：首页/成绩/考试/我；家长：首页/成绩/通知/我；管理员：首页/服务/锁定/统计/我

---

## 🎯 界面元素级通用组件（跨端复用）

| 组件 | PyQt5 实现 | Web 实现 | 用途 |
|------|------------|----------|------|
| `SemesterBadge` | QLabel + 状态色 + tooltip | `<span class="badge semester">` | 学期显示 |
| `LockIndicator` | QToolButton 🔒 + 菜单 | `<button class="lock">` | 锁定状态 |
| `StatBadge` | QLabel 只读灰背景 | `<span class="stat">` | 缓存统计值 |
| `ServiceToggle` | QCheckBox + 权限灰化 | `<switch class="service">` | 服务开关 |
| `OfflineBadge` | N/A | `<span class="offline">` | 离线待同步数 |
| `VersionTag` | 状态栏永久显示 | 页脚 `v2.0.0·API v1` | 版本追踪 |
| `ContextSwitcher` | 顶部栏下拉 | Select + BroadcastChannel | 学期/校区/角色切换 |
| `InheritPreview` | QDialog 四色表格 | Modal 四色 Diff | 配置继承预览 |
| `A11yToolbar` | 菜单高对比度/字号 | 浮动按钮 | 无障碍入口 |

---

## 🎯 许可证合规清单（引入前必核）

| 库 | 许可证 | 商用可否 | 修改需开源 | 备注 |
|----|--------|----------|------------|------|
| PyQt-Fluent-Widgets | GPL v3 | ✅ | ✅ (若改源码) | 仅 import 使用不触发传染 |
| Tabulator / Alpine.js | MIT | ✅ | ❌ | 完全自由 |
| ECharts | Apache 2.0 | ✅ | ❌ | 保留版权声明 |
| CRUDAdmin | MIT | ✅ | ❌ | 完全自由 |
| QScintilla | GPL v3 | ✅ | ✅ | 同 PyQt-Fluent-Widgets |
| markdown-it-py | MIT | ✅ | ❌ | 完全自由 |

> **决策**：仅通过 import/调用使用，不修改库源码 → GPL 传染不触发，商用零风险。

---

## ⚠️ 风险与缓解

| 风险 | 缓解 |
|------|------|
| PyQt-Fluent-Widgets 版本破坏 API | 锁定精确版本、单测覆盖关键组件 |
| GPL 传染误区 | 仅 import 调用、不修改源码、动态链接 |
| 组件库过重影响启动 | 按需导入、延迟加载非首屏组件 |
| Web CDN 离线不可用 | Service Worker 缓存所有 CDN 资源 |
| 数据模型重构数据丢失 | 双写过渡 + 校验和 + 回滚演练 + 预演环境 |
| 字段动态增删性能 | 低频 JSON、高频字段提升为真实列 |

---

## 📋 附录：打磨约定（Sprint 3.8.5）

> 逐项打磨阶段的工程规范，2026-08-03 落文。

### 表结构变更四步曲（禁止手写 ALTER）

1. **改模型**：`models/__init__.py` 修改字段/表（新模型加类，旧模型改列）
2. **生成迁移**：`./venv/bin/alembic revision --autogenerate -m "描述"`
   - 检查生成的迁移文件：**剔除 autogenerate 误报的存量差异**（如 uq_student_code drop_index）
   - 新表/新列若由 baseline_v2 create_all 幂等创建，**无需单独迁移**（实测：手写会重复建表冲突）
3. **本地验证**：`alembic upgrade head` + `pytest tests/ -q`
4. **提交**：模型+迁移+测试同一 PR；CI db-migrate job 全绿后合并

### 经验（2026-08-03 实测）

- **新模型靠 baseline 同步**：baseline_v2 用 `Base.metadata.create_all()`，新增模型自动建表；autogenerate 手写迁移会「table already exists」冲突 → 删掉多余迁移即可
- **SQLite DDL 隐式提交**：CREATE TABLE 不可被 `session.rollback()` 撤销（迁移脚本测试须用 DML 验证回滚）
- **改表必带测试**：新增/修改列的同时补模型测试，防止 CI 迁移校验漏检

---

*文档版本：v2.0（2026-08-03 全面对齐）*
*上次更新：Sprint 3.7 数据模型重构完成（PR #42-63），Sprint 3.8 打磨准备收尾，下一步逐项打磨*
