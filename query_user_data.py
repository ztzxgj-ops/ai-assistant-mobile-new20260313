#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查询用户数据脚本"""

import json
import pymysql

# 读取数据库配置
with open('mysql_config.json', 'r') as f:
    config = json.load(f)

# 连接数据库
conn = pymysql.connect(
    host=config['host'],
    user=config['user'],
    password=config['password'],
    database=config['database'],
    charset=config['charset']
)

try:
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # 查询用户信息
    print("=" * 60)
    print("🔍 查询用户：俊哥")
    print("=" * 60)

    cursor.execute("SELECT * FROM users WHERE username = %s", ('俊哥',))
    user = cursor.fetchone()

    if user:
        print(f"\n✅ 找到用户：")
        print(f"   ID: {user['id']}")
        print(f"   用户名: {user['username']}")
        print(f"   存储模式: {user.get('storage_mode', '未设置')}")
        print(f"   是否已选择存储模式: {user.get('storage_mode_selected', '未设置')}")

        user_id = user['id']

        # 查询该用户的待办事项
        print(f"\n📋 查询用户的待办事项：")
        print("=" * 60)

        cursor.execute("""
            SELECT id, title, content, status, priority, due_date, created_at
            FROM work_tasks
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))

        tasks = cursor.fetchall()

        if tasks:
            print(f"\n找到 {len(tasks)} 条待办事项：\n")
            for i, task in enumerate(tasks, 1):
                print(f"{i}. 【{task['title']}】")
                print(f"   ID: {task['id']}")
                print(f"   内容: {task.get('content', '无')}")
                print(f"   状态: {task['status']}")
                print(f"   优先级: {task.get('priority', '无')}")
                print(f"   截止日期: {task.get('due_date', '无')}")
                print(f"   创建时间: {task['created_at']}")
                print()
        else:
            print("   ⚠️ 该用户没有待办事项")

    else:
        print("❌ 未找到用户：俊哥")

finally:
    cursor.close()
    conn.close()
