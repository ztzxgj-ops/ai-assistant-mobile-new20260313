# AI助理形象功能 - 紧急修复指南

## 问题诊断

根据错误信息分析：
```
设置失败: Exception: 网络错误: FormatException: Unexpected character (at character 1)
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
```

**问题根源：** 数据库字段 `ai_avatar_url` 还没有添加到服务器数据库中！

当前端调用 `/api/user/update-ai-avatar` API时：
1. 后端尝试执行 `UPDATE users SET ai_avatar_url = ...`
2. 因为字段不存在，SQL执行失败
3. Python抛出异常，返回HTML错误页面
4. 前端尝试解析JSON失败，显示错误

## 修复步骤

### 方案1：SSH连接服务器执行（推荐）

```bash
# 1. SSH连接到服务器
ssh root@47.109.148.176

# 2. 进入项目目录
cd /var/www/ai-assistant

# 3. 连接MySQL数据库
mysql -u ai_assistant -p ai_assistant
# 密码: ai_assistant_2024

# 4. 执行以下SQL命令
ALTER TABLE users
ADD COLUMN ai_avatar_url VARCHAR(500) DEFAULT NULL
COMMENT 'AI助理头像URL';

# 5. 验证字段已添加
DESCRIBE users;

# 6. 退出MySQL
exit

# 7. 重启后端服务
sudo supervisorctl restart ai-assistant

# 8. 查看服务状态
sudo supervisorctl status ai-assistant

# 9. 查看日志（如有错误）
sudo tail -f /var/log/ai-assistant-error.log
```

### 方案2：使用SQL脚本文件

```bash
# 1. SSH连接到服务器
ssh root@47.109.148.176

# 2. 进入项目目录
cd /var/www/ai-assistant

# 3. 创建SQL脚本（如果不存在）
cat > add_ai_avatar_field.sql << 'EOF'
-- 添加AI助理头像字段
USE ai_assistant;

-- 检查字段是否已存在
SET @col_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'ai_assistant'
    AND TABLE_NAME = 'users'
    AND COLUMN_NAME = 'ai_avatar_url'
);

-- 如果不存在则添加
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE users ADD COLUMN ai_avatar_url VARCHAR(500) DEFAULT NULL COMMENT "AI助理头像URL"',
    'SELECT "字段已存在" AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 显示结果
DESCRIBE users;
EOF

# 4. 执行SQL脚本
mysql -u ai_assistant -p'ai_assistant_2024' ai_assistant < add_ai_avatar_field.sql

# 5. 重启服务
sudo supervisorctl restart ai-assistant
```

### 方案3：使用Python脚本（需要pymysql）

```bash
# 1. SSH连接到服务器
ssh root@47.109.148.176

# 2. 进入项目目录
cd /var/www/ai-assistant

# 3. 确保pymysql已安装
pip3 install pymysql

# 4. 创建Python脚本
cat > add_field.py << 'EOF'
#!/usr/bin/env python3
import pymysql
import json

# 读取配置
with open('mysql_config.json', 'r') as f:
    config = json.load(f)

# 连接数据库
conn = pymysql.connect(**config)
cursor = conn.cursor()

try:
    # 检查字段是否存在
    cursor.execute("SHOW COLUMNS FROM users LIKE 'ai_avatar_url'")
    if cursor.fetchone():
        print("✅ 字段已存在")
    else:
        # 添加字段
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN ai_avatar_url VARCHAR(500) DEFAULT NULL
            COMMENT 'AI助理头像URL'
        """)
        conn.commit()
        print("✅ 字段添加成功")

    # 验证
    cursor.execute("DESCRIBE users")
    print("\n📊 users表结构:")
    for row in cursor.fetchall():
        print(row)

except Exception as e:
    print(f"❌ 错误: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()
EOF

# 5. 执行脚本
python3 add_field.py

# 6. 重启服务
sudo supervisorctl restart ai-assistant
```

## 验证修复

### 1. 检查数据库字段

```bash
mysql -u ai_assistant -p'ai_assistant_2024' ai_assistant -e "DESCRIBE users;"
```

应该能看到 `ai_avatar_url` 字段。

### 2. 测试API端点

```bash
# 获取token（先登录）
TOKEN="your_token_here"

# 测试更新AI头像
curl -X POST http://localhost:8000/api/user/update-ai-avatar \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ai_avatar_url":"https://api.dicebear.com/7.x/bottts/svg?seed=test"}'
```

应该返回：
```json
{"success": true, "message": "AI头像更新成功"}
```

### 3. 在移动应用中测试

1. 打开"设置" → "助理形象"
2. 点击任意预设头像
3. 应该显示"✅ 已设置为 xxx"
4. 返回对话页面，AI头像应该更新

## 常见问题

### Q1: 执行SQL时提示权限不足
```bash
# 使用root用户
mysql -u root -p ai_assistant
# 然后执行ALTER TABLE命令
```

### Q2: 服务重启失败
```bash
# 查看错误日志
sudo tail -100 /var/log/ai-assistant-error.log

# 手动启动测试
cd /var/www/ai-assistant
python3 assistant_web.py
```

### Q3: 字段添加成功但API仍然失败
```bash
# 检查user_manager.py是否有语法错误
python3 -m py_compile user_manager.py

# 检查assistant_web.py是否有语法错误
python3 -m py_compile assistant_web.py

# 强制重启服务
sudo supervisorctl stop ai-assistant
sudo supervisorctl start ai-assistant
```

## 后续检查清单

- [ ] 数据库字段已添加
- [ ] 后端服务已重启
- [ ] API测试成功
- [ ] 移动应用测试成功
- [ ] 预设头像选择正常
- [ ] 自定义头像上传正常
- [ ] 对话中AI头像显示正常

## 联系方式

如果遇到问题，请提供：
1. 错误日志：`sudo tail -100 /var/log/ai-assistant-error.log`
2. 服务状态：`sudo supervisorctl status ai-assistant`
3. 数据库字段：`mysql -u ai_assistant -p ai_assistant -e "DESCRIBE users;"`
