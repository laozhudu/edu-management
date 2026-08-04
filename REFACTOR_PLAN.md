# 教务管理系统 v3.0 重构规划（公开仓库版 · 双端架构）

> 规划版本：v2.0（2026-08-04 重写）
> 缘由：v1.0 规划未考虑双端架构，且中途插入需求（公开脱敏/改名/报表四件套/权限RLS/折算分）已改变系统形态，整套方案重写。
> 决策基线：新建干净公开仓库 `项目根目录`；旧仓库 `旧仓库` 冻结兜底，新系统稳定后删除。

---

## 1. 双端现状核实（2026-08-04 实测）

### 1.1 桌面端（PyQt5）— 当前唯一 UI
- 18 个视图（student/score/exam/teacher/class/dashboard/settings/system_config/remaining/init_system 等）
- 主题系统：theme.py（25 键 C 字典）+ theme_manager.py（亮/暗切换，PR #65）
- 组件：components.py + crash_guard（三层防护）+ main_window + server_thread
- 配置驱动：ui_config.json 单一来源（学校/名称/版本/6 域导航/页签）
- 登录：LoginDialog（记住我/自动登录）

### 1.2 网页端 — 纯 API 后端，无前端
- FastAPI 8 路由模块：auth/score/exam/attendance/stats/meta/scheduler + admin_interface
- **templates/ 与 static/ 均为空目录**（git 零文件），无 Jinja2 模板引擎，无 HTML 渲染路由
- 嵌入式：桌面 server_thread 用 QThread 跑 uvicorn，局域网访问 API
- 结论：**"网页端"目前 = API 服务层，非完整 Web 应用**

### 1.3 中途插入需求（v3.0 已吸收，重构时保留）
| 需求 | 状态 | 保留内容 |
|------|------|----------|
| 项目改名"教务管理系统" | ✅ | APP_NAME/标题统一 |
| 校名配置化 | ✅ | ui_config.school_name 默认"示例学校" |
| 公开脱敏 | ✅ | SECRET_KEY 环境变量化/隐私数据删除/历史清零 |
| 报表四件套 | ✅ | report_excel/certificate/print/factory |
| 权限规范化+RLS | ✅ | RolePermission 表 + RowLevelSecurity |
| 成绩折算分 | ✅ | Score.converted_score + convert_scores |
| 主题切换 | ✅ | ThemeManager 亮/暗 |

### 1.4 测试基线
- **277 passed**（master 253 + 报表四件套 24）
- CI 9 jobs（lint/test/test-contract/db-migrate/test-gui/security/build-win/build-linux）

---

## 2. 目标（Goal）

1. **零敏感公开**：edu-management 干净历史仓库，任何位置（源码/测试/文档/历史/配置默认值）零敏感
2. **双端清晰定位**：明确「桌面端 = 主 UI，API = 服务层，Web 前端 = 可选扩展」，不再模糊"网页端"概念
3. **模块化配置化重构**：分层边界保持 + 配置单源 + 死代码清理
4. **277 测试全绿 + CI 可用**：公开仓库免费 runner
5. **双仓库并行**：旧仓库冻结兜底，稳定后删除

---

## 3. 架构设计（Architecture）

### 3.1 目标结构（双端分层）

```
edu-management/
├── src/edu_system/
│   ├── config/            # ui_config.json + features.json + settings（单一配置源）
│   ├── core/              # auth/permissions/features/audit/rls/idempotency/result/context
│   ├── models/            # 36 模型（单文件，保持）
│   ├── repository/        # base/movement
│   ├── services/          # 21 业务模块（含报表四件套/折算分/权限）
│   ├── api/               # FastAPI 纯 API 层（8 routes + registry + middleware）
│   ├── gui/               # PyQt5 桌面端（18 视图 + theme + components）
│   └── schemas/
├── alembic/               # 迁移（8 版本）
├── tests/                 # unit/contract/gui/integration（277）
├── scripts/               # 归档/迁移脚本
├── .github/workflows/     # CI 9 jobs
├── docs/                  # 脱敏设计文档
├── README.md              # 公开友好
└── pyproject.toml         # 脱敏元数据
```

### 3.2 双端架构决策（重构核心）

| 决策点 | 现状 | 重构后 | 理由 |
|--------|------|--------|------|
| 桌面端 | 唯一 UI（18 视图） | **保留为主 UI，配置驱动强化** | 用户主力使用形态 |
| 网页端 | 纯 API（无前端） | **与桌面功能完全一致的双端（2026-08-04 定案）**：6 域 26 页签 + 全局能力逐项对等，共用 ui_config 与业务 API，技术栈后续单定 | 用户明确要求：Web 非简化版/非只读 |
| 配置共享 | ui_config.json | **双端共享 ui_config.json**（桌面读配置渲染；API 暴露 /api/config 供未来 Web 消费） | 配置单源 |
| 嵌入式服务 | server_thread QThread uvicorn | 保留 + 文档化（局域网 API 访问） | 桌面内嵌 API 已有价值 |
| 死代码 | navigation/design_system/templates/static | **不迁入**（重构即清理） | 无引用 |

### 3.3 配置单源化设计

- `config/__init__.py`（Settings，pydantic-settings）合并旧 `config.py`（扁平模块）
- ui_config.json：学校/名称/版本/域/页签/状态栏（桌面 UI 渲染源）
- features.json：功能开关（模块级）
- SECRET_KEY：环境变量（未注入随机生成）
- 新增：API 层 `/api/config` 只读端点（暴露 UI 配置，供未来 Web 前端消费）

### 3.4 Web 端全功能实现（Phase 5 核心交付，2026-08-04 定案）

