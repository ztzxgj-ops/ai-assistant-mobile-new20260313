#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阿里云邮件配置向导"""

import json
import os

def setup_wizard():
    """配置向导"""
    print("=" * 60)
    print("🚀 阿里云邮件推送配置向导")
    print("=" * 60)
    print()
    print("本向导将帮助你配置阿里云邮件推送服务")
    print()

    # 读取现有配置
    config_file = 'aliyun_email_config.json'
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("✅ 找到现有配置文件")
    else:
        print("⚠️  未找到配置文件，将创建新配置")
        config = {}

    print()
    print("请按照提示输入信息（直接回车保持原值）:")
    print()

    # 1. AccessKey ID
    current_key_id = config.get('access_key_id', '')
    if current_key_id and not current_key_id.startswith('LTAI5t...'):
        display_key = current_key_id[:8] + "..." + current_key_id[-4:]
        prompt = f"AccessKey ID [当前: {display_key}]: "
    else:
        prompt = "AccessKey ID [当前: 测试模式]: "

    key_id = input(prompt).strip()
    if key_id:
        config['access_key_id'] = key_id

    # 2. AccessKey Secret
    current_secret = config.get('access_key_secret', '')
    if current_secret and '填写' not in current_secret:
        display_secret = current_secret[:4] + "..." + current_secret[-4:]
        prompt = f"AccessKey Secret [当前: {display_secret}]: "
    else:
        prompt = "AccessKey Secret [当前: 未配置]: "

    secret = input(prompt).strip()
    if secret:
        config['access_key_secret'] = secret

    # 3. 区域
    current_region = config.get('region', 'cn-hangzhou')
    region = input(f"区域 [当前: {current_region}]: ").strip()
    if region:
        config['region'] = region
    elif 'region' not in config:
        config['region'] = 'cn-hangzhou'

    # 4. 发信地址
    current_email = config.get('from_email', '')
    email = input(f"发信地址 [当前: {current_email}]: ").strip()
    if email:
        config['from_email'] = email
        config['account_name'] = email  # 通常相同

    # 5. 发件人名称
    current_alias = config.get('from_alias', 'AI个人助理')
    alias = input(f"发件人名称 [当前: {current_alias}]: ").strip()
    if alias:
        config['from_alias'] = alias
    elif 'from_alias' not in config:
        config['from_alias'] = 'AI个人助理'

    print()
    print("=" * 60)
    print("📝 配置预览")
    print("=" * 60)

    # 显示配置（隐藏敏感信息）
    for key, value in config.items():
        if key.startswith('_'):
            continue
        if 'secret' in key.lower() or 'key' in key.lower():
            if value and len(str(value)) > 10:
                display = str(value)[:4] + "..." + str(value)[-4:]
            else:
                display = "***"
        else:
            display = value
        print(f"  {key}: {display}")

    print()
    confirm = input("确认保存配置？(y/n): ").strip().lower()

    if confirm == 'y':
        # 保留模板配置
        if 'templates' not in config:
            # 从原配置文件读取模板
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    old_config = json.load(f)
                    if 'templates' in old_config:
                        config['templates'] = old_config['templates']

        # 保存配置
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print()
        print("✅ 配置已保存到:", config_file)
        print()
        print("📋 下一步:")
        print("  1. 运行检查工具: python3 check_email_config.py")
        print("  2. 测试邮件发送: python3 test_email_send.py")
        print("  3. 重启服务器使配置生效")
    else:
        print()
        print("❌ 配置未保存")

    print()


if __name__ == '__main__':
    setup_wizard()
