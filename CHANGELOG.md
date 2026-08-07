# 变更日志

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

