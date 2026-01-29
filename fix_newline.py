#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复换行符问题"""

# 读取文件
with open('command_system.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换错误的换行符
# 将 \\n 替换为 \n（在Python字符串中，\\n 是两个字符，\n 是换行符）
content = content.replace('\\\\n', '\\n')

# 写回文件
with open('command_system.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 修复完成！已将所有 \\\\n 替换为 \\n")
