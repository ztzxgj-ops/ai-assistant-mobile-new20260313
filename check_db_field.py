#!/usr/bin/env python3
"""
检查数据库ai_avatar_url字段是否存在
"""
import sys
sys.path.insert(0, '/Users/gj/编程/ai助理new')

from mysql_manager import MySQLManager

try:
    db = MySQLManager()

    # 查询users表结构
    with db.get_cursor() as cursor:
        cursor.execute("DESCRIBE users")
        columns = cursor.fetchall()

    print("📊 users表字段列表:\n")
    print(f"{'字段名':<25} {'类型':<20} {'允许NULL':<10} {'键':<10} {'默认值':<15}")
    print("="*90)

    ai_avatar_exists = False
    for col in columns:
        field = col[0]
        type_ = col[1]
        null = col[2]
        key = col[3]
        default = col[4]
        print(f"{field:<25} {type_:<20} {null:<10} {key:<10} {str(default):<15}")
        if field == 'ai_avatar_url':
            ai_avatar_exists = True

    print("\n" + "="*90)

    if ai_avatar_exists:
        print("✅ ai_avatar_url 字段已存在")
    else:
        print("❌ ai_avatar_url 字段不存在！")
        print("\n需要执行数据库迁移:")
        print("  mysql -u ai_assistant -p'ai_assistant_2024' ai_assistant < migrations/add_ai_avatar_url.sql")

    db.close()

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
