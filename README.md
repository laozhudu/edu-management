# 教务管理系统 v3.0（edu-management）

> 适配小型学校的教务管理系统：学生/成绩/学籍/考试/报表核心闭环，配置驱动零代码扩展，桌面为主、Web 只读为辅，Linux 开发 / Windows 部署。

## 🚀 新对话接手指引（必读）

1. **读计划**：`DEV_PLAN_v3.md`（主计划 v3.6）+ `REQUIREMENTS.md`（需求）+ `EDU_REVIEW.md`（教务审视）
2. **代码源头**：本地 `项目根目录` master（a73a775，277 passed 零敏感，旧仓库已 archived 冻结）
3. **测试基线**：`rm -rf .pytest_cache && QT_QPA_PLATFORM=offscreen ./venv/bin/pytest -q -p no:cacheprovider` = **277 passed**
4. **开发纪律**：每轮 ≤150 步；小步快进；**每任务先搜成品**（GitHub/PyPI/本地资产），不重复造轮子
5. **续接说法**：「继续 M0 新仓库搭建」/「执行 M5-G1 桌面快捷方式」

## 技术栈
Python 3.11 + PyQt5 + FastAPI + SQLAlchemy + Pydantic 2.x + openpyxl + docxtpl + WeasyPrint

## 启动（开发环境 Linux）
```bash
cd 项目根目录   # 代码源头（M1 迁移后改 edu-management）
/usr/bin/python3.12 main.py  # 或 venv/bin/python main.py
```

## 文档索引
| 文档 | 内容 |
|------|------|
| DEV_PLAN_v3.md | 主开发计划（里程碑/需求绑定/纪律） |
| REQUIREMENTS.md | 需求清单（源头） |
| EDU_REVIEW.md | 教务审视（务实剪裁定案） |
| REFACTOR_PLAN.md | 重构执行路线（Phase 0-5） |
| DEV_STANDARDS.md | 工程规范 |
| SECURITY_CHECKLIST.md | 安全清单 |
