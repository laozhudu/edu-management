# 教务管理系统 v3.0 开发需求清单（基于旧 DEV_PLAN v2.0 整理）

> 文档状态：2026-08-04 整理 · 来源：旧仓库 DEV_PLAN.md（835 行全量提取）
> 用途：新仓库重构的需求依据，每项含状态/产出/验收，实施时逐项勾选
> 状态图例：✅已实现（迁入新仓库）｜🟡部分实现｜⬜待做｜❌取消（用户决策）

---

## 一、核心原则（重构必须遵守）

1. **教务员不加班，系统才算合格**
2. **时间分界**：学年/学期为核心上下文，业务数据/配置/权限随学期隔离
3. **数据模型**：主数据 + 学期快照 + 变动流水三层；ext_json + FieldDefinition 字段注册表
4. **性能策略**：预计算统计 + 学期配置继承 + 分级缓存 + 数据锁定 + 服务级权限
5. **开发方法论**：零部件优先 + TDD 轻量化 + 根因修复 + AI 模拟人工验收
6. **双端定位**：桌面 PyQt5 = 主 UI；API FastAPI = 服务层；Web 前端 = 可选扩展（YAGNI）
7. **目标平台**：Windows 原生部署（Linux 仅开发调试）

---

## 二、已完成基线（v2.0 迁移前实测，迁入新仓库）

### 2.1 数据模型层（36 模型，全部迁入）
| 模型组 | 明细 | 状态 |
|--------|------|------|
| 核心业务 | Student/Teacher/Class/Subject/Score/Exam/Attendance 等 | ✅ |
| 学期上下文 | AcademicYear/Semester/SemesterConfig/GlobalSetting | ✅ |
| 底座 | DataLock/OutboxEvent/IdempotencyKey/DeviceTrust/School/ServiceConfig | ✅ |
| 统计缓存 | SemesterStatsCache | ✅ |
| 考试扩展 | ExamRoom/ExamSeat/Invigilation/AdmitCard/ExamSubjectSetting | ✅ |
| 动态字段 | FieldDefinition（实体/字段/类型/选项/排序/系统标记） | ✅ |
| 权限 | RolePermission（规范化权限表，读写双轨） | ✅ |
| 学籍 | StudentMovement（movement_category 8 类） | ✅ |

### 2.2 基础设施层（全部迁入）
| 模块 | 明细 | 状态 |
|------|------|------|
| 幂等性 | Idempotency-Key + 唯一索引 + TTL | ✅ 5 单测 |
| Outbox 事件 | outbox_events + APScheduler 轮询/重试/死信 | ✅ 5 单测 |
| Feature Flag | features.json + 热加载 + 装饰器 | ✅ 13 单测 |
| 审计 | before_flush 审计监听 | ✅ |
| 认证 | JWT access15m/refresh7d + 设备信任 + HttpOnly | ✅ 9 契约测试 |
| 服务注册表 | ServiceRegistry + ServiceConfig 持久化 | ✅ |
| API 网关 | service_code → enabled → 权限 → 审计 | ✅ |
| RLS | RowLevelPolicy 四作用域(all/none/own_class/own_classes) | ✅ 14 单测 |
| 迁移 | alembic 8 版本 + baseline_v2 create_all 幂等 | ✅ |

### 2.3 业务服务层（21 模块，全部迁入）
| 服务 | 明细 | 状态 |
|------|------|------|
| 成绩 | ScoreService + convert_scores（原始分+折算分，满分/目标满分可配） | ✅ 8 单测 |
| 报表四件套 | report_excel/certificate/print_service/factory | ✅ 24 单测 |
| 数据质量 | data_quality/data_cleaning/import_export/export | ✅ |
| 学籍 | enrollment + movement（分类自动） | ✅ |
| 学期 | semester/semester_config（配置继承）/locks（数据锁定） | ✅ |
| 统计 | statistics/stats/cache（预计算） | ✅ |
| 元数据 | meta（字段注册表 API） | ✅ 13 契约测试 |
| 调度 | scheduler（APScheduler） | ✅ |

