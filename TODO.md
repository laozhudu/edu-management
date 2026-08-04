# 待办缺口跟踪（TODO）

> 与 DEV_PLAN_v3.md 状态保持一致。完成一项划一项 `[x]`。
> 最后同步：2026-08-04

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

## ✅ 敏感残留清零（2026-08-04，首次 commit 前置）

- [x] test_data/generate.py:348-349：校名关键词→示例学校、校名代码→SLZX（无测试断言依赖旧值，test_ui_config 断言"示例学校"一致）
- [x] scripts/migrate_semester_context.py:183：校名代码→SLZX
- [x] docs/ui_redesign_preview.html + _v2.html（含校名关键词原型）已删（旧仓库兜底）
- [x] 复查：校名代码 全仓零命中；"校名关键词"仅剩文档扫描命令示例/防回归断言（tests/gui/test_gui_main_window.py:110）

## 🔴 基础设施缺口

- [x] **alembic CI 门禁推送验证**（db-migrate job 多 PR 全绿，PR #42-63）
- [x] 打磨约定落文：表结构变更一律 `alembic revision`（禁手写 ALTER）→ DEV_PLAN 附录
- [x] ~~CHANGELOG.md 初始化~~（git-cliff 配置 + 内容已生成）
- [x] ~~清理远端 8 个已合并旧分支~~（远端仅保留 master）

## 🟡 Sprint 4 剩余（4.10.5 收尾）

- [ ] 列配置持久化 / 主题密度切换（4.2.9）
- [ ] 6 域导航 + 全部页签 + 角色过滤集成验收（4.9.11）
- [ ] **桌面 GUI 真实启动确认**（xvfb 已验证，待用户本机验证）

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
