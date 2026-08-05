# 待办缺口跟踪（TODO）

> 与 DEV_PLAN_v3.md 状态保持一致。完成一项划一项 `[x]`。
> 最后同步：2026-08-04

## ✅ M2 模块化配置化重构（已完成 2026-08-04）

- [x] M2-1 配置单源化：删死代码 config.py（零引用），全仓统一 config/ 包单一配置源
- [x] M2-2 死代码清理：删 navigation.py/design_system.py（互成闭环零引用）+ templates 空目录 + TEMPLATE_DIR 死配置
- [x] M2-3 API 补 /api/config：新路由暴露 ui_config（品牌/6域导航/页签/主题），gateway 白名单公开，+2 契约测试
- [x] M2-4 依赖精简：104→79 包（移除 great-expectations/pdf-reports/pyqt-fluent-widgets 三个零引用包），pandas 转显式；cache 双模块核查非重复
- [x] M2-5 文档重写：README 公开友好版（清本机路径）+ CHANGELOG 重写为新仓库历史
- [x] M2-6 CI 适配：补 license job（pip-licenses 门禁 + THIRD_PARTY.md）；lint exclude 清理已删文件；本地预演 ruff/format/许可证全绿

## ✅ M1 新仓库搭建（已完成 2026-08-04）

- [x] M1-1 git init -b main + 首次 commit（f5d4082，182 文件，敏感清零前置）
- [x] M1-2 venv 重建（python3.11 + requirements.lock，108 运行包 + 测试工具）；补齐依赖清单缺口 factory_boy/pytest-timeout/itsdangerous（旧仓库遗漏，CI 会红）
- [x] M1-3 冒烟：fresh pytest = **277 passed** + main.py --help 正常退出
- [x] main.py 新增 --help/-h 支持（GUI 前退出，供冒烟）
- [x] data/ 目录（CI 对齐方式 `mkdir -p data/cache/stats`，测试空库，内容 gitignore 忽略）

## ✅ M0 准备与冻结（已完成 2026-08-04）

- [x] M0-1 旧仓库冻结：README 顶部 FROZEN 标注（master a73a775），停止推送
- [x] M0-2 复核 integrate-clean：=== master(a73a775)，fresh pytest = **277 passed**，零残留
- [x] M0-3 排除项核验：新仓库已清 73400340/import_exam_scores.py/import_real_data.py/`"alembic`；templates+static(3死文件base.html/js/css) 已删；data/logs/crudadmin_data/exports 未复制
- [x] ~/.git 误建 home 仓库已隔离为 ~/.git.bak_home_mistake（可逆）

## ✅ M4 公开上线（已完成 2026-08-04）

- [x] M4-1 建公开仓库 + push：https://github.com/laozhudu/edu-management（PUBLIC，main，11+ commit）
- [x] M4-2 CI 全绿：10 jobs（lint/license/security/test/contract/db-migrate/test-gui + win/linux 构建）。修复：跨平台 lock（pyqt5-qt5 双分支 marker）、Ubuntu 24.04 libgl1、nuitka pyqt5 插件、GUI 测试挂起（MainWindow 登录框跳过）
- [x] M4-3 Release v3.0.0（gh release create --generate-notes；产物按用户要求不上传，assets=0）
- [x] M4-4 旧仓库 edu_system_v2 已 archived+PRIVATE 确认（无需操作）
- [x] ci.yml on.push 加 tags 触发（未来 tag 自动发 Release）

## ✅ M3 加固验收（已完成 2026-08-04）

