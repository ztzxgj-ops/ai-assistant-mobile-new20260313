#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查询本地和云服务器的最后10条消息"""

import json
import pymysql
from datetime import datetime

def query_local_messages():
    """查询本地数据库最后10条消息"""
    try:
        # 读取本地数据库配置
        with open('mysql_config.json', 'r') as f:
            config = json.load(f)

        # 连接本地数据库
        conn = pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset=config['charset']
        )

        cursor = conn.cursor()

        # 查询最后10条消息
        sql = """
        SELECT id, user_id, role, content, timestamp
        FROM messages
        ORDER BY timestamp DESC
        LIMIT 10
        """

        cursor.execute(sql)
        results = cursor.fetchall()

        print("\n" + "="*80)
        print("本地数据库最后10条消息：")
        print("="*80)

        if results:
            for row in results:
                msg_id, user_id, role, content, timestamp = row
                # 限制内容长度
                content_preview = content[:200] if len(content) > 200 else content
                print(f"\nID: {msg_id} | 用户ID: {user_id} | 角色: {role}")
                print(f"时间: {timestamp}")
                print(f"内容: {content_preview}")
                if len(content) > 200:
                    print(f"... (共{len(content)}字符)")
                print("-" * 80)
        else:
            print("没有找到消息记录")

        cursor.close()
        conn.close()

        return len(results) if results else 0

    except Exception as e:
        print(f"查询本地数据库出错: {e}")
        return 0

def query_server_messages():
    """查询云服务器数据库最后10条消息"""
    try:
        # 连接云服务器数据库
        conn = pymysql.connect(
            host='47.109.148.176',
            user='ai_assistant',
            password='ai_assistant_2024',
            database='ai_assistant',
            charset='utf8mb4'
        )

        cursor = conn.cursor()

        # 查询最后10条消息
        sql = """
        SELECT id, user_id, role, content, timestamp
        FROM messages
        ORDER BY timestamp DESC
        LIMIT 10
        """

        cursor.execute(sql)
        results = cursor.fetchall()

        print("\n" + "="*80)
        print("云服务器数据库最后10条消息：")
        print("="*80)

        if results:
            for row in results:
                msg_id, user_id, role, content, timestamp = row
                # 限制内容长度
                content_preview = content[:200] if len(content) > 200 else content
                print(f"\nID: {msg_id} | 用户ID: {user_id} | 角色: {role}")
                print(f"时间: {timestamp}")
                print(f"内容: {content_preview}")
                if len(content) > 200:
                    print(f"... (共{len(content)}字符)")
                print("-" * 80)
        else:
            print("没有找到消息记录")

        cursor.close()
        conn.close()

        return len(results) if results else 0

    except Exception as e:
        print(f"查询云服务器数据库出错: {e}")
        return 0

if __name__ == '__main__':
    print("\n开始查询数据库消息...")

    local_count = query_local_messages()
    server_count = query_server_messages()

    print("\n" + "="*80)
    print(f"查询完成！本地: {local_count}条, 云服务器: {server_count}条")
    print("="*80)