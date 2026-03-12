#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行好友提醒功能数据库迁移
"""

import pymysql
import json

def run_migration():
    # 读取数据库配置
    with open('mysql_config.json', 'r') as f:
        config = json.load(f)

    # 连接数据库
    connection = pymysql.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        charset=config['charset']
    )

    try:
        with connection.cursor() as cursor:
            print("开始执行数据库迁移...")

            # 1. 添加 creator_id 字段
            print("\n1. 添加 creator_id 字段...")
            try:
                cursor.execute("""
                    ALTER TABLE reminders
                    ADD COLUMN creator_id INT(11) DEFAULT NULL COMMENT '提醒创建者ID（NULL表示自己创建）' AFTER user_id
                """)
                print("   ✓ creator_id 字段添加成功")
            except pymysql.err.OperationalError as e:
                if "Duplicate column name" in str(e):
                    print("   - creator_id 字段已存在，跳过")
                else:
                    raise

            # 2. 添加 is_friend_reminder 字段
            print("\n2. 添加 is_friend_reminder 字段...")
            try:
                cursor.execute("""
                    ALTER TABLE reminders
                    ADD COLUMN is_friend_reminder TINYINT(1) DEFAULT 0 COMMENT '是否为好友提醒（0=自己的，1=好友的）' AFTER creator_id
                """)
                print("   ✓ is_friend_reminder 字段添加成功")
            except pymysql.err.OperationalError as e:
                if "Duplicate column name" in str(e):
                    print("   - is_friend_reminder 字段已存在，跳过")
                else:
                    raise

            # 3. 添加 confirmed 字段
            print("\n3. 添加 confirmed 字段...")
            try:
                cursor.execute("""
                    ALTER TABLE reminders
                    ADD COLUMN confirmed TINYINT(1) DEFAULT 0 COMMENT '接收者是否已确认（仅好友提醒使用）' AFTER is_friend_reminder
                """)
                print("   ✓ confirmed 字段添加成功")
            except pymysql.err.OperationalError as e:
                if "Duplicate column name" in str(e):
                    print("   - confirmed 字段已存在，跳过")
                else:
                    raise

            # 4. 添加外键约束
            print("\n4. 添加外键约束...")
            try:
                cursor.execute("""
                    ALTER TABLE reminders
                    ADD CONSTRAINT fk_reminders_creator
                    FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE CASCADE
                """)
                print("   ✓ 外键约束添加成功")
            except pymysql.err.OperationalError as e:
                if "Duplicate key name" in str(e) or "already exists" in str(e):
                    print("   - 外键约束已存在，跳过")
                else:
                    raise

            # 5. 添加索引
            print("\n5. 添加索引...")
            indexes = [
                ("idx_creator_id", "creator_id"),
                ("idx_is_friend_reminder", "is_friend_reminder"),
                ("idx_confirmed", "confirmed")
            ]
            for idx_name, column in indexes:
                try:
                    cursor.execute(f"""
                        ALTER TABLE reminders
                        ADD INDEX {idx_name} ({column})
                    """)
                    print(f"   ✓ 索引 {idx_name} 添加成功")
                except pymysql.err.OperationalError as e:
                    if "Duplicate key name" in str(e):
                        print(f"   - 索引 {idx_name} 已存在，跳过")
                    else:
                        raise

            # 6. 更新现有数据
            print("\n6. 更新现有数据...")
            cursor.execute("""
                UPDATE reminders
                SET creator_id = user_id,
                    is_friend_reminder = 0,
                    confirmed = 1
                WHERE creator_id IS NULL
            """)
            affected_rows = cursor.rowcount
            print(f"   ✓ 更新了 {affected_rows} 条现有记录")

            # 提交事务
            connection.commit()

            # 7. 验证表结构
            print("\n7. 验证表结构...")
            cursor.execute("DESCRIBE reminders")
            columns = cursor.fetchall()
            print("\n当前 reminders 表结构：")
            for col in columns:
                print(f"   {col[0]}: {col[1]}")

            print("\n✅ 数据库迁移完成！")

    except Exception as e:
        connection.rollback()
        print(f"\n❌ 迁移失败: {e}")
        raise
    finally:
        connection.close()

if __name__ == '__main__':
    run_migration()
