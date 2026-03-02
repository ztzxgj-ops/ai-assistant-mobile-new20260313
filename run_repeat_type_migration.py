#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""执行 repeat_type 字段迁移脚本"""

import json
import pymysql
from pymysql.cursors import DictCursor

def run_migration():
    """执行数据库迁移"""

    # 读取数据库配置
    with open('mysql_config.json', 'r') as f:
        config = json.load(f)

    print("📊 连接到数据库...")
    connection = pymysql.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        charset=config['charset'],
        cursorclass=DictCursor
    )

    try:
        with connection.cursor() as cursor:
            print("🔧 开始修改 repeat_type 字段...")

            # 修改 repeat_type 字段
            sql = """
            ALTER TABLE reminders
            MODIFY COLUMN repeat_type ENUM(
                'once',
                'minutely',
                'every_5_minutes',
                'every_10_minutes',
                'every_30_minutes',
                'hourly',
                'daily',
                'weekly',
                'monthly',
                'yearly'
            ) NOT NULL DEFAULT 'once'
            COMMENT '循环类型：once-单次, minutely-每分钟, every_5_minutes-每5分钟, every_10_minutes-每10分钟, every_30_minutes-每30分钟, hourly-每小时, daily-每天, weekly-每周, monthly-每月, yearly-每年'
            """

            cursor.execute(sql)
            connection.commit()

            print("✅ repeat_type 字段修改成功！")

            # 验证修改
            print("\n📋 验证字段结构...")
            cursor.execute("DESCRIBE reminders")
            columns = cursor.fetchall()

            for col in columns:
                if col['Field'] == 'repeat_type':
                    print(f"\n字段名: {col['Field']}")
                    print(f"类型: {col['Type']}")
                    print(f"默认值: {col['Default']}")
                    print(f"注释: 已更新")
                    break

            print("\n✅ 迁移完成！现在支持以下循环类型：")
            print("  - once: 单次")
            print("  - minutely: 每分钟")
            print("  - every_5_minutes: 每5分钟")
            print("  - every_10_minutes: 每10分钟")
            print("  - every_30_minutes: 每30分钟")
            print("  - hourly: 每小时")
            print("  - daily: 每天")
            print("  - weekly: 每周")
            print("  - monthly: 每月")
            print("  - yearly: 每年")

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        connection.rollback()
    finally:
        connection.close()
        print("\n🔌 数据库连接已关闭")

if __name__ == '__main__':
    run_migration()
