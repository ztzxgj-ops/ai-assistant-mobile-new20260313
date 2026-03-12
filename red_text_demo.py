#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""红色文字演示"""

# 红色文字代码
RED = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'

# 演示
print(f"{RED}🔴 你好！{RESET}")
print(f"{RED}{BOLD}🔴 这是红色加粗文字{RESET}")
print(f"{RED}🔴 你试试：你好！{RESET}")
