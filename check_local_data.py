#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查本地和云端数据存储情况"""

import sqlite3
import json
import os
from pathlib import Path

print("=" * 80)
print("🔍 检查用户'俊哥'的数据存储情况")
print("=" * 80)

# 用户ID
USER_ID = 6

# 要查找的4条数据
TARGET_TITLES = ['b222', '本地111', 'y222', '云端111', '本地2222']

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

        # 检查所有可能的表
        for table_name in ['daily_records', 'work_tasks', 'work_plans']:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            if cursor.fetchone():
                print(f"\n📋 {table_name} 表中的数据：")

                # 先查看表结构
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                col_names = [col[1] for col in columns]
                print(f"   表结构：{col_names}")

                # 查询数据
                cursor.execute(f"SELECT * FROM {table_name} ORDER BY created_at DESC LIMIT 30;")
                records = cursor.fetchall()

                if records:
                    print(f"   找到 {len(records)} 条记录：")
                    found_local = []
                    for record in records:
                        # 尝试获取title或content字段
                        title = None
                        if 'title' in col_names:
                            title = record[col_names.index('title')]
                        elif 'content' in col_names:
                            title = record[col_names.index('content')]

                        record_id = record[col_names.index('id')] if 'id' in col_names else '?'
                        created_at = record[col_names.index('created_at')] if 'created_at' in col_names else '?'

                        if title and any(target in str(title) for target in TARGET_TITLES):
                            print(f"   ✅ 【{title}】- ID:{record_id}, 创建时间:{created_at}")
                            found_local.append(title)
                        else:
                            # 只显示前50个字符
                            display_title = str(title)[:50] if title else '无标题'
                            print(f"      【{display_title}】- ID:{record_id}")

                    if found_local:
                        print(f"\n   🎯 在本地 {table_name} 表找到目标数据：{found_local}")
                else:
                    print(f"   ⚠️ {table_name} 表为空")

        conn.close()

    except Exception as e:
        print(f"   ❌ 读取本地数据库失败：{e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ 本地数据库文件不存在")

print("\n" + "=" * 80)
print("✅ 本地数据库检查完成")
print("=" * 80)
