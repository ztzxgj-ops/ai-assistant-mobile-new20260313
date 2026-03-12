#!/bin/bash
# 查询云服务器上的所有用户

SERVER_IP="47.109.148.176"
SERVER_USER="root"

echo "🔍 查询所有用户..."

ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'

cd /var/www/ai-assistant

cat > /tmp/list_users.py << 'ENDPYTHON'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import pymysql

def load_mysql_config():
    with open('/var/www/ai-assistant/mysql_config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def list_users():
    config = load_mysql_config()

    conn = pymysql.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        charset=config['charset']
    )

    try:
        cursor = conn.cursor()

        # 查询所有用户
        cursor.execute("SELECT id, username, created_at FROM users ORDER BY id")
        users = cursor.fetchall()

        if not users:
            print("❌ 数据库中没有用户")
            return

        print(f"\n📋 数据库中的所有用户 (共 {len(users)} 个):\n")
        for user_id, username, created_at in users:
            print(f"   ID: {user_id:3d} | 用户名: {username:40s} | 创建时间: {created_at}")

    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    list_users()
ENDPYTHON

python3 /tmp/list_users.py
rm /tmp/list_users.py

ENDSSH

echo ""
echo "✅ 查询完成"