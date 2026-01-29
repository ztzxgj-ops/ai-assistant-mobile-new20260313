#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复command_system.py，为'other'类别添加支持"""

# 读取文件
with open('command_system.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到需要插入的位置（在第1424行的else之后）
insert_position = 1423  # 0-indexed, 所以是1423

# 准备要插入的代码
new_code = '''
        elif self.category_code == 'other':
            # 其他类 - 用户自定义类别，使用与记录类相同的逻辑
            record_mgr = managers['record']
            category_mgr = managers['category']

            if not args:
                # 查看该子类别的记录
                subcategory_id = self._get_subcategory_id(category_mgr, user_id)
                if subcategory_id:
                    records = record_mgr.list_records(user_id, subcategory_id=subcategory_id, status='pending')
                    # ✨ 按优先级排序：紧急 > 重要 > 普通
                    records = sort_by_priority(records)
                else:
                    records = []

                if not records:
                    return {'response': f'📝 暂无{self.name}', 'is_command': True}

                response = f"未完成{self.name}（共{len(records)}个）：\\\\n\\\\n"
                for idx, record in enumerate(records, 1):
                    # ✨ 优先显示 title，如果 title 为空则显示 content
                    display_text = record.get('title') or record.get('content', '')
                    if len(display_text) > 50:
                        display_text = display_text[:50]
                    response += f"{idx}. {display_text}\\\\n"

                # ✨ 返回上下文信息，供AI系统使用
                return {
                    'response': response,
                    'is_command': True,
                    'list_data': records,  # 添加列表数据，供前端使用
                    'context': {
                        'type': 'daily_records',
                        'data': records,
                        'subcategory_name': self.name  # 添加子类别名称
                    }
                }

            # 解析参数
            args_str = ' '.join(args)

            # 完成记录
            if args_str.startswith('完成 ') or args_str.startswith('done '):
                record_nums_str = args_str.split(' ', 1)[1] if ' ' in args_str else ''

                # ✨ 支持批量完成
                record_nums = parse_batch_numbers(record_nums_str)

                if not record_nums:
                    return {'response': '❌ 请提供有效的记录序号', 'is_command': True}

                # 获取该子类别的所有未完成记录
                subcategory_id = self._get_subcategory_id(category_mgr, user_id)
                records = record_mgr.list_records(user_id, subcategory_id=subcategory_id, status='pending')
                # ✨ 按优先级排序：紧急 > 重要 > 普通
                records = sort_by_priority(records)

                # 批量完成
                completed_records = []
                failed_nums = []

                for num_str in record_nums:
                    idx = int(num_str) - 1
                    if 0 <= idx < len(records):
                        record = records[idx]
                        try:
                            record_mgr.update_record_status(record['id'], 'completed', user_id)
                            content = record['content'][:30]
                            completed_records.append(f"{num_str}. {content}")
                        except Exception as e:
                            failed_nums.append(num_str)
                            print(f"完成记录失败: {num_str}, 错误: {e}")
                    else:
                        failed_nums.append(num_str)

                # 生成响应
                if completed_records:
                    response = f"✅ 已完成 {len(completed_records)} 条记录：\\\\n\\\\n"
                    for record_info in completed_records:
                        response += f"{record_info}\\\\n"
                    if failed_nums:
                        response += f"\\\\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
                    return {'response': response, 'is_command': True}
                else:
                    return {'response': f'❌ 所有序号都无效：{", ".join(failed_nums)}', 'is_command': True}

            # 删除记录
            if args_str.startswith('删除 ') or args_str.startswith('delete '):
                record_nums_str = args_str.split(' ', 1)[1] if ' ' in args_str else ''

                # ✨ 支持批量删除
                record_nums = parse_batch_numbers(record_nums_str)

                if not record_nums:
                    return {'response': '❌ 请提供有效的记录序号', 'is_command': True}

                # 获取该子类别的所有未完成记录
                subcategory_id = self._get_subcategory_id(category_mgr, user_id)
                records = record_mgr.list_records(user_id, subcategory_id=subcategory_id, status='pending')
                # ✨ 按优先级排序：紧急 > 重要 > 普通
                records = sort_by_priority(records)

                # 批量删除（从大到小删除）
                deleted_records = []
                failed_nums = []

                sorted_nums = sorted([int(n) for n in record_nums], reverse=True)

                for num in sorted_nums:
                    idx = num - 1
                    if 0 <= idx < len(records):
                        record = records[idx]
                        try:
                            record_mgr.delete_record(record['id'], user_id)
                            content = record['content'][:30]
                            deleted_records.append(f"{num}. {content}")
                        except Exception as e:
                            failed_nums.append(str(num))
                            print(f"删除记录失败: {num}, 错误: {e}")
                    else:
                        failed_nums.append(str(num))

                # 生成响应
                if deleted_records:
                    deleted_records.reverse()
                    response = f"✅ 已删除 {len(deleted_records)} 条记录：\\\\n\\\\n"
                    for record_info in deleted_records:
                        response += f"{record_info}\\\\n"
                    if failed_nums:
                        response += f"\\\\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
                    return {'response': response, 'is_command': True}
                else:
                    return {'response': f'❌ 所有序号都无效：{", ".join(failed_nums)}', 'is_command': True}

            # 添加记录（支持批量添加）
            content = args_str
            subcategory_id = self._get_subcategory_id(category_mgr, user_id)

            # 支持用逗号、分号、换行符分隔多条记录
            records_list = re.split(r'[,，;；\\\\n]+', content)
            records_list = [r.strip() for r in records_list if r.strip()]

            if len(records_list) == 0:
                return {'response': '❌ 请提供记录内容', 'is_command': True}

            # 批量添加
            added_count = 0
            for record_content in records_list:
                try:
                    record_mgr.add_record(user_id, record_content, subcategory_id=subcategory_id)
                    added_count += 1
                except Exception as e:
                    print(f"添加记录失败: {record_content}, 错误: {e}")

            if added_count == 1:
                return {'response': f'✅ 已保存{self.name}', 'is_command': True}
            else:
                response = f'✅ 已批量添加 {added_count} 条{self.name}：\\\\n\\\\n'
                for idx, r in enumerate(records_list, 1):
                    response += f'{idx}. {r}\\\\n'
                return {'response': response, 'is_command': True}

'''

# 插入新代码
lines.insert(insert_position, new_code)

# 写回文件
with open('command_system.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ 修复完成！已为'other'类别添加支持")
print(f"在第{insert_position + 1}行之后插入了{len(new_code.split(chr(10)))}行代码")
