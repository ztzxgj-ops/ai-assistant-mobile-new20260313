#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查数据库中的记录"""

from mysql_manager import MySQLManager
from category_system import CategoryManager, DailyRecordManager

# 初始化管理器
db = MySQLManager('mysql_config.json')
category_mgr = CategoryManager()
record_mgr = DailyRecordManager()

# 查找"忘了吗"子类别
all_categories = category_mgr.get_all_categories()
for cat in all_categories:
    query = "SELECT * FROM subcategories WHERE category_id = %s"
    subs = category_mgr.query(query, (cat['id'],))
    for sub in subs:
        if sub['name'] == '忘了吗':
            print(f"找到子类别: {sub['name']} (ID: {sub['id']})")

            # 查询该子类别下的所有记录
            records_query = """
                SELECT id, title, content, status, created_at
                FROM daily_records
                WHERE subcategory_id = %s AND status = 'pending'
                ORDER BY id DESC
            """
            records = category_mgr.query(records_query, (sub['id'],))

            print(f"\n共找到 {len(records)} 条记录：\n")
            for idx, record in enumerate(records, 1):
                print(f"{idx}. ID={record['id']}")
                print(f"   title: '{record.get('title', '')}'")
                print(f"   content: '{record.get('content', '')}'")
                print(f"   status: {record.get('status', '')}")
                print(f"   created_at: {record.get('created_at', '')}")
                print()
