#!/bin/bash
# 删除云服务器上的用户数据

SERVER_IP="47.109.148.176"
SERVER_USER="root"
USERNAME="Gj1112221112222026@outlook.com"

echo "🔍 连接到云服务器..."

# 创建远程执行的 Python 脚本
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'

cd /var/www/ai-assistant

# 创建临时删除脚本
cat > /tmp/delete_user.py << 'ENDPYTHON'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import pymysql

def load_mysql_config():
    with open('/var/www/ai-assistant/mysql_config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def delete_user_data(username):
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

        # 查询用户
        cursor.execute("SELECT id, username, created_at FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if not user:
            print(f"❌ 用户 {username} 不存在")
            return

        user_id, username, created_at = user
        print(f"\n✅ 找到用户:")
        print(f"   ID: {user_id}")
        print(f"   用户名: {username}")
        print(f"   创建时间: {created_at}")

        # 统计数据
        print(f"\n📊 数据统计:")

        cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE user_id = %s", (user_id,))
        print(f"   会话数: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM messages WHERE user_id = %s", (user_id,))
        print(f"   消息数: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM work_plans WHERE user_id = %s", (user_id,))
        print(f"   工作计划数: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM reminders WHERE user_id = %s", (user_id,))
        print(f"   提醒数: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM images WHERE user_id = %s", (user_id,))
        print(f"   图片数: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM search_keywords WHERE user_id = %s", (user_id,))
        print(f"   关键词数: {cursor.fetchone()[0]}")

        # 执行删除
        print(f"\n🗑️  正在删除用户数据...")
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()

        print(f"✅ 用户 {username} 及其所有数据已删除")

    except Exception as e:
        print(f"❌ 错误: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    username = 'Gj1112221112222026'
    delete_user_data(username)
ENDPYTHON

# 执行删除脚本
python3 /tmp/delete_user.py

# 清理临时文件
rm /tmp/delete_user.py

ENDSSH

echo ""
echo "✅ 操作完成"
