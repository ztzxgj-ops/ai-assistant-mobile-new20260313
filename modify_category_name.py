#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修改"记录"类别名称为"其他类"的脚本"""

import sys
sys.path.insert(0, '/var/www/ai-assistant')

from category_system import CategoryManager

def modify_category_name():
    """修改类别名称"""
    try:
        mgr = CategoryManager()

        # 1. 查看现有类别
        print("📋 现有类别列表：")
        print("-" * 80)
        categories = mgr.get_all_categories()
        for cat in categories:
            print(f"ID: {cat['id']}, 名称: {cat['name']}, 代码: {cat['code']}")

        print("\n" + "=" * 80 + "\n")

        # 2. 查找"记录"类别
        print("🔍 查找'记录'类别...")
        query = "SELECT id, name, code FROM categories WHERE code = %s OR name = %s"
        result = mgr.query(query, ('record', '记录'))

        if not result:
            print("❌ 未找到'记录'类别")
            return False

        record_category = result[0]
        category_id = record_category['id']
        old_name = record_category['name']

        print(f"✅ 找到'记录'类别")
        print(f"   ID: {category_id}")
        print(f"   名称: {old_name}")
        print(f"   代码: {record_category['code']}")

        print("\n" + "=" * 80 + "\n")

        # 3. 查看该类别下的子类别
        print("📋 该类别下的子类别：")
        sub_query = "SELECT id, name, code FROM subcategories WHERE category_id = %s"
        subcategories = mgr.query(sub_query, (category_id,))

        if subcategories:
            for sub in subcategories:
                print(f"   - ID: {sub['id']}, 名称: {sub['name']}, 代码: {sub['code']}")
        else:
            print("   （无子类别）")

        print("\n" + "=" * 80 + "\n")

        # 4. 查看该类别下的记录数
        print("📊 该类别下的记录数：")
        count_query = """
            SELECT COUNT(*) as count FROM daily_records
            WHERE subcategory_id IN (SELECT id FROM subcategories WHERE category_id = %s)
        """
        count_result = mgr.query(count_query, (category_id,))
        record_count = count_result[0]['count'] if count_result else 0
        print(f"   共 {record_count} 条记录")

        print("\n" + "=" * 80 + "\n")

        # 5. 修改类别名称
        print("🔄 修改类别名称为'其他类'...")
        update_query = "UPDATE categories SET name = %s WHERE id = %s"
        mgr.execute(update_query, ('其他类', category_id))
        print("✅ 修改完成！")

        print("\n" + "=" * 80 + "\n")

        # 6. 验证修改
        print("✅ 验证修改结果：")
        verify_query = "SELECT id, name, code FROM categories WHERE id = %s"
        verify_result = mgr.query(verify_query, (category_id,))

        if verify_result:
            cat = verify_result[0]
            print(f"   ID: {cat['id']}")
            print(f"   名称: {cat['name']} (原: {old_name})")
            print(f"   代码: {cat['code']}")

        print("\n" + "=" * 80 + "\n")

        print("✅ 类别名称修改成功！")
        print(f"   - 类别名称：{old_name} → 其他类")
        print(f"   - 类别代码：record（不变）")
        print(f"   - 子类别数：{len(subcategories)}（保持不变）")
        print(f"   - 记录数：{record_count}（保持不变）")

        return True

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = modify_category_name()
    sys.exit(0 if success else 1)
