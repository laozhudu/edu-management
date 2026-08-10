# 变更日志

## [3.10.0] - 2026-08-10

### 若依底座学习批次 2：模型拆分 + 仓库层 + 视图瘦身 + 系统监控

**P2 models 按域拆分（对齐若依多 domain 包）：**
- models/ 单文件 46 表 → base/academic/student/teacher/exam/system/attendance/report 8 文件
- base.py 单一 Base + __all__ 明确导出（星导入安全）
- __init__.py 纯 re-export（零破坏，现有 from edu_system.models import X 不变）

**B3 Repository 层（对齐若依 Mapper）：**
- repository/__init__.py：get_repo(model, session) 工厂 + register_repository 特化注册
- BaseRepository 泛型 CRUD（get/list/count/add/update/delete）

**G2 视图瘦身：**
- student.py 1959 行 → student.py(1485) + student_edit_dialog.py(490) 拆分

**M3 系统监控（对齐若依 #15）：**
- /api/monitor/server（CPU/内存/磁盘/主机信息 psutil）+ /api/monitor/cache（服务统计）
- Web monitor.html（进度条卡片 + 服务统计）+ 桌面 MonitorView
- 契约+测试通过

## [3.9.0] - 2026-08-10

### 若依底座学习批次 1：M2 系统扩展 + 结构纪律

**M2 通知公告 + 登录日志 + 在线用户（对齐若依 #8/#10/#11）：**
- Notice/NoticeRead/LoginLog/OnlineUser 四表 + 登录成功/失败真实写入
- /api/notice CRUD+已读 / /api/login-logs 分页 / /api/online-users 列表+强制下线
- 桌面 SystemExtView（公告/日志/在线 3 tab）+ Web system_ext.html
- 契约 +9 测试

**若依风格主题：** theme.py RUOYI_THEME 预设 + apply_theme()，样式配置界面加主题预设下拉

**P0 删死代码：** updater.py / settings.py / views/__init__.py 旧索引
**P1 单一数据源：** service_registry 三处重复 → DEFAULT_SERVICES 常量（821→360 行）
**B1 统一返回：** 全局异常处理器 code/msg/data（对齐 AjaxResult）
**B2 通用分页：** PageQuery 依赖 + paginate_response（对齐 PageHelper）
**G1 GUI 底座：** make_button 工厂 + BaseView btn/confirm/empty 便捷方法

## [3.8.0] - 2026-08-09

### 字典管理 + 参数管理（对齐若依 #6/#7）
- DictType/DictData + seed 6 类 23 条 + /api/dict 全套 CRUD + 表单下拉
- /api/params CRUD（GlobalSetting UI 化）
- 桌面 DictManagerView（字典+参数 2 tab）+ Web dict.html
- 契约 +15，全量 636 passed

## [3.7.0] - 2026-08-09

### 样式可配置化 + 权限视图修复 + 审计闭环（用户指导）

**界面样式零代码配置（代码有、界面无 → 补全）：**
- 后端 `POST /api/config/save-ui`：theme/topbar/login/statusbar 写回 ui_config.json + reload 双端生效
- 桌面 system_config 加「界面样式」Tab：外观主题（强调色/侧栏/内容背景/密度）+ 登录框（尺寸/字号/圆角/品牌区）+ 顶部栏开关
- Web system_config 加同款配置卡片（取色器 + 表单）

**权限桌面端修复（代码有、挂错 → 新建视图）：**
- 实锤：users 页签此前错误挂 SettingsView（内容是数据库信息/数据统计）
- 新建 UserPermissionView（用户列表/新增/编辑/停用/重置密码 + 角色），registry 修正

**审计完整闭环（写入已有、查询 UI 缺 → 补全）：**
- 新增 `GET /api/audit/operations`：业务操作审计（8 表增删改 + 操作者 + 新旧值，分页/过滤）
- 桌面「操作审计」Tab + Web「业务操作审计」卡片
- 实测：40 条历史操作记录可查

**验收：** 全量 612+ passed，ruff 全绿

## [3.6.0] - 2026-08-09

### 信息架构重整：四大工作流域（用户指导）

