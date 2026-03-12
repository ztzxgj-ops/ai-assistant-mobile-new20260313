#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""彩色文本输出示例"""

# 方法1：使用ANSI转义码
class Colors:
    """ANSI颜色代码"""
    # 前景色（文字颜色）
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    # 亮色
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

    # 背景色
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'

    # 样式
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'

    # 重置
    RESET = '\033[0m'


def demo_basic_colors():
    """演示基本颜色"""
    print("\n" + "=" * 60)
    print("基本颜色演示")
    print("=" * 60)

    print(f"{Colors.RED}这是红色文字{Colors.RESET}")
    print(f"{Colors.GREEN}这是绿色文字{Colors.RESET}")
    print(f"{Colors.YELLOW}这是黄色文字{Colors.RESET}")
    print(f"{Colors.BLUE}这是蓝色文字{Colors.RESET}")
    print(f"{Colors.MAGENTA}这是品红色文字{Colors.RESET}")
    print(f"{Colors.CYAN}这是青色文字{Colors.RESET}")


def demo_bright_colors():
    """演示亮色"""
    print("\n" + "=" * 60)
    print("亮色演示")
    print("=" * 60)

    print(f"{Colors.BRIGHT_RED}这是亮红色文字{Colors.RESET}")
    print(f"{Colors.BRIGHT_GREEN}这是亮绿色文字{Colors.RESET}")
    print(f"{Colors.BRIGHT_YELLOW}这是亮黄色文字{Colors.RESET}")
    print(f"{Colors.BRIGHT_BLUE}这是亮蓝色文字{Colors.RESET}")


def demo_styles():
    """演示文字样式"""
    print("\n" + "=" * 60)
    print("文字样式演示")
    print("=" * 60)

    print(f"{Colors.BOLD}这是加粗文字{Colors.RESET}")
    print(f"{Colors.ITALIC}这是斜体文字{Colors.RESET}")
    print(f"{Colors.UNDERLINE}这是下划线文字{Colors.RESET}")
    print(f"{Colors.REVERSE}这是反色文字{Colors.RESET}")


def demo_combinations():
    """演示组合效果"""
    print("\n" + "=" * 60)
    print("组合效果演示")
    print("=" * 60)

    print(f"{Colors.RED}{Colors.BOLD}红色加粗{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.UNDERLINE}绿色下划线{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BG_YELLOW}蓝色文字黄色背景{Colors.RESET}")
    print(f"{Colors.WHITE}{Colors.BG_RED}{Colors.BOLD}白色加粗红色背景{Colors.RESET}")


def demo_practical_use():
    """演示实际应用"""
    print("\n" + "=" * 60)
    print("实际应用示例")
    print("=" * 60)

    # 成功消息
    print(f"{Colors.GREEN}✅ 操作成功{Colors.RESET}")

    # 错误消息
    print(f"{Colors.RED}❌ 操作失败{Colors.RESET}")

    # 警告消息
    print(f"{Colors.YELLOW}⚠️  警告：请注意{Colors.RESET}")

    # 信息消息
    print(f"{Colors.CYAN}ℹ️  提示信息{Colors.RESET}")

    # 重要消息
    print(f"{Colors.BOLD}{Colors.RED}🔥 重要：请立即处理{Colors.RESET}")

    # 验证码显示
    print(f"\n{Colors.BRIGHT_CYAN}{Colors.BOLD}🔑 验证码：{Colors.BRIGHT_YELLOW}123456{Colors.RESET}")


def demo_progress():
    """演示进度显示"""
    print("\n" + "=" * 60)
    print("进度显示示例")
    print("=" * 60)

    import time

    steps = [
        ("初始化系统", Colors.CYAN),
        ("加载配置", Colors.BLUE),
        ("连接数据库", Colors.GREEN),
        ("启动服务", Colors.MAGENTA),
        ("完成", Colors.BRIGHT_GREEN)
    ]

    for i, (step, color) in enumerate(steps, 1):
        print(f"{color}[{i}/{len(steps)}] {step}...{Colors.RESET}")
        time.sleep(0.5)

    print(f"\n{Colors.BRIGHT_GREEN}{Colors.BOLD}✅ 所有步骤完成！{Colors.RESET}")


if __name__ == '__main__':
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}")
    print("=" * 60)
    print("🎨 Python 彩色文本输出演示")
    print("=" * 60)
    print(Colors.RESET)

    demo_basic_colors()
    demo_bright_colors()
    demo_styles()
    demo_combinations()
    demo_practical_use()
    demo_progress()

    print("\n" + "=" * 60)
    print(f"{Colors.BRIGHT_GREEN}演示完成！{Colors.RESET}")
    print("=" * 60 + "\n")
