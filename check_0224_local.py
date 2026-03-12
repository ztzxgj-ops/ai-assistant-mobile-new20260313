#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查2月24日的本地数据"""

import sqlite3
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("🔍 检查2月24日的数据存储情况")
print("=" * 80)

USER_ID = 6
TARGET_TITLES = ['b222', '本地111', 'y222', '云端111']

# 本地数据库路径
local_db_path = Path.home() / "Library/Containers/com.wanglewang.assistant/Data/Documents/local_databases" / f"ai_assistant_local_{USER_ID}.db"

print(f"\n【本地SQLite数据库】")
print("-" * 80)
print(f"📂 路径：{local_db_path}")

if local_db_path.exists():
    print("✅ 数据库文件存在\n")

    conn = sqlite3.connect(str(local_db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 查询2月24日的数据
    cursor.execute("""
        SELECT id, title, content, status, created_at
        FROM daily_records
        WHERE created_at >= '2026-02-24'
        ORDER BY created_at DESC;
    """)

    records = cursor.fetchall()

    if records:
        print(f"📋 找到 {len(records)} 条2月24日的记录：\n")
        found = []
        for record in records:
            title = record['title']
            is_target = title in TARGET_TITLES
            marker = "✅" if is_target else "  "

            print(f"{marker} ID:{record['id']:3d} | 【{title}】")
            print(f"      状态: {record['status']}")
            print(f"      创建时间: {record['created_at']}")
            print()

            if is_target:
                found.append(title)

        if found:
            print(f"🎯 找到目标数据：{found}")
        else:
            print("⚠️ 未找到目标数据")
    else:
        print("⚠️ 2月24日没有数据")

    conn.close()
else:
    print("❌ 数据库文件不存在")

print("\n" + "=" * 80)
