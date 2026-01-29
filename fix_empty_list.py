#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为所有空列表添加add_action标记"""

import re

# 读取文件
with open('command_system.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 定义需要替换的模式和对应的替换内容
replacements = [
    # record类 - 第916行附近
    (
        r"if not records:\s+return \{'response': f'📝 暂无\{self\.name\}', 'is_command': True\}",
        """if not records:
                    return {
                        'response': f'📝 暂无{self.name}',
                        'is_command': True,
                        'empty_list': True,
                        'subcategory_name': self.name,
                        'add_action': True
                    }"""
    ),
    # work类 - 第1073行附近
    (
        r"if not tasks:\s+return \{'response': f'✅ 暂无\{self\.name\}任务', 'is_command': True\}",
        """if not tasks:
                    return {
                        'response': f'✅ 暂无{self.name}任务',
                        'is_command': True,
                        'empty_list': True,
                        'subcategory_name': self.name,
                        'add_action': True
                    }"""
    ),
    # finance类 - 第1095行附近
    (
        r"if not records:\s+return \{'response': f'💰 暂无\{self\.name\}记录', 'is_command': True\}",
        """if not records:
                    return {
                        'response': f'💰 暂无{self.name}记录',
                        'is_command': True,
                        'empty_list': True,
                        'subcategory_name': self.name,
                        'add_action': True
                    }"""
    ),
    # time类（时间规划）- 第1279行附近
    (
        r"if not schedules:\s+return \{'response': f'⏱️ 暂无\{self\.name\}', 'is_command': True\}",
        """if not schedules:
                    return {
                        'response': f'⏱️ 暂无{self.name}',
                        'is_command': True,
                        'empty_list': True,
                        'subcategory_name': self.name,
                        'add_action': True
                    }"""
    ),
]

# 执行替换
for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# 写回文件
with open('command_system.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 修复完成！已为所有空列表添加add_action标记")
