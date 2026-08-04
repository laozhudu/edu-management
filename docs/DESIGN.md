# 教务管理系统 v2.0 — 系统设计说明书
## 示例学校

---

## 一、教务管理员视角：业务需求与工作流

### 1.1 系统定位
面向初中学校教务员的单机桌面管理系统，支持三年完整学业周期管理。

### 1.2 核心工作流（按频率排序）

**日常操作（每天）：**
1. 查看学生信息，修改联系方式等
2. 处理单个学籍变动（转班、休学、复学）

**考试周期（每月1次，持续2-3天）：**
1. 创建考试 → 设置科目与分数线
2. 导入成绩 Excel → 核对缺考
3. 查看统计概览 → 各班均分/及格率/优秀率
4. 生成正式报表（原始成绩+科分析+排名）→ 打印/分发

**学期初（每学期1次）：**
1. 设置当前学期
2. 确认班级列表、各年级科目
3. 导入教师任课表
4. 新生注册

**学年末（每年1次）：**
1. 升年级（101→201, 201→301, 301→9xx存档）
2. 初三毕业处理
3. 新初一招生/摇号 → 分班

### 1.3 功能需求清单

| ID | 功能 | 优先级 | 频率 |
|----|------|--------|------|
| F1 | 学生信息管理（CRUD/导入/导出/打印/筛选） | P0 | 每天 |
| F2 | 学生批量操作（转班/改状态/考号/座号） | P0 | 每周 |
| F3 | 学籍变动记录（转班/休学/复学/退学/毕业） | P0 | 每周 |
| F4 | 教师信息管理 | P1 | 每学期 |
| F5 | 教师任课分配 | P1 | 每学期 |
| F6 | 班级与科目配置 | P1 | 每学期 |
| F7 | 考试管理（创建/分数线/科目设置） | P0 | 每月 |
| F8 | 成绩导入（Excel/CSV） | P0 | 每月 |
| F9 | 成绩表格编辑与保存 | P0 | 每月 |
| F10 | 统计分析（各班各科均分/及格率/优秀率/低分率） | P0 | 每月 |
| F11 | 考试对比（进退步分析） | P1 | 每月 |
| F12 | 报表生成（标准20张表+变动情况表） | P0 | 每月 |
| F13 | 升年级/毕业处理 | P0 | 每年 |
| F14 | 新生注册（摇号导入+分班） | P0 | 每年 |
| F15 | 学期管理（创建/切换） | P1 | 每学期 |
| F16 | 数据维护（初始化/备份/恢复） | P2 | 按需 |

---

## 二、架构师视角：系统架构与数据模型

### 2.1 技术选型

| 层 | 选型 | 版本 | 理由 |
|----|------|------|------|
| 语言 | Python | 3.12 | 系统自带，PyQt5绑此版本 |
| GUI | PyQt5 | 5.15 | 中文原生支持，跨平台，Qt成熟生态 |
| ORM | SQLAlchemy | 1.4 | 兼容系统apt包，声明式模型 |
| 校验 | Pydantic | 2.x | 类型安全数据校验 |
| Excel | openpyxl | 3.x | 读写xlsx，无numpy依赖 |
| 拼音 | pypinyin | 0.5 | 中文姓名拼音排序 |
| 样式 | Qt Fusion | — | 系统自带统一主题 |

### 2.2 分层架构

```
┌──────────────────────────────────────┐
│              gui/                     │  PyQt5 视图层
│  main_window.py  views/  dialogs/     │  只管布局、事件、渲染
│         ↓ 调用 services               │
├──────────────────────────────────────┤
│            services/                  │  业务逻辑层
│  student  enrollment  teacher         │  纯 Python，可被 GUI/CLI/Web 调用
│  exam  score  report  importer       │
│  semester  stats                      │
│         ↓ 调用 repository/models      │
├──────────────────────────────────────┤
│            core/                      │  数据访问层
│  models  crud  database              │  SQLAlchemy ORM + 通用 CRUD
│         ↓ 持久化 to SQLite            │
├──────────────────────────────────────┤
│         data/school_data.db           │  SQLite 数据库
└──────────────────────────────────────┘
```

### 2.3 数据库实体关系

```
Grade(年级) 1──* Class(班级) 1──* Student(学生) 1──* Score(成绩) *──1 Exam(考试)
                      │                     │                         │
Semester(学期) 1──* ClassSubject(任课)      StudentMovement(学籍变动)   ExamSubjectSetting(科目分数线)
                │                                    │
Subject(科目) ──┘                                    Semester
                                                     │
Teacher(教师) ────────────────────────────────────────┘
                                                     
Setting(系统设置) — 独立键值表
```

