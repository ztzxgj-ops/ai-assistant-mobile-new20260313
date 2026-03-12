#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查阿里云邮件配置是否正确"""

import json
import os
import sys

def check_config():
    """检查配置文件"""
    config_file = 'aliyun_email_config.json'

    print("=" * 60)
    print("🔍 阿里云邮件配置检查工具")
    print("=" * 60)
    print()

    # 1. 检查配置文件是否存在
    if not os.path.exists(config_file):
        print("❌ 配置文件不存在: aliyun_email_config.json")
        return False

    print("✅ 配置文件存在")

    # 2. 读取配置
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ 配置文件读取失败: {e}")
        return False

    print("✅ 配置文件格式正确")
    print()

    # 3. 检查必需字段
    required_fields = [
        'access_key_id',
        'access_key_secret',
        'region',
        'from_email',
        'account_name'
    ]

    print("📋 检查必需字段:")
    all_ok = True
    for field in required_fields:
        if field not in config:
            print(f"  ❌ 缺少字段: {field}")
            all_ok = False
        else:
            value = config[field]
            # 检查是否是占位符
            is_placeholder = (
                not value or
                '填写' in str(value) or
                'LTAI5t...' in str(value) or
                'xxx' in str(value) or
                len(str(value)) < 10
            )

            if is_placeholder:
                print(f"  ⚠️  {field}: 使用占位符（测试模式）")
                all_ok = False
            else:
                # 隐藏敏感信息
                if 'secret' in field.lower() or 'key' in field.lower():
                    display_value = str(value)[:8] + "..." + str(value)[-4:]
                else:
                    display_value = value
                print(f"  ✅ {field}: {display_value}")

    print()

    # 4. 判断模式
    access_key_id = config.get('access_key_id', '')
    is_test_mode = (
        not access_key_id or
        access_key_id.startswith('LTAI5t...') or
        '填写' in access_key_id or
        len(access_key_id) < 10
    )

    if is_test_mode:
        print("🧪 当前模式: 测试模式")
        print("   - 验证码会打印到控制台")
        print("   - 不会发送真实邮件")
        print("   - 适合开发和测试")
        print()
        print("💡 如需发送真实邮件，请配置真实的AccessKey")
    else:
        print("🚀 当前模式: 生产模式")
        print("   - 会发送真实邮件")
        print("   - 需要确保域名已验证")
        print("   - 需要安装依赖: pip3 install aliyun-python-sdk-core aliyun-python-sdk-dm")

    print()
    print("=" * 60)

    return all_ok


if __name__ == '__main__':
    check_config()
