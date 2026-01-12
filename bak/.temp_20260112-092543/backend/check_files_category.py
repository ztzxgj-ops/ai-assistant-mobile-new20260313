#!/usr/bin/env python3
"""检查数据库中文件的category字段"""

import json
from mysql_manager import MySQLManager

# 读取数据库配置
with open('mysql_config.json', 'r') as f:
    db_config = json.load(f)

# 连接数据库
db = MySQLManager(**db_config)

# 查询所有文件
sql = """
    SELECT id, original_name, mime_type, category, user_id
    FROM files
    ORDER BY id DESC
    LIMIT 20
"""

files = db.query(sql)

print(f"数据库中共有 {len(files)} 条文件记录（最近20条）：\n")
print(f"{'ID':<5} {'文件名':<30} {'MIME类型':<40} {'分类':<15} {'用户ID':<8}")
print("-" * 110)

for file in files:
    print(f"{file['id']:<5} {file['original_name'][:28]:<30} {(file['mime_type'] or 'None')[:38]:<40} {file['category']:<15} {file['user_id']:<8}")

print("\n" + "=" * 110)
print("分类统计：")
sql_stats = """
    SELECT category, COUNT(*) as count
    FROM files
    GROUP BY category
"""
stats = db.query(sql_stats)
for stat in stats:
    print(f"  {stat['category']}: {stat['count']} 个文件")
