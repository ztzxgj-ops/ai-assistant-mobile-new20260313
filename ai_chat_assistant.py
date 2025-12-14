#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI聊天助手 - 智能两阶段搜索 (MySQL版本)"""

import json
import os
import re
from datetime import datetime, timedelta
# 使用MySQL版本的管理器
from mysql_manager import (
    MySQLManager,
    MemoryManagerMySQL,
    WorkPlanManagerMySQL,
    ReminderSystemMySQL,
    ImageManagerMySQL
)
# 导入新的提醒调度器
from reminder_scheduler import get_global_scheduler

class AIAssistant:
    """AI聊天助手 (MySQL版本)"""

    def __init__(self):
        # 初始化MySQL连接
        self.db = MySQLManager('mysql_config.json')

        # 使用MySQL管理器
        self.memory = MemoryManagerMySQL(self.db)
        self.planner = WorkPlanManagerMySQL(self.db)
        self.reminder = ReminderSystemMySQL(self.db)
        self.image_manager = ImageManagerMySQL(self.db, 'uploads/images')

        # 改为按用户ID存储对话历史的字典
        self.conversation_history = {}  # {user_id: [conversation_list]}

        self.config = self.load_config()
        self.model_type = self.config.get('model_type', 'simple')
        self.api_key = self.config.get('api_key', '')
        
    def load_config(self):
        """加载AI配置"""
        config_file = 'ai_config.json'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'model_type': 'simple',
            'model_name': 'simple-rules',
            'temperature': 0.5,
            'max_tokens': 300
        }
    
    def get_smart_context(self, user_message, user_id=None):
        """智能两阶段搜索：先找相关数据，再给AI"""
        keywords = []
        numbers = re.findall(r'\d+', user_message)
        keywords.extend(numbers)

        important_words = [
            '贷款', '公积金', '政策', '会议', '报告', '计划', '任务', '工作',
            '额度', '房屋', '套数', '调整', '材料', '方案', '总结',
            '心情', '老公', '老婆', '生气', '伯乐', '手机', '电话', '号码',
            '高俊', '金荣莹', '名字', '叫', '今天', '昨天', '最近'
        ]
        for word in important_words:
            if word in user_message:
                keywords.append(word)

        # 智能日期扩展：如果用户输入日期相关的查询，扩展关键词
        date_keywords = self._expand_date_keywords(user_message)
        keywords.extend(date_keywords)

        relevant_chats = []
        if keywords:
            for keyword in keywords:
                results = self.memory.search_by_keyword(keyword, user_id=user_id)
                relevant_chats.extend(results)

        if not relevant_chats:
            relevant_chats = self.memory.get_recent_conversations(10, user_id=user_id)

        seen = set()
        unique_chats = []
        for chat in relevant_chats:
            chat_id = f"{chat['timestamp']}{chat['content']}"
            if chat_id not in seen:
                seen.add(chat_id)
                unique_chats.append(chat)

        relevant_plans = []
        all_plans = self.planner.list_plans(user_id=user_id)
        # 过滤掉已完成的任务
        pending_plans = [p for p in all_plans if p.get('status') not in ['completed', '已完成']]
        if keywords:
            for plan in pending_plans:
                for keyword in keywords:
                    if (keyword in plan['title'] or
                        keyword in plan['description'] or
                        keyword in str(plan.get('deadline', ''))):
                        relevant_plans.append(plan)
                        break
        else:
            relevant_plans = [p for p in all_plans if p['status'] not in ['已完成', '已取消']]
        
        context = f"""你是个人助手AI，严格基于用户的记录和计划回答问题。

重要规则：
1. 基于下方的聊天记录和计划列表来回答问题
2. 当用户查询日期相关的任务/工作时，关键词如"明天"、"后天"、"今天"都应与计划中的相对时间描述匹配
3. 用户问"12月9日有哪些工作"应该对应计划中的"明天 (2025-12-09)"（如果今天是12月8日）
4. 如果记录和计划中都没有相关信息，明确告知"没有找到相关记录"
5. 不要推测、假设或编造任何信息
6. 简洁准确地回答

当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

相关聊天记录({len(unique_chats)}条):
"""
        
        for chat in unique_chats[:15]:
            context += f"[{chat['timestamp']}] {chat['content']}\n"
        
        if relevant_plans:
            context += f"\n相关计划({len(relevant_plans)}个):\n"
            for plan in relevant_plans[:10]:
                # 将截止日期转换为相对时间描述
                relative_time = self._get_relative_time_desc(plan['deadline'])
                context += f"- [{plan['status']}] {plan['title']} (截止:{relative_time}, {plan['priority']})\n"

        return context

    def _get_relative_time_desc(self, deadline_str):
        """将截止日期转换为相对时间描述（今天、明天、后天等）"""
        if not deadline_str:
            return "未设置"

        try:
            # 解析截止日期
            if isinstance(deadline_str, str):
                deadline_date = datetime.strptime(deadline_str.split()[0], '%Y-%m-%d').date()
            else:
                deadline_date = deadline_str.date() if hasattr(deadline_str, 'date') else deadline_str

            # 获取今天的日期
            today = datetime.now().date()

            # 计算天数差
            delta = (deadline_date - today).days

            if delta == 0:
                return f"今天 ({deadline_str.split()[0]})"
            elif delta == 1:
                return f"明天 ({deadline_str.split()[0]})"
            elif delta == 2:
                return f"后天 ({deadline_str.split()[0]})"
            elif delta == -1:
                return f"昨天 ({deadline_str.split()[0]})"
            elif delta < -1:
                return f"{abs(delta)}天前 ({deadline_str.split()[0]})"
            elif delta <= 7:
                return f"{delta}天后 ({deadline_str.split()[0]})"
            else:
                return deadline_str.split()[0]
        except:
            return deadline_str

    def parse_relative_time(self, time_str):
        """将相对时间转换为绝对日期

        支持的格式：
        - 明天、后天、大后天
        - 明早、明日
        - 今天、今日
        - 下周X、本周X
        - X天后

        特殊处理：
        - "明早"：如果当前时间在早上6点前，指今天；否则指明天
        """
        if not time_str or time_str == '':
            return ''

        # 如果已经是日期格式，直接返回
        if re.match(r'\d{4}-\d{2}-\d{2}', time_str):
            return time_str

        now = datetime.now()
        time_str = time_str.strip()
        current_hour = now.hour

        # 处理"明早" - 智能判断
        if '明早' in time_str:
            if current_hour < 6:
                return now.strftime('%Y-%m-%d')
            else:
                return (now + timedelta(days=1)).strftime('%Y-%m-%d')

        # 处理"明天"、"明日"、"明晚"
        elif any(word in time_str for word in ['明天', '明日', '明晚']):
            return (now + timedelta(days=1)).strftime('%Y-%m-%d')

        # 处理"后天"
        elif '后天' in time_str:
            return (now + timedelta(days=2)).strftime('%Y-%m-%d')

        # 处理"大后天"
        elif '大后天' in time_str:
            return (now + timedelta(days=3)).strftime('%Y-%m-%d')

        # 处理"今早"、"今天"、"今日"、"今晚"
        elif any(word in time_str for word in ['今天', '今日', '今早', '今晚', '今夜']):
            return now.strftime('%Y-%m-%d')

        # 处理"昨天"
        elif '昨天' in time_str:
            return (now - timedelta(days=1)).strftime('%Y-%m-%d')

        # 处理"X天后"
        match = re.search(r'(\d+)天后', time_str)
        if match:
            days = int(match.group(1))
            return (now + timedelta(days=days)).strftime('%Y-%m-%d')

        # 【新增】处理时段短语 - 隐含日期（返回当前日期）
        # 这些词如果单独出现或与任务一起出现，表示当天完成
        if any(word in time_str for word in ['下午', '上午', '早上', '晚上', '夜间', '夜里']):
            # "下午"、"上午"等时段短语 -> 当天
            return now.strftime('%Y-%m-%d')

        # 处理"下周"
        if '下周' in time_str:
            return (now + timedelta(days=7)).strftime('%Y-%m-%d')

        # 处理"本周末"、"周末"
        if '周末' in time_str:
            days_until_sunday = (6 - now.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7
            return (now + timedelta(days=days_until_sunday)).strftime('%Y-%m-%d')

        # 如果无法解析，返回空字符串
        return ''

    def _expand_date_keywords(self, user_message):
        """扩展日期相关的关键词

        例如：
        - "12月9日" -> ["2025-12-09", "12-09", "12月9日"]
        - "明天" -> ["2025-12-09", "明天", "明日"]
        """
        expanded = []
        now = datetime.now()
        current_year = now.year

        # 匹配"X月X日"格式
        date_match = re.search(r'(\d{1,2})月(\d{1,2})日', user_message)
        if date_match:
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            # 添加完整日期格式
            expanded.append(f"{current_year}-{month:02d}-{day:02d}")
            expanded.append(f"{month:02d}-{day:02d}")
            expanded.append(f"{month}月{day}日")

        # 匹配相对时间词，转换为绝对日期
        relative_time_words = {
            '今天': now,
            '今日': now,
            '明天': now + timedelta(days=1),
            '明日': now + timedelta(days=1),
            '后天': now + timedelta(days=2),
            '大后天': now + timedelta(days=3),
            '昨天': now - timedelta(days=1),
        }

        for word, date_obj in relative_time_words.items():
            if word in user_message:
                expanded.append(date_obj.strftime('%Y-%m-%d'))
                expanded.append(date_obj.strftime('%m-%d'))
                # 也添加原词
                expanded.append(word)

        return expanded

    def chat_with_openai_compatible(self, user_message, context, user_id=None):
        """使用OpenAI兼容API（通义千问等）"""
        # ✅ 安全检查：确保user_id存在，未登录用户无法使用API
        if user_id is None:
            return "❌ 请先登录后再使用此功能"

        try:
            import requests

            base_url = self.config.get('base_url', 'https://api.openai.com/v1')
            url = base_url.rstrip('/') + '/chat/completions'

            messages = [{"role": "system", "content": context}]

            # 获取该用户的对话历史（仅包含最近的对话，不包含已完成的任务查询）
            user_history = self.conversation_history.get(user_id or 'default', [])
            for hist in user_history[-3:]:
                messages.append({"role": "user", "content": hist['user']})
                messages.append({"role": "assistant", "content": hist['assistant']})

            messages.append({"role": "user", "content": user_message})
            
            headers = {
                "Authorization": f"Bearer {self.config.get('api_key', '')}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.config.get('model_name', 'gpt-3.5-turbo'),
                "messages": messages,
                "temperature": self.config.get('temperature', 0.5),
                "max_tokens": self.config.get('max_tokens', 300)
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"API错误 ({response.status_code}): {response.text[:200]}"
        
        except ImportError:
            return "⚠️ 需要安装 requests\n\n" + self._fallback_response(user_message, user_id)
        except Exception as e:
            print(f"API错误: {e}")
            return f"⚠️ API调用失败: {str(e)}\n\n{self._fallback_response(user_message, user_id)}"
    
    def chat(self, user_message, user_id=None):
        """处理用户消息"""
        # 检查是否是快捷命令
        shortcut_result = self.process_shortcut_command(user_message, user_id)
        if shortcut_result:
            return shortcut_result

        context = self.get_smart_context(user_message, user_id)

        try:
            if self.model_type == 'openai':
                response = self.chat_with_openai_compatible(user_message, context, user_id)
            else:
                response = self._fallback_response(user_message, user_id)
        except Exception as e:
            response = f"⚠️ AI暂不可用\n\n{self._fallback_response(user_message, user_id)}"

        # 将对话添加到该用户的历史中
        user_key = user_id or 'default'
        if user_key not in self.conversation_history:
            self.conversation_history[user_key] = []

        self.conversation_history[user_key].append({
            'user': user_message,
            'assistant': response,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        # 保存用户消息到数据库
        try:
            self.memory.add_message('user', user_message, user_id=user_id)
            # 保存AI回复到数据库
            self.memory.add_message('assistant', response, user_id=user_id)
        except Exception as e:
            print(f"⚠️ 保存聊天记录失败: {e}")

        # 从用户消息中提取计划信息
        detected_plans = self.extract_plans_from_message(user_message)

        # 从用户消息中提取提醒信息并创建
        detected_reminders = self.extract_and_create_reminders(user_message, user_id)

        # 检测并完成工作计划
        completed_plans = self.detect_and_complete_plans(user_message, user_id)

        return {
            'response': response,
            'detected_plans': detected_plans,
            'detected_reminders': detected_reminders,
            'completed_plans': completed_plans
        }

    def process_shortcut_command(self, user_message, user_id=None):
        """处理快捷命令 - 工作: 和 计划:（兼容中文冒号）"""
        message = user_message.strip()

        # 检查是否是"工作:"或"工作："命令（兼容中英文冒号）
        if message.startswith('工作:') or message.startswith('工作：'):
            # 移除"工作:"或"工作："前缀
            if message.startswith('工作:'):
                content = message[3:].strip()
            else:
                content = message[3:].strip()

            if content:
                try:
                    # 解析工作内容，提取时间信息
                    work_data = self._parse_work_shortcut(content)

                    # 将相对时间转换为绝对日期
                    absolute_date = ''
                    if work_data['deadline']:
                        absolute_date = self.parse_relative_time(work_data['deadline'])
                        # 如果转换失败，保留原始文本
                        if not absolute_date:
                            absolute_date = work_data['deadline']
                    else:
                        # 【新增】如果没有显式的截止日期，使用当前日期
                        # 这样可以捕获"下午准备..."这样的记录
                        absolute_date = datetime.now().strftime('%Y-%m-%d')

                    # 存储带有绝对日期的工作记录
                    formatted_content = content
                    if absolute_date:
                        formatted_content = f"[{absolute_date}] {work_data['task']}"

                    self.memory.add_message('user', f"工作: {formatted_content}", user_id=user_id)

                    # **新增：同时保存到工作计划表**
                    # 【重要改进】现在总是保存，不再需要 if absolute_date 条件
                    try:
                        # 【修复晚上/等时段丢失问题】保留原始的时段短语
                        # 生成包含时段词的完整title，用于查询匹配
                        task_title = work_data['task']
                        if work_data['deadline']:
                            # 如果有时段词（晚上、上午等），添加到title前面
                            time_phrase = work_data['deadline']
                            # 检查是否已包含该时段词
                            if time_phrase not in task_title:
                                task_title = f"{time_phrase}{task_title}"

                        # 保存为工作计划（使用推导的截止日期或当前日期）
                        self.planner.add_plan(
                            title=task_title,  # ✅ 现在包含时段词
                            description='通过"工作:"命令记录',
                            deadline=absolute_date,
                            priority='medium',
                            status='pending',
                            user_id=user_id
                        )
                        print(f"✅ 工作已同步到计划表: {task_title} (截止日期: {absolute_date})")
                    except Exception as e:
                        print(f"⚠️ 同步到工作计划失败: {e}")

                    response = f"✅ 工作内容已记录：{work_data['task']}"
                    if work_data['deadline']:
                        # 只有当用户明确提供了时间时，才在响应中显示
                        # 显示时显示原始相对时间，但也注明绝对日期
                        if work_data['deadline'] != absolute_date:
                            response += f"\n⏰ 时间：{work_data['deadline']} ({absolute_date})"
                        else:
                            response += f"\n⏰ 时间：{absolute_date}"
                    else:
                        # 没有显式时间时，显示为今天
                        response += f"\n⏰ 截止日期：{absolute_date} (今天)"

                    return {
                        'response': response,
                        'detected_plans': [],
                        'is_shortcut': True
                    }
                except Exception as e:
                    return {
                        'response': f"❌ 记录失败: {e}",
                        'detected_plans': [],
                        'is_shortcut': True
                    }
            else:
                return {
                    'response': "⚠️ 请提供工作内容：工作: (你的工作内容)",
                    'detected_plans': [],
                    'is_shortcut': True
                }

        # 检查是否是"计划:"或"计划："命令（兼容中英文冒号）
        elif message.startswith('计划:') or message.startswith('计划：'):
            # 移除"计划:"或"计划："前缀
            if message.startswith('计划:'):
                content = message[3:].strip()
            else:
                content = message[3:].strip()

            if content:
                try:
                    # 尝试从内容中提取计划信息
                    # 格式: 计划: 标题 (截止日期) [优先级]
                    # 例如: 计划: 完成报表 (明天) 高

                    # 简单解析
                    plan_data = self._parse_plan_shortcut(content)

                    # 如果没有设置截止日期，使用当前日期作为默认值
                    deadline = plan_data['deadline'] if plan_data['deadline'] else datetime.now().strftime('%Y-%m-%d')

                    self.planner.add_plan(
                        title=plan_data['title'],
                        description=content,
                        deadline=deadline,
                        priority=plan_data['priority'],
                        status='pending',
                        user_id=user_id
                    )

                    response = f"✅ 计划已添加：{plan_data['title']}"
                    if plan_data['deadline']:
                        response += f"\n📅 截止：{plan_data['deadline']}"
                    if plan_data['priority'] != 'medium':
                        response += f"\n🎯 优先级：{plan_data['priority']}"

                    return {
                        'response': response,
                        'detected_plans': [plan_data],
                        'is_shortcut': True
                    }
                except Exception as e:
                    return {
                        'response': f"❌ 计划添加失败: {e}",
                        'detected_plans': [],
                        'is_shortcut': True
                    }
            else:
                return {
                    'response': "⚠️ 请提供计划内容：计划: (标题) (截止日期) [优先级]",
                    'detected_plans': [],
                    'is_shortcut': True
                }

        return None

    def _parse_plan_shortcut(self, content):
        """解析计划快捷命令的内容

        支持格式:
        - 完成报表
        - 完成报表 明天
        - 完成报表 2025-12-08
        - 完成报表 本月底
        - 完成报表 明天 高
        - 完成报表 (明天)
        - 完成报表 (明天) 高
        """
        import re

        result = {
            'title': content,
            'deadline': '',
            'priority': 'medium'
        }

        # 匹配格式: 标题 (日期) 优先级 或 标题 日期 优先级
        # 示例: 完成报表 明天 高 或 完成报表 (2025-12-08) 高

        # 首先检查是否有括号中的日期
        paren_match = re.search(r'\s*\(([^)]+)\)', content)
        if paren_match:
            deadline = paren_match.group(1)
            # 移除括号部分，保留标题
            title = content[:paren_match.start()].strip()
            remaining = content[paren_match.end():].strip()
            result['deadline'] = deadline
            result['title'] = title
            content = remaining
        else:
            # 尝试从末尾提取日期和优先级
            # 检查是否包含时间词或优先级词
            time_keywords = ['明天', '后天', '这周', '下周', '本周', '下月', '本月', '月底', '年底', '周末']
            priority_keywords = {'高': 'high', '中': 'medium', '低': 'low', '紧急': 'urgent'}

            parts = content.split()

            # 从后往前查找优先级
            for i in range(len(parts) - 1, -1, -1):
                if parts[i] in priority_keywords:
                    result['priority'] = priority_keywords[parts[i]]
                    result['title'] = ' '.join(parts[:i])
                    remaining = ' '.join(parts[i+1:])
                    if remaining:
                        result['deadline'] = remaining
                    break

            # 如果还没找到，再查找时间词
            if result['priority'] == 'medium' and result['deadline'] == '':
                for i in range(len(parts) - 1, -1, -1):
                    if parts[i] in time_keywords:
                        result['title'] = ' '.join(parts[:i+1])
                        result['deadline'] = parts[i]
                        break

        # 清理标题
        result['title'] = result['title'].strip()
        if not result['title']:
            result['title'] = content

        return result

    def _parse_work_shortcut(self, content):
        """解析工作快捷命令的内容，提取时间信息

        支持格式:
        - 起草政策分析报告
        - 后天起草政策分析报告
        - 起草政策分析报告 后天
        - 起草政策分析报告 (后天)
        - 下午准备管委会会议 (包含时段短语)
        """
        import re

        result = {
            'task': content,
            'deadline': ''
        }

        # 时间关键词列表 - 包括相对日期和时段短语
        time_keywords = [
            # 相对日期
            '明天', '后天', '大后天', '今天', '昨天',
            # 时段短语（重要：用于隐含日期推断）
            '早上', '上午', '下午', '晚上', '夜间', '夜里',
            '今晚', '今天晚上', '明晚', '明天晚上',
            # 周相关
            '这周', '下周', '周末', '本周', '上周',
            # 月相关
            '下月', '本月', '上月', '月底', '月初', '月中',
            # 年相关
            '年底', '年初', '这年',
            # 具体日期（周几）
            '周一', '周二', '周三', '周四', '周五', '周六', '周日'
        ]

        # 首先检查是否有括号中的时间
        paren_match = re.search(r'\(([^)]+)\)', content)
        if paren_match:
            potential_time = paren_match.group(1).strip()
            if potential_time in time_keywords:
                result['deadline'] = potential_time
                result['task'] = content[:paren_match.start()].strip() + content[paren_match.end():].strip()
                return result

        # 从内容中查找时间词
        for time_word in time_keywords:
            if time_word in content:
                # 找到时间词后分割
                idx = content.find(time_word)
                before = content[:idx].strip()
                after = content[idx + len(time_word):].strip()

                # 判断时间词是在开头还是结尾
                if before == '':
                    # 时间词在开头："后天起草政策分析报告"
                    result['deadline'] = time_word
                    result['task'] = after
                else:
                    # 时间词在中间或结尾："起草政策分析报告 后天"
                    if after == '':
                        result['task'] = before
                    else:
                        result['task'] = before + after
                    result['deadline'] = time_word

                # 清理任务描述
                result['task'] = result['task'].replace('  ', ' ').strip()
                if result['task']:
                    break

        return result


    def clear_conversation(self, user_id=None):
        """清空对话历史"""
        user_key = user_id or 'default'
        if user_key in self.conversation_history:
            self.conversation_history[user_key] = []
        return True

    def extract_plans_from_message(self, user_message):
        """从用户消息中提取工作计划信息"""
        plans = []

        # 首先分句处理
        sentences = re.split(r'[，。；！？\n]+', user_message)

        # 定义关键行为词和时间词
        action_keywords = ['做', '完成', '提交', '交付', '处理', '审核', '检查', '修改', '实现']
        time_keywords = ['明天', '后天', '这周', '下周', '本周', '下月', '本月', '月底', '年底', '今年底', '周末', '个月', '天内']
        priority_keywords = ['重要', '紧急', '急', '优先', '重点', '关键', '首先']

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 2:
                continue

            # 判断是否包含计划信息
            has_plan = any(keyword in sentence for keyword in action_keywords)

            if not has_plan:
                # 如果没有行为词，跳过
                continue

            # 提取任务信息
            title = sentence
            deadline = ''
            priority = '中'

            # 查找时间词
            for time_word in time_keywords:
                if time_word in sentence:
                    deadline = time_word
                    # 移除时间词和关键词,保留任务内容
                    title = re.sub(time_word, '', title)
                    break

            # 检查优先级
            if any(kw in sentence for kw in priority_keywords):
                priority = '高'

            # 清理标题：移除虚词、连接词等
            remove_words = ['我', '要', '在', '于', '到', '的', '前', '内', '并', '且', '，', '。', '；', '！', '？', '也', '还']
            for word in remove_words:
                title = title.replace(word, ' ')

            # 进一步清理：移除所有行为词前面的内容（通常标题从行为词开始）
            for action in action_keywords:
                if action in title:
                    # 取行为词之后的部分
                    idx = title.find(action)
                    if idx >= 0:
                        title = title[idx:]
                        break

            # 最后的清理
            title = re.sub(r'\s+', ' ', title).strip()  # 统一空格
            title = title[:35]  # 限制长度

            # 避免重复
            if len(title) >= 2 and not any(p['title'] == title for p in plans):
                plans.append({
                    'title': title,
                    'deadline': deadline,
                    'priority': priority,
                    'source': 'AI识别自对话'
                })

        return plans

    def extract_and_create_reminders(self, user_message, user_id=None):
        """从用户消息中提取提醒信息并创建系统提醒"""
        reminders = []

        # 提醒关键词
        reminder_keywords = ['提醒', '提示', '通知', '叫我', '告诉我']

        # 检查是否包含提醒意图
        has_reminder = any(kw in user_message for kw in reminder_keywords)

        if not has_reminder:
            return reminders

        # 提取时间信息的正则表达式
        time_patterns = [
            r'(\d+)分钟后',
            r'(\d+)秒后',
            r'(\d+)小时后',
            r'明天(\d+):(\d+)',
            r'后天(\d+):(\d+)',
            r'明天',
            r'后天'
        ]

        # 提取提醒内容
        # 移除提醒关键词和时间词,剩下的就是要提醒的内容
        content = user_message
        for kw in reminder_keywords:
            content = content.replace(kw, '')

        # 提取时间
        remind_time = None
        for pattern in time_patterns:
            match = re.search(pattern, user_message)
            if match:
                remind_time = match.group(0)
                content = content.replace(remind_time, '')
                break

        # 清理内容
        remove_words = ['我', '你', '的', '了', '吗', '呢', '吧', '啊', '一下', '我要', '要']
        for word in remove_words:
            content = content.replace(word, '')
        content = content.strip('，。；！？、 ')

        # 如果提取到了时间和内容，创建提醒
        if remind_time and content and user_id:
            try:
                # 获取全局调度器
                scheduler = get_global_scheduler(db_manager=self.db)

                # 先解析自然语言时间
                parsed_time = scheduler.parse_reminder_time(remind_time)
                if not parsed_time:
                    print(f"⚠️ 无法解析时间: {remind_time}")
                    return reminders

                # 调用调度器创建提醒
                result = scheduler.add_reminder(
                    user_id=user_id,
                    message=content,
                    remind_time=parsed_time,  # 使用解析后的时间对象
                    remind_type='once'
                )

                if result.get('status') == 'success':
                    reminders.append({
                        'content': content,
                        'time': remind_time,
                        'created': True
                    })
                    print(f"✅ 已创建提醒: {content} - {remind_time}")
                else:
                    print(f"⚠️ 创建提醒失败: {result.get('message')}")

            except Exception as e:
                print(f"❌ 创建提醒时出错: {e}")

        return reminders

    def detect_and_complete_plans(self, user_message, user_id=None):
        """检测并完成工作计划

        识别用户表达如：
        - "第3项完成了"
        - "完成第3项"
        - "第3个任务做完了"
        - "明早8点半上班完成了"
        """
        if user_id is None:
            return []

        # 完成意图的关键词
        complete_keywords = ['完成', '做完', '做好', '已完成', '搞定', '弄好', '结束']

        # 检查是否包含完成意图
        has_complete_intent = any(kw in user_message for kw in complete_keywords)
        if not has_complete_intent:
            return []

        completed_plans = []

        # 获取用户的未完成计划
        all_plans = self.planner.list_plans(user_id=user_id)
        pending_plans = [p for p in all_plans if p['status'] not in ['已完成', '已取消', 'completed', 'cancelled']]

        if not pending_plans:
            return []

        # 方式1: 提取序号 "第X项"、"第X个"
        number_patterns = [
            r'第\s*(\d+)\s*[项个条件]',
            r'(\d+)\s*[项个条件]',
            r'工作\s*(\d+)',
            r'任务\s*(\d+)',
        ]

        for pattern in number_patterns:
            match = re.search(pattern, user_message)
            if match:
                index = int(match.group(1)) - 1  # 转换为0-based索引
                if 0 <= index < len(pending_plans):
                    plan = pending_plans[index]
                    # 更新计划状态
                    success = self.planner.update_plan(
                        plan['id'],
                        user_id=user_id,
                        status='completed'
                    )
                    if success:
                        completed_plans.append({
                            'id': plan['id'],
                            'title': plan['title'],
                            'method': 'index'
                        })
                        print(f"✅ 已标记计划为完成: {plan['title']}")
                        # 清空该用户的对话历史，避免AI参考过时信息
                        self.clear_conversation(user_id=user_id)
                        # 删除数据库中包含已完成任务标题的消息记录
                        self.memory.delete_messages_by_keywords([plan['title']], user_id=user_id)
                    return completed_plans

        # 方式2: 通过关键词匹配标题
        # 提取用户消息中的关键词（排除完成相关的词）
        msg_clean = user_message
        for kw in complete_keywords + ['第', '项', '个', '工作', '任务', '了', '的', '我', '要', '在']:
            msg_clean = msg_clean.replace(kw, ' ')

        # 提取可能的关键词
        keywords = [w.strip() for w in msg_clean.split() if len(w.strip()) >= 2]

        # 尝试匹配计划标题
        for keyword in keywords:
            for plan in pending_plans:
                title = plan.get('title', '')
                if keyword in title or title in user_message:
                    # 找到匹配的计划
                    success = self.planner.update_plan(
                        plan['id'],
                        user_id=user_id,
                        status='completed'
                    )
                    if success:
                        completed_plans.append({
                            'id': plan['id'],
                            'title': plan['title'],
                            'method': 'keyword',
                            'keyword': keyword
                        })
                        print(f"✅ 已标记计划为完成(关键词匹配): {plan['title']}")
                        # 清空该用户的对话历史，避免AI参考过时信息
                        self.clear_conversation(user_id=user_id)
                        # 删除数据库中包含已完成任务标题的消息记录
                        self.memory.delete_messages_by_keywords([plan['title']], user_id=user_id)
                        return completed_plans

        return completed_plans

    def _fallback_response(self, user_message, user_id=None):
        """简单模式回答"""
        # ✅ 安全检查：确保user_id存在，未登录用户无法访问数据库
        if user_id is None:
            return "❌ 请先登录后再使用此功能"

        message_lower = user_message.lower()
        
        keywords = []
        for word in ['贷款', '公积金', '政策', '会议', '报告', '计划', '任务', '工作',
                     '心情', '老公', '老婆', '手机', '号码', '高俊', '金荣莹']:
            if word in user_message:
                keywords.append(word)
        
        numbers = re.findall(r'\d+', user_message)
        keywords.extend(numbers)
        
        if any(w in message_lower for w in ['说过', '提到', '记录', '聊天', '内容']):
            if keywords:
                keyword = keywords[0]
                results = self.memory.search_by_keyword(keyword, user_id=user_id)
                
                if results:
                    response = f"🔍 找到 {len(results)} 条包含「{keyword}」的记录：\n\n"
                    for i, chat in enumerate(results[:10], 1):
                        response += f"{i}. [{chat['timestamp']}] {chat['content']}\n"
                    
                    if len(results) > 10:
                        response += f"\n...还有 {len(results) - 10} 条相关记录"
                    
                    return response
                else:
                    return f"没有找到包含「{keyword}」的记录"
            else:
                recent = self.memory.get_recent_conversations(10, user_id=user_id)
                response = f"📝 最近10条聊天:\n\n"
                for i, chat in enumerate(recent, 1):
                    response += f"{i}. [{chat['timestamp']}] {chat['content']}\n"
                return response
        
        elif any(w in message_lower for w in ['计划', '工作', '任务']):
            plans = self.planner.list_plans(user_id=user_id)
            
            if keywords:
                keyword = keywords[0]
                plans = [p for p in plans if keyword in p['title'] or keyword in p['description']]
            
            if '未完成' in message_lower:
                plans = [p for p in plans if p['status'] not in ['已完成', '已取消']]
            
            if plans:
                response = f"📅 找到 {len(plans)} 个计划:\n\n"
                for plan in plans[:10]:
                    response += f"• [{plan['status']}] {plan['title']}\n"
                    response += f"  截止: {plan['deadline']} | {plan['priority']}\n\n"
                return response
            else:
                return "没有找到相关计划"
        
        else:
            return """👋 你好！我可以帮你：

📝 查聊天: "我说过XX吗"
📅 查计划: "我有XX计划吗"
⏰ 查提醒: "我有什么待办"
📊 总结: "帮我总结"

试试问我具体问题吧！"""
