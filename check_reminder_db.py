#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import pymysql
from datetime import datetime

# 读取数据库配置
with open('mysql_config.json', 'r') as f:
    db_config = json.load(f)

# 连接数据库
conn = pymysql.connect(
    host=db_config['host'],
    user=db_config['user'],
    password=db_config['password'],
    database=db_config['database'],
    charset='utf8mb4'
)

try:
    cursor = conn.cursor()

    # 查询用户6最近的提醒记录
    sql = """
    SELECT id, user_id, content, remind_time, is_completed, created_at
    FROM reminders
    WHERE user_id = 6
    ORDER BY created_at DESC
    LIMIT 10
    """

    cursor.execute(sql)
    results = cursor.fetchall()

    print("=" * 80)
    print("用户6最近的10条提醒记录：")
    print("=" * 80)
    print(f"{'ID':<6} {'内容':<20} {'提醒时间':<20} {'已完成':<8} {'创建时间':<20}")
    print("-" * 80)

    for row in results:
        id, user_id, content, remind_time, is_completed, created_at = row
        is_completed_str = "是" if is_completed else "否"
        print(f"{id:<6} {content:<20} {str(remind_time):<20} {is_completed_str:<8} {str(created_at):<20}")

    print("=" * 80)

    # 查询内容包含"单次2316"的提醒
    sql2 = """
    SELECT id, user_id, content, remind_time, is_completed, created_at
    FROM reminders
    WHERE user_id = 6 AND content LIKE '%单次2316%'
    """

    cursor.execute(sql2)
    results2 = cursor.fetchall()

    if results2:
        print("\n查询内容包含'单次2316'的提醒：")
        print("=" * 80)
        for row in results2:
            id, user_id, content, remind_time, is_completed, created_at = row
            is_completed_str = "是" if is_completed else "否"
            print(f"ID: {id}")
            print(f"内容: {content}")
            print(f"提醒时间: {remind_time}")
            print(f"已完成: {is_completed_str}")
            print(f"创建时间: {created_at}")
            print("-" * 80)
    else:
        print("\n未找到内容包含'单次2316'的提醒")

finally:
    cursor.close()
    conn.close()
