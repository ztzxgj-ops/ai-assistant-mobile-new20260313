#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
执行分类系统的数据库表创建和初始数据导入
"""

import json
import pymysql


def init_database():
    """初始化数据库"""
    # 读取配置
    with open('mysql_config.json', 'r') as f:
        config = json.load(f)

    # 连接数据库
    conn = pymysql.connect(**config)
    cursor = conn.cursor()

    print("📦 开始初始化分类管理系统数据库...")

    # 读取SQL文件
    with open('database_category_schema.sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # 分割SQL语句（按分号分割，但要注意函数和存储过程）
    statements = []
    current_statement = []

    for line in sql_content.split('\n'):
        line = line.strip()
        # 跳过注释和空行
        if not line or line.startswith('--'):
            continue

        current_statement.append(line)

        # 如果行以分号结尾，表示一个完整的语句
        if line.endswith(';'):
            statement = ' '.join(current_statement)
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
            if 'CREATE TABLE' in statement:
                table_name = statement.split('CREATE TABLE IF NOT EXISTS')[1].split('(')[0].strip()
                print(f"✅ 创建表: {table_name}")
            elif 'INSERT INTO' in statement:
                table_name = statement.split('INSERT INTO')[1].split('(')[0].strip()
                print(f"✅ 插入数据: {table_name}")
        except pymysql.Error as e:
            error_count += 1
            print(f"⚠️ 执行失败: {e}")
            # 如果是表已存在的错误，继续执行
            if e.args[0] != 1050:  # Table already exists
                print(f"   语句: {statement[:100]}...")

    cursor.close()
    conn.close()

    print(f"\n✅ 数据库初始化完成！")
    print(f"   成功: {success_count} 条语句")
    print(f"   失败: {error_count} 条语句")


if __name__ == '__main__':
    init_database()
