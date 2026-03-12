#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""服务器端数据库迁移脚本 - 添加repeat_type字段到reminders表"""

import json
import pymysql
from pymysql.cursors import DictCursor
import sys

def load_mysql_config():
    """加载MySQL配置"""
    try:
        with open('/var/www/ai-assistant/mysql_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ 找不到mysql_config.json文件")
        return None

def migrate_reminders_table():
    """迁移reminders表，添加repeat_type字段"""
    config = load_mysql_config()
    if not config:
        return False

    try:
        # 连接数据库
        connection = pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset=config.get('charset', 'utf8mb4'),
            cursorclass=DictCursor
        )

        with connection.cursor() as cursor:
            # 检查repeat_type字段是否已存在
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'reminders'
                AND COLUMN_NAME = 'repeat_type'
            """, (config['database'],))

            if cursor.fetchone():
                print("✅ repeat_type字段已存在，无需迁移")
                return True

            # 添加repeat_type字段
            print("📝 正在添加repeat_type字段...")
            cursor.execute("""
                ALTER TABLE reminders
                ADD COLUMN repeat_type ENUM('once', 'daily', 'weekly', 'monthly', 'yearly')
                NOT NULL DEFAULT 'once'
                COMMENT '循环类型：once-单次, daily-每天, weekly-每周, monthly-每月, yearly-每年'
                AFTER remind_time
            """)

            # 为现有记录设置默认值
            cursor.execute("""
                UPDATE reminders
                SET repeat_type = 'once'
                WHERE repeat_type IS NULL
            """)

            connection.commit()
            print("✅ repeat_type字段添加成功！")

            # 显示表结构
            cursor.execute("DESCRIBE reminders")
            columns = cursor.fetchall()
            print("\n📋 更新后的reminders表结构：")
            for col in columns:
                print(f"  - {col['Field']}: {col['Type']} {col['Null']} {col['Default']}")

            return True

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == '__main__':
    print("=" * 60)
    print("数据库迁移：添加循环提醒支持")
    print("=" * 60)

    success = migrate_reminders_table()

    if success:
        print("\n✅ 迁移完成！循环提醒功能现在可以正常工作了。")
        sys.exit(0)
    else:
        print("\n❌ 迁移失败，请检查错误信息。")
        sys.exit(1)
