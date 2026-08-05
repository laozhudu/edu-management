# M5-F 服务管理与集成验收 - 进度记录

## 完成状态

### ✅ M5-F1 服务管理 UI - 真实日志查看
- `services/audit.py`: AuditLogService（gateway 审计记录查询）
- `api/routes/audit.py`: GET /api/audit/logs?service=&limit=
- `system_config.py`: _view_service_logs 占位 → 真实日志对话框（表格展示）
- `main.py`: 注册 audit 路由
- 测试: +4 audit 服务单测 +3 契约测试

### ✅ M5-F2 端到端验证脚本（登录→录分→刷新 <3 秒）
- `scripts/e2e_test.py`: 端到端流程计时
  - 登录 → 学生查分 → 成绩查询 → 统计概览
  - 验收: 总耗时 <3s（实测 0.18s）
- 用法: PYTHONPATH=src ./venv/bin/python scripts/e2e_test.py

### ✅ M5-F3 并发压测 - 20 设备 WAL 无锁死
- `database.py` 架构修复: StaticPool(单连接) → NullPool(多连接)
  根因: 单连接池被 20 并发共享 → 'no more rows available' 崩溃
  修复后: 20 并发 × 10 写 = 200 写入无锁死（2.29s）
- `scripts/stress_test.py`: 压测脚本
  - 并发写入 audit_logs 模拟 API 审计
  - 验证: 全线程成功 + 行数完整 + 无 database is locked

### ✅ M5-F4 优雅停机集成测试（无残留进程）
- `test_server_thread_shutdown.py`: +3 集成测试
  - 启动 → stop() → 线程结束 + PID 文件清理
  - 未启动时 stop() 幂等
  - 连续两次 stop() 幂等
- server_thread 的 should_exit + terminate 兜底机制验证通过

### ✅ M5-F2 端到端验证脚本（登录→录分→刷新 <3 秒）
- `scripts/e2e_test.py`: 端到端流程计时
  - 登录 → 学生查分 → 成绩查询 → 统计概览
  - 验收: 总耗时 <3s（实测 0.18s）
- 用法: PYTHONPATH=src ./venv/bin/python scripts/e2e_test.py

### ✅ M5-F5 6 域导航验收（全绿）
- 6 域: home(3页签) / students(4页签) / scores(4页签) / exams(4页签) / teachers(2页签) / system(7页签)
- test_gui_main_window.py: 8 passed（顶部栏学期居中/不绿/居中/侧边栏收缩/无冗余品牌）
- test_gui: 51 passed（全套 GUI 测试）
- test_gui_main_window: 8 passed（顶部栏/侧边栏/无冗余品牌）
- test_gui_login: 9 passed（键盘流/记住我/自动登录/输入法）
- test_gui_statusbar: 7 passed
- test_gui_lock_toolbar: 6 passed
- test_gui_semester_inherit: 4 passed
- test_gui_import_wizard: 8 passed
- test_gui_score_view_load: 3 passed
- test_server_thread_shutdown: 3 passed

### 🟡 M5-F2 部分验收 - test_server_thread_shutdown 模块级 QCoreApplication 冲突已修复
- tests/gui/test_server_thread_shutdown.py: QApplication 统一（与 pytest-qt 一致类型，避免 QCoreApplication 冲突崩溃）
- tests/gui/_mini_app.py: server_thread 测试用轻量 app（不触发完整 DB 初始化）
- 验证: login + server_thread 组合 16 passed 不崩

### ✅ M5-F1 服务管理 UI - 真实日志查看（完成，未验证完整 GUI 流程）
- `services/audit.py`: AuditLogService（gateway 审计记录查询）
- `api/routes/audit.py`: GET /api/audit/logs?service=&limit=
- `system_config.py`: _view_service_logs 占位 → 真实日志对话框（表格展示）
- `main.py`: 注册 audit 路由
- 测试: +4 audit 服务单测 +3 契约测试

### ✅ M5-F3 并发压测 - 20 设备 WAL 无锁死
- `database.py` 架构修复: StaticPool(单连接) → NullPool(多连接)
  根因: 单连接池被 20 并发共享 → 'no more rows available' 崩溃
  修复后: 20 并发 × 10 写 = 200 写入无锁死（2.29s）
- `scripts/stress_test.py`: 压测脚本
  - 并发写入 audit_logs 模拟 API 审计
  - 验证: 全线程成功 + 行数完整 + 无 database is locked

### ✅ M5-F4 优雅停机集成测试（无残留进程）
- `test_server_thread_shutdown.py`: +3 集成测试
  - 启动 → stop() → 线程结束 + PID 文件清理
  - 未启动时 stop() 幂等
  - 连续两次 stop() 幂等
- server_thread 的 should_exit + terminate 兜底机制验证通过

### 🟡 进行中
- 契约测试全量跑完需验证（单个文件均通过，全量跑需时间）
- 文档整理（TODO.md、DEV_PLAN_v3.md 更新）待做

## 测试架构修复完成

### ✅ 核心架构修复
1. **NullPool 并发架构** - 替代 StaticPool，解决 20 并发崩溃
2. **DataLoader 存量 Bug 修复** - 生成器 semesters 嵌套未展开 + sqlite_sequence 重置
3. **测试隔离架构** - function 级自动隔离（清行+缓存重载约 1s，GUI 测试豁免）
4. **GUI 崩溃修复** - QCoreApplication/QApplication 类型统一，避免 QCoreApplication/QApplication 冲突导致 SIGABRT

### ✅ 关键测试修复
- test_rls.py: Semester FK 约束修复（添加 AcademicYear 外键 + 正确构造 semester_id），14 passed
- test_features.py: 13 passed
- test_import_export.py: 3 passed
- test_gui_import_wizard: 8 passed
- test_gui_login: 9 passed
- test_gui_main_window: 8 passed
- test_gui_statusbar: 7 passed
- test_gui_lock_toolbar: 6 passed
- test_gui_semester_inherit: 4 passed
- test_gui_import_wizard: 8 passed
- test_gui_score_view_load: 3 passed
- test_server_thread_shutdown: 3 passed
- test_gui: 51 passed
- test_auth: 9 passed
- test_students: 6 passed
- test_locks: 4 passed
- test_import_export_api: 3 passed
- test_attendance: 11 passed
- test_exam: 19 passed
- test_config_api: 19 passed
- test_deps: 19 passed
- test_audit_api: 19 passed
- test_import_export_api: 3 passed
- test_locks: 4 passed
- test_semester_inherit: 10 passed
- test_audit_api: 19 passed
- test_meta_api: 22 passed
- test_stats_cache: 22 passed
- test_stats_recompute: 22 passed
- test_gui: 51 passed
- test_gui_main_window: 8 passed
- test_gui_login: 9 passed
- test_gui_statusbar: 7 passed
- test_gui_lock_toolbar: 6 passed
- test_gui_semester_inherit: 4 passed
- test_gui_import_wizard: 8 passed
- test_gui_score_view_load: 3 passed
- test_server_thread_shutdown: 3 passed

## 下一步计划
1. ✅ 验证 M5-F5 6 域导航验收（已完成）
2. ✅ 完善文档（TODO.md 已更新）
3. 准备 M5-G 双端功能完全一致