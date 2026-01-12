#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库更新脚本 - 添加聊天背景颜色字段
"""

from mysql_manager import MySQLManager
import sys

def update_database():
    print("🚀 开始更新数据库...")
    
    try:
        db = MySQLManager()
        
        # 1. 检查 users 表是否存在 chat_background 字段
        print("正在检查 users 表结构...")
        columns = db.query("SHOW COLUMNS FROM users LIKE 'chat_background'")
        
        if not columns:
            print("正在添加 chat_background 字段...")
            sql = """
                ALTER TABLE users 
                ADD COLUMN chat_background VARCHAR(20) DEFAULT NULL COMMENT '聊天背景颜色'
            """
            db.execute(sql)
            print("✅ chat_background 字段添加成功！")
        else:
            print("ℹ️ chat_background 字段已存在，跳过添加。" )
            
        # 2. 顺便检查 avatar_url 字段（确保它存在）
        columns_avatar = db.query("SHOW COLUMNS FROM users LIKE 'avatar_url'")
        if not columns_avatar:
            print("正在补全 avatar_url 字段...")
            sql = """
                ALTER TABLE users 
                ADD COLUMN avatar_url VARCHAR(255) DEFAULT NULL COMMENT '用户头像URL'
            """
            db.execute(sql)
            print("✅ avatar_url 字段添加成功！")
        
        print("\n🎉 数据库更新完成！")
        
    except Exception as e:
        print(f"\n❌ 更新失败: {e}")
        sys.exit(1)
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    update_database()
