"""
安全清单文档
用于代码审查时核对
"""
# SQL 注入防护
## ✅ 参数化查询 100%
- 所有 SQL 查询使用 SQLAlchemy ORM 或 text() + bindparam
- 禁止字符串拼接 SQL
- 原始 SQL 必须使用 :param 绑定参数

## ✅ 输入验证
- Pydantic 模型验证所有 API 输入
- 文件上传验证 MIME、大小、扩展名
- 路径遍历防护：使用安全路径拼接

# XSS 防护
## ✅ Jinja2 autoescape
- 所有模板启用 autoescape
- 未受信数据渲染前转义
- CSP 头部配置严格

## ✅ 前端输入消毒
- Alpine.js/Vue 3 自动转义插值
- dangerouslySetInnerHTML 等危险 API 禁用
- 用户内容仅在安全上下文渲染

# CSRF 防护
## ✅ CSRF Token 双端同步
- 登录后设置 HttpOnly Cookie 存储 CSRF token
- 所有 POST/PUT/DELETE 请求需携带 X-CSRF-Token 头
- 前端自动从 Cookie 读取并附加到请求

## ✅ SameSite Cookie
- 会话 Cookie 设置 SameSite=Lax
- 敏感操作 Cookie 设置 SameSite=Strict

# 认证与授权
## ✅ JWT 签发/校验
- access_token 15min + refresh_token 7d
- 签名算法 RS256（非对称）
- Token 存储 SQLite TokenStore 表，支持撤销

## ✅ 密码策略
- passlib bcrypt 哈希（cost=12）
- 最小长度 8，含大小写/数字/特殊字符
- 登录失败锁定（5次/15min）

## ✅ 权限模型
- RBAC：角色-权限-资源三层
- 服务级权限：API 网关中间件统一拦截
- 数据级权限：学期/校区上下文自动注入

# 传输安全
## ✅ HTTPS 强制
- 生产环境强制 HTTPS
- HSTS 头部：max-age=31536000; includeSubDomains

## ✅ 安全头部
- CSP: 严格策略，仅允许自域 + CDN
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: 禁用地理位置/麦克风/摄像头

# 审计与日志
## ✅ 关键操作审计
- 所有增删改自动记录审计日志
- 含：操作人、时间、IP、表名、记录ID、动作、新旧值
- 审计日志月度分表，核心操作永久保留

## ✅ 敏感操作双人复核
- 成绩解锁、数据归档、备份恢复需二次确认
- 审计日志记录确认人

# 依赖安全
## ✅ 依赖扫描
- pip-audit 定期扫描已知漏洞
- 依赖版本锁定（requirements.txt 固定版本）
- 仅使用维护活跃、星标高的库

# 部署安全
## ✅ 最小权限原则
- 数据库用户仅必要权限
- 文件存储目录权限 750
- 进程以非 root 用户运行

## ✅ 环境变量管理
- SECRET_KEY 等敏感配置仅环境变量
- .env 文件不提交版本控制
- 生产环境使用密钥管理服务