### 2.4 桌面端（PyQt5，18 视图迁入）
| 组件 | 明细 | 状态 |
|------|------|------|
| 视图 | student/score/exam/teacher/class/dashboard/settings/system_config/remaining/init_system 等 | ✅ |
| 主题 | theme.py 25键 + theme_manager（亮/暗切换） | ✅ 10 单测 |
| 组件库 | components.py（FilterBar/Toolbar/PaginationBar/StatusBadge/EmptyState/ConfirmDialog/BatchActionBar/CommandPalette） | ✅ |
| 动态表单 | DynamicFormWidget（7 字段类型） | ✅ 11 单测 |
| 动态表格 | TableColumnManager（合并列+QSettings 持久化） | ✅ 8 单测 |
| 装配 | main_window 单导航 + view registry | ✅ |
| 崩溃防护 | crash_guard 三层 | ✅ |
| 嵌入式服务 | server_thread（QThread + uvicorn） | ✅ |

### 2.5 测试基线（迁入验收标准）
- **277 passed**（unit 218 + contract 13 + gui 8 + 其余）
- CI 9 jobs：lint/test/test-contract/db-migrate/test-gui/security/build-win/build-linux

---

## 三、待办缺口（⬜ 迁入后按序开发）

### A. 学期上下文（Sprint 3.1 收尾）
| # | 需求 | 产出 | 验收标准 |
|---|------|------|----------|
| A1 | Session 级上下文：set/get_active_semester | database.py | 线程局部+请求级绑定 |
| A2 | SQLAlchemy before_compile 自动注入 WHERE semester_id | database.py | 排除系统表/跨学期报表 |
| A3 | FastAPI Depends(get_current_semester) | api/deps.py | 双端复用 |
| A4 | PyQt5 顶部栏学期切换器 | semester.py+main_window | 切换即写配置+广播刷新 |
| A5 | 学期维度细粒度权限 | core/permissions.py | 教师仅操作自己班级当前学期 |

### B. 统计预计算（Sprint 3.2 收尾）
| # | 需求 | 产出 | 验收标准 |
|---|------|------|----------|
| B1 | 30 核心指标清单 | statistics.py | 学生数/均分/及格率/排名 |
| B2 | 增量刷新（成绩变更→脏位→重算） | statistics.py+events | 事件驱动 |
| B3 | 后台计算 Worker（QThread+进度+取消） | statistics_worker.py | 复用连接池 |
| B4 | 手动触发入口（GUI+API） | system_config+admin | 幂等 |
| B5 | 缓存读取 API + 版本 304 | stats.py | 无实时聚合 |

### C. 配置继承与数据锁定（Sprint 3.3 收尾）
| # | 需求 | 产出 | 验收标准 |
|---|------|------|----------|
| C1 | 继承向导 UI（四色预览：绿新增/蓝修改/灰保留/红冲突） | semester.py | <3 分钟初始化新学期 |
| C2 | 配置版本回滚 | models | 软删除+version |
| C3 | 锁定 UI（工具栏/行内锁/批量/理由必填） | base.py | 权限控制按钮 |
| C4 | 典型锁定场景（成绩发布/学籍审核/考号生成/学期归档） | score/enrollment | 自动加锁 |

### D. 桌面端补全（Sprint 4 收尾）
| # | 需求 | 产出 | 验收标准 |
|---|------|------|----------|
| D1 | **PyQt5 LoginDialog**（记住我/自动登录） | gui/dialogs/login.py | 键盘全流程可达 |
| D2 | **导入向导 UI**（拖拽→字段映射→规则预览→验证报告→入库） | gui/views/import_wizard.py | 3000 人<2 分钟 |
| D3 | **列配置持久化/主题密度切换** | components.py | QSettings 持久化 |
| D4 | **主窗口状态栏**：局域网地址+二维码+服务开关+端口 | main_window.py | ServerThread 接入 |
| D5 | 报表模板管理 UI（上传→变量预览→测试渲染→版本） | report_template.py | 模板制作规范 |
| D6 | 批量生成 Worker（QThread+进度+重试+ZIP） | report_worker.py | 500 份<30 秒 |

