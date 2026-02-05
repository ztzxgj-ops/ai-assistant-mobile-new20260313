#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单清理系统类别
删除除"工作"类别外的所有系统子类别
"""

from mysql_manager import MySQLManager

def get_system_subcategories():
    """获取所有系统子类别（除工作类别外）"""
    mgr = MySQLManager()

    query = """
        SELECT
            s.id,
            s.name as subcategory_name,
            c.name as category_name,
            c.code as category_code,
            COUNT(dr.id) as record_count
        FROM subcategories s
        JOIN categories c ON s.category_id = c.id
        LEFT JOIN daily_records dr ON s.id = dr.subcategory_id
        WHERE s.user_id IS NULL  -- 系统类别
          AND c.code != 'work'   -- 排除"工作"类别
        GROUP BY s.id
        ORDER BY c.name, s.name
    """

    return mgr.query(query)

def delete_system_subcategories():
    """删除系统子类别"""
    mgr = MySQLManager()

    query = """
        DELETE FROM subcategories
        WHERE user_id IS NULL
          AND category_id != (SELECT id FROM categories WHERE code = 'work')
    """

    affected = mgr.execute(query)
    return affected

def main():
    print("=" * 70)
    print("系统类别清理工具（简化版）")
    print("=" * 70)
    print()
    print("⚠️ 此脚本将：")
    print("  1. 删除除\"工作\"类别外的所有系统子类别")
    print("  2. 现有数据的subcategory_id会变成NULL（数据不丢失）")
    print("  3. 用户需要重新创建类别并重新分类")
    print()

    # 查询要删除的系统子类别
    print("🔍 正在查找系统子类别...")
    subcategories = get_system_subcategories()

    if not subcategories:
        print("✅ 没有需要删除的系统子类别")
        return

    print(f"⚠️ 发现 {len(subcategories)} 个系统子类别：\n")

    total_records = 0
    for sub in subcategories:
        record_info = f"({sub['record_count']} 条记录)" if sub['record_count'] > 0 else "(无记录)"
        print(f"  - {sub['category_name']} > {sub['subcategory_name']} {record_info}")
        total_records += sub['record_count']

    print(f"\n⚠️ 共有 {total_records} 条记录将失去分类（subcategory_id变为NULL）")

    # 确认执行
    print("\n" + "=" * 70)
    response = input("是否继续删除？(yes/no): ").strip().lower()

    if response != 'yes':
        print("\n❌ 已取消操作")
        return

    print("\n🔧 正在删除系统子类别...\n")

    try:
        affected = delete_system_subcategories()
        print(f"✅ 删除完成！共删除 {affected} 个系统子类别")
        print()
        print("⚠️ 请重启服务以使更改生效：")
        print("   sudo supervisorctl restart ai-assistant")
        print()
        print("📝 后续步骤：")
        print("   1. 用户可以重新创建自己需要的类别")
        print("   2. 失去分类的数据可以通过查询subcategory_id=NULL找到")
        print("   3. 新用户只会看到\"工作\"类别")
    except Exception as e:
        print(f"❌ 删除失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
