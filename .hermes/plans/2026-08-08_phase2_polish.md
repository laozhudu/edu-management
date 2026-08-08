# 第二阶段：底座加固 + 功能打磨（Phase 2）开发计划

> 版本：v0.2 · 2026-08-08 · 来源：第一阶段验收实测 + 底座技术债全量盘点
> 定位：第一阶段（M0-M6，双端 24 页签 + 授权 + 打包，566 passed）已完成。第二阶段**先清底座技术债（不留后期麻烦），再做功能打磨（好用）**。
> 状态图例：⬜待做 ｜ 🟡进行中 ｜ ✅完成 ｜ ❌取消

---

## 0. 总览

### 为什么先清底座
你的要求是"后期任何功能修改都方便"。经实测盘点，当前**底座存在会快速恶化、且后期修复成本递增的缺口**——尤其 CI 质量门禁名存实亡。若后期功能叠加在脆底座上，改动会越积越难。故本阶段**底座优先**。

**已确认的底座现状（实测证据）**：
| 项 | 现状 | 后果 |
|----|------|------|
| CI lint（ruff） | **排除 api 51 / gui 112 / services 66 / repository 1 / schemas 8，全忽略** | 核心层代码质量无门禁，风格退化 |
| CI typecheck（mypy） | **整个 job 注释禁用**（~1975 存量错误） | 类型安全零保障，重构易错 |
| CI 安全扫描 | bandit / pip-audit 皆 `\|\| true` 兜底 | 扫描失败也不拦截，门禁假绿 |
| pip-audit | requirements.lock 未纳入 | 依赖漏洞无法自动审计 |
| ruff 弃用警告 | pyproject `[tool.ruff]` 顶层弃用 + UP038 移除 | CI lint 输出噪音、规则失效 |
| 死代码 | navigation.php / design_system.py 待清（早期 TODO） | 困惑 + 冗余 |
| 视图颜色令牌化 | 54 处硬编码色未入 theme C 字典 | 主题换肤不彻底 |
| 移动端 | Web 无小屏适配 | 手机体验差 |

### 阶段目标（两阶段合一的完整目标）
- **B 底座加固**：CI 门禁真正生效（lint/安全/类型）、死代码清零、依赖审计、配置整洁。
- **F 功能打磨**：每个页签从"渲染 200"落到实处（查/增/改/删/导走通）、已知缺口清零、双端观感一致、性能达标。
- **M 移动端**：Web 小屏可用（用户明确要求）。

### 验收基线（每 Sprint fresh 验证）
- 全量 pytest：**566 passed 不降**（随实现增长）
- ruff：**All checks passed（含取消核心层排除后）**
- 安全：bandit 0 高危（修复子进程误报后）、pip-audit 0 已知漏洞
- 类型：mypy 存量清零或明确豁免清单，CI typecheck 恢复
- CI：main push 全绿

---

## ═══════ 底座加固（先做，最高优先）═══════

## B0 收尾（前置）
| 任务 | 说明 | 验收 |
|------|------|------|
| B0-1 移除误提交 uvicorn.pid | 已提交 | ✅ 1b6d07e |
| B0-2 记录基线 | 566 passed @ 794ef51 | ✅ |
| B0-3 端点清单固化 | scripts/check_api_alignment.py 入库 | 可复现缺口分析 |

## B1 恢复 ruff 门禁（核心层不再排除）——最高价值
**根因**：`.github/workflows/ci.yml` 的 ruff 两个命令用 `--exclude=src/edu_system/api/ ...gui/ ...services/ ...models/__init__.py ...repository/ ...schemas/`（共 51/112/66/1/8 错误被隐藏）。
**任务（分两步，避免一次性大爆炸）**：
1. **注册台阶解决自动可修项**：`ruff check --fix src/edu_system/api/ src/edu_system/gui/ src/edu_system/services/ src/edu_system/repository/ src/edu_system/schemas/`（自动修 F401/I001/E712/W292/UP 等 ~72 项）
2. **人工研修余下高频项**：E741（ambiguous lvar，31）→ 改名；PLC2401/TRY300/TRY301/PLW0108/SIM 等本地规则（存量大），按 `extend-ignore` 显式放白名单并注明理由，**不放入 CI exclude**。
3. **CI 收口**：删掉 ci.yml 里除 alembic/test_data 外的核心层 exclude；pyproject 将 `[tool.ruff]` 弃用字段迁到 `[tool.ruff.lint]`；删 UP038。
**验收**：
- `ruff check src/` 0 error（含核心层）
- `ruff format --check` 通过
- CI lint job 重新覆盖 api/gui/services 层
- full_test：566 不降

