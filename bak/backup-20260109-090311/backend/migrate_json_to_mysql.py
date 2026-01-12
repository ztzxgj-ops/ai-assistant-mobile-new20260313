#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
将JSON数据迁移到MySQL数据库
"""

import json
import os
from datetime import datetime
from mysql_manager import MySQLManager

def load_json_file(filename):
    """加载JSON文件"""
    if not os.path.exists(filename):
        print(f"⚠️  文件不存在: {filename}")
        return None

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ 加载成功: {filename} ({len(data) if isinstance(data, list) else 1} 条记录)")
        return data
    except Exception as e:
        print(f"❌ 加载失败: {filename} - {e}")
        return None

def migrate_users(db):
    """迁移用户数据"""
    print("\n" + "="*60)
    print("📦 迁移用户数据 (users.json -> users 表)")
    print("="*60)

    users = load_json_file('users.json')
    if not users:
        return {}

    user_id_map = {}  # 用户名到user_id的映射

    for user in users:
        try:
            # 检查用户是否已存在
            check_sql = "SELECT id FROM users WHERE username = %s"
            existing = db.query_one(check_sql, (user['username'],))

            if existing:
                user_id_map[user['username']] = existing['id']
                print(f"  ⏭️  用户已存在: {user['username']} (ID: {existing['id']})")
                continue

            # 插入用户（注意字段名是password_hash）
            sql = """
                INSERT INTO users (username, password_hash, phone, created_at, last_login)
                VALUES (%s, %s, %s, %s, %s)
            """
            phone = user.get('phone', '') or None  # 空字符串转为NULL
            new_id = db.execute(sql, (
                user['username'],
                user['password'],  # JSON中是password，数据库是password_hash
                phone,
                user.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                user.get('last_login')
            ))
            user_id_map[user['username']] = new_id
            print(f"  ✅ 迁移成功: {user['username']} -> ID: {new_id}")
        except Exception as e:
            print(f"  ❌ 迁移失败: {user.get('username', 'unknown')} - {e}")

    return user_id_map

def migrate_sessions(db, user_id_map):
    """迁移会话数据"""
    print("\n" + "="*60)
    print("📦 迁移会话数据 (sessions.json -> user_sessions 表)")
    print("="*60)

    sessions = load_json_file('sessions.json')
    if not sessions:
        return

    # sessions.json是list格式
    for session_data in sessions:
        try:
            username = session_data['username']
            user_id = session_data.get('user_id') or user_id_map.get(username)

            if not user_id:
                print(f"  ⚠️  跳过: 用户 {username} 不存在")
                continue

            token = session_data['token']

            # 检查会话是否已存在（注意表名是user_sessions，字段名是session_token）
            check_sql = "SELECT id FROM user_sessions WHERE session_token = %s"
            existing = db.query_one(check_sql, (token,))

            if existing:
                print(f"  ⏭️  会话已存在: {token[:20]}...")
                continue

            # 插入会话（注意表名和字段名）
            sql = """
                INSERT INTO user_sessions (user_id, session_token, expires_at, created_at)
                VALUES (%s, %s, %s, %s)
            """
            db.execute(sql, (
                user_id,
                token,
                session_data['expires_at'],
                session_data.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            ))
            print(f"  ✅ 迁移成功: {username} -> {token[:20]}...")
        except Exception as e:
            print(f"  ❌ 迁移失败: {e}")

def migrate_messages(db, user_id_map):
    """迁移聊天记录"""
    print("\n" + "="*60)
    print("📦 迁移聊天记录 (web_chat_memory.json -> messages 表)")
    print("="*60)

    messages = load_json_file('web_chat_memory.json')
    if not messages:
        return

    for msg in messages:
        try:
            user_id = msg.get('user_id')

            # 插入消息
            sql = """
                INSERT INTO messages (user_id, role, content, timestamp, tags, image_url)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            tags_json = json.dumps(msg.get('tags', []), ensure_ascii=False) if msg.get('tags') else None

            db.execute(sql, (
                user_id,
                msg.get('role', 'user'),
                msg['content'],
                msg.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                tags_json,
                msg.get('image_url')
            ))
            print(f"  ✅ 迁移消息: user_id={user_id}, role={msg.get('role')}")
        except Exception as e:
            print(f"  ❌ 迁移失败: {e}")

