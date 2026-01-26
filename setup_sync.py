#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交互式配置脚本"""

import json
import getpass
import os

CONFIG_FILE = "sync_config.json"

def main():
    print("=" * 60)
    print("Mac备忘录同步服务 - 配置向导")
    print("=" * 60)
    print()

    # 读取现有配置
    config = {
        "server_url": "http://47.109.148.176/ai/",
        "username": "",
        "password": "",
        "sync_interval": 30,
        "note_folder": "Notes"
    }

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                existing_config = json.load(f)
                config.update(existing_config)
            print("✅ 找到现有配置文件")
            print()
        except:
            pass

    # 配置服务器地址
    print(f"服务器地址 [当前: {config['server_url']}]")
    server_url = input("按回车使用默认值，或输入新地址: ").strip()
    if server_url:
        config['server_url'] = server_url
    print()

    # 配置用户名
    print(f"用户名 [当前: {config['username'] or '未设置'}]")
    username = input("请输入用户名: ").strip()
    if username:
        config['username'] = username
    print()

    # 配置密码
    print("密码")
    password = getpass.getpass("请输入密码（输入时不显示）: ")
    if password:
        config['password'] = password
    print()

    # 配置同步间隔
    print(f"同步间隔（秒） [当前: {config['sync_interval']}]")
    interval = input("按回车使用默认值，或输入新值: ").strip()
    if interval and interval.isdigit():
        config['sync_interval'] = int(interval)
    print()

    # 保存配置
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print("✅ 配置已保存到", CONFIG_FILE)
        print()
        print("配置内容：")
        print(f"  服务器: {config['server_url']}")
        print(f"  用户名: {config['username']}")
        print(f"  密码: {'*' * len(config['password'])}")
        print(f"  同步间隔: {config['sync_interval']}秒")
        print()
        print("现在可以运行 ./start_sync.sh 启动同步服务")
    except Exception as e:
        print(f"❌ 保存配置失败: {e}")

if __name__ == '__main__':
    main()