### E. 核心业务 API 补全（Sprint 4.6）
| # | 需求 | 产出 | 验收标准 |
|---|------|------|----------|
| E1 | 成绩录入增强（Excel 粘贴/实时排名/锁定检查） | score.py | 路由已有，补粘贴/排名 |
| E2 | 考勤增强（WebSocket 推送/离线队列） | attendance.py | 路由已有，补推送/离线 |
| E3 | 学生查分 | students/me/scores | 仅本人+趋势图+缓存 |
| E4 | 班级名单 | classes/{id}/students | 只读+搜索+导出 |
| E5 | 配置继承 API | semester/{id}/inherit | 四色预览+审计 |
| E6 | 数据锁定 API | /api/locks | 加锁/解锁/批量/理由 |
| E7 | 导入导出 API | /api/import /api/export | 模板下载+字段映射 |

### F. 服务管理与集成验收（Sprint 4.3/4.9）
| # | 需求 | 产出 | 验收标准 |
|---|------|------|----------|
| F1 | PyQt5 服务管理 UI（启停/权限/限流/日志） | system_config.py | 实时生效 |
| F2 | 端到端：桌面启动→手机浏览器→登录→录分→刷新 | 集成 | <3 秒 |
| F3 | 并发 20 设备，SQLite WAL 无锁死 | 压测 | 通过 |
| F4 | 关闭桌面→uvicorn 优雅停止 | server_thread | 无残留进程 |
| F5 | 6 域导航+全部页签+角色过滤 | 集成 | 全绿 |

### G. 双端一致 + 快捷验收（用户 2026-08-04 补充）⭐
> 用户定位：桌面端 + 网页端**都要**，**两端界面一致**（同一 ui_config.json 驱动），桌面快捷方式方便实时验收。

| # | 需求 | 产出 | 验收标准 |
|---|------|------|----------|
| G1 | **桌面快捷方式**：Linux .desktop + Windows 快捷方式，双击直达主界面 | 打包/安装脚本 | 桌面双击即启动 |
| G2 | **Web 前端真实存在**（不再是空 templates/static）：基于 ui_config.json 渲染 6 域导航 + 页签 | `src/edu_system/static/` + Jinja2 模板 | 浏览器访问 / → 完整界面 |
| G3 | **双端界面一致**：桌面(PyQt5)与 Web 渲染同一 ui_config.json，品牌/导航/页签/主题同步 | ui_config.json 单一源 + 两端渲染器 | 视觉对照一致 |
| G4 | **快捷验收路径**：改 ui_config → 桌面/Web 同时生效，无需改代码 | 配置热加载 | 改配置即见效果 |
| G5 | Web 端登录/角色权限与桌面一致 | auth API 复用 | 同一账号两端通行 |

---

## 四、后续 Sprint（v3.1+，不阻塞公开）

### Sprint 5：考试管理+排课引擎
| # | 需求 | 状态 |
|---|------|------|
| 5.1 | 考试创建向导 | ⬜ |
| 5.2 | 自动分考场算法（OR-Tools CP-SAT） | ⬜ |
| 5.3 | 排座次（蛇形/拼音/考号）+ 座次表 PDF | ⬜ |
| 5.4 | 监考表（教师 Web 查看/提醒） | ⬜ |
| 5.5 | 准考证批量（Word/PDF/二维码核验） | ⬜ |
| 5.6 | 排课引擎（OR-Tools 约束求解） | ⬜ |

