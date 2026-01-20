#!/usr/bin/env python3
"""修复数据库中现有文件的category字段"""

import json
import sys

# 导入必要的模块
try:
    from mysql_manager import MySQLManager, FileManagerMySQL
except ImportError as e:
    print(f"错误：无法导入模块 - {e}")
    print("请确保在正确的目录下运行此脚本")
    sys.exit(1)

def main():
    # 连接数据库（使用默认配置文件）
    try:
        db = MySQLManager('mysql_config.json')
    except FileNotFoundError:
        print("错误：找不到 mysql_config.json 文件")
        sys.exit(1)
    except Exception as e:
        print(f"错误：无法连接数据库 - {e}")
        sys.exit(1)
    file_manager = FileManagerMySQL(db)

    # 查询所有文件
    sql = """
        SELECT id, original_name, mime_type, category
        FROM files
        ORDER BY id
    """

    files = db.query(sql)
    print(f"找到 {len(files)} 个文件记录\n")

    # 统计
    updated_count = 0
    unchanged_count = 0
    category_changes = {}

    # 更新每个文件的category
    for file in files:
        file_id = file['id']
        old_category = file['category']
        mime_type = file['mime_type']

        # 使用新的分类逻辑
        new_category = file_manager._get_category_from_mime(mime_type)

        if old_category != new_category:
            # 更新数据库
            update_sql = "UPDATE files SET category = %s WHERE id = %s"
            db.execute(update_sql, (new_category, file_id))

            # 记录变化
            change_key = f"{old_category} -> {new_category}"
            category_changes[change_key] = category_changes.get(change_key, 0) + 1

            print(f"✅ 更新文件 ID={file_id}: {file['original_name'][:40]}")
            print(f"   MIME: {mime_type}")
            print(f"   分类: {old_category} -> {new_category}\n")

            updated_count += 1
        else:
            unchanged_count += 1

    # 输出统计信息
    print("=" * 80)
    print(f"更新完成！")
    print(f"  已更新: {updated_count} 个文件")
    print(f"  未变化: {unchanged_count} 个文件")
    print(f"  总计: {len(files)} 个文件")

    if category_changes:
        print("\n分类变化统计：")
        for change, count in sorted(category_changes.items()):
            print(f"  {change}: {count} 个文件")

    # 显示最终的分类统计
    print("\n" + "=" * 80)
    print("最终分类统计：")
    sql_stats = """
        SELECT category, COUNT(*) as count
        FROM files
        GROUP BY category
        ORDER BY count DESC
    """
    stats = db.query(sql_stats)
    for stat in stats:
        print(f"  {stat['category']}: {stat['count']} 个文件")

if __name__ == '__main__':
    main()
