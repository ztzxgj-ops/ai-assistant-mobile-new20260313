# 🚀 AI助理系统 - 阿里云部署包

## 📦 部署包内容

本部署包包含将AI助理系统部署到阿里云服务器（47.109.148.176）所需的所有配置文件和文档。

### 目录结构

```
deploy/
├── README.md                      # 本文件 - 快速入门
├── DEPLOYMENT_GUIDE.md            # 📘 完整部署指南（必读）
├── DATABASE_SETUP.md              # 📘 数据库配置详解
├── deploy.sh                      # 🔧 一键部署脚本
├── nginx-config.conf              # ⚙️ Nginx配置模板
├── supervisor-config.conf         # ⚙️ Supervisor进程管理配置
└── database_update_avatar.sql    # 🗄️ 数据库更新脚本（用户头像）
```

---

## 🎯 快速开始

### 部署方式选择

#### 方案A：自动部署（推荐新手）
使用一键部署脚本，自动完成所有配置：

```bash
# 1. 上传文件到服务器
scp -r 202511/* root@47.109.148.176:/var/www/ai-assistant/

# 2. 登录服务器
ssh root@47.109.148.176

# 3. 执行部署脚本
cd /var/www/ai-assistant/deploy
sudo bash deploy.sh
```

#### 方案B：手动部署（推荐有经验者）
按照完整部署指南逐步配置：

1. 📖 **阅读完整部署指南**
   - 打开 `DEPLOYMENT_GUIDE.md`
   - 按照步骤1-9执行

2. 🗄️ **配置数据库**
   - 参考 `DATABASE_SETUP.md`
   - 执行 `database_schema.sql`
   - 执行 `database_update_avatar.sql`

3. ⚙️ **配置Web服务**
   - 合并 `nginx-config.conf` 到Nginx配置
   - 安装 `supervisor-config.conf`

---

## 📚 文档说明

### 1. DEPLOYMENT_GUIDE.md（主要文档）

**适用对象**：所有部署人员

**内容概要**：
- ✅ 完整的step-by-step部署流程
- ✅ 系统架构和技术栈说明
- ✅ 文件上传方法（SCP/Git/FTP）
- ✅ 数据库、应用、Nginx、Supervisor完整配置
- ✅ 服务启动和验证步骤
- ✅ 常见问题排查（7个典型问题）
- ✅ 快速命令参考

**推荐阅读顺序**：
1. 部署架构（了解系统结构）
2. 准备工作（检查环境）
3. 按步骤3-8顺序执行
4. 验证部署（确保成功）
5. 收藏"常见问题"章节备用

---

### 2. DATABASE_SETUP.md（数据库专题）

**适用对象**：需要详细了解数据库配置的人员

**内容概要**：
- ✅ MySQL/MariaDB版本要求
- ✅ 3种初始化方法（脚本/手动/导入）
- ✅ 6个数据表的详细说明
- ✅ 必需的表结构更新（avatar_url字段）
- ✅ 6步验证流程
- ✅ 7个常见数据库问题和解决方案
- ✅ 安全建议和备份脚本

**何时阅读**：
- 遇到数据库相关错误时
- 需要理解数据表结构时
- 需要手动修复数据库问题时
- 规划数据备份策略时

---

### 3. deploy.sh（自动化脚本）

**功能说明**：
- ✅ 检查系统环境（Ubuntu/Debian）
- ✅ 安装系统依赖（Python、Nginx、Supervisor、MySQL客户端）
- ✅ 安装Python依赖（pymysql）
- ✅ 创建目录结构
- ✅ 配置数据库（可选）
- ✅ 设置文件权限
- ✅ 配置Nginx（半自动，需手动确认）
- ✅ 配置Supervisor
- ✅ 检查服务状态
- ✅ 显示访问信息

**使用建议**：
- ✅ 适合全新服务器
- ⚠️ 在已有配置的服务器上使用需谨慎
- ⚠️ Nginx配置需要手动合并（避免覆盖鱼缸系统）
- ✅ 脚本有完整的错误检查和日志输出