### Sprint 6：配置/家校报表/教师人事 + 报表引擎全集成
| # | 需求 | 状态 |
|---|------|------|
| 6.1 | 学年/学期管理 UI | ⬜ |
| 6.2 | 系统设置分级+版本回滚 | ⬜ |
| 6.3 | 成绩单推送（邮件/微信/短信多通道） | ⬜ |
| 6.4 | 跨学年切换（历史只读/趋势对比） | ⬜ |
| 6.5 | 毕业生档案包 | ⬜ |
| 6.6 | 教师人事档案（资质/合同/入离职） | ⬜ |
| 6.7 | 教师请假/考勤（多级审批/代课） | ⬜ |
| 6.8 | 教师绩效考核 | ⬜ |
| 6.9 | 报表模板市场（内置常用模板） | ⬜ |
| 6.10 | 报表引擎全集成（四件套打通） | ⬜ |
| 6.11 | 毕业证书套打流程 | ⬜ |
| 6.12 | 成绩单/名册批量打印 | ⬜ |

### Sprint 7：打包/签名/更新/无障碍
| # | 需求 | 状态 |
|---|------|------|
| 7.1 | Nuitka 编译/单文件/源码加密 | ⬜ |
| 7.2 | 代码签名（signtool/GPG） | ⬜ |
| 7.3 | 自动更新器（GitHub Release/静默/回滚） | ⬜ |
| 7.4 | 无障碍（axe-core 0 违规/键盘全流程） | ⬜ |
| 7.5 | 发布 edu-system-common 内部 PyPI | ⬜ |
| 7.6 | 文档站（Sphinx） | ⬜ |
| 7.7 | Windows 专项矩阵（中文路径/高 DPI/防火墙） | ⬜ |
| 7.8 | NSIS 安装包 | ⬜ |
| 7.9 | 杀毒白名单（360/火绒/Defender） | ⬜ |

---

## 五、已取消/简化（用户决策，不实施）

| 项 | 原因 |
|----|------|
| 学分/课程/教材/三级分类（Course/CourseOffering） | 学科简单化，保留 Subject |
| 复杂统计（等级制/加权/宽表物化视图） | 原始分+折算分即可 |
| 实体拆双表（Student/Teacher/Class） | semester_id 单表已满足 |
| Web 动态渲染（templates/static 空目录） | YAGNI，PyQt5 闭环 |
| 双写过渡期（3.7.21） | 无新旧表切换场景 |

---

## 六、工程规范（新仓库强制执行）

1. **版本号**：语义化 MAJOR.MINOR.PATCH-PRERELEASE+BUILD
2. **提交**：约定式 commit（feat/fix/perf/refactor/docs/chore/ci/test）
3. **分支**：GitHub Flow（main 保护 + feature/fix/release/hotfix）
4. **变更日志**：git-cliff 打标签自动生成
5. **TDD**：tests/contract 先行，新增 API 必先契约测试
6. **迁移**：改表四步曲（改模型→autogenerate→验证→提交），禁手写 ALTER
7. **DoD**：CI 全绿 + CHANGELOG + 版本递增 + 标签 + 制品 + 迁移验证 + 回滚演练
8. **安全**：SECRET_KEY 环境变量化 + CodeQL + Secret scanning + pip-audit
9. **敏感零容忍**：校名关键词/真实学生数据/凭据任何位置禁止出现

---

## 七、验收基线（新仓库公开前）

| 验收项 | 标准 |
|--------|------|
| 全量测试 | 277 passed（迁入后不降） |
| 敏感扫描 | grep "校名关键词" 零命中 + git log 历史零敏感 |
| ruff/format | 全绿 |
| 安全扫描 | bandit/gitleaks 0 高危 |
| 迁移演练 | 空库 alembic upgrade head 全表一致 |
| 冒烟 | python main.py --help 正常 |
| CI | 9 jobs 全绿（公开仓库免费 runner） |
| 文档 | README（公开友好）+ CHANGELOG + 需求清单本文件 |

---

*需求版本：v1.0（2026-08-04）· 依据：旧 DEV_PLAN v2.0 全量提取 + 代码实测*
