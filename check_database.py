#!/usr/bin/env python3
"""
检查数据库ai_avatar_url字段是否存在
"""
import json
import mysql.connector

# 读取数据库配置
with open('mysql_config.json', 'r') as f:
    config = json.load(f)

try:
    # 连接数据库
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    # 查询users表结构
    cursor.execute("DESCRIBE users")
    columns = cursor.fetchall()

    print("📊 users表字段列表:\n")
    print(f"{'字段名':<25} {'类型':<20} {'允许NULL':<10} {'键':<10} {'默认值':<15}")
    print("="*90)

    ai_avatar_exists = False
    for col in columns:
        field, type_, null, key, default, extra = col
        print(f"{field:<25} {type_:<20} {null:<10} {key:<10} {str(default):<15}")
        if field == 'ai_avatar_url':
            ai_avatar_exists = True

    print("\n" + "="*90)

    if ai_avatar_exists:
        print("✅ ai_avatar_url 字段已存在")
    else:
        print("❌ ai_avatar_url 字段不存在！")
        print("\n需要执行数据库迁移:")
        print("  mysql -u ai_assistant -p ai_assistant < migrations/add_ai_avatar_url.sql")

    cursor.close()
    conn.close()

except mysql.connector.Error as e:
    print(f"❌ 数据库连接失败: {e}")
    print("\n请检查:")
    print("  1. MySQL服务是否运行")
    print("  2. mysql_config.json配置是否正确")
    print("  3. 数据库用户权限是否正确")
except Exception as e:
    print(f"❌ 错误: {e}")