def migrate_reminders(db):
    """迁移提醒事项"""
    print("\n" + "="*60)
    print("📦 迁移提醒事项 (web_reminders.json -> reminders 表)")
    print("="*60)

    reminders = load_json_file('web_reminders.json')
    if not reminders:
        return

    for reminder in reminders:
        try:
            user_id = reminder.get('user_id')

            # 映射状态字段
            status_map = {'活跃': 'pending', '已完成': 'completed', '已取消': 'cancelled'}
            status = status_map.get(reminder.get('status', '活跃'), 'pending')

            # 插入提醒
            sql = """
                INSERT INTO reminders (user_id, content, remind_time, status, triggered, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            db.execute(sql, (
                user_id,
                reminder.get('message') or reminder.get('title', ''),
                reminder['remind_time'],
                status,
                1 if reminder.get('status') == '已触发' else 0,
                reminder.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            ))
            print(f"  ✅ 迁移提醒: user_id={user_id}, {reminder.get('message', '')[:30]}")
        except Exception as e:
            print(f"  ❌ 迁移失败: {e}")

def migrate_images(db):
    """迁移图片信息"""
    print("\n" + "="*60)
    print("📦 迁移图片信息 (web_images.json -> images 表)")
    print("="*60)

    images = load_json_file('web_images.json')
    if not images:
        return

    for img in images:
        try:
            user_id = img.get('user_id')

            # 插入图片
            sql = """
                INSERT INTO images (user_id, filename, original_name, file_path, description,
                                   tags, chat_id, file_size, mime_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            tags_json = json.dumps(img.get('tags', []), ensure_ascii=False) if img.get('tags') else None

            db.execute(sql, (
                user_id,
                img['filename'],
                img.get('original_name', img['filename']),
                img['file_path'],
                img.get('description', ''),
                tags_json,
                img.get('chat_id'),
                img.get('file_size'),
                img.get('mime_type'),
                img.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            ))
            print(f"  ✅ 迁移图片: user_id={user_id}, {img['filename']}")
        except Exception as e:
            print(f"  ❌ 迁移失败: {e}")

def migrate_work_plans(db):
    """迁移工作计划"""
    print("\n" + "="*60)
    print("📦 迁移工作计划 (web_work_plans.json -> work_plans 表)")
    print("="*60)

    plans = load_json_file('web_work_plans.json')
    if not plans:
        return

    for plan in plans:
        try:
            user_id = plan.get('user_id')

            # 映射状态和优先级
            status_map = {'进行中': 'in_progress', '已完成': 'completed', '待办': 'pending'}
            priority_map = {'低': 'low', '中': 'medium', '高': 'high', '紧急': 'urgent'}

            status = status_map.get(plan.get('status', '待办'), 'pending')
            priority = priority_map.get(plan.get('priority', '中'), 'medium')

            # 插入计划
            sql = """
                INSERT INTO work_plans (user_id, title, content, priority, status, due_date,
                                       tags, created_at, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            tags_json = json.dumps(plan.get('tags', []), ensure_ascii=False) if plan.get('tags') else None

            db.execute(sql, (
                user_id,
                plan['title'],
                plan.get('description', ''),
                priority,
                status,
                plan.get('deadline'),
                tags_json,
                plan.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                plan.get('completed_at')
            ))
            print(f"  ✅ 迁移计划: user_id={user_id}, {plan['title']}")
        except Exception as e:
            print(f"  ❌ 迁移失败: {e}")

def main():
    print("="*60)
    print("🚀 开始从JSON迁移数据到MySQL")
    print("="*60)

    try:
        # 连接数据库
        db = MySQLManager('mysql_config.json')

        # 按顺序迁移数据
        user_id_map = migrate_users(db)
        migrate_sessions(db, user_id_map)
        migrate_messages(db, user_id_map)
        migrate_reminders(db)
        migrate_images(db)
        migrate_work_plans(db)

        print("\n" + "="*60)
        print("🎉 数据迁移完成！")
        print("="*60)

        # 显示迁移统计
        print("\n📊 数据库统计:")
        tables = ['users', 'user_sessions', 'messages', 'reminders', 'images', 'work_plans']
        for table in tables:
            result = db.query_one(f"SELECT COUNT(*) as count FROM {table}")
            print(f"  {table}: {result['count']} 条记录")

        db.close()

    except Exception as e:
        print(f"\n❌ 迁移过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