- [x] M3-1 敏感扫描：filter-repo 重写 8 commit 历史中性化敏感字样；git log + 工作树 校名关键词 零命中
- [x] M3-2 全量测试+格式：279 passed + ruff All checks passed
- [x] M3-3 安全扫描：bandit 0 高危（修复 cache.py B324 ETag-md5 usedforsecurity=False）+ gitleaks no leaks
- [x] M3-4 空库迁移：alembic upgrade head 到 head，模型 37 表全建（missing=[]；extra 3 历史表 domain_events/dw_refresh_logs/teacher_subjects，CI 兼容不阻断）
- [x] M3-5 Windows dry-run：10 jobs YAML 语法验证；修复 build-windows 缺失的 assets/icon.ico（Pillow 生成占位图标）；实际构建 M4 push 后 CI 触发

## 🔴 规划变更（2026-08-04）

- [x] **Web 端升级为与桌面功能完全一致**（用户定案）：非简化版/非只读；6 域 26 页签 + 全局能力逐项对等。规划已改：REQUIREMENTS G 组（含功能对等清单）、DEV_PLAN_v3 M5-G（G1-G11）、REFACTOR_PLAN Phase 5、README。技术栈后续单定（候选 SPA Vue3 / HTMX+Jinja2）
- [ ] 历史重写后 CHANGELOG commit hash 待更新（filter-repo 重写 8 个 commit）

## ✅ M3-1 敏感扫描（已完成 2026-08-04，M4 前补漏二次）

- [x] test_data/generate.py:348-349：校名关键词→示例学校、校名代码→SLZX（无测试断言依赖旧值，test_ui_config 断言"示例学校"一致）
- [x] scripts/migrate_semester_context.py:183：校名代码→SLZX
- [x] docs/ui_redesign_preview.html + _v2.html（含校名原型）已删（旧仓库兜底）
- [x] 复查：校名代码 全仓零命中；"校名关键词"仅剩文档扫描命令示例/防回归断言（tests/gui/test_gui_main_window.py:110）
- [x] **补漏（M4 前自查发现）**：源码/脚本 13 处硬编码本机路径 `/home/xsx/旧仓库/...` → 全部改 config 引用（PROJECT_ROOT/STORAGE_DIR/CACHE_DIR/DB_PATH/DATA_DIR）；tests/smoke.py 改相对路径；ui_config.json $schema 旧仓库 URL 移除；pyproject URLs 改新仓库名
- [x] 历史二次重写（filter-repo + filter-branch）：城南中学/CNZX//home/xsx/edu_system_v2/edu_system_v2 全词 git log 零命中
- [x] **经验**：敏感扫描词表必须含【本机绝对路径 / 旧仓库名 / 内网 IP】——首次只扫校名漏了路径，M4 前自查才抓出

## 🔴 基础设施缺口

- [x] **alembic CI 门禁推送验证**（db-migrate job 多 PR 全绿，PR #42-63）
- [x] 打磨约定落文：表结构变更一律 `alembic revision`（禁手写 ALTER）→ DEV_PLAN 附录
- [x] ~~CHANGELOG.md 初始化~~（git-cliff 配置 + 内容已生成）
- [x] ~~清理远端 8 个已合并旧分支~~（远端仅保留 master）

## 🟡 Sprint 4 剩余（4.10.5 收尾）

- [ ] 列配置持久化 / 主题密度切换（4.2.9）
- [ ] 6 域导航 + 全部页签 + 角色过滤集成验收（4.9.11）
- [x] **桌面 GUI 真实启动确认**（快捷方式已建：~/桌面/教务管理系统.desktop，真实启动验证通过）

## ⬜ Sprint 4 未开始

- [ ] PyQt5 LoginDialog（4.4.6，auth API 已就绪）
- [ ] 导入向导 UI（4.5.2，服务层已就绪）
- [ ] 报表服务四件套：report_excel / report_certificate / print_service / report_factory（4.8）
- [ ] 主题切换 manager（4.2.6）
- [ ] 主窗口状态栏局域网地址 + 二维码（4.1.6）

## ✅ Sprint 3.7 数据模型重构（已完成 PR #42-63）