**教务工作流分类（管人/管事/管工具/管系统）+ 菜单-标签两级架构：**
- 管人：学生管理 + 教师管理（对称）
- 管事：班级科目/教室位置/考试管理/成绩管理（录入+独立统计）
- 管工具：报表工具域（报表生成/模板管理/批量打印集中，底座可复用）
- 管系统：学期设置/用户权限/数据维护/系统设置/初始化

**关键改动：**
- **成绩统计修复**：score_stats 从错挂的 ReportView 改为新建 ScoreStatsView（总分/均分/及格率/优秀率/分段分布/班级平均对比）
- **报表工具域新建**：ReportView 支持 view_id 定位 3 tab（生成/模板/批量打印），从成绩域+系统域集中
- **教师生命周期**：Teacher model 加 status（在职/离职/退休）+ 新表 teacher_movements；教师列表显示状态列
- **ui_config 重构为 9 域**（首页 + 四大类），双端 Web 自动跟随
- 测试断言更新（8 域→9 域：test_ui_config/test_web_pages/test_config_api）

## [3.5.0] - 2026-08-09

### 第四阶段（续）：报表打印闭环 Web 化

- **修复 report 页签空白**：ui_config view=report 此前无对应模板，打开是 index 占位 → 新建 `report.html`
- **报表生成下载页**：类型选择（考试/学籍变动/成绩单/证书）+ 参数区（考试/学期下拉）+ 格式选择（Word/Excel）+ 证书类型 + 生成下载 + 本地打印
- **契约测试**：+5（change/成绩单选/report 缺参/report 页渲染）+ system_tabs 页面断言
- **修复后端 bug**：report.py generate_change_report 字符串 SQL 未 text() 包裹 → 新 SQLAlchemy 500（change 报表此前从未被调用暴露）
- 浏览器实测：report 页渲染 4 类型 + 考试下拉正常，考试报表生成 200 Excel 下载

## [3.4.0] - 2026-08-09

### 第四阶段：数据看板双端可视化（Dashboard）

- **后端**：新增 `GET /api/stats/dashboard` 聚合端点（KPI/性别构成/成绩分段/班级人数，直查 DB 保证准确）+ 契约测试
- **桌面端**：dashboard.py 加 QtCharts 图表区（性别饼图 + 班级人数柱状图），复用 score.py 成熟范式；修复 `is_current`→`is_active` 学期查询无效 bug
- **Web 端**：overview.html 用已加载的 ECharts 渲染 3 图表（性别饼/班级柱/成绩分段分布），深浅色主题适配
- **单一数据源**：两端独立查询，数据口径一致；图表渲染失败静默不阻塞看板
- 浏览器实测：3 图表 canvas 正常渲染（503×256/1022×224）；全量 605+ passed

## [3.3.0] - 2026-08-09

### 第三阶段：双端操作对等（P3-A 高频页签 CRUD 补全）

#### 信息架构重组（P3-0 + UI 整改）
- **6 域 → 8 域**：班级/教室从系统域提升为独立域（用户反馈系统域太杂、业务域单薄）
- **孤儿 Web 模板接入**：分考场/监考/准考证/任课分配 4 个有代码无菜单的功能接入导航
- **成绩域精简**：score_query/score_rank 从菜单移除（ScoreView 内部 Tab 已涵盖）
- **样式统一**：表格样式 TABLE_STYLE 集中到 theme.py（删 3 处本地重复硬编码）
- **登录框升级**：品牌区（校名+副标题）卡片式观感，对齐 Web 端

#### 班级管理完整 CRUD（P3-A1）
- 后端：POST/PUT/DELETE /api/class + 年级下拉 /api/class/grades（重名校验/学期注入/有学生班级禁删）
- 前端：class_list.html 重写为真实班级 CRUD（新增/编辑模态框 + 行操作）

#### 教师管理完整 CRUD（P3-A2）
- 后端：teacher_service.py + POST/PUT/DELETE /api/teachers
- 前端：teacher_list.html 教师列表 Tab 增删改

#### 成绩录入增强（P3-A3）
- 单条编辑/删除 + 发布全部/取消发布切换（复用既有 PUT/DELETE/publish API）

#### 考试管理编辑/删除（P3-A4）
- 后端：DELETE /api/exam/{id}（级联删成绩）
- 前端：exam_manage.html 编辑/删除 + 新建模态框复用为编辑

#### 教室位置页真实化（P3-A5）
- 占位页 → 班级教室映射（统计卡片/改教室/搜索）

