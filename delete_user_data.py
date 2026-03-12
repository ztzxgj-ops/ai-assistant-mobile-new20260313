#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除指定用户的所有数据
"""

import json
import pymysql

def load_mysql_config():
    """加载MySQL配置"""
    with open('mysql_config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def delete_user_data(username):
    """删除指定用户的所有数据"""
    config = load_mysql_config()

    # 连接数据库
    conn = pymysql.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        charset=config['charset']
    )

    try:
        cursor = conn.cursor()

        # 1. 查询用户是否存在
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

        # 2. 统计相关数据
        print(f"\n📊 数据统计:")

        # 会话数
        cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE user_id = %s", (user_id,))
        sessions_count = cursor.fetchone()[0]
        print(f"   会话数: {sessions_count}")

        # 消息数
        cursor.execute("SELECT COUNT(*) FROM messages WHERE user_id = %s", (user_id,))
        messages_count = cursor.fetchone()[0]
        print(f"   消息数: {messages_count}")

        # 工作计划数
        cursor.execute("SELECT COUNT(*) FROM work_plans WHERE user_id = %s", (user_id,))
        plans_count = cursor.fetchone()[0]
        print(f"   工作计划数: {plans_count}")

        # 提醒数
        cursor.execute("SELECT COUNT(*) FROM reminders WHERE user_id = %s", (user_id,))
        reminders_count = cursor.fetchone()[0]
        print(f"   提醒数: {reminders_count}")

        # 图片数
        cursor.execute("SELECT COUNT(*) FROM images WHERE user_id = %s", (user_id,))
        images_count = cursor.fetchone()[0]
        print(f"   图片数: {images_count}")

        # 关键词数
        cursor.execute("SELECT COUNT(*) FROM search_keywords WHERE user_id = %s", (user_id,))
        keywords_count = cursor.fetchone()[0]
        print(f"   关键词数: {keywords_count}")

        # 3. 确认删除
        print(f"\n⚠️  即将删除用户 {username} 的所有数据")
        print(f"   由于数据库设置了 ON DELETE CASCADE，删除用户将自动删除所有相关数据")

        confirm = input("\n确认删除？(输入 'YES' 确认): ")
        if confirm != 'YES':
            print("❌ 取消删除操作")
            return

        # 4. 执行删除
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
    username = 'Gj1112221112222026@outlook.com'
    delete_user_data(username)
