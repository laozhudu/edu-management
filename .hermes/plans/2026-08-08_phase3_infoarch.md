# 第三阶段 P3-0：桌面端信息架构重组方案（双端自动同步）

> 2026-08-08 · 依据：6 域 20 页签实测分布 + 视图功能盘点（功能齐全但导航折叠）
> 核心发现：exam/teacher/class_management/semester/data_maintenance 视图内部 Tab 齐全，
>   问题在 ui_config.json 导航只暴露 1 个页签 → 重组配置即可释放全部功能，几乎零代码。

---

## 一、现状 vs 目标

### 现状（6 域 20 页签）
```
home      3  dashboard / quick / status
students  4  student_list / register / movement / promotion
scores    4  score_entry / query / stats / rank
exams     1  exam_manage            ← 折叠了考场/监考/准考证
teachers  1  teacher_list           ← 折叠了任课/查询
system    8  semester/classes/classrooms/users/data_maintenance/system_config/init/report
```

### 目标（8 域 24 页签）
```
home      3  dashboard / quick / status                    （不变）
students  4  student_list / register / movement / promotion（不变）
scores    4  score_entry / query / stats / rank            （不变）
exams     3  exam_manage / exam_rooms / exam_invigilation  ← 考试域扩容（复用 exam 视图内部 Tab）
teachers  2  teacher_list / teacher_assign                 ← 教师域扩容（任课分配独立）
classes   2  class_list / class_edit                        ← 班级独立成域（从 system 提升）
classroom 1  classroom_list                                 ← 教室独立成域（从 system 提升）
system    5  semester/users/data_maintenance/system_config/init
            （report 保留在系统 或 移入 scores 域——待定）
```

## 二、重组原则

1. **复用不新建**：所有页签映射到现有视图类（VIEW_REGISTRY 已注册），只改 ui_config.json 的 domains 结构
2. **Web 自动同步**：Web 渲染器读同一 ui_config → 桌面改配置，Web 导航立即一致（已验证热加载机制）
3. **保持 view_id 稳定**：现有 view_id 全部保留，只调整分组和顺序 → 零代码改动、零回归风险
4. **权限不变**：roles 字段沿用现有配置

## 三、具体映射表

| 新域 | 页签 id | 视图类（现有） | 说明 |
|------|---------|---------------|------|
| exams | exam_manage | ExamView(build_list_tab) | 考试列表/创建 |
| exams | exam_rooms | ExamView(build_rooms_tab) | 考场/座位（内部 Tab） |
| exams | exam_invigilation | ExamView(build_invigilation_tab) | 监考/准考证（内部 Tab） |
| teachers | teacher_list | TeacherView(build_list_tab) | 教师列表 |
| teachers | teacher_assign | TeacherView(build_assign_tab) | 任课分配 |
| classes | class_list | ClassView | 班级管理 |
| classes | class_edit | ClassView | 班级编辑（或合并） |
| classroom | classroom_list | ClassroomView | 教室管理 |
| system | semester | SemesterView | 学期设置 |
| system | users | SettingsView | 用户权限 |
| system | data_maintenance | DataMaintenanceView | 数据维护 |
| system | system_config | SystemConfigView | 系统设置 |
| system | init | InitView | 初始化 |

## 四、执行步骤

1. **备份 ui_config.json** → 修改 domains 结构（新增 exams/teachers/classes/classroom 域，system 收缩）
2. **验证**：桌面端启动 → 8 域 24 页签导航正确、各页签可切换
3. **Web 端验证**：浏览器导航与桌面一致（热加载自动生效）
4. **GUI 测试**：22 视图加载测试 + 导航测试全绿
5. **契约测试**：/api/config 返回新结构
6. commit + push

## 五、待确认事项

- [ ] report 页签放哪？（系统域保留 vs 移入 scores）
- [ ] class_edit 是否需要独立页签，还是并入 class_list？
- [ ] 域内页签顺序是否有偏好？
- [ ] 视觉/交互统一（P3-0b）是否本轮一并做，还是先重组结构验收后再做？
