#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令系统基础架构
支持统一的命令解析、路由和执行
"""

import re
from abc import ABC, abstractmethod
from category_system import (
    CategoryManager, WorkTaskManager, FinanceManager,
    AccountManager, DailyRecordManager, TimeScheduleManager
)


def parse_batch_numbers(nums_str):
    """解析批量序号字符串

    支持格式：
    - "1.2.3.4"
    - "1,2,3,4"
    - "1 2 3 4"
    - "1、2、3、4"

    返回：数字列表 [1, 2, 3, 4]
    """
    return re.findall(r'\d+', nums_str)


class Command(ABC):
    """命令基类"""

    def __init__(self, name, aliases=None, description=''):
        self.name = name
        self.aliases = aliases or []
        self.description = description

    @abstractmethod
    def execute(self, args, user_id, managers):
        """执行命令"""
        pass

    def get_help(self):
        """获取命令帮助"""
        return f"{self.name}: {self.description}"


class CategoryCommand(Command):
    """类别查看命令"""

    def __init__(self):
        super().__init__(
            name='类别',
            aliases=['category', 'cat', '分类'],
            description='查看所有类别和子类别'
        )

    def execute(self, args, user_id, managers):
        """执行类别查看"""
        global _router  # 声明全局变量，用于重新加载命令路由器
        category_mgr = managers['category']

        # 如果有参数，处理不同的操作
        if args:
            args_str = ' '.join(args)

            # 添加子类别：类别 添加 记录 子类别名
            if args_str.startswith('添加 ') or args_str.startswith('add '):
                parts = args_str.split(' ', 2) if ' ' in args_str else []
                if len(parts) >= 3:
                    category_name = parts[1]
                    subcategory_name = parts[2]

                    # ✨ 检查名称是否与一级类别重名
                    all_categories = category_mgr.get_all_categories()
                    for cat in all_categories:
                        if cat['name'] == subcategory_name or subcategory_name in cat['name']:
                            return {'response': f'❌ 名称"{subcategory_name}"与一级类别"{cat["name"]}"冲突，不能添加', 'is_command': True}

                    # 查找类别
                    tree = category_mgr.get_category_tree(user_id)
                    target_category = None
                    for cat in tree:
                        if category_name in cat['name'] or category_name in cat['code']:
                            target_category = cat
                            break

                    if not target_category:
                        return {'response': f'❌ 未找到类别：{category_name}', 'is_command': True}

                    # ✨ 检查名称是否与该类别下的二级类别重名
                    for sub in target_category['subcategories']:
                        if sub['name'] == subcategory_name:
                            return {'response': f'❌ 子类别"{subcategory_name}"已存在于{target_category["name"]}中，不能重复添加', 'is_command': True}

                    # ✨ 检查名称是否与其他类别的二级类别重名
                    for cat in tree:
                        if cat['id'] != target_category['id']:
                            for sub in cat['subcategories']:
                                if sub['name'] == subcategory_name:
                                    return {'response': f'❌ 名称"{subcategory_name}"与{cat["name"]}的子类别重名，不能添加', 'is_command': True}

                    # 生成子类别代码（使用拼音或简写）
                    import hashlib
                    subcategory_code = hashlib.md5(subcategory_name.encode()).hexdigest()[:8]

                    # 添加子类别
                    try:
                        category_mgr.add_subcategory(
                            target_category['id'],
                            subcategory_name,
                            subcategory_code,
                            f'用户自定义：{subcategory_name}',
                            user_id
                        )

                        # ✨ 重新加载命令路由器以注册新的子类别命令
                        _router = None  # 清空单例，下次调用时会重新初始化

                        return {'response': f'✅ 已添加子类别：{subcategory_name} 到 {target_category["name"]}\n\n💡 现在可以直接使用"{subcategory_name}"作为快捷命令', 'is_command': True}
                    except Exception as e:
                        return {'response': f'❌ 添加失败：{str(e)}', 'is_command': True}
                else:
                    return {'response': '❌ 格式错误\n\n使用：类别 添加 类别名 子类别名', 'is_command': True}

            # 删除子类别：类别 删除 记录 子类别名
            elif args_str.startswith('删除 ') or args_str.startswith('delete '):
                parts = args_str.split(' ', 2) if ' ' in args_str else []
                if len(parts) >= 3:
                    category_name = parts[1]
                    subcategory_name = parts[2]

                    # 查找类别
                    tree = category_mgr.get_category_tree(user_id)
                    target_category = None
                    for cat in tree:
                        if category_name in cat['name'] or category_name in cat['code']:
                            target_category = cat
                            break

                    if not target_category:
                        return {'response': f'❌ 未找到类别：{category_name}', 'is_command': True}

                    # 查找子类别
                    subcategories = category_mgr.get_subcategories(target_category['id'], user_id)
                    target_sub = None
                    for sub in subcategories:
                        if sub['name'] == subcategory_name and sub.get('user_id') == user_id:
                            target_sub = sub
                            break

                    if not target_sub:
                        return {'response': f'❌ 未找到子类别：{subcategory_name}\n\n提示：只能删除自己创建的子类别', 'is_command': True}

                    # 删除子类别
                    try:
                        category_mgr.delete_subcategory(target_sub['id'], user_id)

                        # ✨ 重新加载命令路由器以移除已删除的子类别命令
                        _router = None  # 清空单例，下次调用时会重新初始化

                        return {'response': f'✅ 已删除子类别：{subcategory_name}', 'is_command': True}
                    except Exception as e:
                        return {'response': f'❌ 删除失败：{str(e)}', 'is_command': True}
                else:
                    return {'response': '❌ 格式错误\n\n使用：类别 删除 类别名 子类别名', 'is_command': True}

            # 查看特定类别
            else:
                category_name = args_str
                tree = category_mgr.get_category_tree(user_id)

                # 查找匹配的类别
                target_category = None
                for cat in tree:
                    if category_name in cat['name'] or category_name in cat['code']:
                        target_category = cat
                        break

                if target_category:
                    response = f"{target_category['icon']} {target_category['name']} ({target_category['code']})\n"
                    response += f"{target_category['description']}\n\n"

                    if target_category['subcategories']:
                        response += "子类别：\n"
                        for sub in target_category['subcategories']:
                            # 标记用户自定义的子类别
                            user_mark = " [自定义]" if sub.get('user_id') else ""
                            response += f"• {sub['name']}{user_mark} - {sub['description']}\n"
                    else:
                        response += "暂无子类别\n"

                    # ✨ 添加使用提示
                    response += "\n💡 使用方法：\n"
                    if target_category['subcategories']:
                        # 获取第一个子类别作为示例
                        example_sub = target_category['subcategories'][0]['name']
                        response += f"• 快捷记录：{example_sub} 内容\n"
                        response += f"• 查看记录：{example_sub}\n"
                        response += f"• 模糊查询：{example_sub[:1]}相关 内容\n"
                    response += f"• 添加子类别：类别 添加 {target_category['name']} 子类别名\n"
                    response += f"• 删除子类别：类别 删除 {target_category['name']} 子类别名"

                    return {'response': response, 'is_command': True}
                else:
                    return {'response': f'❌ 未找到类别：{category_name}', 'is_command': True}

        # 没有参数，显示所有类别
        tree = category_mgr.get_category_tree(user_id)

        response = "📚 系统类别结构：\n\n"
        for cat in tree:
            response += f"{cat['icon']} {cat['name']} ({cat['code']})\n"
            response += f"   {cat['description']}\n"

            if cat['subcategories']:
                response += "   子类别：\n"
                for sub in cat['subcategories']:
                    response += f"   • {sub['name']} - {sub['description']}\n"
            response += "\n"

        response += "💡 使用方法：\n"
        response += "• 查看具体类别：类别 工作\n"
        response += "• 添加子类别：类别 添加 工作 我的项目\n"
        response += "• 删除子类别：类别 删除 工作 我的项目"

        return {'response': response, 'is_command': True}


class WorkCommand(Command):
    """工作任务命令"""

    def __init__(self):
        super().__init__(
            name='工作',
            aliases=['work', 'w', '任务', 'task'],
            description='管理工作任务'
        )

    def execute(self, args, user_id, managers):
        """执行工作命令"""
        work_mgr = managers['work']
        record_mgr = managers['record']

        if not args:
            # 只查询 work_tasks 表中的任务
            tasks = work_mgr.list_tasks(user_id, status='pending')

            if not tasks:
                return {'response': '✅ 当前没有未完成工作', 'is_command': True}

            response = f"未完成工作（共{len(tasks)}个）：\n\n"
            for idx, task in enumerate(tasks, 1):
                response += f"{idx}. {task['title']}\n"

            # ✨ 返回上下文信息，供AI系统使用
            return {
                'response': response,
                'is_command': True,
                'context': {
                    'type': 'work_list',
                    'data': tasks
                }
            }

        # 解析参数
        args_str = ' '.join(args)

        # 查看已完成任务
        if args_str in ['已完成', 'completed', '完成列表']:
            tasks = work_mgr.list_tasks(user_id, status='completed')
            if not tasks:
                return {'response': '✅ 暂无已完成的任务', 'is_command': True}

            response = f"✅ 已完成的任务（共{len(tasks)}个）：\n\n"
            for idx, task in enumerate(tasks, 1):
                response += f"{idx}. {task['title']}\n"
                if task.get('completed_at'):
                    completed_time = str(task['completed_at'])[:10]
                    response += f"   完成于：{completed_time}\n"
            return {'response': response, 'is_command': True}

        # 完成任务
        if args_str.startswith('完成 ') or args_str.startswith('done '):
            task_nums_str = args_str.split(' ', 1)[1] if ' ' in args_str else ''

            # ✨ 支持批量完成：解析多个序号（如"1.2.3.4"或"1,2,3,4"或"1 2 3 4"）
            task_nums = re.findall(r'\d+', task_nums_str)

            if not task_nums:
                return {'response': '❌ 请提供有效的任务序号', 'is_command': True}

            # 获取所有未完成任务
            tasks = work_mgr.list_tasks(user_id, status='pending')

            # 批量完成
            completed_tasks = []
            failed_nums = []

            for num_str in task_nums:
                idx = int(num_str) - 1
                if 0 <= idx < len(tasks):
                    task = tasks[idx]
                    try:
                        work_mgr.update_task_status(task['id'], 'completed', user_id)
                        completed_tasks.append(f"{num_str}. {task['title']}")
                    except Exception as e:
                        failed_nums.append(num_str)
                        print(f"完成任务失败: {num_str}, 错误: {e}")
                else:
                    failed_nums.append(num_str)

            # 生成响应
            if completed_tasks:
                response = f"✅ 已完成 {len(completed_tasks)} 个任务：\n\n"
                for task_info in completed_tasks:
                    response += f"{task_info}\n"
                if failed_nums:
                    response += f"\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
                return {'response': response, 'is_command': True}
            else:
                return {'response': f'❌ 所有序号都无效：{", ".join(failed_nums)}', 'is_command': True}

        # 删除任务
        if args_str.startswith('删除 ') or args_str.startswith('delete '):
            task_nums_str = args_str.split(' ', 1)[1] if ' ' in args_str else ''

            # ✨ 支持批量删除：解析多个序号（如"1.2.3.4"或"1,2,3,4"或"1 2 3 4"）
            task_nums = re.findall(r'\d+', task_nums_str)

            if not task_nums:
                return {'response': '❌ 请提供有效的任务序号', 'is_command': True}

            # 获取所有未完成任务
            tasks = work_mgr.list_tasks(user_id, status='pending')

            # 批量删除（需要从大到小删除，避免索引变化）
            deleted_tasks = []
            failed_nums = []

            # 按序号从大到小排序
            sorted_nums = sorted([int(n) for n in task_nums], reverse=True)

            for num in sorted_nums:
                idx = num - 1
                if 0 <= idx < len(tasks):
                    task = tasks[idx]
                    try:
                        work_mgr.delete_task(task['id'], user_id)
                        deleted_tasks.append(f"{num}. {task['title']}")
                    except Exception as e:
                        failed_nums.append(str(num))
                        print(f"删除任务失败: {num}, 错误: {e}")
                else:
                    failed_nums.append(str(num))

            # 生成响应（按原始顺序显示）
            if deleted_tasks:
                deleted_tasks.reverse()  # 恢复原始顺序
                response = f"✅ 已删除 {len(deleted_tasks)} 个任务：\n\n"
                for task_info in deleted_tasks:
                    response += f"{task_info}\n"
                if failed_nums:
                    response += f"\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
                return {'response': response, 'is_command': True}
            else:
                return {'response': f'❌ 所有序号都无效：{", ".join(failed_nums)}', 'is_command': True}

        # 添加任务（支持批量添加）
        # 如果以"添加"开头，或者包含逗号/分号（批量添加），则添加任务
        if args_str.startswith('添加 ') or args_str.startswith('add '):
            content = args_str.split(' ', 1)[1] if ' ' in args_str else ''
        else:
            # 直接内容（支持批量）
            content = args_str

        if content:
            # 支持用逗号、分号、换行符分隔多个任务
            # 分割任务（支持中英文逗号、分号、换行）
            tasks = re.split(r'[,，;；\n]+', content)
            tasks = [t.strip() for t in tasks if t.strip()]

            if len(tasks) == 0:
                return {'response': '❌ 请提供任务内容', 'is_command': True}

            # 批量添加
            added_count = 0
            for task in tasks:
                try:
                    work_mgr.add_task(user_id, task)
                    added_count += 1
                except Exception as e:
                    print(f"添加任务失败: {task}, 错误: {e}")

            if added_count == 1:
                return {'response': f'✅ 已添加工作任务：{tasks[0]}', 'is_command': True}
            else:
                response = f'✅ 已批量添加 {added_count} 个工作任务：\n\n'
                for idx, task in enumerate(tasks[:10], 1):  # 最多显示10个
                    response += f'{idx}. {task}\n'
                if len(tasks) > 10:
                    response += f'\n...还有 {len(tasks) - 10} 个任务'
                return {'response': response, 'is_command': True}

        return {'response': '❌ 命令格式错误\n\n使用方法：\n• 工作 任务1,任务2,任务3\n• 工作 完成 序号\n• 工作 删除 序号\n• 工作 已完成', 'is_command': True}


class FinanceCommand(Command):
    """财务记录命令"""

    def __init__(self):
        super().__init__(
            name='财务',
            aliases=['finance', 'money', '💰'],
            description='管理财务记录'
        )

    def execute(self, args, user_id, managers):
        """执行财务命令"""
        finance_mgr = managers['finance']

        if not args:
            # 显示汇总
            summary = finance_mgr.get_summary(user_id)
            if not summary:
                return {'response': '📊 暂无财务记录', 'is_command': True}

            response = "💰 财务汇总：\n\n"
            type_names = {'income': '收入', 'expense': '支出', 'investment': '投资', 'return': '收益'}
            for item in summary:
                type_name = type_names.get(item['type'], item['type'])
                response += f"{type_name}：¥{item['total']:.2f} ({item['count']}笔)\n"

            return {'response': response, 'is_command': True}

        # 解析参数
        args_str = ' '.join(args)

        # 查看已完成财务记录
        if args_str in ['已完成', 'completed', '完成列表']:
            records = finance_mgr.list_records(user_id, status='completed')
            if not records:
                return {'response': '✅ 暂无已完成的财务记录', 'is_command': True}

            response = f"✅ 已完成的财务记录（共{len(records)}个）：\n\n"
            type_names = {'income': '收入', 'expense': '支出', 'investment': '投资', 'return': '收益'}
            for idx, record in enumerate(records, 1):
                type_name = type_names.get(record['type'], record['type'])
                response += f"{idx}. {type_name} ¥{record['amount']} - {record['title']}\n"
            return {'response': response, 'is_command': True}

        # 完成财务记录
        if args_str.startswith('完成 ') or args_str.startswith('done '):
            record_nums_str = args_str.split(' ', 1)[1] if ' ' in args_str else ''

            # ✨ 支持批量完成
            record_nums = parse_batch_numbers(record_nums_str)

            if not record_nums:
                return {'response': '❌ 请提供有效的记录序号', 'is_command': True}

            # 获取所有未完成记录
            records = finance_mgr.list_records(user_id, status='pending')

            # 批量完成
            completed_records = []
            failed_nums = []

            for num_str in record_nums:
                idx = int(num_str) - 1
                if 0 <= idx < len(records):
                    record = records[idx]
                    try:
                        finance_mgr.update_finance_status(record['id'], 'completed', user_id)
                        completed_records.append(f"{num_str}. ¥{record['amount']} - {record['title']}")
                    except Exception as e:
                        failed_nums.append(num_str)
                        print(f"完成财务记录失败: {num_str}, 错误: {e}")
                else:
                    failed_nums.append(num_str)

            # 生成响应
            if completed_records:
                response = f"✅ 已完成 {len(completed_records)} 条财务记录：\n\n"
                for record_info in completed_records:
                    response += f"{record_info}\n"
                if failed_nums:
                    response += f"\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
                return {'response': response, 'is_command': True}
            else:
                return {'response': f'❌ 所有序号都无效：{", ".join(failed_nums)}', 'is_command': True}

        # 删除财务记录
        if args_str.startswith('删除 ') or args_str.startswith('delete '):
            record_nums_str = args_str.split(' ', 1)[1] if ' ' in args_str else ''

            # ✨ 支持批量删除
            record_nums = parse_batch_numbers(record_nums_str)

            if not record_nums:
                return {'response': '❌ 请提供有效的记录序号', 'is_command': True}

            # 获取所有未完成记录
            records = finance_mgr.list_records(user_id, status='pending')

            # 批量删除（从大到小删除）
            deleted_records = []
            failed_nums = []

            sorted_nums = sorted([int(n) for n in record_nums], reverse=True)

            for num in sorted_nums:
                idx = num - 1
                if 0 <= idx < len(records):
                    record = records[idx]
                    try:
                        finance_mgr.delete_finance_record(record['id'], user_id)
                        deleted_records.append(f"{num}. ¥{record['amount']} - {record['title']}")
                    except Exception as e:
                        failed_nums.append(str(num))
                        print(f"删除财务记录失败: {num}, 错误: {e}")
                else:
                    failed_nums.append(str(num))

            # 生成响应
            if deleted_records:
                deleted_records.reverse()
                response = f"✅ 已删除 {len(deleted_records)} 条财务记录：\n\n"
                for record_info in deleted_records:
                    response += f"{record_info}\n"
                if failed_nums:
                    response += f"\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
                return {'response': response, 'is_command': True}
            else:
                return {'response': f'❌ 所有序号都无效：{", ".join(failed_nums)}', 'is_command': True}

        # 解析参数：财务 收入 1000 工资
        if len(args) >= 3:
            type_map = {'收入': 'income', '支出': 'expense', '投资': 'investment', '收益': 'return'}
            record_type = type_map.get(args[0])
            if record_type:
                try:
                    amount = float(args[1])
                    title = ' '.join(args[2:])
                    finance_mgr.add_record(user_id, record_type, amount, title)
                    return {'response': f'✅ 已记录{args[0]}：¥{amount} - {title}', 'is_command': True}
                except ValueError:
                    return {'response': '❌ 金额格式错误', 'is_command': True}

        return {'response': '❌ 命令格式：财务 收入/支出 金额 说明', 'is_command': True}


class RecordCommand(Command):
    """记录命令"""

    def __init__(self):
        super().__init__(
            name='记录',
            aliases=['record', 'note', '📝'],
            description='添加日常记录'
        )

    def _get_grouped_records_list(self, user_id, managers, status='pending'):
        """获取按子类别分组后的扁平记录列表（保持分组顺序）"""
        record_mgr = managers['record']
        category_mgr = managers['category']

        # 获取记录
        records = record_mgr.list_records(user_id, status=status)[:50]
        if not records:
            return []

        # 获取所有子类别信息
        subcategories_map = {}
        all_categories = category_mgr.get_all_categories()
        for cat in all_categories:
            if cat['code'] == 'record':
                query = "SELECT * FROM subcategories WHERE category_id = %s"
                subs = category_mgr.query(query, (cat['id'],))
                for sub in subs:
                    subcategories_map[sub['id']] = sub['name']
                break

        # 按子类别分组
        grouped_records = {}
        for record in records:
            sub_id = record.get('subcategory_id')
            sub_name = subcategories_map.get(sub_id, '未分类')
            if sub_name not in grouped_records:
                grouped_records[sub_name] = []
            grouped_records[sub_name].append(record)

        # 构建扁平列表（按分组顺序）
        flat_list = []
        for sub_name, sub_records in grouped_records.items():
            flat_list.extend(sub_records)  # 显示所有记录，不限制数量

        return flat_list

    def execute(self, args, user_id, managers):
        """执行记录命令"""
        record_mgr = managers['record']
        category_mgr = managers['category']

        if not args:
            # 使用辅助方法获取分组后的记录列表
            flat_records = self._get_grouped_records_list(user_id, managers, status='pending')

            if not flat_records:
                return {'response': '📝 暂无记录', 'is_command': True}

            # 获取子类别信息用于分组显示
            subcategories_map = {}
            all_categories = category_mgr.get_all_categories()
            for cat in all_categories:
                if cat['code'] == 'record':
                    query = "SELECT * FROM subcategories WHERE category_id = %s"
                    subs = category_mgr.query(query, (cat['id'],))
                    for sub in subs:
                        subcategories_map[sub['id']] = sub['name']
                    break

            # 按子类别分组显示（用于美化输出）
            grouped_display = {}
            for record in flat_records:
                sub_id = record.get('subcategory_id')
                sub_name = subcategories_map.get(sub_id, '未分类')
                if sub_name not in grouped_display:
                    grouped_display[sub_name] = []
                grouped_display[sub_name].append(record)

            # 生成响应
            response = "📝 最近的记录：\n\n"
            idx = 0
            for sub_name, sub_records in grouped_display.items():
                response += f"【{sub_name}】\n"
                for record in sub_records:
                    idx += 1
                    title = record['title'] or record['content'][:30]
                    response += f"{idx}. {title}\n"
                response += "\n"

            return {'response': response, 'is_command': True}

        # 解析参数
        args_str = ' '.join(args)

        # 查看已完成记录
        if args_str in ['已完成', 'completed', '完成列表']:
            records = record_mgr.list_records(user_id, status='completed')
            if not records:
                return {'response': '✅ 暂无已完成的记录', 'is_command': True}

            response = f"✅ 已完成的记录（共{len(records)}个）：\n\n"
            for idx, record in enumerate(records, 1):
                title = record['title'] or record['content'][:30]
                response += f"{idx}. {title}\n"
            return {'response': response, 'is_command': True}

        # 完成记录
        if args_str.startswith('完成 ') or args_str.startswith('done '):
            record_nums_str = args_str.split(' ', 1)[1] if ' ' in args_str else ''

            # ✨ 支持批量完成
            record_nums = parse_batch_numbers(record_nums_str)

            if not record_nums:
                return {'response': '❌ 请提供有效的记录序号', 'is_command': True}

            # 获取所有未完成记录
            records = self._get_grouped_records_list(user_id, managers, status='pending')

            # 批量完成
            completed_records = []
            failed_nums = []

            for num_str in record_nums:
                idx = int(num_str) - 1
                if 0 <= idx < len(records):
                    record = records[idx]
                    try:
                        record_mgr.update_record_status(record['id'], 'completed', user_id)
                        title = record['title'] or record['content'][:30]
                        completed_records.append(f"{num_str}. {title}")
                    except Exception as e:
                        failed_nums.append(num_str)
                        print(f"完成记录失败: {num_str}, 错误: {e}")
                else:
                    failed_nums.append(num_str)

            # 生成响应
            if completed_records:
                response = f"✅ 已完成 {len(completed_records)} 条记录：\n\n"
                for record_info in completed_records:
                    response += f"{record_info}\n"
                if failed_nums:
                    response += f"\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
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

            # 获取所有未完成记录
            records = self._get_grouped_records_list(user_id, managers, status='pending')

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
                        title = record['title'] or record['content'][:30]
                        deleted_records.append(f"{num}. {title}")
                    except Exception as e:
                        failed_nums.append(str(num))
                        print(f"删除记录失败: {num}, 错误: {e}")
                else:
                    failed_nums.append(str(num))

            # 生成响应
            if deleted_records:
                deleted_records.reverse()
                response = f"✅ 已删除 {len(deleted_records)} 条记录：\n\n"
                for record_info in deleted_records:
                    response += f"{record_info}\n"
                if failed_nums:
                    response += f"\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
                return {'response': response, 'is_command': True}
            else:
                return {'response': f'❌ 所有序号都无效：{", ".join(failed_nums)}', 'is_command': True}

        # 添加记录
        if args_str.startswith('添加 ') or args_str.startswith('add '):
            content = args_str.split(' ', 1)[1] if ' ' in args_str else ''
            if content:
                record_mgr.add_record(user_id, content)
                return {'response': '✅ 已保存记录', 'is_command': True}
            return {'response': '❌ 请提供记录内容', 'is_command': True}

        # 搜索记录
        if args_str.startswith('搜索 ') or args_str.startswith('search '):
            keyword = args_str.split(' ', 1)[1] if ' ' in args_str else ''
            if keyword:
                records = record_mgr.search_records(user_id, keyword)
                if not records:
                    return {'response': f'🔍 未找到包含"{keyword}"的记录', 'is_command': True}

                response = f"🔍 搜索结果（共{len(records)}条）：\n\n"
                for idx, record in enumerate(records, 1):
                    title = record['title'] or record['content'][:30]
                    response += f"{idx}. {title}\n"
                return {'response': response, 'is_command': True}
            return {'response': '❌ 请提供搜索关键词', 'is_command': True}

        # 直接添加（没有"添加"前缀）
        record_mgr.add_record(user_id, args_str)
        return {'response': '✅ 已保存记录', 'is_command': True}


class OtherCommand(Command):
    """其他命令 - 查询"其他类"下的所有数据"""

    def __init__(self):
        super().__init__(
            name='其他',
            aliases=['other', '📋'],
            description='查询"其他类"下的所有数据'
        )

    def execute(self, args, user_id, managers):
        """执行其他命令"""
        record_mgr = managers['record']
        category_mgr = managers['category']

        # 查询"其他类"类别（code='record'）
        query = "SELECT id, name FROM categories WHERE code = %s"
        result = category_mgr.query(query, ('record',))

        if not result:
            return {'response': '❌ 未找到"其他类"类别', 'is_command': True}

        category_id = result[0]['id']
        category_name = result[0]['name']

        # 查询该类别下的所有子类别
        sub_query = "SELECT id, name FROM subcategories WHERE category_id = %s ORDER BY id"
        subcategories = category_mgr.query(sub_query, (category_id,))

        if not subcategories:
            return {'response': f'📭 "{category_name}"类别下没有子类别', 'is_command': True}

        # 查询所有子类别下的记录
        grouped_records = {}

        for subcategory in subcategories:
            sub_id = subcategory['id']
            sub_name = subcategory['name']

            # 查询该子类别下的所有记录
            records_query = """
                SELECT id, title, content FROM daily_records
                WHERE subcategory_id = %s AND user_id = %s
                ORDER BY id DESC
            """
            records = category_mgr.query(records_query, (sub_id, user_id))

            if records:
                grouped_records[sub_name] = records

        if not grouped_records:
            return {'response': f'📭 "{category_name}"类别下没有记录', 'is_command': True}

        # 格式化输出（按子类别分组）
        response = f"📋 最近的{category_name}：\n\n"

        idx = 0
        for sub_name, records in grouped_records.items():
            response += f"【{sub_name}】\n"
            for record in records:
                idx += 1
                title = record.get('title', '') or record.get('content', '')[:50]
                # 限制标题长度
                if len(title) > 50:
                    title = title[:50] + '...'

                response += f"{idx}. {title}\n"
            response += "\n"

        return {'response': response, 'is_command': True}


class DynamicSubcategoryCommand(Command):
    """动态子类别命令 - 支持所有子类别作为快捷命令"""

    def __init__(self, subcategory_name, subcategory_code, category_code, category_id):
        super().__init__(
            name=subcategory_name,
            aliases=[],
            description=f'快捷命令：{subcategory_name}'
        )
        self.subcategory_code = subcategory_code
        self.category_code = category_code
        self.category_id = category_id

    def execute(self, args, user_id, managers):
        """执行动态子类别命令"""
        # 根据类别类型路由到不同的管理器
        if self.category_code == 'record':
            # 记录类 - 使用 DailyRecordManager
            record_mgr = managers['record']
            category_mgr = managers['category']

            if not args:
                # 查看该子类别的记录
                subcategory_id = self._get_subcategory_id(category_mgr, user_id)
                if subcategory_id:
                    records = record_mgr.list_records(user_id, subcategory_id=subcategory_id, status='pending')
                else:
                    records = []

                if not records:
                    return {'response': f'📝 暂无{self.name}', 'is_command': True}

                response = f"未完成{self.name}（共{len(records)}个）：\n\n"
                for idx, record in enumerate(records, 1):
                    # ✨ 优先显示 title，如果 title 为空则显示 content
                    display_text = record.get('title') or record.get('content', '')
                    if len(display_text) > 50:
                        display_text = display_text[:50]
                    response += f"{idx}. {display_text}\n"

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

                # 批量完成
                completed_records = []
                failed_nums = []

                # ✨ 调试日志：打印所有记录
                print(f"🔍 DEBUG: records总数={len(records)}")
                for i, r in enumerate(records):
                    print(f"🔍 DEBUG: records[{i}] = {r.get('content', r.get('title', ''))[:30]}")

                for num_str in record_nums:
                    idx = int(num_str) - 1
                    print(f"🔍 DEBUG: 用户输入序号={num_str}, 计算idx={idx}, records长度={len(records)}")
                    if 0 <= idx < len(records):
                        record = records[idx]
                        print(f"🔍 DEBUG: 找到记录 records[{idx}] = {record.get('content', record.get('title', ''))[:30]}")
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
                    response = f"✅ 已完成 {len(completed_records)} 条记录：\n\n"
                    for record_info in completed_records:
                        response += f"{record_info}\n"
                    if failed_nums:
                        response += f"\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
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
                    response = f"✅ 已删除 {len(deleted_records)} 条记录：\n\n"
                    for record_info in deleted_records:
                        response += f"{record_info}\n"
                    if failed_nums:
                        response += f"\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
                    return {'response': response, 'is_command': True}
                else:
                    return {'response': f'❌ 所有序号都无效：{", ".join(failed_nums)}', 'is_command': True}

            # 添加记录（支持批量添加）
            content = args_str
            subcategory_id = self._get_subcategory_id(category_mgr, user_id)

            # 支持用逗号、分号、换行符分隔多条记录
            records_list = re.split(r'[,，;；\n]+', content)
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
                response = f'✅ 已批量添加 {added_count} 条{self.name}：\n\n'
                for idx, r in enumerate(records_list, 1):
                    response += f'{idx}. {r}\n'
                return {'response': response, 'is_command': True}

        elif self.category_code == 'work':
            # 工作类 - 使用 WorkTaskManager
            work_mgr = managers['work']
            category_mgr = managers['category']

            if not args:
                # 查看该优先级的任务
                subcategory_id = self._get_subcategory_id(category_mgr, user_id)
                tasks = work_mgr.list_tasks(user_id, status='pending', subcategory_id=subcategory_id)

                if not tasks:
                    return {'response': f'✅ 暂无{self.name}任务', 'is_command': True}

                response = f"📋 {self.name}任务（共{len(tasks)}个）：\n\n"
                for idx, task in enumerate(tasks, 1):
                    response += f"{idx}. {task['title']}\n"
                return {'response': response, 'is_command': True}

            # 添加任务
            content = ' '.join(args)
            subcategory_id = self._get_subcategory_id(category_mgr, user_id)
            work_mgr.add_task(user_id, content, subcategory_id=subcategory_id)
            return {'response': f'✅ 已添加{self.name}任务：{content}', 'is_command': True}

        elif self.category_code == 'finance':
            # 财务类 - 使用 FinanceManager
            finance_mgr = managers['finance']

            if not args:
                # 查看该类型的财务记录
                records = finance_mgr.list_records(user_id, type=self.subcategory_code)

                if not records:
                    return {'response': f'💰 暂无{self.name}记录', 'is_command': True}

                response = f"💰 {self.name}记录：\n\n"
                for idx, record in enumerate(records, 1):
                    response += f"{idx}. ¥{record['amount']} - {record['title']} ({record['record_date']})\n"
                return {'response': response, 'is_command': True}

            # 添加财务记录
            parts = ' '.join(args).split(None, 1)
            if len(parts) >= 2:
                try:
                    amount = float(parts[0])
                    title = parts[1]
                    finance_mgr.add_record(user_id, self.subcategory_code, amount, title)
                    return {'response': f'✅ 已记录{self.name}：¥{amount} - {title}', 'is_command': True}
                except ValueError:
                    return {'response': '❌ 金额格式错误\n\n使用：{self.name} 金额 说明', 'is_command': True}
            else:
                return {'response': f'❌ 格式错误\n\n使用：{self.name} 金额 说明', 'is_command': True}

        elif self.category_code == 'time':
            # 特殊处理：日记使用记录类的逻辑
            if self.subcategory_code == 'diary':
                # 日记使用 DailyRecordManager
                record_mgr = managers['record']
                category_mgr = managers['category']

                if not args:
                    # 查看该子类别的记录
                    subcategory_id = self._get_subcategory_id(category_mgr, user_id)
                    if subcategory_id:
                        records = record_mgr.list_records(user_id, subcategory_id=subcategory_id, status='pending')
                    else:
                        records = []

                    if not records:
                        return {'response': f'📝 暂无{self.name}', 'is_command': True}

                    response = f"未完成{self.name}（共{len(records)}个）：\n\n"
                    for idx, record in enumerate(records, 1):
                        display_text = record.get('title') or record.get('content', '')
                        if len(display_text) > 50:
                            display_text = display_text[:50]
                        response += f"{idx}. {display_text}\n"
                        # 添加日期显示
                        if record.get('record_date'):
                            record_date = str(record['record_date'])[:10]
                            response += f"   {record_date}\n"

                    return {
                        'response': response,
                        'is_command': True,
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
                    record_nums = parse_batch_numbers(record_nums_str)

                    if not record_nums:
                        return {'response': '❌ 请提供有效的记录序号', 'is_command': True}

                    subcategory_id = self._get_subcategory_id(category_mgr, user_id)
                    records = record_mgr.list_records(user_id, subcategory_id=subcategory_id, status='pending')

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

                    if completed_records:
                        response = f"✅ 已完成 {len(completed_records)} 条记录：\n\n"
                        for record_info in completed_records:
                            response += f"{record_info}\n"
                        if failed_nums:
                            response += f"\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
                        return {'response': response, 'is_command': True}
                    else:
                        return {'response': f'❌ 所有序号都无效：{", ".join(failed_nums)}', 'is_command': True}

                # 删除记录
                if args_str.startswith('删除 ') or args_str.startswith('delete '):
                    record_nums_str = args_str.split(' ', 1)[1] if ' ' in args_str else ''
                    record_nums = parse_batch_numbers(record_nums_str)

                    if not record_nums:
                        return {'response': '❌ 请提供有效的记录序号', 'is_command': True}

                    subcategory_id = self._get_subcategory_id(category_mgr, user_id)
                    records = record_mgr.list_records(user_id, subcategory_id=subcategory_id, status='pending')

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

                    if deleted_records:
                        deleted_records.reverse()
                        response = f"✅ 已删除 {len(deleted_records)} 条记录：\n\n"
                        for record_info in deleted_records:
                            response += f"{record_info}\n"
                        if failed_nums:
                            response += f"\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
                        return {'response': response, 'is_command': True}
                    else:
                        return {'response': f'❌ 所有序号都无效：{", ".join(failed_nums)}', 'is_command': True}

                # 添加记录（支持批量添加）
                records_list = re.split(r'[,，;；\n]+', args_str)
                records_list = [r.strip() for r in records_list if r.strip()]

                if not records_list:
                    return {'response': '❌ 请提供记录内容', 'is_command': True}

                from datetime import datetime
                record_date = datetime.now().strftime('%Y-%m-%d')
                subcategory_id = self._get_subcategory_id(category_mgr, user_id)

                for content in records_list:
                    record_mgr.add_record(
                        user_id=user_id,
                        content=content,
                        record_date=record_date,
                        subcategory_id=subcategory_id
                    )

                if len(records_list) == 1:
                    return {'response': f'✅ 已保存{self.name}', 'is_command': True}
                else:
                    return {'response': f'✅ 已保存 {len(records_list)} 条{self.name}', 'is_command': True}

            # 时间类 - 使用 TimeScheduleManager
            time_mgr = managers['time']
            category_mgr = managers['category']

            if not args:
                # 查看该子类别的时间规划
                subcategory_id = self._get_subcategory_id(category_mgr, user_id)
                if subcategory_id:
                    schedules = time_mgr.list_schedules(user_id, subcategory_id=subcategory_id, status='pending')
                else:
                    schedules = []

                if not schedules:
                    return {'response': f'⏱️ 暂无{self.name}', 'is_command': True}

                response = f"⏱️ 最近的{self.name}：\n\n"
                for idx, schedule in enumerate(schedules, 1):
                    title = schedule.get('title', '')
                    start_time = str(schedule.get('start_time', ''))[:5]  # HH:MM
                    end_time = str(schedule.get('end_time', ''))[:5]
                    response += f"{idx}. {title} ({start_time}-{end_time})\n"

                return {
                    'response': response,
                    'is_command': True,
                    'context': {
                        'type': 'time_schedules',
                        'data': schedules
                    }
                }

            # 解析参数
            args_str = ' '.join(args)

            # 完成时间规划
            if args_str.startswith('完成 ') or args_str.startswith('done '):
                schedule_nums_str = args_str.split(' ', 1)[1] if ' ' in args_str else ''
                schedule_nums = parse_batch_numbers(schedule_nums_str)

                if not schedule_nums:
                    return {'response': '❌ 请提供有效的序号', 'is_command': True}

                subcategory_id = self._get_subcategory_id(category_mgr, user_id)
                schedules = time_mgr.list_schedules(user_id, subcategory_id=subcategory_id, status='pending')

                completed_schedules = []
                failed_nums = []

                for num_str in schedule_nums:
                    idx = int(num_str) - 1
                    if 0 <= idx < len(schedules):
                        schedule = schedules[idx]
                        try:
                            time_mgr.update_schedule_status(schedule['id'], 'completed', user_id)
                            title = schedule['title'][:30]
                            completed_schedules.append(f"{num_str}. {title}")
                        except Exception as e:
                            failed_nums.append(num_str)
                            print(f"完成时间规划失败: {num_str}, 错误: {e}")
                    else:
                        failed_nums.append(num_str)

                if completed_schedules:
                    response = f"✅ 已完成 {len(completed_schedules)} 个时间规划：\n\n"
                    for schedule_info in completed_schedules:
                        response += f"{schedule_info}\n"
                    if failed_nums:
                        response += f"\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
                    return {'response': response, 'is_command': True}
                else:
                    return {'response': f'❌ 所有序号都无效：{", ".join(failed_nums)}', 'is_command': True}

            # 删除时间规划
            if args_str.startswith('删除 ') or args_str.startswith('delete '):
                schedule_nums_str = args_str.split(' ', 1)[1] if ' ' in args_str else ''
                schedule_nums = parse_batch_numbers(schedule_nums_str)

                if not schedule_nums:
                    return {'response': '❌ 请提供有效的序号', 'is_command': True}

                subcategory_id = self._get_subcategory_id(category_mgr, user_id)
                schedules = time_mgr.list_schedules(user_id, subcategory_id=subcategory_id, status='pending')

                deleted_schedules = []
                failed_nums = []

                sorted_nums = sorted([int(n) for n in schedule_nums], reverse=True)

                for num in sorted_nums:
                    idx = num - 1
                    if 0 <= idx < len(schedules):
                        schedule = schedules[idx]
                        try:
                            time_mgr.delete_schedule(schedule['id'], user_id)
                            title = schedule['title'][:30]
                            deleted_schedules.append(f"{num}. {title}")
                        except Exception as e:
                            failed_nums.append(str(num))
                            print(f"删除时间规划失败: {num}, 错误: {e}")
                    else:
                        failed_nums.append(str(num))

                if deleted_schedules:
                    deleted_schedules.reverse()
                    response = f"✅ 已删除 {len(deleted_schedules)} 个时间规划：\n\n"
                    for schedule_info in deleted_schedules:
                        response += f"{schedule_info}\n"
                    if failed_nums:
                        response += f"\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
                    return {'response': response, 'is_command': True}
                else:
                    return {'response': f'❌ 所有序号都无效：{", ".join(failed_nums)}', 'is_command': True}

            # 添加时间规划
            # 格式：子类别名: 标题 开始时间-结束时间 [日期]
            # 例如：工作时间: 开会 9:00-10:00 明天
            from datetime import datetime, timedelta

            # 解析内容
            content = args_str

            # 提取时间范围（格式：HH:MM-HH:MM）
            time_pattern = r'(\d{1,2}:\d{2})-(\d{1,2}:\d{2})'
            time_match = re.search(time_pattern, content)

            if not time_match:
                return {'response': '❌ 请提供时间范围，格式：标题 开始时间-结束时间\n例如：开会 9:00-10:00', 'is_command': True}

            start_time = time_match.group(1)
            end_time = time_match.group(2)

            # 移除时间部分，获取标题
            title = content[:time_match.start()].strip()
            remaining = content[time_match.end():].strip()

            # 解析日期（默认今天）
            schedule_date = datetime.now().date()
            if remaining:
                if '明天' in remaining:
                    schedule_date = (datetime.now() + timedelta(days=1)).date()
                elif '后天' in remaining:
                    schedule_date = (datetime.now() + timedelta(days=2)).date()

            if not title:
                return {'response': '❌ 请提供标题', 'is_command': True}

            # 保存时间规划
            subcategory_id = self._get_subcategory_id(category_mgr, user_id)
            time_mgr.add_schedule(
                user_id=user_id,
                title=title,
                schedule_date=schedule_date,
                start_time=start_time,
                end_time=end_time,
                subcategory_id=subcategory_id
            )

            return {'response': f'✅ 已添加时间规划：{title} ({start_time}-{end_time})', 'is_command': True}
        else:


            # 其他类别暂不支持快捷命令
            return {'response': f'⚠️ {self.name}命令暂不支持快捷操作\n\n请使用完整命令格式', 'is_command': True}

    def _get_subcategory_id(self, category_mgr, user_id):
        """获取子类别ID"""
        subcategories = category_mgr.get_subcategories(self.category_id, user_id)
        for sub in subcategories:
            if sub['code'] == self.subcategory_code:
                return sub['id']
        return None


class AccountCommand(Command):
    """账号密码管理命令"""

    def __init__(self):
        super().__init__(
            name='账号',
            aliases=['account', 'acc', '密码', 'password'],
            description='管理账号密码'
        )

    def execute(self, args, user_id, managers):
        """执行账号命令"""
        account_mgr = managers['account']

        if not args:
            # 列出所有账号（不显示密码）
            accounts = account_mgr.list_accounts(user_id, status='pending')
            if not accounts:
                return {'response': '🔐 暂无账号记录', 'is_command': True}

            response = f"🔐 账号列表（共{len(accounts)}个）：\n\n"
            for idx, acc in enumerate(accounts, 1):
                response += f"{idx}. {acc['platform']} - {acc['account']}\n"
                if acc.get('email'):
                    response += f"   {acc['email']}\n"

            return {'response': response, 'is_command': True}

        # 解析参数
        args_str = ' '.join(args)

        # 查看已完成账号
        if args_str in ['已完成', 'completed', '完成列表']:
            accounts = account_mgr.list_accounts(user_id, status='completed')
            if not accounts:
                return {'response': '✅ 暂无已完成的账号记录', 'is_command': True}

            response = f"✅ 已完成的账号（共{len(accounts)}个）：\n\n"
            for idx, acc in enumerate(accounts, 1):
                response += f"{idx}. {acc['platform']} - {acc['account']}\n"
            return {'response': response, 'is_command': True}

        # 完成账号
        if args_str.startswith('完成 ') or args_str.startswith('done '):
            acc_nums_str = args_str.split(' ', 1)[1] if ' ' in args_str else ''

            # ✨ 支持批量完成
            acc_nums = parse_batch_numbers(acc_nums_str)

            if not acc_nums:
                return {'response': '❌ 请提供有效的账号序号', 'is_command': True}

            # 获取所有未完成账号
            accounts = account_mgr.list_accounts(user_id, status='pending')

            # 批量完成
            completed_accounts = []
            failed_nums = []

            for num_str in acc_nums:
                idx = int(num_str) - 1
                if 0 <= idx < len(accounts):
                    acc = accounts[idx]
                    try:
                        account_mgr.update_account_status(acc['id'], 'completed', user_id)
                        completed_accounts.append(f"{num_str}. {acc['platform']} - {acc['account']}")
                    except Exception as e:
                        failed_nums.append(num_str)
                        print(f"完成账号失败: {num_str}, 错误: {e}")
                else:
                    failed_nums.append(num_str)

            # 生成响应
            if completed_accounts:
                response = f"✅ 已完成 {len(completed_accounts)} 个账号：\n\n"
                for acc_info in completed_accounts:
                    response += f"{acc_info}\n"
                if failed_nums:
                    response += f"\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
                return {'response': response, 'is_command': True}
            else:
                return {'response': f'❌ 所有序号都无效：{", ".join(failed_nums)}', 'is_command': True}

        # 删除账号
        if args_str.startswith('删除 ') or args_str.startswith('delete '):
            acc_nums_str = args_str.split(' ', 1)[1] if ' ' in args_str else ''

            # ✨ 支持批量删除
            acc_nums = parse_batch_numbers(acc_nums_str)

            if not acc_nums:
                return {'response': '❌ 请提供有效的账号序号', 'is_command': True}

            # 获取所有未完成账号
            accounts = account_mgr.list_accounts(user_id, status='pending')

            # 批量删除（从大到小删除）
            deleted_accounts = []
            failed_nums = []

            sorted_nums = sorted([int(n) for n in acc_nums], reverse=True)

            for num in sorted_nums:
                idx = num - 1
                if 0 <= idx < len(accounts):
                    acc = accounts[idx]
                    try:
                        account_mgr.delete_account(acc['id'], user_id)
                        deleted_accounts.append(f"{num}. {acc['platform']} - {acc['account']}")
                    except Exception as e:
                        failed_nums.append(str(num))
                        print(f"删除账号失败: {num}, 错误: {e}")
                else:
                    failed_nums.append(str(num))

            # 生成响应
            if deleted_accounts:
                deleted_accounts.reverse()
                response = f"✅ 已删除 {len(deleted_accounts)} 个账号：\n\n"
                for acc_info in deleted_accounts:
                    response += f"{acc_info}\n"
                if failed_nums:
                    response += f"\n⚠️ 序号 {', '.join(failed_nums)} 不存在或操作失败"
                return {'response': response, 'is_command': True}
            else:
                return {'response': f'❌ 所有序号都无效：{", ".join(failed_nums)}', 'is_command': True}

        # 添加账号
        if args_str.startswith('添加 ') or args_str.startswith('add '):
            parts = args_str.split(' ', 1)[1].split() if ' ' in args_str else []
            if len(parts) >= 3:
                platform, account, password = parts[0], parts[1], parts[2]
                account_mgr.add_account(user_id, platform, account, password)
                return {'response': f'✅ 已添加账号：{platform} - {account}', 'is_command': True}
            return {'response': '❌ 格式：账号 添加 平台 账号 密码', 'is_command': True}

        # 查看账号详情（包含密码）
        if args_str.startswith('查看 ') or args_str.startswith('view '):
            acc_num = args_str.split(' ', 1)[1] if ' ' in args_str else ''
            if acc_num.isdigit():
                accounts = account_mgr.list_accounts(user_id, status='pending')
                idx = int(acc_num) - 1
                if 0 <= idx < len(accounts):
                    acc_id = accounts[idx]['id']
                    detail = account_mgr.get_account_detail(acc_id, user_id)
                    if detail:
                        response = f"🔐 账号详情：\n\n"
                        response += f"平台：{detail['platform']}\n"
                        response += f"账号：{detail['account']}\n"
                        response += f"密码：{detail['password']}\n"
                        if detail.get('email'):
                            response += f"邮箱：{detail['email']}\n"
                        if detail.get('url'):
                            response += f"网址：{detail['url']}\n"
                        return {'response': response, 'is_command': True}
                return {'response': f'❌ 账号序号 {acc_num} 不存在', 'is_command': True}
            return {'response': '❌ 请提供有效的账号序号', 'is_command': True}

        return {'response': '❌ 命令格式错误\n\n使用方法：\n• 账号 添加 平台 账号 密码\n• 账号 查看 序号', 'is_command': True}


class ReminderCommand(Command):
    """提醒管理命令"""

    def __init__(self):
        super().__init__(
            name='提醒',
            aliases=['reminder', 'remind', '⏰'],
            description='管理提醒事项'
        )

    def execute(self, args, user_id, managers):
        """执行提醒命令"""
        # 使用现有的reminder系统
        from reminder_scheduler import get_global_scheduler
        scheduler = get_global_scheduler()

        if not args:
            # 列出所有未触发的提醒
            reminders = scheduler.list_reminders(user_id)
            active_reminders = [r for r in reminders if not r.get('triggered')]

            if not active_reminders:
                return {'response': '⏰ 暂无提醒', 'is_command': True}

            response = f"⏰ 提醒列表（共{len(active_reminders)}个）：\n\n"
            for idx, reminder in enumerate(active_reminders, 1):
                response += f"{idx}. {reminder['content']}\n"
                response += f"   ⏰ {reminder['remind_time']}\n"

            return {'response': response, 'is_command': True}

        # 解析参数
        args_str = ' '.join(args)

        # 添加提醒
        if args_str.startswith('添加 ') or args_str.startswith('add '):
            parts = args_str.split(' ', 1)[1] if ' ' in args_str else ''
            # 简单解析：最后一个词作为时间
            if parts:
                words = parts.split()
                if len(words) >= 2:
                    content = ' '.join(words[:-1])
                    time_str = words[-1]
                    # 这里需要时间解析，暂时直接使用
                    scheduler.add_reminder(user_id, content, time_str)
                    return {'response': f'✅ 已添加提醒：{content} ({time_str})', 'is_command': True}
            return {'response': '❌ 格式：提醒 添加 内容 时间', 'is_command': True}

        # 删除提醒
        if args_str.startswith('删除 ') or args_str.startswith('delete '):
            reminder_num = args_str.split(' ', 1)[1] if ' ' in args_str else ''
            if reminder_num.isdigit():
                reminders = scheduler.list_reminders(user_id)
                active_reminders = [r for r in reminders if not r.get('triggered')]
                idx = int(reminder_num) - 1
                if 0 <= idx < len(active_reminders):
                    reminder = active_reminders[idx]
                    scheduler.delete_reminder(reminder['id'], user_id)
                    return {'response': f'✅ 已删除提醒：{reminder["content"]}', 'is_command': True}
                return {'response': f'❌ 提醒序号 {reminder_num} 不存在', 'is_command': True}
            return {'response': '❌ 请提供有效的提醒序号', 'is_command': True}

        return {'response': '❌ 命令格式错误\n\n使用方法：\n• 提醒 添加 内容 时间\n• 提醒 删除 序号', 'is_command': True}


class PlanCommand(Command):
    """计划管理命令"""

    def __init__(self):
        super().__init__(
            name='计划',
            aliases=['plan', 'p', '📅'],
            description='管理计划安排'
        )

    def execute(self, args, user_id, managers):
        """执行计划命令"""
        # 使用现有的work_plans表
        from mysql_manager import WorkPlanManagerMySQL, MySQLManager
        db = MySQLManager('mysql_config.json')
        plan_mgr = WorkPlanManagerMySQL(db)

        if not args:
            # 列出所有未完成计划
            plans = plan_mgr.list_plans(user_id=user_id)
            pending_plans = [p for p in plans if p.get('status') not in ['completed', '已完成']]

            if not pending_plans:
                return {'response': '📅 暂无计划', 'is_command': True}

            response = f"📅 计划列表（共{len(pending_plans)}个）：\n\n"
            for idx, plan in enumerate(pending_plans, 1):
                response += f"{idx}. {plan['title']}\n"
                if plan.get('deadline'):
                    response += f"   📅 {plan['deadline']}\n"

            return {'response': response, 'is_command': True}

        # 解析参数
        args_str = ' '.join(args)

        # 完成计划
        if args_str.startswith('完成 ') or args_str.startswith('done '):
            plan_num = args_str.split(' ', 1)[1] if ' ' in args_str else ''
            if plan_num.isdigit():
                plans = plan_mgr.list_plans(user_id=user_id)
                pending_plans = [p for p in plans if p.get('status') not in ['completed', '已完成']]
                idx = int(plan_num) - 1
                if 0 <= idx < len(pending_plans):
                    plan = pending_plans[idx]
                    plan_mgr.update_plan_status(plan['id'], 'completed', user_id=user_id)
                    return {'response': f'✅ 已完成计划：{plan["title"]}', 'is_command': True}
                return {'response': f'❌ 计划序号 {plan_num} 不存在', 'is_command': True}
            return {'response': '❌ 请提供有效的计划序号', 'is_command': True}

        # 添加计划（支持批量添加）
        # 如果以"添加"开头，或者直接是内容
        if args_str.startswith('添加 ') or args_str.startswith('add '):
            content = args_str.split(' ', 1)[1] if ' ' in args_str else ''
        else:
            # 直接内容（支持批量）
            content = args_str

        if content:
            # 支持用逗号、分号、换行符分隔多个计划
            plans_list = re.split(r'[,，;；\n]+', content)
            plans_list = [p.strip() for p in plans_list if p.strip()]

            if len(plans_list) == 0:
                return {'response': '❌ 请提供计划内容', 'is_command': True}

            # 批量添加
            added_count = 0
            for plan_text in plans_list:
                try:
                    # 简单解析：最后一个词可能是时间
                    words = plan_text.split()
                    if len(words) >= 2:
                        title = ' '.join(words[:-1])
                        deadline = words[-1]
                    else:
                        title = plan_text
                        deadline = ''

                    plan_mgr.add_plan(title=title, description='', deadline=deadline,
                                    priority='medium', status='pending', user_id=user_id)
                    added_count += 1
                except Exception as e:
                    print(f"添加计划失败: {plan_text}, 错误: {e}")

            if added_count == 1:
                return {'response': f'✅ 已添加计划：{plans_list[0]}', 'is_command': True}
            else:
                response = f'✅ 已批量添加 {added_count} 个计划：\n\n'
                for idx, plan in enumerate(plans_list, 1):
                    response += f'{idx}. {plan}\n'
                return {'response': response, 'is_command': True}

        return {'response': '❌ 命令格式错误\n\n使用方法：\n• 计划 计划1,计划2,计划3\n• 计划 完成 序号', 'is_command': True}


class HelpCommand(Command):
    """帮助命令"""

    def __init__(self):
        super().__init__(
            name='帮助',
            aliases=['help', 'h', '命令'],
            description='查看命令帮助'
        )

    def execute(self, args, user_id, managers):
        """执行帮助命令"""
        if not args:
            response = "📖 命令系统帮助\n\n"
            response += "🔹 类别管理\n"
            response += "  类别 - 查看所有类别\n\n"
            response += "🔹 工作管理\n"
            response += "  工作 - 查看未完成任务\n"
            response += "  工作 任务1,任务2,任务3 - 批量添加\n"
            response += "  工作 完成 序号\n"
            response += "  工作 已完成\n\n"
            response += "🔹 计划管理\n"
            response += "  计划 - 查看计划列表\n"
            response += "  计划 计划1,计划2,计划3 - 批量添加\n"
            response += "  计划 完成 序号\n\n"
            response += "🔹 财务管理\n"
            response += "  财务 - 查看财务汇总\n"
            response += "  财务 收入/支出 金额 说明\n\n"
            response += "🔹 账号密码\n"
            response += "  账号 - 查看账号列表\n"
            response += "  账号 添加 平台 账号 密码\n"
            response += "  账号 查看 序号\n\n"
            response += "🔹 提醒管理\n"
            response += "  提醒 - 查看提醒列表\n"
            response += "  提醒 添加 内容 时间\n"
            response += "  提醒 删除 序号\n\n"
            response += "🔹 记录管理\n"
            response += "  记录 - 查看最近记录\n"
            response += "  记录 添加 内容\n"
            response += "  记录 搜索 关键词\n"
            response += "  日记/随想/信息/学习笔记 内容 - 快捷记录\n\n"
            response += "💡 直接输入：类别 内容1,内容2,内容3\n"
            response += "💡 支持逗号、分号分隔多项\n"
            response += "💡 查看详细帮助：帮助 类别名"
            return {'response': response, 'is_command': True}

        # 查看特定类别的帮助
        category_name = ' '.join(args)
        category_mgr = managers['category']

        # 类别名称映射
        category_map = {
            '记录': 'record',
            '工作': 'work',
            '计划': 'plan',
            '财务': 'finance',
            '账号': 'account',
            '提醒': 'reminder',
            '文件': 'file'
        }

        category_code = category_map.get(category_name)
        if not category_code:
            return {'response': f'❌ 未找到类别：{category_name}\n\n可用类别：记录、工作、计划、财务、账号、提醒、文件', 'is_command': True}

        # 获取类别信息
        category = category_mgr.get_category_by_code(category_code)
        if not category:
            return {'response': f'❌ 类别不存在：{category_name}', 'is_command': True}

        # 获取子类别
        subcategories = category_mgr.get_subcategories(category['id'], user_id)

        response = f"{category['icon']} {category['name']}帮助\n\n"
        response += f"📝 {category['description']}\n\n"

        if subcategories:
            response += "📂 子类别：\n"
            for sub in subcategories:
                response += f"• {sub['name']} - {sub['description']}\n"
            response += "\n"

        # 特殊处理记录类的快捷命令
        if category_code == 'record':
            response += "⚡ 快捷命令：\n"
            response += "• 日记 内容 - 快速记录日记\n"
            response += "• 随想 内容 - 快速记录想法\n"
            response += "• 信息 内容 - 快速记录信息\n"
            response += "• 学习笔记 内容 - 快速记录笔记\n\n"

        response += "🔧 子类别管理：\n"
        response += "• 查看子类别：类别 记录\n"
        response += "• 添加子类别：类别 添加 记录 子类别名\n"
        response += "• 删除子类别：类别 删除 记录 子类别名"

        return {'response': response, 'is_command': True}


class CommandRouter:
    """命令路由器"""

    def __init__(self):
        self.commands = {}
        self.managers = {}
        self._register_commands()
        self._init_managers()

    def _register_commands(self):
        """注册所有命令"""
        commands = [
            CategoryCommand(),
            WorkCommand(),
            FinanceCommand(),
            RecordCommand(),
            AccountCommand(),
            ReminderCommand(),
            PlanCommand(),
            HelpCommand()
        ]

        # 动态加载所有子类别作为快捷命令（包括系统和用户自定义）
        try:
            category_mgr = CategoryManager()
            all_categories = category_mgr.get_all_categories()

            for category in all_categories:
                # 直接查询数据库获取所有子类别（不限制user_id）
                query = """
                    SELECT * FROM subcategories
                    WHERE category_id = %s
                    ORDER BY sort_order, id
                """
                subcategories = category_mgr.query(query, (category['id'],))

                for sub in subcategories:
                    # 创建动态子类别命令
                    cmd = DynamicSubcategoryCommand(
                        sub['name'],
                        sub['code'],
                        category['code'],
                        category['id']
                    )
                    commands.append(cmd)
                    user_mark = " [自定义]" if sub.get('user_id') else ""
                    print(f"✅ 注册子类别命令: {sub['name']}{user_mark} ({category['name']})")
        except Exception as e:
            print(f"⚠️ 动态加载子类别命令失败: {e}")

        # ✨ 在动态命令之后注册OtherCommand，这样可以覆盖"文件类"下的"其他"子类别命令
        commands.append(OtherCommand())
        print(f"✅ 注册特殊命令: 其他 (查询其他类所有数据)")

        for cmd in commands:
            # 注册主命令名
            self.commands[cmd.name] = cmd
            # 注册别名
            for alias in cmd.aliases:
                self.commands[alias] = cmd

    def _init_managers(self):
        """初始化管理器"""
        self.managers = {
            'category': CategoryManager(),
            'work': WorkTaskManager(),
            'finance': FinanceManager(),
            'account': AccountManager(),
            'record': DailyRecordManager(),
            'time': TimeScheduleManager()
        }

    def parse_command(self, message):
        """解析命令
        返回: (command_name, args) 或 None
        """
        message = message.strip()

        # 检查是否是命令（单独的命令词）
        if message in self.commands:
            return (message, [])

        # 检查是否是冒号格式（命令: 参数 或 命令：参数）
        import re
        colon_match = re.match(r'^(\S+)[：:]\s*(.+)$', message)
        if colon_match:
            cmd_name = colon_match.group(1)
            content = colon_match.group(2)
            if cmd_name in self.commands:
                # 将冒号后的内容作为单个参数传递（保持完整，支持批量）
                return (cmd_name, [content])

        # 检查是否是带参数的命令（命令词 + 空格 + 参数）
        parts = message.split(None, 1)
        if len(parts) >= 1 and parts[0] in self.commands:
            args = parts[1].split() if len(parts) > 1 else []
            return (parts[0], args)

        return None

    def execute(self, message, user_id):
        """执行命令"""
        parsed = self.parse_command(message)
        if not parsed:
            return None

        command_name, args = parsed
        command = self.commands.get(command_name)

        if command:
            try:
                return command.execute(args, user_id, self.managers)
            except Exception as e:
                print(f"❌ 命令执行错误: {e}")
                return {'response': f'❌ 命令执行失败: {str(e)}', 'is_command': True}

        return None


# 全局命令路由器实例
_router = None


def get_command_router():
    """获取命令路由器单例"""
    global _router
    if _router is None:
        _router = CommandRouter()
    return _router