---

### 4. nginx-config.conf（Nginx模板）

**配置说明**：
```nginx
# 智能鱼缸系统（保持不变）
location / {
    # 现有配置...
}

# AI助理系统（新增）
location /ai/ {
    proxy_pass http://127.0.0.1:8000/;
    # WebSocket支持、超时设置等...
}

# 静态文件
location /ai/uploads/ {
    alias /var/www/ai-assistant/uploads/;
}
```

**部署方法**：
- **方法1（推荐）**：手动合并到现有配置
- **方法2（谨慎）**：直接替换（会覆盖现有配置）

**关键配置项**：
- `proxy_pass` - 转发到Python应用（端口8000）
- `proxy_set_header` - 传递客户端信息
- `proxy_http_version 1.1` - WebSocket支持
- `client_max_body_size 10M` - 文件上传限制

---

### 5. supervisor-config.conf（进程管理）

**配置说明**：
```ini
[program:ai-assistant]
command=/usr/bin/python3 /var/www/ai-assistant/assistant_web.py
directory=/var/www/ai-assistant
user=www-data
autostart=true        # 开机自启
autorestart=true      # 崩溃自动重启
```

**安装位置**：`/etc/supervisor/conf.d/ai-assistant.conf`

**管理命令**：
```bash
sudo supervisorctl start ai-assistant    # 启动
sudo supervisorctl stop ai-assistant     # 停止
sudo supervisorctl restart ai-assistant  # 重启
sudo supervisorctl status ai-assistant   # 状态
```

---

### 6. database_update_avatar.sql（数据库补丁）

**作用**：为用户表添加头像字段（avatar_url）

**执行方式**：
```bash
sudo mysql -u root -p ai_assistant < database_update_avatar.sql
```

**说明**：
- 脚本会自动检测字段是否已存在
- 如果存在则跳过，避免重复执行错误
- 安全执行，不会影响现有数据

---

## 🔑 关键配置文件

在部署前，需要修改以下配置文件：

### 1. mysql_config.json
```json
{
  "host": "localhost",
  "user": "ai_assistant",
  "password": "YOUR_SECURE_PASSWORD_HERE",  // ← 修改
  "database": "ai_assistant",
  "charset": "utf8mb4"
}
```

### 2. ai_config.json
```json
{
  "model_type": "openai",
  "api_key": "sk-YOUR_API_KEY_HERE",  // ← 修改
  "model_name": "qwen-turbo",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "temperature": 0.5,
  "max_tokens": 300
}
```

---

## 🎯 部署检查清单

### 部署前检查
- [ ] 服务器可以SSH登录
- [ ] 智能鱼缸系统正常运行（http://47.109.148.176/）
- [ ] 已准备好通义千问API密钥
- [ ] 已生成强数据库密码
- [ ] 已备份现有Nginx配置

### 部署过程检查
- [ ] 文件成功上传到 `/var/www/ai-assistant/`
- [ ] MySQL数据库 `ai_assistant` 创建成功
- [ ] 7个数据表全部创建
- [ ] users表包含avatar_url字段
- [ ] mysql_config.json密码已修改
- [ ] ai_config.json API密钥已配置
- [ ] uploads目录权限设置为775
- [ ] Nginx配置已合并并测试通过
- [ ] Supervisor配置已安装

### 部署后验证
- [ ] `lsof -i :8000` 显示python3进程
- [ ] `curl http://localhost:8000/` 返回HTML
- [ ] `curl http://47.109.148.176/ai/` 返回AI助理页面
- [ ] 浏览器可以打开登录页面
- [ ] 可以成功注册新用户
- [ ] 可以成功登录
- [ ] AI对话功能正常
- [ ] 文件上传功能正常
- [ ] 智能鱼缸系统仍然可以访问（无影响）

---

## ⚠️ 重要提醒

### 安全注意事项
1. **修改默认密码**
   - MySQL密码不要使用 `ai_assistant_2024`
   - 使用强密码：大小写+数字+特殊字符，至少16位

