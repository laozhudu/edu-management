# edu-management

![CI](https://img.shields.io/github/actions/workflow/status/laozhudu/edu-management/ci.yml?branch=main)

## 概述

个人项目。PyQt5 桌面应用 + FastAPI 服务层。

## 快速开始

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.lock
./venv/bin/python main.py
```

运行测试：

```bash
QT_QPA_PLATFORM=offscreen ./venv/bin/pytest -q -p no:cacheprovider
```

## 目录结构

```
src/edu_system/    核心代码（gui/ 桌面界面、api/ 服务层、services/ 业务逻辑）
tests/             测试（unit/ 单测、contract/ 契约、gui/ 界面）
alembic/           数据库迁移
```

## License

见 pyproject.toml。