```text
GUI 配置驱动 ──→ ui_config.json ──→ /api/config (REST)
                                        ↓
                        Web 前端（功能与桌面完全一致：6 域 26 页签 + 全局能力）
                        复用同一配置 + 业务 API，双端功能/视觉一致
```
> **2026-08-04 用户定案**：Web 端不再是可选/简化版，功能与桌面完全相同（学生/成绩/考试/教师/系统域全业务 + 报表下载/导入向导/动态字段/主题切换等全局能力）。技术栈后续单定（候选：SPA Vue3+Vite / HTMX+Jinja2）；功能对等清单见 REQUIREMENTS.md G 组。

---

## 4. 执行计划（Step-by-Step，每步 TDD + commit）

### Phase 0：准备与冻结（0.5 天）
- [ ] P0-1 旧仓库冻结：README 顶部 FROZEN 标注，停止推送
- [ ] P0-2 复核 integrate-clean 分支（master+改名+报表+脱敏）：277 passed、零残留
- [ ] P0-3 排除清单核验：73400340/data/logs/import_real_data/templates/static 空目录

### Phase 1：新仓库搭建（0.5 天）
- [ ] P1-1 git init 项目根目录 + 复制源码（排除清单）→ 首次 commit
- [ ] P1-2 重建 venv + requirements.lock 核对
- [ ] P1-3 **验收**：fresh pytest = 277 passed + `python main.py --help` 冒烟

### Phase 2：模块化配置化重构（2-3 天）
- [ ] P2-1 配置单源化：合并 config.py → config/__init__.py；test_smoke/test_ui_config 对齐
- [ ] P2-2 死代码清理：删 navigation/design_system/templates/static；grep 零引用确认
- [ ] P2-3 API 层补 `/api/config` 端点（暴露 ui_config，供未来 Web）；测试 +2
- [ ] P2-4 cache.py 去重 + 依赖精简（requirements.lock 移除未用）
- [ ] P2-5 文档重写：README（项目介绍/双端说明/快速开始/配置指南/CI 徽章）+ CHANGELOG
- [ ] P2-6 CI 适配：workflow 更新仓库名/公开 runner

### Phase 3：加固验收（1 天）
- [ ] P3-1 敏感扫描：`grep -rn "校名关键词"` 零命中 + git log 历史零敏感
- [ ] P3-2 fresh pytest 277 + ruff/format + bandit/gitleaks 安全扫描
- [ ] P3-3 空库迁移演练（alembic upgrade head 全表）
- [ ] P3-4 Windows 构建 dry-run（CI build job 手动触发）

### Phase 4：公开上线（0.5 天）
- [ ] P4-1 `gh repo create edu-management --public` + push
- [ ] P4-2 CI 全绿确认（公开仓库免费 runner）
- [ ] P4-3 README 徽章 + 首次 Release
- [ ] P4-4 旧仓库转 private 归档（观察 1 个月后删）

### Phase 5：Web 端全功能实现（2026-08-04 升级为核心交付）
- [ ] P5-1 技术栈选型（SPA Vue3+Vite / HTMX+Jinja2 评估定案）→ 骨架 + 登录 + 6 域导航
- [ ] P5-2 Web 业务页：学生域（学生信息 CRUD/动态字段/新生注册/学籍变动/升留级）——功能对等
- [ ] P5-3 Web 业务页：成绩域（录入粘贴/Excel 导入/查询/统计/排名/锁定）——功能对等
- [ ] P5-4 Web 业务页：考试/教师/首页域——功能对等
- [ ] P5-5 Web 业务页：系统域（学期/班级科目/教室/用户权限/数据维护/初始化）——功能对等
- [ ] P5-6 Web 全局能力：主题/学期切换、报表下载(Word/Excel/PDF)、导入向导、服务管理——功能对等
- [ ] P5-7 双端一致渲染 + 配置热加载 + 认证一致（G3/G4/G5）
- [ ] P5-8 功能对等验收（G6）：桌面 18 视图 ↔ Web 映射表 100% 覆盖

---

## 5. 测试与验证（Tests / Validation）

| 验证点 | 命令 | 通过标准 |
|--------|------|----------|
| 全量测试 | `rm -rf .pytest_cache && QT_QPA_PLATFORM=offscreen ./venv/bin/pytest -q -p no:cacheprovider` | 277 passed |
| 敏感扫描 | `grep -rn "校名关键词" .` | 零命中 |
| 历史审计 | `git log --all --oneline` | 无敏感 |
| 格式 | `./venv/bin/ruff check src/ tests/` | All checks passed |
| 安全 | bandit + gitleaks | 无高危/无泄露 |
| 迁移 | `alembic upgrade head` | 空库全表一致 |
| 冒烟 | `python main.py --help`（offscreen） | 正常退出 |

## 6. 风险与对策（Risks）

| 风险 | 对策 |
|------|------|
| 复制遗漏 | Phase 1 后 277 测试 + 清单 diff |
| 死代码误删引用 | P2-2 先全仓 grep 再删 |
| 配置合并破坏兼容 | P2-1 测试先行 |
| 双端定位模糊 | 本文档 3.2 决策表明确：桌面=主 UI，Web=API 层 |
| 公开后误提交敏感 | P3-1 扫描 + .gitignore 加固 + pre-commit gitleaks |
| 旧仓库数据丢失 | 冻结不删，观察 1 个月 |

## 7. 开放问题（Open Questions）

- [ ] README 语言（默认中文）
- [ ] GitHub 账户额度是否恢复（决定公开后 CI 立即可用性）
- [ ] 是否在 v3.0 就规划 Web 前端（默认 YAGNI 延后到 Phase 5）
- [ ] 旧仓库归档后是否彻底删除（默认观察 1 个月）

---

*规划 v2.0 · 2026-08-04 · 依据：双端现状实测 + DEV_STANDARDS.md*
