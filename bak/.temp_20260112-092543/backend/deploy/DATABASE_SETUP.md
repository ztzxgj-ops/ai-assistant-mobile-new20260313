# 数据库初始化指南

## 📋 目录
1. [前置要求](#前置要求)
2. [快速初始化](#快速初始化)
3. [手动初始化步骤](#手动初始化步骤)
4. [数据表结构说明](#数据表结构说明)
5. [必需的表结构更新](#必需的表结构更新)
6. [验证安装](#验证安装)
7. [常见问题](#常见问题)

---

## 前置要求

### MySQL/MariaDB 版本
- MySQL 5.7+ 或 MariaDB 10.3+
- 支持 utf8mb4 字符集
- 支持 JSON 数据类型

### 检查MySQL状态
```bash
# 检查MySQL是否运行
sudo systemctl status mysql
# 或
sudo systemctl status mariadb

# 检查版本
mysql --version
```

### 确保MySQL正在运行
```bash
sudo systemctl start mysql
# 或
sudo systemctl start mariadb
```

---

## 快速初始化

### 方法1：使用部署脚本（推荐）
```bash
cd /var/www/ai-assistant
sudo bash deploy/deploy.sh
```
部署脚本会自动完成数据库创建和初始化。

### 方法2：手动导入SQL文件
```bash
# 1. 以root身份登录MySQL
mysql -u root -p

# 2. 在MySQL命令行中执行
source /var/www/ai-assistant/database_schema.sql

# 3. 创建应用用户
CREATE USER 'ai_assistant'@'localhost' IDENTIFIED BY 'your_secure_password_here';
GRANT ALL PRIVILEGES ON ai_assistant.* TO 'ai_assistant'@'localhost';
FLUSH PRIVILEGES;
exit;
```

---

## 手动初始化步骤

### 步骤1：创建数据库
```sql
CREATE DATABASE IF NOT EXISTS ai_assistant
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

### 步骤2：创建应用用户
```sql
-- 替换 'your_secure_password' 为强密码
CREATE USER IF NOT EXISTS 'ai_assistant'@'localhost'
IDENTIFIED BY 'your_secure_password';

GRANT ALL PRIVILEGES ON ai_assistant.* TO 'ai_assistant'@'localhost';
FLUSH PRIVILEGES;
```

### 步骤3：导入表结构
```bash
mysql -u root -p ai_assistant < /var/www/ai-assistant/database_schema.sql
```

### 步骤4：更新数据库配置文件
编辑 `/var/www/ai-assistant/mysql_config.json`：
```json
{
  "host": "localhost",
  "user": "ai_assistant",
  "password": "your_secure_password",
  "database": "ai_assistant",
  "charset": "utf8mb4"
}
```

**⚠️ 安全提示：**
```bash
# 设置配置文件权限（重要！）
sudo chmod 600 /var/www/ai-assistant/mysql_config.json
sudo chown www-data:www-data /var/www/ai-assistant/mysql_config.json
```

---

## 数据表结构说明

系统包含以下6个核心数据表：

### 1. users - 用户账号表
存储用户账号信息和认证数据。

**关键字段：**
- `id` - 用户唯一标识
- `username` - 用户名（唯一）
- `password` - 密码哈希（SHA256）
- `phone` - 手机号
- `avatar_url` - 用户头像路径
- `created_at` - 注册时间
- `last_login` - 最后登录时间

### 2. sessions - 登录会话表
管理用户登录Token和会话有效期。

**关键字段：**
- `token` - 会话Token（唯一）
- `user_id` - 关联用户ID
- `expires_at` - 过期时间（7天）

### 3. messages - AI对话记录表
存储用户与AI助理的对话历史。

**关键字段：**
- `user_id` - 用户ID（数据隔离）
- `role` - user/assistant
- `content` - 消息内容
- `tags` - JSON标签数组

### 4. reminders - 提醒事项表
智能提醒系统数据。

**关键字段：**
- `user_id` - 用户ID（数据隔离）
- `content` - 提醒内容
- `remind_time` - 提醒时间
- `status` - pending/completed/cancelled
- `triggered` - 是否已触发

### 5. images - 图片管理表
用户上传的图片索引。

**关键字段：**
- `user_id` - 用户ID（数据隔离）
- `filename` - 存储文件名
- `file_path` - 文件路径
- `description` - 图片描述
- `tags` - JSON标签数组

### 6. work_plans - 工作计划表
工作计划和待办事项。

**关键字段：**
- `user_id` - 用户ID（数据隔离）
- `title` - 计划标题
- `content` - 计划内容
- `priority` - low/medium/high/urgent
- `status` - pending/in_progress/completed/cancelled
- `due_date` - 截止日期

---

## 必需的表结构更新

**⚠️ 重要：** 原始 `database_schema.sql` 文件缺少 `users` 表的 `avatar_url` 字段，需要手动添加：

### 添加 avatar_url 字段
```sql
USE ai_assistant;

-- 检查字段是否存在
SHOW COLUMNS FROM users LIKE 'avatar_url';

-- 如果不存在，执行以下语句添加
ALTER TABLE users
ADD COLUMN avatar_url VARCHAR(500) COMMENT '用户头像URL'
AFTER phone;

-- 验证添加成功
DESC users;
```

### 更新后的 users 表结构应包含：
```
+---------------+--------------+------+-----+-------------------+
| Field         | Type         | Null | Key | Default           |
+---------------+--------------+------+-----+-------------------+
| id            | int          | NO   | PRI | NULL              |
| username      | varchar(50)  | NO   | UNI | NULL              |
| password      | varchar(255) | NO   |     | NULL              |
| phone         | varchar(20)  | YES  | MUL | NULL              |
| avatar_url    | varchar(500) | YES  |     | NULL              | ← 必需
| created_at    | datetime     | NO   |     | CURRENT_TIMESTAMP |
| last_login    | datetime     | YES  |     | NULL              |
+---------------+--------------+------+-----+-------------------+
```

---

## 验证安装

### 1. 检查数据库和表
```sql
-- 登录MySQL
mysql -u ai_assistant -p

-- 切换数据库
USE ai_assistant;

-- 查看所有表
SHOW TABLES;

-- 应该看到以下6个表：
-- +-------------------------+
-- | Tables_in_ai_assistant  |
-- +-------------------------+
-- | images                  |
-- | messages                |
-- | reminders               |
-- | sessions                |
-- | system_config           |
-- | users                   |
-- | work_plans              |
-- +-------------------------+
```

### 2. 验证字符集
```sql
SHOW VARIABLES LIKE 'character_set_database';
-- 应该显示 utf8mb4

SHOW VARIABLES LIKE 'collation_database';
-- 应该显示 utf8mb4_unicode_ci
```

### 3. 检查外键约束
```sql
SELECT
    TABLE_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE REFERENCED_TABLE_NAME = 'users'
AND TABLE_SCHEMA = 'ai_assistant';

-- 应该显示所有表都正确引用了 users 表
```

### 4. 测试连接
```bash
# 测试应用能否连接数据库
cd /var/www/ai-assistant
python3 -c "
import pymysql
import json

with open('mysql_config.json') as f:
    config = json.load(f)

try:
    conn = pymysql.connect(**config)
    print('✅ 数据库连接成功')
    cursor = conn.cursor()
    cursor.execute('SELECT VERSION()')
    print(f'MySQL版本: {cursor.fetchone()[0]}')
    conn.close()
except Exception as e:
    print(f'❌ 连接失败: {e}')
"
```

### 5. 创建测试用户
```bash
# 使用API创建测试用户
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "Test123456",
    "phone": "13800138000"
  }'

# 应该返回：{"success": true, "message": "注册成功"}
```

### 6. 验证数据隔离
```sql
-- 查看测试用户
SELECT id, username, phone, created_at FROM users;

-- 查看会话表（应该为空或只有测试用户的session）
SELECT * FROM sessions;
```

---

## 常见问题

### Q1: 导入SQL文件时报错 "Unknown command"
**原因：** SQL文件编码问题或MySQL版本不兼容。

**解决：**
```bash
# 确保文件是UTF-8编码
file database_schema.sql

# 如果不是，转换编码
iconv -f GB18030 -t UTF-8 database_schema.sql > database_schema_utf8.sql

# 重新导入
mysql -u root -p ai_assistant < database_schema_utf8.sql
```

### Q2: 应用无法连接数据库
**检查清单：**
1. MySQL服务是否运行：`sudo systemctl status mysql`
2. 用户权限是否正确：检查 `mysql_config.json` 中的密码
3. 防火墙是否阻止：`sudo ufw status`
4. pymysql是否已安装：`pip3 list | grep pymysql`

**日志查看：**
```bash
# 查看应用日志
tail -f /var/log/ai-assistant.log

# 查看MySQL错误日志
sudo tail -f /var/log/mysql/error.log
```

### Q3: 报错 "Access denied for user"
**原因：** 用户权限不足或密码错误。

**解决：**
```sql
-- 重新授权
GRANT ALL PRIVILEGES ON ai_assistant.* TO 'ai_assistant'@'localhost';
FLUSH PRIVILEGES;

-- 如果仍然失败，删除并重建用户
DROP USER 'ai_assistant'@'localhost';
CREATE USER 'ai_assistant'@'localhost' IDENTIFIED BY 'new_password';
GRANT ALL PRIVILEGES ON ai_assistant.* TO 'ai_assistant'@'localhost';
FLUSH PRIVILEGES;
```

### Q4: 表不支持JSON类型
**原因：** MySQL版本过旧（5.7以下）。

**解决方案1（推荐）：** 升级MySQL到5.7+
```bash
sudo apt update
sudo apt upgrade mysql-server
```

**解决方案2（临时）：** 将JSON字段改为TEXT
```sql
ALTER TABLE work_plans MODIFY COLUMN tags TEXT;
ALTER TABLE images MODIFY COLUMN tags TEXT;
ALTER TABLE messages MODIFY COLUMN tags TEXT;
```

### Q5: 外键约束错误 "Cannot add foreign key constraint"
**原因：** 表引擎不一致或字段类型不匹配。

**解决：**
```sql
-- 检查所有表的引擎
SELECT TABLE_NAME, ENGINE
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'ai_assistant';

-- 如果有表不是InnoDB，转换它
ALTER TABLE table_name ENGINE=InnoDB;
```

### Q6: 字符集问题 - 中文乱码
**检查当前字符集：**
```sql
SHOW VARIABLES LIKE 'character%';
```

**修复字符集：**
```sql
-- 修改数据库字符集
ALTER DATABASE ai_assistant
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- 修改所有表（示例）
ALTER TABLE users CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE messages CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- ... 对所有表执行
```

### Q7: 数据库已存在，如何重置？
**⚠️ 警告：此操作会删除所有数据！**

```sql
-- 备份现有数据（如果需要）
mysqldump -u ai_assistant -p ai_assistant > backup_$(date +%Y%m%d).sql

-- 删除数据库
DROP DATABASE ai_assistant;

-- 重新创建
CREATE DATABASE ai_assistant CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 重新导入
mysql -u ai_assistant -p ai_assistant < database_schema.sql
```

---

## 安全建议

### 1. 生产环境密码强度
```bash
# 生成强密码（示例）
openssl rand -base64 32
```

### 2. 限制用户权限（可选，更安全）
```sql
-- 只授予必需的权限
REVOKE ALL PRIVILEGES ON ai_assistant.* FROM 'ai_assistant'@'localhost';

GRANT SELECT, INSERT, UPDATE, DELETE ON ai_assistant.* TO 'ai_assistant'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 启用慢查询日志（性能监控）
```sql
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2; -- 记录超过2秒的查询
```

### 4. 定期备份
```bash
# 创建每日备份脚本
cat > /usr/local/bin/backup_ai_assistant.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/ai-assistant"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

mysqldump -u ai_assistant -p'your_password' ai_assistant | gzip > "$BACKUP_DIR/ai_assistant_$DATE.sql.gz"

# 保留最近7天的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
EOF

chmod +x /usr/local/bin/backup_ai_assistant.sh

# 添加到crontab（每天凌晨2点备份）
# crontab -e
# 0 2 * * * /usr/local/bin/backup_ai_assistant.sh
```

---

## 下一步

数据库初始化完成后：

1. ✅ 更新 `mysql_config.json` 配置文件
2. ✅ 设置正确的文件权限
3. ✅ 验证数据库连接
4. ✅ 创建测试用户验证功能
5. ➡️ 继续部署应用（参考 `deploy.sh`）
6. ➡️ 配置Nginx反向代理
7. ➡️ 配置Supervisor守护进程

---

**文档版本：** v1.0
**最后更新：** 2025-12-10
**作者：** AI Assistant Deployment Team