#### 学期管理新建（P3-A6）
- 后端：POST /api/semester（学年自动查找创建）
- 前端：semester.html 新建学期模态框

#### 测试
- +22 契约测试（class/teacher/exam/semester CRUD）+ 4 孤儿页签页面契约
- 全量 599+ passed；8 个核心业务页签全部具备写操作

### 第三阶段续：全局能力 Web 化（P3-B）

#### 数据维护真实化
- 新增 maintenance 路由：POST /backup（BackupManager 每日增量）/ GET /backups（列表）/ POST /clean/cache
- service_registry 注册 maintenance 服务码
- 修复 scripts/backup.py：text 仅 __main__ 导入导致库调用 NameError
- 前端备份/清理从模拟改为真实 API + 备份记录表

#### 用户管理完整功能
- 新增 users 路由：列表/创建/更新（角色/停启用）/重置密码/角色列表
- 修复 passlib 1.7.4 + bcrypt 4.x 不兼容（get_password_hash 必崩）→ 直连 bcrypt 库
- 前端用户管理占位 → 真实列表 + 增删改 + 停用/重置密码

#### 报表下载
- 修复 5 处中文文件名 latin-1 编码 500 → RFC 5987（filename*=UTF-8''）
- score_entry 加「下载报表」按钮（考试标准报表 Excel）

#### 孤儿页签契约补全（P3-0）
- 4 个孤儿模板（分考场/监考/准考证/任课分配）接入后补页面契约测试

#### 桌面联动（P3-C）
- 8 域导航桌面端加载验证：GUI 66 passed，ui_config 单一源两端同步

#### 测试
- 新增 10 契约测试（维护3/用户6/报表2 去重后净增）
- 全量 599 passed + 孤儿页签 4 passed

## [3.2.0] - 2026-08-08

### 底座加固（CI 质量门禁全面恢复）

#### 代码质量门禁
- **ruff 全仓覆盖恢复**（此前 CI 排除了 api/gui/services/repository/schemas 核心层，lint 名存实亡）
  - 自动修复 + 人工清理全部 lint 错误（重复类定义/重复 dict key/未用 import/变量遮蔽等真实 bug）
  - pyproject 配置弃用警告迁移、风格规则显式豁免（有理由）
- **mypy 类型检查恢复**（CI typecheck job 重新启用，core/config/database 严格模式）
  - 从 145 errors 清零至 Success，修复漏 import `wraps`(NameError 隐患) 等真实 bug

#### 安全加固
- **diskcache 反序列化漏洞 CVE-2025-69872**：SafeJSONDisk 以 JSON 序列化替代 pickle（实测验证）
- **meta.py SQL 注入防护**：字段名白名单正则校验
- **bandit 修复 + CI 拦截生效**（移除 `|| true` 兜底）：修 B608、逐条审查标注
- **pip-audit 漏洞审计拦截**：发现并评估 2 个漏洞（diskcache/ecdsa），豁免并记录理由
- **gitleaks 秘密扫描** 加入 CI
- **monitoring.py 修复**：'项目根目录'伪路径 bug（psutil.disk_usage 会崩）+ 补 psutil 依赖

### 功能打磨（Web 双端一致）

#### Web 页签功能补全
- **成绩查询 keyword 生效**：/api/score 增加关键字搜索（姓名/学号/班级名模糊过滤），修复搜索框 inert
- **学期端点归一**：base.html/overview.html 修正为 /api/semester/active
- **学生信息页完整 CRUD**（此前仅只读查询，桌面端 CRUD 未暴露为 API）
  - 后端：student_service 服务层 + POST/PUT/DELETE/GET 详情 API + 班级列表 API
  - 前端：新增/编辑模态框、行操作按钮、表单校验、错误提示
- **端点一致性脚本** scripts/check_api_alignment.py：扫描模板 fetch 端点逐一探测，404 即拦截（可接入 CI）

### 验证
- 全量测试 571 passed（+6 新契约测试）
- 链路抽测 14/14：6 域核心 API 增→查→改→删真操作走通
- 性能冒烟：启动 6.3s、全部关键 API 平均延迟 <100ms、缓存正常
- ruff/mypy/bandit/pip-audit 全绿

## [3.1.0] - 2026-08-07

### 新增功能

