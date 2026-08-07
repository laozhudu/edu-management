# edu-management

![CI](https://img.shields.io/github/actions/workflow/status/laozhudu/edu-management/ci.yml?branch=main)
![Release](https://img.shields.io/github/v/release/laozhudu/edu-management)
![License](https://img.shields.io/github/license/laozhudu/edu-management)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

## 概述

**edu-management** 是一套面向中小学校的教务管理系统，采用 **PyQt5 桌面端 + FastAPI 服务层** 双端架构，实现桌面与 Web 双端功能完全一致（24 页签映射 100%）。

核心定位：**小型学校核心闭环打磨到极致，配置驱动零代码扩展，桌面与 Web 双端功能完全一致**。

---

## 核心特性

| 领域 | 功能模块 |
|------|----------|
| **学期管理** | 创建/切换/继承配置(四色预览)/版本回滚/锁定/典型锁定场景 |
| **学生管理** | 列表/新生注册/学籍变动/升留级/班级名单导出 |
| **成绩管理** | 录入(粘贴/Excel导入/锁定)/查询/统计/排名/折算分/锁定联动 |
| **考试管理** | 考试CRUD/分考场/自动排座/监考安排/准考证批量生成 |
| **教师管理** | 列表/任课安排 |
| **系统设置** | 学期/班级科目/教室/用户权限/数据维护/系统配置/初始化 |
| **报表生成** | 考试标准报表/学籍变动表/成绩单/证书奖状/模板管理/批量打印 |
| **服务管理** | 审计日志/实时生效/健康检查/缓存管理/服务注册表 |

---

## 快速开始

### 环境要求
- Python 3.11+
- Windows / Linux (Ubuntu 22.04+ 推荐)
- SQLite (内置，零配置)

### 安装运行

```bash
# 1. 克隆仓库
git clone https://github.com/laozhudu/edu-management.git
cd edu-management

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖 (使用锁定版本)
pip install -r requirements.lock

# 4. 初始化数据库
PYTHONPATH=src python -c "from edu_system.database import init_db_with_defaults; init_db_with_defaults()"

# 5. 运行桌面端
python main.py

# 6. 运行 Web 服务 (另开终端)
PYTHONPATH=src uvicorn edu_system.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 运行测试

```bash
# 全量测试 (GUI 需 xvfb / QT_QPA_PLATFORM=offscreen)
QT_QPA_PLATFORM=offscreen ./venv/bin/pytest -q -p no:cacheprovider

# 仅契约测试
./venv/bin/pytest tests/contract -q

# 仅 GUI 测试
QT_QPA_PLATFORM=offscreen ./venv/bin/pytest tests/gui -q

# 单元测试
./venv/bin/pytest tests/unit -q
```

---

## 架构概览

```
edu-management/
├── main.py                    # 桌面端入口 (PyQt5 + 后台 DB 初始化)
├── src/edu_system/
│   ├── api/                   # FastAPI 服务层
│   │   ├── main.py            # FastAPI 应用工厂
│   │   ├── routes/            # 路由 (auth/students/exams/scores/...)
│   │   └── deps.py            # 依赖注入 (权限/学期/DB)
│   ├── gui/                   # PyQt5 桌面视图
│   │   ├── views/             # 24 个视图 (6域×4页签)
│   │   ├── theme.py           # 统一主题/字体/色板
│   │   └── crash_guard.py     # 全局异常/Qt消息捕获
│   ├── services/              # 业务逻辑层
│   │   ├── statistics.py      # 统计预计算 Worker
│   │   ├── report.py          # 报表工厂/证书/打印
│   │   ├── report_template.py # 模板管理
│   │   ├── report_worker.py   # 批量生成 Worker
│   │   ├── updater.py         # 自动更新服务
│   │   └── ...
│   ├── models/                # SQLAlchemy 2.0 模型
│   ├── database.py            # DB 引擎/会话/学期上下文注入
│   └── config/                # 配置单源化 (ui_config.json)
├── tests/
│   ├── contract/              # API 契约测试
│   ├── gui/                   # GUI 测试 (pytest-qt + xvfb)
│   └── unit/                  # 单元测试
├── alembic/                   # 数据库迁移
├── scripts/                   # 部署/验收脚本
└── docs/                      # 文档 (FUNCTION_PARITY.md 等)
```

---

## 核心设计原则

1. **配置驱动零代码扩展** - `ui_config.json` 是唯一配置源，桌面/Web 各自实现渲染器
2. **学期上下文自动注入** - SQLAlchemy `before_compile` 事件自动注入 `semester_id`，零侵入
3. **双端功能完全一致** - 6 域 24 页签 + 全局能力逐项对等，Web 端通过 `ui_config.json` 动态渲染
4. **配置单源化** - 消除双源配置，单一文件驱动双端
5. **测试驱动开发** - 569 测试基线，CI 全绿门禁

---

## 部署指南

### Windows 打包分发

```bash
# 本地构建
pip install nuitka pyinstaller
python -m nuitka --standalone --onefile --enable-plugin=pyqt5 --assume-yes-for-downloads --windows-icon-from-ico=assets/icon.ico main.py
# 生成 main.exe

# 代码签名 (需证书)
signtool sign /f cert.pfx /p <pwd> /t http://timestamp.sectigo.com /fd sha256 main.exe
```

### CI/CD 自动化

GitHub Actions 已配置完整流水线：
- **Lint** (ruff/format) → **Test** (unit/contract) → **DB Migrate** → **GUI Test** → **Security** (bandit/semgrep/pip-audit) → **License** (pip-licenses 门禁) → **Build** (Windows/Linux) → **Release** (tag 触发)

### 代码签名配置

在 GitHub 仓库 Settings → Secrets 添加：
- `WINDOWS_CODESIGN_CERT` - Base64 编码的 .pfx 证书
- `WINDOWS_CODESIGN_PWD` - 证书密码

---

## 许可证

本项目采用 **MIT License** - 详见 [LICENSE](LICENSE)。

第三方依赖许可证清单见 `THIRD_PARTY.md` (CI 自动生成)。

---

## 贡献指南

1. Fork 仓库 → 创建 feature 分支
2. TDD: 先写失败测试 → 实现 → 测试通过 → 重构
3. `ruff check/format` 通过 → 提交 PR
4. CI 全绿 → Squash Merge

---

## 版本历史

参见 [CHANGELOG.md](CHANGELOG.md)。

当前版本：**v3.1.0** (2026-08-07) - M5 全部完成 + M6 Sprint5/6/7

---

## 联系方式

- 作者：laozhudu
- 仓库：https://github.com/laozhudu/edu-management
- Issues：欢迎提交 Bug/Feature Request

---

> **小型学校定位一句话**：核心闭环（学生/成绩/学籍/考试/报表）打磨到极致，配置驱动零代码扩展，**桌面与 Web 双端功能完全一致**。
