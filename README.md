# 教务管理系统（edu-management）

> 适配**小型学校**的教务管理系统：学生 / 成绩 / 学籍 / 考试 / 报表核心闭环，配置驱动零代码扩展，桌面为主、Web 只读为辅。Linux 开发，Windows / Linux 双端部署。

![CI](https://img.shields.io/github/actions/workflow/status/laozhudu/edu-management/ci.yml?branch=main)

## ✨ 特性

- **核心业务闭环**：学生管理 / 成绩录入与统计 / 学籍变动 / 考试安排 / 报表导出，一整套学期制教务工作流
- **配置驱动，零代码扩展**：改校名、菜单、页签、主题只改一份配置；新增业务字段走界面配置（动态字段），不改代码
- **双端架构**：PyQt5 桌面端（主 UI）+ FastAPI 服务层；`/api/config` 暴露 UI 配置，为 Web 端双端一致渲染预留接口
- **学期上下文**：多学期数据隔离，配置继承、数据锁定
- **性能设计**：全量内存缓存 + 预计算统计 + SQLite WAL，单校区规模毫秒级响应
- **工程化**：279+ 单测契约、CI 门禁（lint/test/契约/迁移/安全/构建）、语义化版本、git-cliff changelog

## 🧰 技术栈

| 层 | 技术 |
|----|------|
| 桌面端 | PyQt5 + 自研组件库 + 主题令牌系统 |
| API 服务层 | FastAPI + SQLAlchemy 2.0 + Pydantic 2.x |
| 数据库 | SQLite（WAL） + Alembic 迁移 |
| 报表 | openpyxl（Excel）/ docxtpl（Word）/ WeasyPrint（PDF） |
| 数据质量 | pandas + pandera Schema 校验 |

## 🚀 快速开始

前置：Python 3.11+（推荐 3.12）

```bash
# 1. 克隆并创建虚拟环境
git clone <repo-url> edu-management && cd edu-management
python3 -m venv venv

# 2. 安装依赖（可复现，由 lock 固定版本）
./venv/bin/pip install -r requirements.lock

# 测试依赖（跑测试/CI 用）
./venv/bin/pip install pytest pytest-asyncio pytest-cov pytest-timeout pytest-mock httpx itsdangerous factory_boy ruff

# 3. 运行桌面端
./venv/bin/python main.py

# 4. 运行 API 服务层（可选，供局域网 / 未来 Web 端）
./venv/bin/uvicorn edu_system.api.main:create_app --factory --host 0.0.0.0 --port 8080

# 5. 运行测试（基线 279 passed）
rm -rf .pytest_cache
QT_QPA_PLATFORM=offscreen ./venv/bin/pytest -q -p no:cacheprovider
```

> 首次运行会自动创建 `data/` 下的空库并建表（生产数据请自行备份，本仓库不含任何真实数据）。

## 🖥️ 双端定位

| 端 | 定位 | 说明 |
|----|------|------|
| 桌面端（PyQt5） | **主 UI** | 18 个视图，学期管理、成绩录入、报表生成的日常操作入口 |
| API 服务层（FastAPI） | 服务层 | 桌面内嵌 uvicorn 供局域网访问；Web 前端复用同一套 API |
| Web 前端 | **与桌面功能完全一致**（2026-08-04 定案） | 6 域 26 页签 + 全局能力逐项对等（报表下载/导入向导/动态字段/主题切换等），共用 ui_config 与业务 API，技术栈后续单定 |

访问 `http://<host>:8080/api/docs` 查看交互式 OpenAPI 文档。

## ⚙️ 配置指南

单一配置源：`src/edu_system/config/ui_config.json`

| 配置 | 作用 | 示例 |
|------|------|------|
| `app` | 校名 / 名称 / 版本 | `"school_name": "示例学校"` |
| `theme` | 品牌 / 强调色 / 侧栏色 / 密度 | `"accent_color": "#3498DB"` |
| `topbar` | 顶栏开关 / 快捷键 | `"shortcuts": {"command_palette": "Ctrl+K"}` |
| `domains` | 6 域导航 + 页签 + 角色权限 | `[{"id": "students", "title": "学生管理", ...}]` |
| `statusbar` | 状态栏内容 | `{"left": [...], "right": [...]}` |

改动即生效（桌面重启或 API 热加载）。完整配置模型见 `src/edu_system/config/ui_config.py`（Pydantic，含 `domains` 角色过滤）。

## 🔐 安全

- `SECRET_KEY` 通过环境变量注入（未注入时自动生成随机密钥）
- 认证：JWT（桌面端与会话共用同一 auth API）
- 服务级权限 + 行级权限（RLS），按角色过滤域 / 页签

## 📚 文档索引

| 文档 | 内容 |
|------|------|
| `CHANGELOG.md` | 版本变更日志 |
| `THIRD_PARTY.md` | 第三方依赖许可证说明 |

> 开发规划与内部文档（开发计划/需求清单/重构路线等）仅保留本地，不随仓库分发。

## 🗺️ 路线图

- M0-M4：公开上线（已完成：CI 门禁、语义化版本、安全清洗）
- M5：待办补齐（学期上下文 / 统计预计算 / 配置继承与锁定 / 桌面补全 / 业务 API / 服务管理 / Web 前端）
- M6：后续 Sprint（考试管理 / 学期 UI / Win 打包签名）

## 📄 License

MIT（公开仓库将在发布时确认）。