- [x] 3.7.1-3.7.5 实体拆分（用户决策简化跳过，现有 semester_id 方案已满足）
- [x] 3.7.6-3.7.12 字段动态机制（ext_json + FieldDefinition + API + 表单/表格/导入导出/查询）
- [x] 3.7.13-3.7.15 课程/学分/教材/宽表（用户决策取消，按需计算）
- [x] 3.7.16-3.7.18 折算分 + 权限规范化 + RLS
- [x] 3.7.19-3.7.22 归档 + 迁移脚本 + 验收基线

## 已知技术债

- [ ] mypy typecheck 禁用中（~1975 存量错误）
- [ ] ruff 弃用警告清理（pyproject lint 忽略表：'unfixable'→'lint.unfixable'、UP038）
- [ ] `components/navigation.py` 死代码（依赖未装 qfluentwidgets，无人引用）——待删或待装库
- [ ] `design_system.py` 死代码（740 行，仅被 navigation.py 引用；主程序用 components.py 的 CommandPalette）——GUI 加固扫描发现，待清理
- [ ] 视图 QSS 批量令牌化（GUI 加固扫描发现）：theme.py C 字典已补全 27 键，但 teacher/exam/student/score 等 12 视图仍硬编码 54 处颜色——需统一改为引用 C 字典（普通字符串 QSS 需谨慎转 f-string 转义）
- [ ] 原型遗留：ui_redesign_preview_v2.html 待办状态列显示原始 tag

## ✅ M5-A 学期上下文 + M5-B1/2 统计预计算（2026-08-05 进行中）

- [x] M5-A1 会话上下文管理器（线程局部 + semester_context，8 单测）
- [x] M5-A2 before_compile 自动注入 semester_id/school_id（6 单测）
- [x] M5-A3 FastAPI 学期依赖注入（5 契约测试）
- [x] M5-A4 学期切换器 UI（顶部栏显示 + 广播刷新，GUI 测试）
- [x] M5-A5 学期维度权限（SEMESTER_VIEW/EDIT/ADMIN，5 单测）
- [x] M5-B1 核心指标清单（20 单测覆盖学生/班级/教师/成绩/考试）
- [x] M5-B2 事件驱动增量刷新（mark_stats_dirty + handle_stats_dirty + 注册，6 单测）
- [ ] M5-B3 后台 Worker（进度/取消）— StatisticsWorker 已有框架，补 2 单测
- [ ] M5-B4 手动触发（幂等契约）
- [ ] M5-B5 缓存 API + 304（无实时聚合契约）

## ✅ M5-C 配置继承与锁定（2026-08-05 进行中）

- [x] M5-C2 配置版本回滚 + 软删除（history 快照表，4 单测，本地全量 346 passed）
- [ ] M5-C1 继承向导 UI（依赖 C2 版本机制，四色预览 GUI 测试）
- [x] M5-C3 锁定工具栏 UI（LockToolbar + 权限控制，5 GUI 测试，PR #7 合并）
- [x] M5-C4 典型锁定场景自动加锁（4 单测 + 修复 _is_entity_locked bug，PR #6 合并）
- [x] M5-C1 继承配置向导 UI（四色预览，4 GUI 测试，PR #5 合并）
- [x] M5-C3 锁定工具栏 UI（LockToolbar + 权限控制，5 GUI 测试，PR #7 合并）
- [x] M5-C4 典型锁定场景自动加锁（4 单测 + 修复 _is_entity_locked bug，PR #6 合并）

## M5-D 桌面补全（2026-08-05 进行中）

- [x] M5-D3 密度切换 + QSettings 持久化（6 单测，PR #8）
- [x] M5-D5 报表模板管理服务（13 单测，PR #9）
- [x] M5-D6 批量生成 Worker（7 单测，500 份 0.3s 基准，PR #10 合并）
- [ ] M5-D1 LoginDialog（GUI 测试）
- [ ] M5-D4 状态栏局域网（GUI 测试）
- [ ] M5-D2 导入向导 UI（最大任务）
