#!/usr/bin/env python3
"""批量修复umbrella header文件中的import语句"""

import os
import re
from pathlib import Path

def fix_umbrella_header(file_path):
    """修复单个umbrella header文件"""
    # 从文件名提取模块名
    module_name = Path(file_path).stem.replace('-umbrella', '')

    with open(file_path, 'r') as f:
        content = f.read()

    # 统计修改数量
    count = 0

    # 替换所有双引号import为尖括号import
    def replace_import(match):
        nonlocal count
        count += 1
        header_name = match.group(1)
        return f'#import <{module_name}/{header_name}>'

    new_content = re.sub(r'#import "([^"]+)"', replace_import, content)

    if count > 0:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f'✅ 修复 {module_name}: {count} 个import语句')
        return True
    return False

def main():
    pods_dir = './ai-assistant-mobile/ios/Pods/Target Support Files'

    if not os.path.exists(pods_dir):
        print(f'错误：目录不存在 {pods_dir}')
        return

    print('开始批量修复umbrella header文件...\n')

    total_fixed = 0

    # 遍历所有umbrella header文件
    for root, dirs, files in os.walk(pods_dir):
        for file in files:
            if file.endswith('-umbrella.h'):
                file_path = os.path.join(root, file)
                if fix_umbrella_header(file_path):
                    total_fixed += 1

    print(f'\n修复完成！共修复 {total_fixed} 个文件')

if __name__ == '__main__':
    main()
