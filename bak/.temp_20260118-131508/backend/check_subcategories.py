#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查子类别命令注册情况"""

import sys
sys.path.insert(0, '.')

from category_system import CategoryManager
from command_system import get_command_router

# 获取数据库中的所有子类别（带详细信息）
category_mgr = CategoryManager()
all_categories = category_mgr.get_all_categories()

print('检查命名冲突：')
print('=' * 60)

db_subcategories_detail = []
name_count = {}

for category in all_categories:
    query = '''
        SELECT * FROM subcategories
        WHERE category_id = %s
        ORDER BY sort_order, id
    '''
    subcategories = category_mgr.query(query, (category['id'],))

    for sub in subcategories:
        sub_name = sub.get('name', '')
        cat_name = category.get('name', '')
        user_mark = '[自定义]' if sub.get('user_id') else '[系统]'

        db_subcategories_detail.append({
            'name': sub_name,
            'category': cat_name,
            'user_mark': user_mark
        })

        # 统计名称出现次数
        if sub_name not in name_count:
            name_count[sub_name] = []
        name_count[sub_name].append(f'{cat_name} {user_mark}')

# 查找重复的名称
print('\n重复的子类别名称：')
duplicates = {name: cats for name, cats in name_count.items() if len(cats) > 1}
if duplicates:
    for name, categories in duplicates.items():
        print(f'\n❌ "{name}" 出现在多个类别中:')
        for cat in categories:
            print(f'   - {cat}')
else:
    print('  无重复名称')

# 检查与主命令冲突的名称
print('\n\n与主命令冲突的子类别：')
print('=' * 60)

main_commands = ['类别', 'category', 'cat', '分类',
                 '工作', 'work', 'w', '任务', 'task',
                 '财务', 'finance', 'money', '💰',
                 '记录', 'record', 'note', '📝',
                 '账号', 'account', 'acc', '密码', 'password',
                 '提醒', 'reminder', 'remind', '⏰',
                 '计划', 'plan', 'p', '📅',
                 '帮助', 'help', 'h', '命令']

conflicts = []
for detail in db_subcategories_detail:
    if detail['name'] in main_commands:
        conflicts.append(detail)
        print(f'❌ "{detail["name"]}" 与主命令冲突 (来自: {detail["category"]} {detail["user_mark"]})')

if not conflicts:
    print('  无冲突')

# 获取实际注册的命令
router = get_command_router()
registered_commands = set(router.commands.keys())

# 找出未注册的子类别
print('\n\n未注册的子类别：')
print('=' * 60)

unregistered = []
for detail in db_subcategories_detail:
    if detail['name'] not in registered_commands:
        unregistered.append(detail)
        print(f'❌ "{detail["name"]}" 未注册 (来自: {detail["category"]} {detail["user_mark"]})')

if not unregistered:
    print('  所有子类别都已注册')

print(f'\n\n总结：')
print(f'  数据库子类别总数: {len(db_subcategories_detail)}')
print(f'  重复名称数: {len(duplicates)}')
print(f'  与主命令冲突数: {len(conflicts)}')
print(f'  未注册数: {len(unregistered)}')
print(f'  实际注册的子类别命令数: {len([cmd for cmd in registered_commands if cmd not in main_commands])}')
