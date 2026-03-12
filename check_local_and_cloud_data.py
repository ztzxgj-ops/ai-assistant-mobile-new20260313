#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查本地和云端数据存储情况"""

import sqlite3
import json
import pymysql
import os
from pathlib import Path

print("=" * 80)
print("🔍 检查用户'俊哥'的数据存储情况")
print("=" * 80)

# 用户ID
USER_ID = 6

# 要查找的4条数据
TARGET_TITLES = ['b222', '本地111', 'y222', '云端111']

print(f"\n📋 目标数据：{TARGET_TITLES}")
print("=" * 80)

# ============================================
# 1. 检查本地SQLite数据库
# ============================================
print("\n【1】检查本地SQLite数据库")
print("-" * 80)

# 本地数据库路径
local_db_path = Path.home() / "Library/Containers/com.wanglewang.assistant/Data/Documents/local_databases" / f"ai_assistant_local_{USER_ID}.db"

print(f"📂 本地数据库路径：{local_db_path}")

if local_db_path.exists():
    print("✅ 本地数据库文件存在")

    try:
        conn = sqlite3.connect(str(local_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 查询所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"\n📊 数据库中的表：{[t[0] for t in tables]}")

        # 查询work_tasks表
        if any(t[0] == 'work_tasks' for t in tables):
            print("\n📋 work_tasks表中的数据：")
            cursor.execute("SELECT id, title, content, status, created_at FROM work_tasks ORDER BY created_at DESC LIMIT 20;")
            local_tasks = cursor.fetchall()

            if local_tasks:
                print(f"   找到 {len(local_tasks)} 条记录：")
                found_local = []
                for task in local_tasks:
                    title = task['title']
                    if title in TARGET_TITLES:
                        print(f"   ✅ 【{title}】- ID:{task['id']}, 状态:{task['status']}, 创建时间:{task['created_at']}")
                        found_local.append(title)
                    else:
                        print(f"      【{title}】- ID:{task['id']}, 状态:{task['status']}")

                print(f"\n   🎯 在本地找到目标数据：{found_local if found_local else '无'}")
            else:
                print("   ⚠️ work_tasks表为空")
        else:
            print("   ⚠️ 未找到work_tasks表")

        conn.close()

    except Exception as e:
        print(f"   ❌ 读取本地数据库失败：{e}")
else:
    print("❌ 本地数据库文件不存在")

# ============================================
# 2. 检查云端MySQL数据库
# ============================================
print("\n" + "=" * 80)
print("【2】检查云端MySQL数据库")
print("-" * 80)
