#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Personal Assistant - Mac App启动包装器
确保打包后的应用能正确找到配置文件
"""

import sys
import os
from pathlib import Path

def setup_config_directory():
    """设置配置目录，如果不存在则创建"""
    # Mac应用的配置目录
    config_dir = Path.home() / "Library" / "Application Support" / "AIAssistant"
    config_dir.mkdir(parents=True, exist_ok=True)

    # 配置文件路径
    mysql_config = config_dir / "mysql_config.json"
    ai_config = config_dir / "ai_config.json"

    # 检查配置文件是否存在，不存在则创建示例
    if not mysql_config.exists():
        mysql_example = """{
  "host": "你的云服务器IP或域名",
  "port": 3306,
  "user": "ai_assistant",
  "password": "你的数据库密码",
  "database": "ai_assistant",
  "charset": "utf8mb4"
}"""
        mysql_config.write_text(mysql_example, encoding='utf-8')
        print(f"⚠️  已创建MySQL配置模板: {mysql_config}")
        print(f"   请编辑此文件填入你的云数据库信息")

    if not ai_config.exists():
        ai_example = """{
  "model_type": "openai",
  "api_key": "你的通义千问API_KEY",
  "model_name": "qwen-turbo",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "temperature": 0.5,
  "max_tokens": 300
}"""
        ai_config.write_text(ai_example, encoding='utf-8')
        print(f"⚠️  已创建AI配置模板: {ai_config}")
        print(f"   请编辑此文件填入你的通义千问API Key")

    return config_dir

def check_config_validity(config_dir):
    """检查配置文件是否已正确配置"""
    mysql_config = config_dir / "mysql_config.json"
    ai_config = config_dir / "ai_config.json"

    import json

    # 检查MySQL配置
    try:
        with open(mysql_config, 'r', encoding='utf-8') as f:
            mysql_cfg = json.load(f)
            if '你的' in mysql_cfg.get('host', '') or '你的' in mysql_cfg.get('password', ''):
                print("\n" + "="*60)
                print("❌ 错误: MySQL数据库配置未完成")
                print("="*60)
                print(f"\n请编辑配置文件: {mysql_config}")
                print("\n需要填入:")
                print("  1. 云服务器IP地址或域名 (host)")
                print("  2. 数据库密码 (password)")
                print("\n编辑完成后重新启动应用")
                print("="*60)

                # 自动打开配置文件目录
                os.system(f'open "{config_dir}"')
                sys.exit(1)
    except Exception as e:
        print(f"❌ 读取MySQL配置失败: {e}")
        sys.exit(1)

    # 检查AI配置
    try:
        with open(ai_config, 'r', encoding='utf-8') as f:
            ai_cfg = json.load(f)
            if '你的' in ai_cfg.get('api_key', ''):
                print("\n" + "="*60)
                print("⚠️  警告: AI配置未完成")
                print("="*60)
                print(f"\n请编辑配置文件: {ai_config}")
                print("\n需要填入:")
                print("  1. 通义千问API Key (api_key)")
                print("\n未配置API Key将无法使用AI聊天功能")
                print("="*60)
                # 不等待用户输入，直接继续
                import time
                time.sleep(2)  # 短暂延迟让用户看到提示
    except Exception as e:
        print(f"⚠️  读取AI配置失败: {e}")

def main():
    """主启动流程"""
    print("\n" + "="*60)
    print("AI个人助理 - 正在启动...")
    print("="*60 + "\n")

    # 1. 设置配置目录
    config_dir = setup_config_directory()

    # 2. 检查配置有效性
    check_config_validity(config_dir)

    # 3. 切换工作目录到配置目录（让assistant_web.py能找到配置）
    os.chdir(str(config_dir))

    # 4. 将配置目录添加到Python路径
    sys.path.insert(0, str(config_dir))

    # 5. 导入并运行主程序
    # 获取打包后的可执行文件所在目录
    if getattr(sys, 'frozen', False):
        # 打包后运行
        bundle_dir = Path(sys._MEIPASS)
    else:
        # 开发环境运行
        bundle_dir = Path(__file__).parent

    # 将主程序目录添加到路径
    sys.path.insert(0, str(bundle_dir))

    print("✅ 配置目录:", config_dir)
    print("✅ 程序目录:", bundle_dir)
    print("\n正在启动HTTP服务器...\n")

    # 导入并运行assistant_web
    import assistant_web

    # 如果assistant_web有main函数则调用，否则它会自动运行
    if hasattr(assistant_web, 'main'):
        assistant_web.main()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n应用已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("\n请检查配置文件和数据库连接")
        # 不等待用户输入
        import time
        time.sleep(3)
        sys.exit(1)
