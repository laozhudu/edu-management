# Changelog

> 由 git log 自动生成（conventional commits 分组）。本表对应公开仓库 `edu-management` 的历史，旧仓库 `旧仓库` 的完整历史见其 archived 仓库。

## 🚀 新功能

- `51ba9d8` feat: M2-3 API 补 `/api/config` 只读端点（暴露 ui_config，双端共享配置源）
- `d60f1bb` feat: M1 收尾 - main.py 支持 `--help` + 依赖清单补齐

## ♻️ 重构

- `d3441f6` refactor: M2-4 依赖精简 - 移除 3 个零引用包（104→79），pandas 转显式依赖
- `4f02b26` refactor: M2-2 死代码清理 - 删 navigation/design_system + TEMPLATE_DIR
- `c2795d5` refactor: M2-1 配置单源化 - 删除死代码 config.py

## 🧹 初始化

- `f5d4082` chore: 新仓库初始化 - v3.0 基线（源自 旧仓库，277 测试基线）