#### M6 Sprint7 - 自动更新与部署
- **自动更新服务** (`src/edu_system/services/updater.py`)
  - 启动时检查 GitHub Release 最新版本（语义化版本比较）
  - 下载进度条 / 取消下载 / 文件完整性校验
  - Windows 批处理脚本原子替换 exe + 重启应用
  - 代码签名验证 (`signtool verify`)

- **CI/CD 增强**
  - Windows 构建集成 `signtool` 代码签名（证书通过 GitHub Secrets 注入）
  - 时间戳服务器 (Sectigo) + SHA256 双重保障
  - 证书 Base64 解码 → signtool 签名 → 时间戳服务器 (Sectigo) → SHA256

#### M6 Sprint6 - 报表模板与批量打印
- **报表模板管理** (Tab: 模板管理)
  - 模板注册：名称/类型/文件路径/版本/变量扫描
  - 版本管理：同名新版本 +1，历史版本保留回滚
  - 变量扫描：Excel/Word 占位符解析 (`{{key}}`)
  - 测试渲染：样例数据预渲染，缺失变量报告

- **批量打印** (Tab: 批量打印)
  - 批量生成成绩单 → ZIP 打包 (ReportBatchWorker)
  - 进度条 / 取消 / 重试 / 错误收集
  - 打印服务：跨平台 (Windows `ShellExecute` / Linux `lp` / macOS `lpr`)

- **报表工厂** (`ReportFactory`)
  - 统一入口：报表类型/格式/参数 → 生成文件
  - 支持：考试报表/变动表/成绩单/证书奖状

#### M6 Sprint5 - 考试管理 GUI 完善
- **ExamView 4 Tab 完整实现**
  1. 考试列表：CRUD + 刷新/编辑/归档
  2. 新建考试：学期/年级/名称/日期/备注
  3. 分考场座位：容量设置 → 自动分考场 → 考场列表 → 自动排座
  4. 监考准考证：监考安排表/编辑保存/准考证批量生成 ZIP

#### M5-G11 功能对等验收
- **24 页签模板全覆盖** (6 域 × 24 页签)
  - Home: overview/quick_actions/data_status (新增 3)
  - Students: student_list/register/movement/promotion
  - Scores: entry/query/stats/rank
  - Exams: manage/rooms/invigilation/admit
  - Teachers: list/assign
  - System: semester/classes/classrooms/users/data_maintenance/system_config/init

- **自动化验收脚本** (`scripts/e2e_function_parity.py`)
  - 桌面 24 视图 ↔ Web 24 页签映射 100%
  - 全页签渲染 HTTP 200 验证

- **文档** (`docs/FUNCTION_PARITY.md`)

### 修复与优化
- **CI 代码签名**: Windows 构建集成 `signtool` 签名（证书 Base64 解码 + 时间戳服务器 + SHA256）
- **数据库迁移钩子健壮性**: 规避 LIMIT/OFFSET 查询注入冲突
- **报表服务重写**: 移除重复类定义，结构清晰化
- **学期过滤钩子**: 规避 `.first()/.count()` 场景 LIMIT 冲突

### 依赖更新
- 新增: `pyqt5` (已有), `signtool` (Windows CI), `pip-licenses` (CI 许可证门禁)

---

## [3.0.0] - 2026-08-04 (MVP 公开版)

### 核心架构
- PyQt5 桌面端 + FastAPI 服务层双端架构
- SQLAlchemy 2.0 + SQLite WAL + NullPool 并发架构
- 配置单源化 (`ui_config.json` 驱动双端渲染)
- 学期上下文自动注入 (RLS 级)

### 核心功能
- 学期管理: 创建/切换/继承配置(四色预览)/版本回滚/锁定
- 学生管理: 列表/新生注册/学籍变动/升留级
- 成绩管理: 录入/查询/统计/排名/折算分/锁定
- 考试管理: 考试/考场/监考/准考证/排座
- 教师管理: 列表/任课安排
- 系统设置: 学期/班级科目/教室/用户权限/数据维护/初始化
- 报表生成: 考试标准报表/学籍变动表/成绩单/证书奖状
- 服务管理: 审计日志/实时生效/健康检查

### 质量基线
- 569 测试通过 (unit/contract/gui)
- ruff/format 全绿
- bandit/gitleaks 0 高危
- 空库迁移演练通过