## B2 恢复类型检查（mypy）
**根因**：`typecheck` job 全注释；`~1975` 存量错误全仓累积。
**任务**：
1. `pyproject [tool.mypy]` 定义 `disallow_untyped_*` 分级：先 `--ignore-missing-imports` + 对业务包开 `not_strict`；`config/` `core/` `database.py` 从严（原 CI 指定）。
2. 新增包（api/services）可先 `allow_redefinition`+宽松，**但禁止新增 ignore 注释**——防无限放水。
3. 选 2-3 个高价值模块（services/score、services/report_worker、api/deps）先修到 mypy 通过，形成"可参照的严格区"。
4. CI 恢复 `mypy` job（先只 `core/ config/ database.py`）。
**验收**：mypy 对 core/config/database 0 error；CI typecheck 绿；存量错误分级降级（1975→按包分解）。

## B3 安全门禁实效（bandit / pip-audit）
**根因**：CI `\|\| true` 兜底（失败不拦）；bandit 全量 High 49（B110 try/except/pass 27 为误报类 + B603/B607 subprocess 8 需人工核）；pip-audit 未入依赖。
**任务**：
1. 修 B603/B607（subprocess 加 shell=False / 参数白名单），B310/B404/B112 逐条核。
2. B110（try/exec/pass）评估后写 bandit 配置豁免并说明理由（非屏蔽）。
3. `requirements.lock` 加 `pip-audit`；CI 移除 `\|\| true`；bandit 新增 `--severity-level=high` gate。
**验收**：bandit 0 High（或豁免项有理由）；pip-audit 0 已知漏洞；CI security job 失败即拦截。

## B4 死代码清零 + 视图令牌化
**任务**：
1. 删 `components/navigation.py`、`design_system.py`（无人引用，早期 TODO 已确认）。
2. 12 视图 54 处硬编码色 → theme.py `C[键]` 令牌（想 f-string 转义警告，普通字符串 QSS 需 `C["..."]`）。
**验收**：grep 零引用；主题换肤完全生效；ruff 无回归。

## B5 配置整洁
- `[tool.ruff]` 顶层弃用项迁移（B1 已含）。
- 清 pyproject UI 遗留（若有无用项）。
- `grep 硬编码` 全仓 0（本机路径/内网 IP）。

---

## ═ F 功能打磨 ═

## F-P1 Web 缺口修复（实测 3 处）
### F-P1-1 成绩查询 keyword 生效
`score_query.html` 发 `keyword`，`score.py list_scores` 未接收（grep=0）→ 关键字框摆设。
- Modify `score.py`：加 `keyword` 参数，按 `Student.name/student_no.contains` 过滤
- +2 契约（命中/未命中）
**验收**：score_query 关键字过滤有结果。

### F-P1-2 统计端点对齐
`score_stats.html` 引用 `/api/stats/semester`（无 ID），后端路由带 `/{semester_id}`。
- 前端从 `/api/semester/active` 取 id 拼接；补契约响应 shape。
**验收**：score_stats 后端 200。

### F-P1-3 semester active 端点归一
`base.html`/`overview.html` 用 `/api/meta/semester/active`，活跃学期在 `/api/semester/active`。
- 页面统一到正确端点；或后端补 alias（DRY）。
**验收**：加载 200 不再 404。

### F-P1-4 端点一致性回归
`scripts/check_api_alignment.py` 固化 → CI 或验收脚本。

## 双端观感
| U | 任务 | 验收 |
|---|------|------|
| U1 移动端 | base 有 viewport；逐页签小屏（Flex换列/侧栏抽屉/表格横滚） | 手机无溢 |
| U2 主题 | 桌面/Web 同色板排距 | 一致 |
| U3 空态/加载/Toast | 统一 Alpine 组件 | 有反馈 |
| U4 表单校验 | 行内提示 | 非法有提示 |
| U5 桌面布局 | 已修 4 tabs，扩到全部 | 无跳动 |

## 业务链路抽测（每域真操作）
| 域 | 验收点 |
|----|------|
| 学生 | CRUD/导入导出/动态字段 |
| 成绩 | 粘贴录入/锁定/排名/查询 |
| 考试 | 建考→分考场→排座→监考→准考证 |
| 教师 | CRUD/任课 |
| 系统 | 学期/继承四色/锁定/备份 |
| 全局 | 报表下载/主题/学期切换/服务 |

## 性能与运维
| W | 目标 |
|---|------|
| 大列表首屏 <200ms / 报表 500份<30s / 统计毫秒 / 启动<3s / 优雅停机无残留 | 压测/计时 |

---
## 风险
| 风险 | 缓解 |
|------|------|
| 全层 ruff 一次性解压导致爆 | 分步：先自动修，再显式豁免清单；每步 fresh |
| mypy 全开存量太大 | 分级放宽 + 先修 2-3 模块立标杆 |
| 566 回归 | 每任务 fresh pytest + CI |

## 执行节奏
**B0→B1→B2→B3→B4→B5→F1→U→链路→W**。每步小步快进（RED→GREEN→REFACTOR→commit→全量回归）。
完成后更新勾选 + CHANGELOG。

*配套：REQUIREMENTS.md（源头）、DEV_PLAN_v3.md（M6+）、REFACTOR_PLAN.md（路线）。*