### 2.4 核心数据表（12张）

| 表 | 说明 | 关键字段 |
|----|------|---------|
| grades | 年级 | id, name(初一级/初二级/初三级), sort_order |
| semesters | 学期 | id, year_start, semester, label, is_current, status |
| subjects | 科目 | id, name, full/pass/good/excellent/low_line |
| classes | 班级 | id, grade_id, name(101/201/301), head_teacher |
| students | 学生 | id, class_id, name, gender, phone, id_card, status, ... |
| teachers | 教师 | id, name, phone, title |
| class_subjects | 任课 | id, semester_id, class_id, subject_id, teacher_id |
| exams | 考试 | id, semester_id, name, exam_date, grade_id |
| scores | 成绩 | id, exam_id, student_id, subject_id, score(NULL=缺考) |
| student_movements | 学籍变动 | id, student_id, move_type, from/to_class_id, reason |
| exam_subject_settings | 考试科目设置 | id, exam_id, subject_id, 各分数线 |
| settings | 系统设置 | key, value |

---

## 三、程序员视角：模块设计与接口规范

### 3.1 服务层接口

```python
# services/student.py — StudentRepository
class StudentRepository:
    search(filter: StudentFilter) -> list[Student]    # 多条件筛选
    count_by_grade() -> list[dict]                    # 各年级统计
    create_from_schema(data: StudentCreate) -> Student  # 校验后创建
    update_from_schema(id, data: StudentUpdate) -> Student

# services/enrollment.py — EnrollmentService
class EnrollmentService:
    transfer(student_id, to_class_id, reason) -> StudentMovement
    change_status(student_id, new_status, reason) -> StudentMovement
    promote_grade(semester_id) -> dict               # 全年级升级

# services/score.py — ScoreService
class ScoreService:
    get_exam_scores(exam_id) -> tuple                 # 成绩矩阵
    calc_class_stats(exam_id) -> list[dict]           # 各班统计
    calc_grade_ranks(exam_id) -> list[dict]           # 年级排名
    compare_exams(id1, id2) -> list[dict]             # 考试对比

# services/report.py — ReportService
class ReportService:
    generate_exam_report(exam_id, path) -> str        # 成绩报表
    generate_change_report(semester_id, path) -> str  # 变动情况表

# services/importer.py — ImportService
class ImportService:
    import_students_from_excel(path) -> ImportResult
    import_scores_from_excel(path, exam_id) -> ImportResult
```

### 3.2 GUI 视图层

```
main_window.py  — QMainWindow + 侧栏 + QStackedWidget
views/student.py     — 学生信息（表格+筛选+导入/导出/+批量操作）
views/remaining.py   — 教师/考试/成绩/报表/学籍/新生/升年级/学期/设置（占位→逐步实现）
```

### 3.3 全局规范

- 所有数据库操作走 service 或 repository，不在 view 层写 SQL
- 所有外部输入用 Pydantic 校验
- 所有视图继承 BaseView(session) 基类
- 侧栏通过 CollapsibleSection 实现二级菜单
- Qt 主题色统一在 theme.py 定义

---

## 四、UI设计师视角：界面规范

### 4.1 布局

```
┌─────────┬──────────────────────────────────┐
│ 侧栏     │           内容区                   │
│ 170px   │                                   │
│         │  ┌─ 标题栏（深蓝底白字）─────────┐  │
│ 教务管理  │  │  学生信息                    │  │
│ v2.0    │  └──────────────────────────────┘  │
│         │                                   │
│ ▶ 学生管理│  ┌─ 概览条（白底）─────────────┐  │
│  学生信息  │  │  全校在校: N人  初一级: N人... │  │
│  学籍变动  │  └──────────────────────────────┘  │
│  新生注册  │                                   │
│  升年级   │  ┌─ 工具栏（彩色按钮）──────────┐  │
│         │  │  [导入] [新增] [导出] ...       │  │
│ ▶ 教师管理│  └──────────────────────────────┘  │
│ ▶ 考试管理│                                   │
│ ▶ 成绩管理│  ┌─ 筛选栏 ────────────────────┐  │
│ ▶ 系统管理│  │  年级:[v] 状态:[v] 搜索:[___] │  │
│         │  └──────────────────────────────┘  │
│         │                                   │
│         │  ┌─ QTableWidget ────────────────┐ │
│         │  │ 班级│座号│姓名│性别│...│状态  │ │
│         │  │ 101 │ 1  │张三│ 男 │...│在校  │ │
│         │  │ ... │... │... │...│...│...   │ │
│         │  └───────────────────────────────┘ │
│         │                                   │
│ 示例学校 │  状态栏: 共 N 名学生               │
└─────────┴──────────────────────────────────┘
```

