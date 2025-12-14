# AI助理系统 - 阿里云部署完整指南

## 📋 目录

1. [部署架构](#部署架构)
2. [准备工作](#准备工作)
3. [文件上传](#文件上传)
4. [数据库配置](#数据库配置)
5. [应用配置](#应用配置)
6. [Nginx配置](#nginx配置)
7. [Supervisor配置](#supervisor配置)
8. [启动服务](#启动服务)
9. [验证部署](#验证部署)
10. [常见问题](#常见问题)

---

## 部署架构

### 系统架构图
```
用户浏览器
    ↓
Nginx (80端口)
    ↓
    ├─→ / (根路径) → 智能鱼缸系统 (/var/www/fish-tank)
    └─→ /ai/ → AI助理系统 (proxy_pass → localhost:8000)
            ↓
    Python应用 (assistant_web.py)
            ↓
    MySQL数据库 (ai_assistant)
```

### 访问地址
- 智能鱼缸系统：`http://47.109.148.176/`
- AI助理系统：`http://47.109.148.176/ai/`

### 技术栈
- **前端**：HTML5 + CSS3 + 原生JavaScript
- **后端**：Python 3 (http.server)
- **数据库**：MySQL/MariaDB
- **反向代理**：Nginx
- **进程管理**：Supervisor

---

## 准备工作

### 1. 服务器要求
- **操作系统**：Ubuntu 18.04+ / Debian 10+ / CentOS 7+
- **内存**：最低512MB，推荐1GB+
- **磁盘**：至少2GB可用空间
- **Python**：3.6+
- **MySQL**：5.7+ 或 MariaDB 10.3+

### 2. 检查现有服务
```bash
# 检查智能鱼缸系统是否正常运行
curl http://47.109.148.176/
# 应该返回鱼缸系统的HTML

# 检查Nginx配置
sudo nginx -t

# 查看Nginx配置文件位置
sudo nginx -V 2>&1 | grep -o '\-\-conf-path=[^ ]*'
```

### 3. 准备本地文件
在本地系统中，准备以下文件和目录：
```
202511/
├── assistant_web.py          # 主程序
├── ai_chat_assistant.py      # AI助手
├── personal_assistant.py     # 数据管理
├── user_manager.py            # 用户管理
├── mysql_manager.py           # MySQL管理器
├── reminder_scheduler.py      # 提醒调度器
├── database_schema.sql        # 数据库结构
├── mysql_config.json          # MySQL配置（需要修改）
├── ai_config.json             # AI配置（需要修改）
├── uploads/                   # 上传目录（空目录）
│   ├── avatars/
│   └── images/
└── deploy/                    # 部署文件
    ├── deploy.sh
    ├── nginx-config.conf
    ├── supervisor-config.conf
    ├── DATABASE_SETUP.md
    └── database_update_avatar.sql
```

---

## 文件上传

### 方法1：使用SCP上传（推荐）
```bash
# 从本地上传整个目录到服务器
scp -r /Users/a1-6/Documents/GJ/贷款管理科/贷款政策调整/202511/* \
    root@47.109.148.176:/tmp/ai-assistant-upload/

# 登录服务器
ssh root@47.109.148.176

# 创建应用目录
sudo mkdir -p /var/www/ai-assistant
sudo mv /tmp/ai-assistant-upload/* /var/www/ai-assistant/
```

### 方法2：使用Git（如果有仓库）
```bash
# 在服务器上克隆仓库
ssh root@47.109.148.176
cd /var/www
sudo git clone <your-repo-url> ai-assistant
```

### 方法3：使用FTP/SFTP工具
使用FileZilla或WinSCP等工具，将文件上传到服务器。

### 设置目录权限
```bash
sudo chown -R www-data:www-data /var/www/ai-assistant
sudo chmod -R 755 /var/www/ai-assistant
```

---

## 数据库配置

### 步骤1：安装MySQL（如果未安装）
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y mysql-server

# CentOS
sudo yum install -y mysql-server

# 启动MySQL
sudo systemctl start mysql
sudo systemctl enable mysql
```

### 步骤2：安全初始化MySQL（首次安装）
```bash
sudo mysql_secure_installation
# 设置root密码
# 删除匿名用户：Y
# 禁止root远程登录：Y
# 删除测试数据库：Y
# 重新加载权限表：Y
```

### 步骤3：创建数据库和用户
```bash
# 登录MySQL
sudo mysql -u root -p

# 执行以下SQL命令
```

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS ai_assistant
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- 创建用户（替换密码为强密码！）
CREATE USER IF NOT EXISTS 'ai_assistant'@'localhost'
IDENTIFIED BY 'AI_assistant_Secure_2024!@#';

-- 授权
GRANT ALL PRIVILEGES ON ai_assistant.* TO 'ai_assistant'@'localhost';
FLUSH PRIVILEGES;

-- 退出
EXIT;
```

### 步骤4：导入数据库结构
```bash
# 导入主数据库结构
sudo mysql -u root -p ai_assistant < /var/www/ai-assistant/database_schema.sql

# 导入用户头像字段更新
sudo mysql -u root -p ai_assistant < /var/www/ai-assistant/deploy/database_update_avatar.sql
```

### 步骤5：验证数据库
```bash
sudo mysql -u ai_assistant -p
```

```sql
USE ai_assistant;
SHOW TABLES;
-- 应该显示：images, messages, reminders, sessions, system_config, users, work_plans

-- 验证users表包含avatar_url字段
DESC users;
EXIT;
```

### 步骤6：配置应用数据库连接
```bash
# 编辑配置文件
sudo nano /var/www/ai-assistant/mysql_config.json
```

```json
{
  "host": "localhost",
  "user": "ai_assistant",
  "password": "AI_assistant_Secure_2024!@#",
  "database": "ai_assistant",
  "charset": "utf8mb4"
}
```

```bash
# 设置安全权限（重要！）
sudo chmod 600 /var/www/ai-assistant/mysql_config.json
sudo chown www-data:www-data /var/www/ai-assistant/mysql_config.json
```

📖 **详细说明**：参考 `deploy/DATABASE_SETUP.md`

---

## 应用配置

### 配置AI模型
```bash
sudo nano /var/www/ai-assistant/ai_config.json
```

```json
{
  "model_type": "openai",
  "api_key": "sk-your-api-key-here",
  "model_name": "qwen-turbo",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "temperature": 0.5,
  "max_tokens": 300,
  "note": "通义千问配置"
}
```

```bash
# 设置安全权限
sudo chmod 600 /var/www/ai-assistant/ai_config.json
sudo chown www-data:www-data /var/www/ai-assistant/ai_config.json
```

### 安装Python依赖
```bash
# 确保Python3和pip已安装
python3 --version
pip3 --version

# 安装pymysql
sudo pip3 install pymysql

# 验证安装
python3 -c "import pymysql; print('✅ pymysql安装成功')"
```

### 创建上传目录
```bash
# 创建目录结构
sudo mkdir -p /var/www/ai-assistant/uploads/avatars
sudo mkdir -p /var/www/ai-assistant/uploads/images

# 设置权限（必须可写）
sudo chown -R www-data:www-data /var/www/ai-assistant/uploads
sudo chmod -R 775 /var/www/ai-assistant/uploads
```

---

## Nginx配置

### 步骤1：备份现有配置
```bash
# 查看当前Nginx配置
sudo cat /etc/nginx/sites-available/default

# 备份现有配置
sudo cp /etc/nginx/sites-available/default \
       /etc/nginx/sites-available/default.backup.$(date +%Y%m%d_%H%M%S)
```

### 步骤2：合并AI助理配置

**选项A - 手动合并（推荐）**

编辑现有Nginx配置：
```bash
sudo nano /etc/nginx/sites-available/default
```

在现有 `server` 块中，添加AI助理的location配置：

```nginx
server {
    listen 80;
    server_name 47.109.148.176;

    # 现有的智能鱼缸系统配置保持不变
    location / {
        # ... 现有配置 ...
    }

    # ==================== 以下是新增的AI助理配置 ====================

    # AI助理系统 (/ai/ 路径)
    location /ai/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # 禁用缓冲
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # AI助理静态文件
    location /ai/uploads/ {
        alias /var/www/ai-assistant/uploads/;
        expires 7d;
        add_header Cache-Control "public";
        autoindex off;
    }

    # 文件上传大小限制（如果不存在）
    client_max_body_size 10M;
    client_body_buffer_size 128k;
}
```

**选项B - 直接替换（仅在确认后使用）**

⚠️ 警告：这会覆盖现有配置！

```bash
# 仅在确认不会影响鱼缸系统时使用
sudo cp /var/www/ai-assistant/deploy/nginx-config.conf \
        /etc/nginx/sites-available/default
```

### 步骤3：测试和重载Nginx
```bash
# 测试配置语法
sudo nginx -t

# 如果测试通过，重载配置
sudo systemctl reload nginx

# 如果重载失败，恢复备份
# sudo cp /etc/nginx/sites-available/default.backup.YYYYMMDD_HHMMSS \
#         /etc/nginx/sites-available/default
# sudo nginx -t && sudo systemctl reload nginx
```

---

## Supervisor配置

### 步骤1：安装Supervisor
```bash
# Ubuntu/Debian
sudo apt install -y supervisor

# CentOS
sudo yum install -y supervisor

# 启动Supervisor
sudo systemctl start supervisor
sudo systemctl enable supervisor
```

### 步骤2：安装应用配置
```bash
# 复制配置文件
sudo cp /var/www/ai-assistant/deploy/supervisor-config.conf \
        /etc/supervisor/conf.d/ai-assistant.conf

# 验证配置文件内容
sudo cat /etc/supervisor/conf.d/ai-assistant.conf
```

### 步骤3：重载Supervisor配置
```bash
# 重新读取配置
sudo supervisorctl reread

# 更新进程组
sudo supervisorctl update

# 查看状态
sudo supervisorctl status

# 应该看到：
# ai-assistant    RUNNING   pid 12345, uptime 0:00:05
```

---

## 启动服务

### 自动启动（使用Supervisor）
```bash
# 启动AI助理服务
sudo supervisorctl start ai-assistant

# 查看状态
sudo supervisorctl status ai-assistant

# 查看实时日志
sudo tail -f /var/log/ai-assistant.log
```

### 手动启动（测试用）
```bash
# 如果需要手动测试
cd /var/www/ai-assistant
sudo -u www-data python3 assistant_web.py

# 按Ctrl+C停止
```

### 常用管理命令
```bash
# 重启服务
sudo supervisorctl restart ai-assistant

# 停止服务
sudo supervisorctl stop ai-assistant

# 查看日志
sudo supervisorctl tail -f ai-assistant

# 查看错误日志
sudo tail -f /var/log/ai-assistant-error.log
```

---

## 验证部署

### 1. 检查端口监听
```bash
# 检查8000端口是否被Python进程占用
sudo lsof -i :8000
# 应该显示python3进程

# 检查80端口
sudo lsof -i :80
# 应该显示nginx进程
```

### 2. 测试本地连接
```bash
# 测试Python应用直接访问
curl http://localhost:8000/

# 测试Nginx代理
curl http://localhost/ai/

# 两者应该返回相同的HTML内容
```

### 3. 测试外部访问
```bash
# 从本地电脑测试（或在浏览器打开）
curl http://47.109.148.176/ai/

# 应该返回AI助理的登录页面HTML
```

### 4. 测试API功能
```bash
# 测试注册API
curl -X POST http://47.109.148.176/ai/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "Test123456",
    "phone": "13800138000"
  }'

# 应该返回：{"success": true, "message": "注册成功"}

# 测试登录API
curl -X POST http://47.109.148.176/ai/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "Test123456"
  }'

# 应该返回包含token的JSON
```

### 5. 浏览器完整测试
1. 打开浏览器访问：`http://47.109.148.176/ai/`
2. 应该看到AI助理登录页面
3. 注册新用户
4. 登录系统
5. 测试核心功能：
   - 发送AI对话消息
   - 添加工作计划
   - 上传用户头像
   - 添加提醒事项

### 6. 查看系统日志
```bash
# 查看最近100行应用日志
sudo tail -100 /var/log/ai-assistant.log

# 查看Nginx访问日志
sudo tail -100 /var/log/nginx/ai-assistant-access.log

# 查看Nginx错误日志
sudo tail -100 /var/log/nginx/ai-assistant-error.log

# 查看MySQL慢查询日志（如果启用）
sudo tail -100 /var/log/mysql/slow-query.log
```

---

## 常见问题

### Q1: 访问 /ai/ 返回502 Bad Gateway
**原因**：Python应用未启动或端口8000未监听。

**排查步骤：**
```bash
# 1. 检查Supervisor状态
sudo supervisorctl status ai-assistant

# 2. 如果未运行，查看错误日志
sudo tail -50 /var/log/ai-assistant-error.log

# 3. 手动启动测试
cd /var/www/ai-assistant
sudo -u www-data python3 assistant_web.py
# 观察是否有错误输出

# 4. 常见错误：
# - 端口被占用：lsof -i :8000 | grep LISTEN
# - Python依赖缺失：pip3 list | grep pymysql
# - 数据库连接失败：检查mysql_config.json
```

### Q2: 页面可以访问，但API返回401 Unauthorized
**原因**：数据库连接失败或用户表未正确创建。

**解决：**
```bash
# 检查数据库连接
sudo mysql -u ai_assistant -p
USE ai_assistant;
SHOW TABLES;
SELECT COUNT(*) FROM users;
EXIT;

# 如果表不存在，重新导入
sudo mysql -u root -p ai_assistant < /var/www/ai-assistant/database_schema.sql
```

### Q3: 文件上传失败
**原因**：uploads目录权限不足。

**解决：**
```bash
# 设置正确的权限
sudo chown -R www-data:www-data /var/www/ai-assistant/uploads
sudo chmod -R 775 /var/www/ai-assistant/uploads

# 验证
ls -la /var/www/ai-assistant/uploads
```

### Q4: AI对话无响应
**原因**：AI配置错误或API密钥无效。

**排查：**
```bash
# 1. 检查配置文件
sudo cat /var/www/ai-assistant/ai_config.json

# 2. 手动测试API（使用通义千问为例）
curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-turbo",
    "messages": [{"role": "user", "content": "你好"}]
  }'

# 3. 查看应用日志中的AI相关错误
sudo grep -i "ai\|api\|qwen" /var/log/ai-assistant.log
```

### Q5: 智能鱼缸系统无法访问
**原因**：Nginx配置冲突或路径错误。

**解决：**
```bash
# 1. 恢复Nginx备份
sudo cp /etc/nginx/sites-available/default.backup.YYYYMMDD_HHMMSS \
        /etc/nginx/sites-available/default

# 2. 只添加AI助理的location块，不修改其他配置
sudo nano /etc/nginx/sites-available/default
# 手动添加 location /ai/ { ... } 配置

# 3. 测试并重载
sudo nginx -t && sudo systemctl reload nginx
```

### Q6: Supervisor进程频繁重启
**原因**：应用启动失败或运行时错误。

**排查：**
```bash
# 查看完整错误日志
sudo cat /var/log/ai-assistant-error.log

# 查看Supervisor日志
sudo supervisorctl tail -1000 ai-assistant

# 手动运行查看详细错误
cd /var/www/ai-assistant
sudo -u www-data python3 assistant_web.py
```

### Q7: 防火墙问题
如果使用了防火墙（UFW/firewalld），需要开放端口：

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status

# firewalld (CentOS)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## 后续优化建议

### 1. 配置HTTPS（强烈推荐）
```bash
# 使用Let's Encrypt免费证书
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d 47.109.148.176
```

### 2. 配置日志轮转
```bash
sudo nano /etc/logrotate.d/ai-assistant
```

```
/var/log/ai-assistant.log
/var/log/ai-assistant-error.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        supervisorctl restart ai-assistant > /dev/null
    endscript
}
```

### 3. 设置定时数据库备份
参考 `deploy/DATABASE_SETUP.md` 中的备份脚本。

### 4. 监控配置
```bash
# 安装htop监控进程
sudo apt install htop

# 安装Netdata实时监控（可选）
bash <(curl -Ss https://my-netdata.io/kickstart.sh)
```

### 5. 性能优化
```bash
# 调整MySQL配置
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

# 添加：
# max_connections = 200
# innodb_buffer_pool_size = 256M

# 重启MySQL
sudo systemctl restart mysql
```

---

## 快速命令参考

### 服务管理
```bash
# 重启所有服务
sudo systemctl restart nginx supervisor mysql

# 重启AI助理
sudo supervisorctl restart ai-assistant

# 查看所有服务状态
sudo systemctl status nginx supervisor mysql
sudo supervisorctl status
```

### 日志查看
```bash
# 实时查看应用日志
sudo tail -f /var/log/ai-assistant.log

# 实时查看错误日志
sudo tail -f /var/log/ai-assistant-error.log

# 查看Nginx访问日志
sudo tail -f /var/log/nginx/ai-assistant-access.log
```

### 故障排查
```bash
# 检查端口占用
sudo lsof -i :8000
sudo lsof -i :80

# 检查进程
ps aux | grep python3 | grep assistant
ps aux | grep nginx

# 检查磁盘空间
df -h

# 检查内存使用
free -h
```

---

## 技术支持

### 问题反馈
如果遇到部署问题，请收集以下信息：

1. **系统信息**
```bash
uname -a
cat /etc/os-release
python3 --version
mysql --version
nginx -v
```

2. **错误日志**
```bash
sudo tail -100 /var/log/ai-assistant-error.log > error_log.txt
sudo tail -100 /var/log/nginx/error.log >> error_log.txt
```

3. **服务状态**
```bash
sudo systemctl status nginx supervisor mysql > service_status.txt
sudo supervisorctl status >> service_status.txt
```

### 相关文档
- `deploy/DATABASE_SETUP.md` - 数据库详细配置
- `CLAUDE.md` - 项目开发文档
- `README.md` - 项目说明（如果存在）

---

**部署指南版本：** v1.0
**最后更新：** 2025-12-10
**服务器地址：** 47.109.148.176
**部署路径：** /var/www/ai-assistant
**访问地址：** http://47.109.148.176/ai/

**祝部署顺利！🚀**
