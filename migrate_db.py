#!/usr/bin/env python3
"""
私信表迁移脚本 - 添加缺失的字段
"""
import pymysql
import json
import sys

# 读取数据库配置
try:
    with open('/var/www/ai-assistant/mysql_config.json', 'r') as f:
        config = json.load(f)
except:
    print("❌ 无法读取数据库配置文件")
    sys.exit(1)

try:
    # 连接数据库
    conn = pymysql.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        charset='utf8mb4'
    )
    cursor = conn.cursor()

    print("✅ 已连接到数据库")

    # 执行迁移
    migrations = [
        "ALTER TABLE private_messages ADD COLUMN IF NOT EXISTS message_type ENUM('text', 'image', 'file') NOT NULL DEFAULT 'text' COMMENT '消息类型' AFTER content;",
        "ALTER TABLE private_messages ADD COLUMN IF NOT EXISTS image_id INT NULL COMMENT '关联图片ID' AFTER message_type;",
        "ALTER TABLE private_messages ADD COLUMN IF NOT EXISTS file_id INT NULL COMMENT '关联文件ID' AFTER image_id;",
        "ALTER TABLE private_messages ADD COLUMN IF NOT EXISTS read_at DATETIME NULL COMMENT '阅读时间' AFTER is_read;",
    ]

    for sql in migrations:
        try:
            cursor.execute(sql)
            print(f"✅ 执行: {sql[:60]}...")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print(f"⚠️  字段已存在: {sql[:60]}...")
            else:
                print(f"❌ 错误: {e}")

    conn.commit()

    # 验证表结构
    cursor.execute("DESCRIBE private_messages;")
    print("\n📋 表结构验证:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cursor.close()
    conn.close()

    print("\n✅ 迁移完成！")

except Exception as e:
    print(f"❌ 迁移失败: {e}")
    sys.exit(1)
