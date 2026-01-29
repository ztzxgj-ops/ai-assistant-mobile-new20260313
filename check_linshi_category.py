#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查"临时"类别的信息"""

import json
import mysql.connector

# 读取数据库配置
with open('mysql_config.json', 'r') as f:
    config = json.load(f)

# 连接数据库
conn = mysql.connector.connect(**config)
cursor = conn.cursor(dictionary=True)

# 查询"临时"子类别
query = """
SELECT s.id, s.name, s.code, s.user_id,
       c.name as category_name, c.code as category_code
FROM subcategories s
JOIN categories c ON s.category_id = c.id
WHERE s.name = '临时'
LIMIT 5
"""

cursor.execute(query)
results = cursor.fetchall()

print("查询结果：")
for row in results:
    print(f"ID: {row['id']}")
    print(f"名称: {row['name']}")
    print(f"代码: {row['code']}")
    print(f"用户ID: {row['user_id']}")
    print(f"主类别: {row['category_name']} ({row['category_code']})")
    print("-" * 50)

cursor.close()
conn.close()
