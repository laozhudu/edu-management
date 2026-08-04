# 教务管理系统 v2.0 — 开发规范与约束

> 基于业界通用标准制定，解决历史开发过程中的乱象，确保代码质量、交付可追溯、团队可协作。

---

## 1. Git 工作流规范

### 1.1 分支模型：GitHub Flow (简化版)
```
main (生产就绪，受保护)
  ↑
feature/* (功能分支，短生命周期)
  ↑
fix/* (热修复分支)
```

### 1.2 分支命名约定
| 类型 | 前缀 | 示例 |
|------|------|------|
| 功能开发 | `feat/` | `feat/sprint-4.1-fastapi-embed` |
| 缺陷修复 | `fix/` | `fix/score-calculation-rounding` |
| 重构 | `refactor/` | `refactor/permission-model` |
| 文档 | `docs/` | `docs/api-spec-update` |
| 测试 | `test/` | `test/contract-score-api` |
| 基建 | `chore/` | `chore/update-dependencies` |
| Sprint 任务 | `sprint/<num>/<desc>` | `sprint/4.2/design-system` |

### 1.3 提交规范：Conventional Commits 1.0.0
```
<type>(<scope>): <subject>

<body>

<footer>
```

**type 取值**:
- `feat`: 新功能
- `fix`: 缺陷修复
- `refactor`: 重构 (非功能、非修复)
- `perf`: 性能优化
- `docs`: 文档变更
- `test`: 测试相关
- `chore`: 构建/工具/依赖
- `ci`: CI 配置
- `style`: 格式化 (不影响逻辑)
- `revert`: 回滚

**scope**: 模块名，如 `api`、`gui`、`models`、`services`、`tests`、`db`、`ci`

**示例**:
```
feat(api): 添加成绩批量导入接口

- 支持 Excel/CSV 格式
- 字段映射预览
- 错误行定位下载

Closes #123
```

### 1.4 保护分支规则 (main)
- ❌ 禁止直接推送
- ✅ 必须通过 PR 合并
- ✅ 必须通过 CI (测试 + 覆盖率 + lint + 安全扫描)
- ✅ 至少 1 次 Code Review 通过
- ✅ 线性历史 (Squash and merge)
- ✅ 签名提交 (GPG)

