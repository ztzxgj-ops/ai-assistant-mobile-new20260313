#!/usr/bin/env python3
"""
查看ai助理数据库所有数据
"""
import json
import mysql.connector
from datetime import datetime

# 读取数据库配置
with open('mysql_config.json', 'r') as f:
    config = json.load(f)

try:
    # 连接数据库
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor(dictionary=True)

    print("\n" + "="*100)
    print(" AI助理数据库 - 所有数据查看 ".center(100, "="))
    print("="*100 + "\n")

    tables = [
        ('users', '用户账户'),
        ('user_sessions', '会话令牌'),
        ('messages', '聊天历史'),
        ('work_plans', '工作计划'),
        ('reminders', '提醒事项'),
        ('images', '图片上传'),
        ('search_keywords', '搜索关键词')
    ]

    for table_name, table_desc in tables:
        # 获取记录数
        cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        count = cursor.fetchone()['count']

        print(f"\n📊 【{table_desc}】表 ({table_name}) - 共 {count} 条记录")
        print("-" * 100)

        if count > 0:
            # 获取所有数据
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 100")
            rows = cursor.fetchall()

            if rows:
                # 打印表头
                headers = rows[0].keys()
                header_line = "  ".join([f"{h:<20}" for h in headers])
                print(header_line)
                print("-" * 100)

                # 打印数据
                for row in rows:
                    values = []
                    for key, value in row.items():
                        if isinstance(value, datetime):
                            value = value.strftime('%Y-%m-%d %H:%M:%S')
                        elif value is None:
                            value = 'NULL'
                        else:
                            value = str(value)
                        # 截断过长的内容
                        if len(value) > 20:
                            value = value[:17] + '...'
                        values.append(f"{value:<20}")
                    print("  ".join(values))
        else:
            print("  (暂无数据)")

        print()

    cursor.close()
    conn.close()

    print("="*100)
    print(" 数据查看完成 ".center(100, "="))
    print("="*100 + "\n")

except mysql.connector.Error as e:
    print(f"❌ 数据库连接失败: {e}")
    print("\n请检查:")
    print("  1. MySQL服务是否运行")
    print("  2. mysql_config.json配置是否正确")
    print("  3. 数据库用户权限是否正确")
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