2. **保护配置文件**
   ```bash
   sudo chmod 600 /var/www/ai-assistant/*_config.json
   sudo chown www-data:www-data /var/www/ai-assistant/*_config.json
   ```

3. **配置HTTPS**（生产环境必须）
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d 47.109.148.176
   ```

### 性能注意事项
1. **MySQL连接池**
   - 系统使用单例MySQL连接
   - 高并发下可能需要优化连接池

2. **文件上传限制**
   - Nginx默认限制10MB
   - 如需调整，修改 `client_max_body_size`

3. **日志轮转**
   - 建议配置logrotate
   - 防止日志文件占满磁盘

---

## 🆘 快速故障排查

### 症状：访问 /ai/ 显示502错误

**可能原因**：
1. Python应用未启动
2. 端口8000被占用
3. 数据库连接失败

**排查步骤**：
```bash
# 1. 检查进程
sudo supervisorctl status ai-assistant

# 2. 查看错误日志
sudo tail -50 /var/log/ai-assistant-error.log

# 3. 检查端口
sudo lsof -i :8000

# 4. 手动启动测试
cd /var/www/ai-assistant
sudo -u www-data python3 assistant_web.py
```

### 症状：可以登录但AI无响应

**可能原因**：
1. ai_config.json配置错误
2. API密钥无效
3. 网络无法访问通义千问API

**排查步骤**：
```bash
# 1. 检查配置
sudo cat /var/www/ai-assistant/ai_config.json

# 2. 测试API连接
curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-turbo","messages":[{"role":"user","content":"测试"}]}'

# 3. 查看应用日志
sudo grep -i "api\|error" /var/log/ai-assistant.log
```

### 症状：智能鱼缸系统无法访问

**可能原因**：Nginx配置冲突

**解决方案**：
```bash
# 1. 恢复Nginx备份
sudo cp /etc/nginx/sites-available/default.backup.YYYYMMDD \
        /etc/nginx/sites-available/default

# 2. 手动合并AI助理配置
sudo nano /etc/nginx/sites-available/default
# 只添加 location /ai/ 部分，不修改其他配置

# 3. 测试并重载
sudo nginx -t && sudo systemctl reload nginx
```

---

## 📞 获取帮助

### 日志文件位置
- **应用日志**：`/var/log/ai-assistant.log`
- **错误日志**：`/var/log/ai-assistant-error.log`
- **Nginx访问日志**：`/var/log/nginx/ai-assistant-access.log`
- **Nginx错误日志**：`/var/log/nginx/ai-assistant-error.log`
- **MySQL日志**：`/var/log/mysql/error.log`

### 系统状态命令
```bash
# 查看所有服务状态
sudo systemctl status nginx supervisor mysql
sudo supervisorctl status

# 查看端口占用
sudo lsof -i :80
sudo lsof -i :8000
sudo lsof -i :3306

# 查看进程
ps aux | grep assistant
ps aux | grep nginx
ps aux | grep mysql

# 查看系统资源
df -h        # 磁盘空间
free -h      # 内存使用
top          # CPU使用
```

---

## 📝 版本信息

- **部署包版本**：v1.0
- **创建日期**：2025-12-10
- **目标服务器**：47.109.148.176
- **应用版本**：多用户版（支持用户头像）
- **Python版本要求**：3.6+
- **MySQL版本要求**：5.7+ / MariaDB 10.3+

---

## 📋 下一步

完成部署后，建议：

1. ✅ **功能测试**
   - 注册多个测试用户
   - 验证数据隔离
   - 测试所有核心功能

2. ✅ **安全加固**
   - 配置HTTPS
   - 设置防火墙规则
   - 定期更新系统

3. ✅ **监控配置**
   - 设置日志轮转
   - 配置数据库备份
   - 安装监控工具（可选）

4. ✅ **性能优化**
   - 根据实际使用调整MySQL配置
   - 优化Nginx缓存策略
   - 监控服务器资源使用

---

**祝部署顺利！如有问题，请参考 DEPLOYMENT_GUIDE.md 完整文档。🚀**
