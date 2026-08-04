# 功能清单（Feature Inventory）

> 逐项打磨的唯一索引。每项含：现状 / 代码位置 / 测试数 / 待打磨点 / 验收标准。
> 生成时间：2026-08-03，来源：代码自动扫描 + 人工核对。

## 一、GUI 视图（26 个，来自 VIEW_REGISTRY）

| view_id | 模块 | 类 | 现状 | 测试数 | 待打磨点 |
|---------|------|-----|------|--------|----------|
| overview | dashboard | DashboardView | ⬜ 待验证 | - | 待逐项验收 |
| quick | dashboard | QuickActionsView | ⬜ 待验证 | - | 待逐项验收 |
| status | dashboard | DataStatusView | ⬜ 待验证 | - | 待逐项验收 |
| student_list | student | StudentView | ⬜ 待验证 | - | 待逐项验收 |
| student_register | remaining | RegistrationView | ⬜ 待验证 | - | 待逐项验收 |
| student_movement | remaining | EnrollmentView | ⬜ 待验证 | - | 待逐项验收 |
| student_promotion | remaining | PromotionView | ⬜ 待验证 | - | 待逐项验收 |
| score_entry | score | ScoreView | ⬜ 待验证 | - | 待逐项验收 |
| score_query | score | ScoreView | ⬜ 待验证 | - | 待逐项验收 |
| score_stats | report | ReportView | ⬜ 待验证 | - | 待逐项验收 |
| score_rank | score | ScoreView | ⬜ 待验证 | - | 待逐项验收 |
| exam_manage | exam | ExamView | ⬜ 待验证 | - | 待逐项验收 |
| exam_rooms | exam | ExamView | ⬜ 待验证 | - | 待逐项验收 |
| exam_invigilation | exam | ExamView | ⬜ 待验证 | - | 待逐项验收 |
| exam_admit | exam | ExamView | ⬜ 待验证 | - | 待逐项验收 |
| teacher_list | teacher | TeacherView | ⬜ 待验证 | - | 待逐项验收 |
| teacher_assign | teacher | TeacherView | ⬜ 待验证 | - | 待逐项验收 |
| class_list | class_management | ClassView | ⬜ 待验证 | - | 待逐项验收 |
| class_edit | class_management | ClassView | ⬜ 待验证 | - | 待逐项验收 |
| classroom_list | classroom | ClassroomView | ⬜ 待验证 | - | 待逐项验收 |
| semester | semester | SemesterView | ⬜ 待验证 | - | 待逐项验收 |
| users | settings | SettingsView | ⬜ 待验证 | - | 待逐项验收 |
| data_maintenance | system_config | SystemConfigView | ⬜ 待验证 | - | 待逐项验收 |
| system_config | system_config | SystemConfigView | ⬜ 待验证 | - | 待逐项验收 |
| init | init_system | InitView | ⬜ 待验证 | - | 待逐项验收 |
| report | report | ReportView | ⬜ 待验证 | - | 待逐项验收 |

## 二、服务层（18 个模块）

| 模块 | 职责 | 现状 | 测试覆盖 |
|------|------|------|----------|
| cache | 统计缓存读写 | 🟡 | — |
| data_cleaning | 数据清洗管道 | 🟡 | ✅ |
| data_quality | 数据质量检查 | 🟡 | ✅ |
| enrollment | 学籍变动 | 🟡 | — |
| export | 导出服务 | 🟡 | ✅ |
| import_export | 导入导出 | 🟡 | ✅ |
| importer | 数据导入 | 🟡 | — |
| locks | 数据锁定 | 🟡 | — |
| memory_student | 学生缓存 | 🟡 | — |
| report | 报表生成 | 🟡 | — |
| scheduler | 定时任务 | 🟡 | — |
| score | 成绩服务 | 🟡 | ✅ |
| semester | 学期服务 | 🟡 | — |
| semester_config | 学期配置继承 | 🟡 | — |
| statistics | 统计预计算 | 🟡 | — |
| stats | 统计读取 | 🟡 | — |
| storage | 文件存储 | 🟡 | — |
| student | 学生仓储 | 🟡 | — |

## 三、API 路由（6 个）

| 路由 | 现状 | 契约测试 |
|------|------|----------|
| attendance | 考勤 | test_attendance.py: 9 测试 |
| auth | 认证会话 | test_auth.py: 9 测试 |
| exam | 考试 | test_exam.py: 9 测试 |
| scheduler | 定时任务 | — |
| score | 成绩 | test_score.py: 10 测试 |
| stats | 统计 | — |

## 四、测试基线

| 文件 | 测试数 |
|------|--------|
| test_attendance.py | 9 |
| test_auth.py | 9 |
| test_data_cleaning.py | 11 |
| test_data_quality.py | 14 |
| test_event_bus.py | 5 |
| test_exam.py | 9 |
| test_export.py | 12 |
| test_features.py | 13 |
| test_idempotency.py | 5 |
| test_import_export.py | 16 |
| test_score.py | 10 |
| test_ui_config.py | 12 |
| **合计** | **125** |

## 五、待打磨优先级建议

1. **P0 功能可用性**：登录（LoginDialog）、导入向导 UI、列持久化/密度切换（4.10.5 剩余）
2. **P1 体验增强**：报表四件套、主题切换、命令面板跨域跳转完善
3. **P2 工程化**：TODO.md 缺口闭环、CHANGELOG 自动化