### 1.5 禁止事项
- ❌ `git push --force` 到 `main` (除非经所有协作者确认)
- ❌ 提交大文件 (>10MB)，使用 Git LFS
- ❌ 提交敏感数据 (密钥、数据库、.env、*.db-wal/*.db-shm)
- ❌ 合并未通过 CI 的 PR
- ❌ 重写已推送到共享分支的历史

---

## 2. 代码质量标准

### 2.1 Python 代码规范
| 工具 | 版本 | 配置文件 | 执行时机 |
|------|------|----------|----------|
| **ruff** | 最新 | `pyproject.toml` | pre-commit + CI |
| **mypy** | 最新 | `pyproject.toml` | CI (严格模式) |
| **black** | 最新 | `pyproject.toml` | pre-commit (自动格式化) |
| **isort** | 最新 | `pyproject.toml` | pre-commit |

**核心规则**:
- 行长度: 100 字符
- 缩进: 4 空格
- 引号: 双引号
- 类型注解: **强制** (公共 API 100%，内部 ≥80%)
- 文档字符串: Google 风格，所有公共类/函数必写

### 2.2 架构分层约束 (严禁跨层调用)
```
┌─────────────────────────────────────┐
│  GUI Layer (PyQt5 Views)            │  ← 仅调用 Services
├─────────────────────────────────────┤
│  API Layer (FastAPI Routes)         │  ← 仅调用 Services
├─────────────────────────────────────┤
│  Service Layer (业务逻辑)            │  ← 调用 Repository + Models
├─────────────────────────────────────┤
│  Repository Layer (数据访问)         │  ← 仅操作 Models + Session
├─────────────────────────────────────┤
│  Model Layer (SQLAlchemy Models)    │  ← 纯数据结构，无业务逻辑
├─────────────────────────────────────┤
│  Database (SQLite)                  │
└─────────────────────────────────────┘
```

**跨层调用检查**: CI 中运行 `import-linter` 或自定义脚本验证。

### 2.3 命名规范
| 对象 | 规范 | 示例 |
|------|------|------|
| 模块/包 | snake_case | `student_service.py` |
| 类 | PascalCase | `StudentService` |
| 函数/方法/变量 | snake_case | `get_student_by_id` |
| 常量 | UPPER_SNAKE_CASE | `MAX_IMPORT_ROWS` |
| 私有成员 | `_leading_underscore` | `_cache` |
| 数据库表 | snake_case 复数 | `students` |
| 数据库列 | snake_case | `student_code` |
| 环境变量 | UPPER_SNAKE_CASE | `DATABASE_URL` |

### 2.4 禁止模式
```python
# ❌ 禁止：裸 except
try:
    ...
except:
    pass

# ✅ 正确：显式异常
try:
    ...
except (ValueError, KeyError) as e:
    logger.error("Failed", exc_info=e)

# ❌ 禁止：可变默认参数
def process(items: list = []): ...

# ✅ 正确
def process(items: list | None = None):
    items = items or []

# ❌ 禁止：硬编码魔法值
if status == 1: ...

# ✅ 正确：枚举/常量
if status == StudentStatus.ACTIVE: ...

# ❌ 禁止：print 调试
print("debug:", x)

# ✅ 正确：结构化日志
logger.debug("processing", student_id=student.id, extra={"key": "value"})
```

---

## 3. 测试规范

### 3.1 测试金字塔
```
        E2E / 集成测试 (少量，关键路径)
       ╱                                  ╲
   契约测试 (API Contract)           GUI 自动化测试
      ╱                                      ╲
  单元测试 (Service/Repository/Model)  ← 核心，覆盖率 ≥ 80%
```

### 3.2 测试分类与命名
| 类型 | 目录 | 命名 | 运行频率 |
|------|------|------|----------|
| 单元测试 | `tests/unit/` | `test_<module>_<function>.py` | 每次提交 |
| 契约测试 | `tests/contract/` | `test_<resource>_contract.py` | 每次提交 |
| 集成测试 | `tests/integration/` | `test_<flow>_integration.py` | PR / 夜ly |
| E2E 测试 | `tests/e2e/` | `test_<scenario>_e2e.py` | Release 前 |
| 性能测试 | `tests/perf/` | `test_<target>_perf.py` | 定期 |
| GUI 测试 | `tests/gui/` | `test_<view>_gui.py` | PR |

### 3.3 测试数据管理
- **统一入口**: `test_data/loader.py` (版本化 + 场景切片 + 角色切片)
- **禁止**: 测试中硬编码数据、直接操作数据库建测试数据
- **基线数据**: `test_data/base/v<semver>/dataset.json` + `manifest.json`
- **CI 场景**: `scenario='test'` (最小数据集，<30秒加载)

### 3.4 覆盖率门槛
| 层级 | 最低覆盖率 | 执行 |
|------|------------|------|
| 单元 + 契约 | **80%** (行) / **70%** (分支) | CI 阻断 |
| 核心 Service | **90%** | CI 警告 |
| 新增代码 | **100%** (增量) | PR 检查 |

### 3.5 测试编写原则
- **AAA 模式**: Arrange → Act → Assert
- **单一职责**: 每个测试只验证一个行为
- **确定性**: 无随机性、无外部依赖 (Mock 外部服务)
- **快速**: 单元测试 < 100ms，契约测试 < 500ms
- **独立**: 可任意顺序并行运行，无状态污染

---

## 4. CI/CD 规范

### 4.1 Pipeline 阶段
```yaml
stages:
  1. lint          # ruff + mypy + black --check + isort --check
  2. typecheck     # mypy 严格模式
  3. test-unit     # pytest tests/unit -x --cov=src --cov-fail-under=80
  4. test-contract # pytest tests/contract -x
  5. test-gui      # pytest tests/gui -x (需虚拟显示器)
  6. security      # pip-audit + bandit + semgrep
  7. build         # Nuitka 编译 (Windows + Linux)
  8. package       # 生成安装包/便携版
  9. release       # 标签触发，GitHub Release
```

### 4.2 触发规则
| 事件 | 触发阶段 |
|------|----------|
| `push` to `main` | 全流程 + 发布构建 |
| `pull_request` | lint → test-unit → test-contract → security |
| `push` to `feat/*` `fix/*` | lint → test-unit → test-contract |
| `schedule` (夜ly) | 全流程 + 集成测试 + 性能测试 |
| `workflow_dispatch` | 手动触发全流程 |
| 标签 `v*` | release |

### 4.3 制品管理
- **构建产物**: 上传为 Artifact (保留 30 天)
- **Release 产物**: GitHub Release Assets (永久)
- **版本号**: 语义化版本 (SemVer) + Git 标签 `v<major>.<minor>.<patch>`
- **Changelog**: `git-cliff` 自动生成 (Conventional Commits)

---

## 5. 架构与设计原则

### 5.1 核心原则 (来自 DEV_PLAN.md)
1. **教务员不加班，系统才算合格** — 效率优先，交互极简
2. **学年/学期为核心上下文** — 所有数据、配置、权限随学期隔离
3. **预计算统计 + 配置继承 + 分级缓存 + 数据锁定 + 服务级权限**
4. **零部件优先** — 先搜成熟开源组件，仅填补业务缺口
5. **AI 模拟人工验收** — 验收由 AI 代理完成，模拟真实用户操作路径

### 5.2 设计模式约束
| 场景 | 推荐模式 | 禁止模式 |
|------|----------|----------|
| 服务层事务 | Unit of Work + Repository | 手动 `session.commit()` 散落 |
| 事件驱动 | Outbox Pattern + APScheduler | 直接调用、同步阻塞 |
| 权限检查 | 装饰器 + 依赖注入 | 硬编码 `if user.role == 'admin'` |
| 配置管理 | Pydantic Settings + 环境变量 | 硬编码常量、全局变量 |
| 缓存 | diskcache + 版本控制 + ETag | 无失效策略的内存字典 |
| 导入导出 | tablib + dlt + Great Expectations | 手写 pandas 循环 |

### 5.3 数据库设计规范
- **主键**: 整型自增 `id` (业务键另建唯一索引)
- **外键**: 显式声明 `ForeignKey` + `ondelete="CASCADE/SET NULL"`
- **索引**: 查询路径必建复合索引，`EXPLAIN QUERY PLAN` 验证
- **软删除**: 统一 `deleted_at` + `is_deleted`，查询自动过滤
- **审计**: 核心表全字段审计 (before_flush 监听器)
- **乐观锁**: 关键表 `version` 字段，并发更新检查
- **分表**: 审计日志按月分表 `audit_logs_YYYYMM`

### 5.4 API 设计规范 (RESTful + 版本化)
- **版本前缀**: `/api/v1/`, `/api/v2/`
- **资源命名**: 复数名词 `/students`, `/exams/{id}/scores`
- **HTTP 语义**: GET/POST/PUT/PATCH/DELETE 严格对应
- **分页**: `?page=1&page_size=50` + `Link` Header
- **筛选**: `?field=value&field__in=a,b,c&field__gte=100`
- **排序**: `?sort=-created_at,name`
- **错误格式**: RFC 7807 Problem Details
- **幂等性**: 写接口支持 `Idempotency-Key` Header

---

## 6. 安全规范

### 6.1 认证授权
- **JWT**: RS256 签名，Access Token 15min + Refresh Token 7d
- **设备信任**: 首次登录记录指纹，30 天免密
- **权限模型**: RBAC + 服务级粒度 + 学期维度
- **会话**: 双端同步踢下线 (版本号机制)

### 6.2 输入验证
- **Pydantic v2**: 所有入参模型强制校验
- **SQL 注入**: 100% 参数化查询 (SQLAlchemy ORM)
- **XSS**: Jinja2 `autoescape` + CSP Header
- **CSRF**: 双端同步 Token (Cookie + Header)
- **文件上传**: 类型白名单 + 大小限制 + 隔离存储 + 病毒扫描

### 6.3 数据保护
- **敏感字段**: 身份证/手机/地址 加密存储 (AES-GCM)
- **日志脱敏**: 结构化日志自动脱敏 PII 字段
- **备份加密**: 备份文件 AES-256 加密
- **传输加密**: 生产环境强制 HTTPS (TLS 1.3)

### 6.4 依赖安全
- `pip-audit` 每次 CI 执行
- `requirements.lock` 版本锁定 + 定期更新
- 禁止引入已知 CVE 高危依赖

---

## 7. 文档规范

### 7.1 必维护文档
| 文档 | 位置 | 更新触发 | 格式 |
|------|------|----------|------|
| 架构设计 | `docs/ARCHITECTURE.md` | 架构变更 | Markdown + Mermaid |
| API 规范 | `docs/API_SPEC.md` | 接口变更 | OpenAPI 3.1 (自动生成) |
| 数据库设计 | `docs/DB_DESIGN.md` | 表结构变更 | Markdown + Mermaid ER |
| 部署运维 | `docs/DEPLOYMENT.md` | 部署变更 | Markdown |
| 开发指南 | `docs/DEVELOPMENT.md` | 流程变更 | Markdown |
| 变更日志 | `CHANGELOG.md` | 每次 Release | git-cliff 自动生成 |
| Sprint 计划 | `DEV_PLAN.md` | Sprint 规划/复盘 | Markdown |
| 看板 | `docs/KANBAN.md` | 每日站会 | Markdown |

### 7.2 代码内文档
- **模块级**: 模块首行 docstring 说明职责
- **类级**: Google 风格 docstring (Args/Returns/Raises/Example)
- **函数级**: 公共 API 必写，内部建议写
- **复杂逻辑**: 行内注释解释「为什么」，而非「做什么」

### 7.3 文档即代码
- API 文档从代码自动生成 (`fastapi` + `scalar`)
- 数据库文档从模型自动生成 (`sqlalchemy` + `eralchemy`)
- 架构图版本控制 (`docs/architecture/*.mmd`)

---

## 8. 发布流程

### 8.1 版本号语义
```
MAJOR.MINOR.PATCH[-PRE]
```
- **MAJOR**: 不兼容 API 变更
- **MINOR**: 向后兼容功能新增
- **PATCH**: 向后兼容缺陷修复
- **PRE**: `alpha`/`beta`/`rc`<num>

### 8.2 Release Checklist
- [ ] 所有 Sprint 任务验收通过 (DoD)
- [ ] CI 全绿 (含集成/性能/安全测试)
- [ ] 版本号已更新 (`pyproject.toml` + `src/edu_system/__init__.py`)
- [ ] `CHANGELOG.md` 已生成且人工校对
- [ ] 数据库迁移脚本已验证 (正向+回滚)
- [ ] 文档已同步更新
- [ ] 打包测试通过 (Windows/Linux/macOS)
- [ ] 签名/公证完成 (Windows signtool / macOS codesign)
- [ ] GitHub Release 创建 + 制品上传
- [ ] 通知相关方 (教务主任/运维/开发)

### 8.3 回滚策略
- **代码回滚**: `git revert` + 热修复分支
- **数据库回滚**: 预置回滚脚本 `<version>_rollback.sql`，< 30 秒恢复
- **配置回滚**: Feature Flag 瞬时关闭新功能

---

## 9. 开发环境标准化

### 9.1 必装工具
```bash
# 核心
python 3.12+ (pyenv 管理)
poetry / pip-tools (依赖管理)
pre-commit (Git 钩子)

# 数据库
sqlite3 (CLI)
DB Browser for SQLite (GUI)

# 调试
pytest + pytest-cov + pytest-asyncio
debugpy (VS Code 远程调试)
py-spy (性能分析)

# 代码质量
ruff + mypy + black + isort
pre-commit run --all-files
```

### 9.2 环境变量 (`.env.example` 模板)
```bash
# 数据库
DATABASE_URL=sqlite:///data/school_data.db

# 安全
JWT_SECRET_KEY=<生成 64 字符随机串>
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY_PATH=keys/private.pem
JWT_PUBLIC_KEY_PATH=keys/public.pem

# 功能开关
EDU_DEV_MODE=0
ENABLE_WEB_API=1
ENABLE_STATS_CACHE=1

# 监控
LOG_LEVEL=INFO
SENTRY_DSN=

# 外部服务 (可选)
SMTP_HOST=
SMTP_PORT=
WECHAT_WEBHOOK=
```

### 9.3 提交前自检清单
```bash
# 一键执行
pre-commit run --all-files
pytest tests/unit tests/contract -x --cov=src --cov-fail-under=80
mypy src/
```

---

## 10. 代码审查标准

### 10.1 PR 模板必填项
```markdown
## 变更类型
- [ ] feat / [ ] fix / [ ] refactor / [ ] docs / [ ] test / [ ] chore

## 关联 Issue
Closes #<issue_number>

## 变更摘要
简述做了什么、为什么做

## 测试验证
- [ ] 单元测试新增/更新
- [ ] 契约测试新增/更新
- [ ] 手工验证步骤 (附截图/录屏)
- [ ] 回归测试通过

## 破坏性变更
- [ ] 无 / [ ] 有 (详述迁移方案)

## 截图/录屏 (GUI 变更必填)
```

### 10.2 审查重点 (按优先级)
1. **正确性**: 逻辑是否满足需求、边界条件处理
2. **安全性**: 权限检查、输入验证、敏感数据处理
3. **性能**: N+1 查询、大数据量渲染、内存泄漏
4. **架构**: 分层约束、设计模式、耦合度
5. **可维护性**: 命名、注释、测试覆盖、复用性
6. **规范**: 代码风格、提交信息、文档同步

### 10.3 审查通过标准
- ✅ 0 个必须修复
- ✅ 0 个安全高危
- ✅ CI 全绿
- ✅ 至少 1 人 Approve
- ✅ 作者自测通过

---

## 11. 事件响应与运维

### 11.1 事故分级
| 级别 | 定义 | 响应时间 | 升级路径 |
|------|------|----------|----------|
| P0 | 核心业务不可用 (成绩录入/查分/考勤) | 15 分钟 | 电话/微信叫醒 |
| P1 | 重要功能受阻 (报表/导入导出/权限) | 1 小时 | 微信通知 |
| P2 | 次要功能异常 (UI 瑕疵/非核心报错) | 4 小时 | 工单跟踪 |
| P3 | 优化/建议/技术债 | 下个 Sprint | 纳入规划 |

### 11.2 观测指标 (最小集)
- **可用性**: API 成功率 ≥ 99.9%
- **延迟**: P95 < 200ms (读) / < 500ms (写)
- **错误率**: 5xx < 0.1%
- **数据库**: 连接池使用率 < 70%、慢查询 < 1s
- **缓存**: 命中率 > 90%
- **队列**: 积压 < 100、处理延迟 < 30s

---

## 12. 违规处理

| 违规类型 | 首次 | 再次 | 严重 |
|----------|------|------|------|
| 绕过 CI 推送 | 警告 + 补课 | 暂停合并权限 1 周 | 移除写权限 |
| 提交敏感数据 | 立即撤销 + 轮换密钥 | 同左 | 同左 |
| 破坏 main 历史 | 通报 + 强制修复 | 暂停权限 | 移除权限 |
| 无测试提交功能 | PR 拒绝 | 强制补测 | 计入绩效 |
| 硬编码密钥/配置 | PR 拒绝 | 警告 | 计入绩效 |

---

## 附录 A：工具配置文件模板

### `pyproject.toml` 关键片段
```toml
[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "UP", "W", "C4", "PTH", "PERF", "TCH", "TID", "SIM", "PIE", "ARG", "PD", "PL", "TRY", "NPY", "RSE", "RET", "SLF", "SUB"]
ignore = ["E501", "PTH118", "PTH123"]
fixable = ["ALL"]
unfixable = ["TCH", "SIM", "PIE", "ARG", "PD", "PL", "TRY", "NPY", "RSE", "RET", "SLF", "SUB"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
follow_imports = "normal"
namespace_packages = true
explicit_package_bases = true
enable_error_code = ["unused-ignore", "attr-defined", "name-defined", "arg-type", "return-type", "union-attr", "assignment", "call-arg", "no-untyped-def", "no-untyped-call", "unused-coroutine", "annotation-unchecked"]

[[tool.mypy.overrides]]
module = ["tests.*", "test_*"]
strict = false
disallow_untyped_defs = false

[tool.black]
line-length = 100
target-version = ["py312"]
include = "\.pyi?$"
extend-exclude = """
/(
  \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | venv
  | _build
  | buck-out
  | build
  | dist
)/
"""

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
atomic = true
```

### `.pre-commit-config.yaml`
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, sqlalchemy, fastapi, pyqt5]
        args: [--strict]

  - repo: https://github.com/psf/black
    rev: 24.4.0
    hooks:
      - id: black
        language_version: python3.12

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest-unit
        entry: pytest tests/unit tests/contract -x --tb=short
        language: system
        pass_filenames: false
        stages: [commit, push]
```

---

## 附录 B：常用命令速查

```bash
# 依赖管理
pip-compile requirements.in --output-file=requirements.lock --upgrade
pip-sync requirements.lock

# 代码质量
pre-commit run --all-files
ruff check src/ tests/ --fix
mypy src/
black src/ tests/
isort src/ tests/

# 测试
pytest tests/unit tests/contract -x -v --cov=src --cov-report=term-missing
pytest tests/gui -x -v --headed  # GUI 测试需显示器

# 数据库
alembic revision --autogenerate -m "message"
alembic upgrade head
alembic downgrade -1

# 打包
python -m nuitka --standalone --onefile --enable-plugin=pyqt5 main.py

# 发布
git cliff --output CHANGELOG.md
git tag -s v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3
```

---

**文档版本**: v1.0
**生效日期**: 2026-08-02
**维护者**: 开发团队
**审批**: 项目负责人

> 本规范为强制执行标准，违规按第 12 条处理。建议每季度评审更新。