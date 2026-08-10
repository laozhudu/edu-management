# 第四阶段（A5）方案：样式配置 + 权限视图修复 + 审计对齐

> 2026-08-09 · 用户反馈："样式配置没出来"、"权限和审计代码有写但 UI 菜单/标签没显示"

## 一、实机盘点结论

### 1. 界面样式配置（代码有、界面无）
- ui_config.py 已完整解析 ThemeConfig/TopBarConfig/StatusBarConfig/LoginDialogConfig（20+ 字段）
- **无任何编辑界面**：system_config 只有服务状态/审计，无样式配置

### 2. 权限桌面端（代码有、挂错）
- registry `users → SettingsView`，但 SettingsView 内容是**数据库信息/数据统计/初始化引导**（标题都写"数据维护"）
- **桌面端无用户权限视图**（无 UserView/PermissionsView 类）
- Web users.html 已完整实现（列表/角色矩阵/新增/编辑/停用/重置密码）

### 3. 审计（代码有、藏得深）
- Web system_config.html 有审计日志列表（/api/audit/logs）
- 桌面 system_config 有"查看日志"按钮弹对话框（能看到）
- 已基本实现，可保留（不动）

## 二、方案（v3.7.0）

### A. 界面样式配置界面
| 层 | 内容 |
|----|------|
| 后端 | `POST /api/config/save-ui`：接收 theme/topbar/login/statusbar 片段 → 写回 ui_config.json（合并）+ reload 生效 |
| 桌面 | system_config 加「界面样式」Tab：外观主题（强调色/侧栏/密度）+ 登录框（尺寸/字体/圆角/品牌）+ 顶部栏（开关/快捷键）表单，「保存并生效」 |
| Web | system_config.html 加同款配置表单 |

### B. 权限桌面端修复
- **新建 `gui/views/user_permission.py`**：UserPermissionView（对齐 users.html）
  - 用户列表（账号/姓名/角色/状态）+ 新增/编辑/停用/重置密码
  - 角色列表 + 权限点矩阵
- registry `users → UserPermissionView`
- 原 SettingsView 的 DB 信息/数据统计内容 **并入 data_maintenance 视图**（数据维护页签更合适）

### C. 审计
- 已实现（Web 列表 + 桌面日志对话框），保持不动

## 三、验收
- 契约：save-ui 写回 + reload 生效；users API 覆盖
- 桌面 GUI：UserPermissionView + 样式配置 Tab 实例化
- 浏览器：样式配置页 + 权限页渲染、保存生效
- ruff 全绿 + 全量不降

## 四、交付
- v3.7.0（样式可配置 + 权限视图修复）
- 全量 612 基线不降

**确认后执行。**