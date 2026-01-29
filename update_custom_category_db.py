#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行自定义类别数据库更新脚本
"""

import json
import pymysql

def update_database():
    """更新数据库"""
    # 读取配置
    with open('mysql_config.json', 'r') as f:
        config = json.load(f)

    # 连接数据库
    conn = pymysql.connect(**config)
    cursor = conn.cursor()

    print("📦 开始更新数据库...")

    # 读取SQL文件
    with open('database_custom_category_update.sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # 分割SQL语句
    statements = []
    current_statement = []
    in_delimiter = False

    for line in sql_content.split('\n'):
        line_stripped = line.strip()

        # 处理DELIMITER命令
        if line_stripped.startswith('DELIMITER'):
            in_delimiter = not in_delimiter
            continue

        # 跳过注释和空行
        if not line_stripped or line_stripped.startswith('--'):
            continue

        current_statement.append(line)

        # 根据是否在DELIMITER块中判断语句结束
        if in_delimiter:
            if line_stripped.endswith('$$'):
                statement = '\n'.join(current_statement)
                if statement.strip():
                    statements.append(statement.replace('$$', ''))
                current_statement = []
        else:
            if line_stripped.endswith(';'):
                statement = '\n'.join(current_statement)
                if statement.strip():
                    statements.append(statement)
                current_statement = []

    # 执行每个SQL语句
    success_count = 0
    error_count = 0

    for statement in statements:
        try:
            cursor.execute(statement)
            conn.commit()
            success_count += 1

            # 打印执行的语句类型
            if 'INSERT INTO' in statement:
                print(f"✅ 插入数据: categories")
            elif 'CREATE INDEX' in statement:
                print(f"✅ 创建索引")
            elif 'CREATE TRIGGER' in statement:
                print(f"✅ 创建触发器: check_custom_category_limit")
            elif 'DROP TRIGGER' in statement:
                print(f"✅ 删除旧触发器")
        except pymysql.Error as e:
            error_count += 1
            # 忽略某些可预期的错误
            if e.args[0] == 1062:  # Duplicate entry
                print(f"⚠️ 数据已存在，跳过")
            elif e.args[0] == 1061:  # Duplicate key name
                print(f"⚠️ 索引已存在，跳过")
            elif e.args[0] == 1359:  # Trigger already exists
                print(f"⚠️ 触发器已存在，跳过")
            else:
                print(f"⚠️ 执行失败: {e}")
                print(f"   语句: {statement[:100]}...")

    cursor.close()
    conn.close()

    print(f"\n✅ 数据库更新完成！")
    print(f"   成功: {success_count} 条语句")
    print(f"   失败: {error_count} 条语句")


if __name__ == '__main__':
    update_database()
