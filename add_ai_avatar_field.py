#!/usr/bin/env python3
"""
添加ai_avatar_url字段到users表
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # 导入数据库管理器
    from mysql_manager import MySQLManager

    print("🔧 开始添加 ai_avatar_url 字段到 users 表...\n")

    db = MySQLManager()

    # 检查字段是否已存在
    with db.get_cursor() as cursor:
        cursor.execute("SHOW COLUMNS FROM users LIKE 'ai_avatar_url'")
        result = cursor.fetchone()

        if result:
            print("✅ ai_avatar_url 字段已存在，无需添加")
        else:
            print("📝 字段不存在，正在添加...")

            # 添加字段
            sql = """
            ALTER TABLE users
            ADD COLUMN ai_avatar_url VARCHAR(500) DEFAULT NULL
            COMMENT 'AI助理头像URL'
            """
            cursor.execute(sql)
            db.connection.commit()

            print("✅ ai_avatar_url 字段添加成功！")

            # 验证
            cursor.execute("SHOW COLUMNS FROM users LIKE 'ai_avatar_url'")
            result = cursor.fetchone()
            if result:
                print(f"\n字段信息: {result}")
            else:
                print("\n❌ 验证失败：字段未成功添加")

    db.close()
    print("\n✅ 数据库迁移完成！")

except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("\n请确保已安装 pymysql:")
    print("  pip3 install pymysql")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

    print("\n如果遇到权限问题，请在服务器上手动执行:")
    print("  mysql -u ai_assistant -p'ai_assistant_2024' ai_assistant")
    print("  然后执行:")
    print("  ALTER TABLE users ADD COLUMN ai_avatar_url VARCHAR(500) DEFAULT NULL COMMENT 'AI助理头像URL';")
