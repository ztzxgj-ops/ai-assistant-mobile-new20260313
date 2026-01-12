#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MySQL数据库交互式安装脚本
"""

import subprocess
import sys
import getpass

def run_mysql_command(sql, user='root', password='', database=''):
    """执行MySQL命令"""
    cmd = ['mysql', '-u', user]
    if password:
        cmd.extend([f'-p{password}'])
    if database:
        cmd.append(database)
    cmd.extend(['-e', sql])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, '', str(e)

def main():
    print("=" * 60)
    print("🚀 MySQL数据库交互式安装")
    print("=" * 60)
    print()
    
    # 步骤1：获取root密码
    print("步骤1：连接MySQL")
    print("-" * 60)
    print("请输入MySQL root密码（如果没有设置密码，直接按回车）：")
    root_password = getpass.getpass("密码: ")
    
    # 测试连接
    print("\n正在测试连接...")
    success, stdout, stderr = run_mysql_command("SELECT 'OK' as test;", 'root', root_password)
    
    if not success:
        print("❌ 连接失败！")
        print(f"错误信息: {stderr}")
        print("\n可能的原因：")
        print("1. 密码不正确")
        print("2. MySQL服务未启动")
        print("3. root用户不存在")
        print("\n请检查后重试，或查看 数据库安装命令.txt 进行手动安装")
        return False
    
    print("✅ MySQL连接成功！")
    
    # 步骤2：创建数据库
    print("\n步骤2：创建数据库和用户")
    print("-" * 60)
    
    sql = """
    CREATE DATABASE IF NOT EXISTS ai_assistant CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """
    success, _, stderr = run_mysql_command(sql, 'root', root_password)
    if success:
        print("✅ 数据库 ai_assistant 创建成功")
    else:
        print(f"❌ 数据库创建失败: {stderr}")
        return False
    
    # 步骤3：创建用户
    sql = """
    CREATE USER IF NOT EXISTS 'ai_assistant'@'localhost' IDENTIFIED BY 'ai_assistant_2024';
    """
    success, _, stderr = run_mysql_command(sql, 'root', root_password)
    if success:
        print("✅ 用户 ai_assistant 创建成功")
    else:
        print(f"⚠️  用户可能已存在: {stderr}")
    
    # 步骤4：授权
    sql = """
    GRANT ALL PRIVILEGES ON ai_assistant.* TO 'ai_assistant'@'localhost';
    FLUSH PRIVILEGES;
    """
    success, _, stderr = run_mysql_command(sql, 'root', root_password)
    if success:
        print("✅ 权限授予成功")
    else:
        print(f"❌ 授权失败: {stderr}")
        return False
    
    # 步骤5：导入表结构
    print("\n步骤3：导入数据表结构")
    print("-" * 60)
    
    try:
        result = subprocess.run(
            ['mysql', '-u', 'ai_assistant', '-pai_assistant_2024', 'ai_assistant'],
            stdin=open('database_schema.sql', 'r'),
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ 数据表结构导入成功")
        else:
            print(f"❌ 表结构导入失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False
    
    # 步骤6：验证
    print("\n步骤4：验证安装")
    print("-" * 60)
    
    success, stdout, stderr = run_mysql_command(
        "SHOW TABLES;", 
        'ai_assistant', 
        'ai_assistant_2024', 
        'ai_assistant'
    )
    
    if success:
        print("✅ 数据表列表：")
        print(stdout)
    else:
        print(f"❌ 验证失败: {stderr}")
        return False
    
    # 步骤7：更新配置文件
    print("\n步骤5：更新配置文件")
    print("-" * 60)
    
    import json
    config = {
        "host": "localhost",
        "port": 3306,
        "user": "ai_assistant",
        "password": "ai_assistant_2024",
        "database": "ai_assistant",
        "charset": "utf8mb4",
        "autocommit": True,
        "pool_size": 5
    }
    
    with open('mysql_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    print("✅ 配置文件已更新：mysql_config.json")
    
    # 完成
    print("\n" + "=" * 60)
    print("🎉 MySQL数据库安装完成！")
    print("=" * 60)
    print("\n数据库信息：")
    print("  数据库名: ai_assistant")
    print("  用户名: ai_assistant")
    print("  密码: ai_assistant_2024")
    print("  主机: localhost")
    print("  端口: 3306")
    print("\n已创建的数据表：")
    print("  - messages (对话记录)")
    print("  - reminders (提醒事项)")
    print("  - images (图片信息)")
    print("  - work_plans (工作计划)")
    print("  - system_config (系统配置)")
    print("\n下一步：运行数据迁移")
    print("  python3 migrate_to_mysql.py")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  安装已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 安装失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)