### 4.2 配色方案

```
侧栏背景: #2C3E50 (深蓝灰)
学生管理: #3498DB (蓝)
教师管理: #27AE60 (绿)
考试管理: #E67E22 (橙)
成绩管理: #1ABC9C (青)
系统管理: #8E44AD (紫)
内容背景: #F5F6FA (浅灰)
表格奇数: #FFFFFF (白)
表格偶数: #EBF5FB (淡蓝)
```

### 4.3 字体

- 系统默认字体（Qt 自动适配中文）
- 基础字号: 9pt
- 标题: 11pt bold
- 侧栏分区: 8pt bold
- 侧栏按钮: 9pt
- 表格内容: 9pt
- 筛选栏: 8pt

---

## 五、看板（Kanban）

### 5.1 状态列

| Backlog | 待开发 | 开发中 | 测试中 | 已完成 |
|---------|--------|--------|--------|--------|

### 5.2 任务卡片

**Phase 1: 基础设施** (已完成 ✅)
- [x] P1-1 项目结构与依赖配置
- [x] P1-2 SQLAlchemy 数据模型（12张表）
- [x] P1-3 通用 CRUD 仓储层
- [x] P1-4 Pydantic 校验模型
- [x] P1-5 数据库初始化与默认数据

**Phase 2: 服务层** (已完成 ✅)
- [x] P2-1 StudentRepository — 学生查询与筛选
- [x] P2-2 EnrollmentService — 学籍变动/升年级
- [x] P2-3 SemesterService — 学期管理
- [x] P2-4 ScoreService — 成绩统计/排名/对比
- [x] P2-5 ImportService — 数据导入与清洗
- [x] P2-6 ReportService — 报表生成

**Phase 3: GUI 框架** (已完成 ✅)
- [x] P3-1 PyQt5 主窗口框架（侧栏+内容区）
- [x] P3-2 二级菜单（CollapsibleSection）
- [x] P3-3 主题系统（配色+字体）
- [x] P3-4 视图路由与切换

**Phase 4: 学生管理视图** (已完成 ✅)
- [x] P4-1 学生表格（QTableWidget + 交替行色）
- [x] P4-2 筛选栏（年级/状态/搜索）
- [x] P4-3 工具栏（导入/导出/新增/编辑）
- [x] P4-4 批量操作（转班/改状态/生成考号）
- [x] P4-5 概览统计条

**Phase 5: 核心业务视图** (待开发)
- [ ] P5-1 成绩管理视图（表格编辑/导入/保存/统计）
- [ ] P5-2 报表生成视图（选择考试/类型/输出路径）
- [ ] P5-3 考试管理视图（创建/列表/科目设置）
- [ ] P5-4 教师任课视图（教师列表+任课分配）
- [ ] P5-5 学籍变动视图（搜索/转班/状态修改/记录）
- [ ] P5-6 升年级/毕业视图
- [ ] P5-7 学期管理视图（创建/切换学期）
- [ ] P5-8 系统设置视图（数据库维护/初始化）
- [ ] P5-9 新生注册视图

**Phase 6: 报表增强**
- [ ] P6-1 完整20张标准成绩报表
- [ ] P6-2 变动情况表（公文格式，含全校汇总）
- [ ] P6-3 各班名册打印

**Phase 7: 收尾**
- [ ] P7-1 旧系统代码归档引用
- [ ] P7-2 README 与使用文档
- [ ] P7-3 桌面快捷方式
- [ ] P7-4 全功能验收测试

---

## 六、验收标准

| 检查项 | 通过条件 |
|--------|---------|
| 启动 | 双击桌面快捷方式，窗口3秒内弹出 |
| 中文 | 所有界面中文正常显示，无乱码无方框 |
| 学生管理 | 能导入Excel、表格显示、筛选正常、双击编辑 |
| 成绩管理 | 能创建考试、导入成绩、编辑保存、查看统计 |
| 报表生成 | 能生成原始成绩+科分析+排名报表 |
| 学期流转 | 能创建/切换学期、升年级、毕业处理 |
| 稳定性 | 连续操作10次无崩溃 |
| 数据持久化 | 关闭重开后数据完整保留 |
