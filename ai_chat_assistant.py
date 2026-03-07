#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI聊天助手 - 智能两阶段搜索 (MySQL版本)"""

import json
import os
import re
from datetime import datetime, timedelta
from enum import Enum
# 使用MySQL版本的管理器
from mysql_manager import (
    MySQLManager,
    MemoryManagerMySQL,
    WorkPlanManagerMySQL,
    ReminderSystemMySQL,
    ImageManagerMySQL,
    FileManagerMySQL
)
# 导入新的提醒调度器
from reminder_scheduler import get_global_scheduler
# 导入命令系统
from command_system import get_command_router
# 导入类别系统管理器
from category_system import WorkTaskManager, DailyRecordManager, CategoryManager
# 导入开发日志管理器
try:
    from development_log import DevelopmentLogManager
except ImportError:
    DevelopmentLogManager = None


class ConversationState(Enum):
    """对话状态枚举"""
    IDLE = "idle"                      # 空闲状态
    WAITING_CONFIRMATION = "waiting"   # 等待用户确认
    EXECUTING = "executing"            # 执行中
    WAITING_INPUT = "input"            # 等待补充信息


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
        self.file_manager = FileManagerMySQL(self.db, 'uploads/files')

        # 初始化工作任务管理器（新分类系统）
        self.work_task_manager = WorkTaskManager('mysql_config.json')

        # 初始化开发日志管理器
        if DevelopmentLogManager:
            try:
                self.dev_log = DevelopmentLogManager()
            except Exception as e:
                print(f"初始化开发日志管理器失败: {e}")
                self.dev_log = None
        else:
            self.dev_log = None

        # 改为按用户ID存储对话历史的字典
        self.conversation_history = {}  # {user_id: [conversation_list]}

        # ✨ 新增：内存中存储session验证状态（关闭网页后失效）
        # 格式：{token: {'verified': True/False, 'is_default_code': True/False}}
        self.session_security_status = {}

        self.config = self.load_config()
        self.model_type = self.config.get('model_type', 'simple')
        # 敏感关键词列表（用于触发安全验证）
        self.sensitive_keywords = [
            # 账号密码类（直接查询）
            '账号', '密码', '用户名', '登录', '注册', '验证码',
            # 个人信息类（直接查询）
            '生日', '身份证', '电话', '号码', '手机',
            # 其他敏感词
            '银行', '卡号', '支付', '密保',
            # 需要特别保护的应用/平台（间接查询）
            '稿定', '淘宝', '支付宝', '微信', '抖音', 'verve'
        ]
        
        # 高优先级精确匹配关键词（完整短语，避免误判）
        self.exact_match_keywords = [
            '我的信息', '个人信息', '我是谁', 
            '我的生日', '我的密码', '我的账号', '我的电话', '我的手机',
            '我的名字', '我的姓名', '关于我', '我的资料',
            '稿定相关', '淘宝相关', '支付宝相关', '微信相关'
        ]

        self.api_key = self.config.get('api_key', '')
        
        # 待验证的查询缓存 {user_id: original_query}
        self.pending_verification_queries = {}

        # ✨ 上下文跟踪器：记录每个用户最后一次AI显示的内容
        # 格式：{user_id: {'type': 'work_list'/'plan_list'/etc, 'data': [...], 'timestamp': ...}}
        self.last_response_context = {}

        # ✨ 新增：待确认的计划和提醒 {user_id: {'plans': [...], 'reminders': [...]}}
        self.pending_confirmations = {}

        # ✨ 新增：对话状态管理 {user_id: ConversationState}
        self.conversation_states = {}

        # ✨ 新增：状态上下文数据 {user_id: {...}}
        self.state_context = {}


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

    def get_all_work_items(self, user_id, status_filter=None):
        """
        查询 work_tasks 表的数据（已完成 work_plans 数据迁移）

        Args:
            user_id: 用户ID
            status_filter: 状态过滤 ('pending', 'completed', None=全部)

        Returns:
            list: 工作项列表，统一格式
        """
        all_items = []

        # 查询 work_tasks 表（已包含迁移的 work_plans 数据）
        try:
            tasks = self.work_task_manager.list_tasks(user_id=user_id)
            for task in tasks:
                # 统一数据格式
                item = {
                    'id': task.get('id'),
                    'title': task.get('title', ''),
                    'content': task.get('content', ''),
                    'description': task.get('content', ''),  # 别名
                    'status': task.get('status', 'pending'),
                    'priority': task.get('priority', 'medium'),
                    'due_date': task.get('due_date'),
                    'deadline': task.get('due_date'),  # 别名
                    'created_at': task.get('created_at', ''),
                    'updated_at': task.get('updated_at', ''),
                    'completed_at': task.get('completed_at', ''),
                    'source': 'work_tasks',  # 标识来源
                    'subcategory_id': task.get('subcategory_id'),
                    'sort_order': task.get('sort_order', 0),
                    'tags': task.get('tags')  # 支持标签
                }
                all_items.append(item)
        except Exception as e:
            print(f"⚠️ 查询 work_tasks 失败: {e}")

        # 根据 status_filter 过滤
        if status_filter == 'pending':
            all_items = [item for item in all_items
                        if item['status'] not in ['completed', '已完成', 'cancelled', '已取消']]
        elif status_filter == 'completed':
            all_items = [item for item in all_items
                        if item['status'] in ['completed', '已完成']]

        # ✨ 按 sort_order 降序排序（数值越大越靠前），然后按创建时间倒序排序
        all_items.sort(key=lambda x: (x.get('sort_order', 0), x.get('created_at', '')), reverse=True)

        return all_items

    def _search_daily_records(self, keyword, user_id):
        """
        ✨ 搜索daily_records表（记录类别）
        """
        try:
            # 使用query方法而不是直接使用cursor
            sql = """
                SELECT dr.id, dr.title, dr.content, dr.created_at, dr.subcategory_id, dr.sort_order, s.name as subcategory_name
                FROM daily_records dr
                LEFT JOIN subcategories s ON dr.subcategory_id = s.id
                WHERE dr.user_id = %s AND (dr.title LIKE %s OR dr.content LIKE %s) AND dr.status != 'completed'
                ORDER BY dr.sort_order DESC, dr.created_at DESC
                LIMIT 20
            """
            results = self.db.query(sql, (user_id, f"%{keyword}%", f"%{keyword}%"))

            print(f"🔍 DEBUG _search_daily_records: keyword='{keyword}', user_id={user_id}, 找到{len(results)}条结果")
            if results:
                print(f"🔍 DEBUG: 第一条结果: {results[0]}")

            # 结果已经是字典格式
            return results
        except Exception as e:
            print(f"❌ 搜索daily_records出错: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _search_guestbook(self, keyword, user_id):
        """
        ✨ 搜索guestbook_messages表（留言墙）
        """
        try:
            # 使用query方法而不是直接使用cursor
            sql = """
                SELECT id, content, created_at, author_id
                FROM guestbook_messages
                WHERE owner_id = %s AND content LIKE %s
                ORDER BY created_at DESC
                LIMIT 20
            """
            results = self.db.query(sql, (user_id, f"%{keyword}%"))

            print(f"🔍 DEBUG _search_guestbook: keyword='{keyword}', user_id={user_id}, 找到{len(results)}条结果")
            if results:
                print(f"🔍 DEBUG: 第一条结果: {results[0]}")

            # 转换为统一格式
            records = []
            for row in results:
                records.append({
                    'id': row.get('id'),
                    'title': '留言墙',
                    'content': row.get('content'),
                    'created_at': row.get('created_at'),
                    'source': 'guestbook'
                })
            return records
        except Exception as e:
            print(f"❌ 搜索guestbook出错: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _clean_command_prefix(self, content):
        """
        清理消息内容中的命令前缀
        例如："保存: 内容" -> "内容"
        """
        if not content:
            return content

        # 定义需要清理的命令前缀
        command_prefixes = [
            '保存:', '保存：', '保存 ',
            '记录:', '记录：', '记录 ',
            '工作:', '工作：', '工作 ',
            '计划:', '计划：', '计划 ',
            '提醒:', '提醒：', '提醒 ',
            '查询:', '查询：', '查询 ',
        ]

        # 尝试移除前缀
        for prefix in command_prefixes:
            if content.startswith(prefix):
                return content[len(prefix):].strip()

        return content

    def _extract_keywords_from_message(self, user_message):
        """
        ✨ 改进的关键词提取：不依赖白名单，直接从用户输入提取所有有意义的词
        使用简单的中文分词策略
        """
        keywords = []

        # 1. 提取数字
        numbers = re.findall(r'\d+', user_message)
        keywords.extend(numbers)

        # 2. 提取中文词汇（长度2-10的连续中文字符）
        # 这样可以捕获任何中文词，包括"留言墙"、"图片"等
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,10}', user_message)
        keywords.extend(chinese_words)

        # ✨ 新增：对长词进行拆分，提取子词（解决"高俊相关"无法匹配"高俊"的问题）
        # 例如："高俊相关" -> ["高俊相关", "高俊", "相关"]
        # 定义常见的后缀词，用于智能拆分
        common_suffixes = {'相关', '有关', '关于', '方面', '问题', '情况', '事情', '内容', '信息', '资料', '记录'}

        for word in chinese_words:
            if len(word) > 2:
                # 优先检查是否以常见后缀结尾，如果是则提取前面的主体词
                for suffix in common_suffixes:
                    if word.endswith(suffix) and len(word) > len(suffix):
                        main_word = word[:-len(suffix)]
                        if main_word and main_word not in keywords:
                            keywords.append(main_word)

                # 拆分为2字词（但跳过明显无意义的组合）
                for i in range(len(word) - 1):
                    sub_word = word[i:i+2]
                    # 只添加不包含停用词的子词
                    if sub_word not in keywords and not any(stop in sub_word for stop in ['的', '了', '吗', '呢', '啊']):
                        keywords.append(sub_word)

        # 3. 提取英文词汇
        english_words = re.findall(r'[a-zA-Z]+', user_message)
        keywords.extend(english_words)

        # 4. 移除重复和过短的词
        keywords = list(set(keywords))
        keywords = [k for k in keywords if len(str(k)) >= 2]

        # 5. 定义停用词（无搜索意义的词）
        stopwords = {
            '的', '了', '吗', '呢', '啊', '哦', '嗯', '是', '有', '没有',
            '我', '你', '他', '她', '它', '们', '这', '那', '什么', '哪',
            '怎么', '为什么', '如何', '请', '谢谢', '好的', '可以', '不',
            '和', '或', '但', '因为', '所以', '如果', '那么', '一', '二',
            '三', '四', '五', '六', '七', '八', '九', '十', '百', '千',
            '万', '个', '件', '条', '张', '次', '下', '上', '中', '里',
            '在', '到', '从', '给', '被', '把', '让', '使', '叫', '要',
            '想', '能', '会', '应该', '必须', '可能', '也许', '就', '才',
            '又', '还', '都', '很', '太', '最', '比', '像', '似', '等',
            '及', '与', '而', '则', '否', '若', '乃', '矣', '焉', '耳',
            '查询', '搜索', '查找', '找', '看', '显示', '相关'  # ✨ 新增：过滤查询类动词
        }

        # 6. 过滤停用词
        keywords = [k for k in keywords if k not in stopwords]

        print(f"🔍 改进的关键词提取: 用户输入='{user_message}' -> 提取的关键词={keywords}")

        return keywords

    def highlight_keywords(self, text, keywords):
        """高亮显示关键词（使用markdown加粗）"""
        if not text or not keywords:
            return text

        highlighted_text = text
        for keyword in keywords:
            if keyword and len(keyword) > 0:
                # 使用markdown加粗语法高亮关键词
                # 使用正则替换，避免重复高亮
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                highlighted_text = pattern.sub(f"**{keyword}**", highlighted_text)

        return highlighted_text

    def calculate_relevance_score(self, content, keyword, timestamp=None):
        """计算内容与关键词的相关性评分"""
        if not content or not keyword:
            return 0.0

        score = 0.0
        content_lower = content.lower()
        keyword_lower = keyword.lower()

        # 1. 关键词出现次数（权重0.4）
        count = content_lower.count(keyword_lower)
        score += count * 0.4

        # 2. 关键词位置（标题/开头权重更高，权重0.3）
        if len(content) > 0:
            # 如果关键词在前50个字符内，加分
            if keyword_lower in content_lower[:50]:
                score += 0.3
            # 如果关键词在前20个字符内（标题位置），再加分
            if keyword_lower in content_lower[:20]:
                score += 0.2

        # 3. 完整匹配加分（权重0.2）
        if keyword_lower in content_lower:
            score += 0.2

        # 4. 时间衰减（越新越好，权重0.1）
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    record_time = datetime.strptime(timestamp[:10], '%Y-%m-%d')
                elif isinstance(timestamp, datetime):
                    record_time = timestamp
                else:
                    record_time = None

                if record_time:
                    days_old = (datetime.now() - record_time).days
                    # 时间衰减：1年内的记录得分最高
                    time_score = max(0, 0.1 * (1 - days_old / 365))
                    score += time_score
            except:
                pass

        return score

    def get_conversation_state(self, user_id):
        """获取用户的对话状态"""
        user_key = user_id or 'default'
        return self.conversation_states.get(user_key, ConversationState.IDLE)

    def set_conversation_state(self, user_id, state, context=None):
        """设置用户的对话状态"""
        user_key = user_id or 'default'
        self.conversation_states[user_key] = state
        if context:
            self.state_context[user_key] = context
        print(f"🔄 用户{user_key}状态变更: {state.value}")

    def clear_conversation_state(self, user_id):
        """清除用户的对话状态"""
        user_key = user_id or 'default'
        if user_key in self.conversation_states:
            del self.conversation_states[user_key]
        if user_key in self.state_context:
            del self.state_context[user_key]
        print(f"🔄 用户{user_key}状态已清除")

    def get_smart_context(self, user_message, user_id=None, ai_assistant_name='小助手'):
        """✨ 改进的智能两阶段搜索：不依赖白名单，直接搜索用户输入的所有关键词"""

        # ✨ 使用改进的关键词提取方法，替代旧的白名单机制
        keywords = self._extract_keywords_from_message(user_message)

        # 智能日期扩展：如果用户输入日期相关的查询，扩展关键词
        date_keywords = self._expand_date_keywords(user_message)
        keywords.extend(date_keywords)

        # 移除重复
        keywords = list(set(keywords))

        relevant_chats = []

        # ✨ 改进：直接使用提取的关键词搜索，不再过滤
        if keywords:
            for keyword in keywords[:5]:  # 增加到5个关键词以提高搜索覆盖率
                results = self.memory.search_by_keyword(keyword, user_id=user_id)
                relevant_chats.extend(results)
                print(f"🔍 搜索关键词'{keyword}'，找到{len(results)}条结果")

                # ✨ 新增：也搜索daily_records表（记录类别）
                try:
                    daily_results = self._search_daily_records(keyword, user_id)
                    if daily_results:
                        print(f"🔍 在daily_records中搜索'{keyword}'，找到{len(daily_results)}条结果")
                        # 将daily_records转换为消息格式
                        for record in daily_results:
                            relevant_chats.append({
                                'timestamp': record.get('created_at', ''),
                                'content': f"[记录] {record.get('title', '')} - {record.get('content', '')[:100]}",
                                'role': 'user',
                                'source': 'daily_records',
                                'record_id': record.get('id')
                            })
                except Exception as e:
                    print(f"🔍 搜索daily_records出错: {e}")

                # ✨ 新增：也搜索guestbook_messages表（留言墙）
                try:
                    guestbook_results = self._search_guestbook(keyword, user_id)
                    if guestbook_results:
                        print(f"🔍 在guestbook中搜索'{keyword}'，找到{len(guestbook_results)}条结果")
                        # 将guestbook转换为消息格式
                        for record in guestbook_results:
                            relevant_chats.append({
                                'timestamp': record.get('created_at', ''),
                                'content': f"[留言墙] {record.get('content', '')[:100]}",
                                'role': 'user',
                                'source': 'guestbook',
                                'record_id': record.get('id')
                            })
                except Exception as e:
                    print(f"🔍 搜索guestbook出错: {e}")

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
        all_items = self.get_all_work_items(user_id, status_filter=None)  # 获取所有工作（合并两表）
        # 过滤掉已完成的任务
        pending_plans = [p for p in all_items if p.get('status') not in ['completed', '已完成']]
        # 获取已完成的任务
        completed_plans = [p for p in all_items if p.get('status') in ['completed', '已完成']]

        print(f"🔍 DEBUG get_smart_context: user_message='{user_message}'")
        print(f"🔍 DEBUG: all_items数量={len(all_items)}, pending_plans数量={len(pending_plans)}, completed_plans数量={len(completed_plans)}")

        # 特殊处理：如果用户查询"已完成工作"，返回指定时间范围内已完成的计划
        if any(w in user_message for w in ['已完成工作', '已完成', '完成的工作', '显示已完成']):
            from datetime import timedelta

            # 提取时间范围（如"3个月"、"1周"、"30天"、"近2天"）
            days = 30  # 默认1个月
            if '3个月' in user_message or '三个月' in user_message:
                days = 90
            elif '2个月' in user_message or '两个月' in user_message:
                days = 60
            elif '1个月' in user_message or '一个月' in user_message:
                days = 30
            elif '1周' in user_message or '一周' in user_message:
                days = 7
            elif '今天' in user_message:
                days = 1
            else:
                # 尝试提取"近X天"或"X天"格式
                day_match = re.search(r'近?(\d+)天', user_message)
                if day_match:
                    days = int(day_match.group(1))

            time_ago = datetime.now() - timedelta(days=days)
            time_ago_str = time_ago.strftime('%Y-%m-%d')
            # 过滤指定时间范围内完成的工作
            recent_completed = []
            for p in completed_plans:
                if p.get('updated_at'):
                    # 统一转换为字符串进行比较
                    updated_at = p['updated_at']
                    if isinstance(updated_at, datetime):
                        updated_at = updated_at.strftime('%Y-%m-%d')
                    elif isinstance(updated_at, str):
                        updated_at = updated_at[:10]  # 只取日期部分
                    if updated_at >= time_ago_str:
                        recent_completed.append(p)
            relevant_plans = recent_completed
            print(f"🔍 DEBUG: 触发已完成工作查询，时间范围={days}天，返回{len(relevant_plans)}个已完成计划")
        # 特殊处理：如果用户查询的是"工作"、"当前工作"、"未完成工作"等，直接返回所有未完成计划
        elif any(w in user_message for w in ['当前工作', '未完成工作', '未完成', '待办', '计划']) or (user_message == '工作'):
            relevant_plans = pending_plans
            print(f"🔍 DEBUG: 触发工作查询特殊处理，返回{len(relevant_plans)}个未完成计划")
        elif keywords:
            # ✨ 改进：使用改进的关键词搜索工作计划
            for plan in all_items:  # 搜索所有计划（包括已完成的）
                for keyword in keywords:
                    # 模糊匹配：检查关键词是否在标题、描述或截止日期中
                    if (str(keyword).lower() in str(plan.get('title', '')).lower() or
                        str(keyword).lower() in str(plan.get('description', '')).lower() or
                        str(keyword).lower() in str(plan.get('deadline', '')).lower()):
                        relevant_plans.append(plan)
                        print(f"🔍 工作计划匹配: 关键词='{keyword}' 匹配到计划='{plan.get('title', '')}'")
                        break
        else:
            relevant_plans = [p for p in all_items if p['status'] not in ['已完成', '已取消']]
        
        context = f"""你是{ai_assistant_name}，用户的个人助手AI，严格基于用户的记录和计划回答问题。

重要规则：
0. **你的名字是"{ai_assistant_name}"，在对话中请使用这个名字称呼自己，不要使用"Assistant"或其他名字**
1. **必须基于下方的聊天记录和计划列表来回答问题**
2. **当用户问"工作"、"当前工作"、"未完成工作"时，必须列出下方的所有未完成计划**
3. **当用户问"已完成工作"、"显示已完成"时，必须列出下方的所有已完成计划**
4. 如果下方有计划列表，你必须回答这些计划，不要说"没有找到"
5. 当用户查询特定主题时，只返回与该主题直接相关的信息
6. 不要推测、假设或编造任何信息
7. 简洁准确地回答

**提醒功能说明**：
- 当用户说"提醒我..."、"X分钟后提醒我..."等时，你应该回复"好的，我将为您设置提醒"
- 系统会自动提取提醒内容和时间，创建提醒任务

**名字设置说明**：
- 当用户想给你取名字时（如"叫你小马"、"以后就叫你小明"），系统会自动识别并设置
- 你只需要自然地回应即可，不需要特殊处理

用户查询的主题：{user_message}
当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

        相关聊天记录({len(unique_chats)}条):
"""

        # ✨ 调试：打印对话记录数量
        print(f"🔍 DEBUG: unique_chats数量={len(unique_chats)}, relevant_plans数量={len(relevant_plans)}")
        if unique_chats:
            print(f"🔍 DEBUG: 前3条对话记录:")
            for i, chat in enumerate(unique_chats[:3]):
                print(f"  {i+1}. [{chat.get('timestamp', 'N/A')}] {chat.get('content', 'N/A')[:50]}")

        for chat in unique_chats:
            context += f"[{chat['timestamp']}] {chat['content']}\n"

        if relevant_plans:
            # 检查是否是已完成工作查询
            is_completed_query = any(w in user_message for w in ['已完成工作', '已完成', '完成的工作', '显示已完成'])

            if is_completed_query:
                # 提取时间范围提示
                time_desc = "最近1个月"
                if '3个月' in user_message or '三个月' in user_message:
                    time_desc = "最近3个月"
                elif '2个月' in user_message or '两个月' in user_message:
                    time_desc = "最近2个月"
                elif '1周' in user_message or '一周' in user_message:
                    time_desc = "最近1周"
                elif '今天' in user_message:
                    time_desc = "今天"

                context += f"\n**{time_desc}已完成的工作（共{len(relevant_plans)}个）：**\n"
                for idx, plan in enumerate(relevant_plans, 1):  # 移除[:20]限制，显示所有
                    # 显示完成时间
                    completed_time = ""
                    if plan.get('updated_at'):
                        if isinstance(plan['updated_at'], str):
                            completed_time = f" (完成于: {plan['updated_at'][:10]})"
                        elif isinstance(plan['updated_at'], datetime):
                            completed_time = f" (完成于: {plan['updated_at'].strftime('%Y-%m-%d')})"
                    context += f"{idx}. {plan['title']}{completed_time}\n"
            else:
                context += f"\n**未完成的工作计划（共{len(relevant_plans)}项，请用序号列出，格式: 1. 标题）：**\n"
                for idx, plan in enumerate(relevant_plans, 1):
                    context += f"{idx}. {plan['title']}\n"
        else:
            # 根据查询类型给出不同的提示
            is_completed_query = any(w in user_message for w in ['已完成工作', '已完成', '完成的工作', '显示已完成'])
            if is_completed_query:
                context += "\n指定时间范围内没有已完成的工作。\n"
            else:
                context += "\n当前没有未完成的工作计划。\n"

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
    

    def check_output_security(self, response_text, user_id, session_id):
        """检查输出内容是否包含敏感信息（✨改进：使用session_id而不是token）"""
        # 定义敏感信息模式

        sensitive_patterns = [
            # 完整的个人信息（电话号码）
            r'1[3-9]\d{9}',  # 手机号
            r'\d{3,4}-\d{7,8}',  # 座机号
            # 密码相关
            r'密码[：:是]\s*\S+',
            r'验证码[：:是]\s*\S+',
            # 身份证
            r'\d{17}[\dXx]',
            # 银行卡
            r'\d{16,19}',
        ]

        # 排除提醒相关的日期(不视为敏感信息)
        # 先临时移除提醒相关的日期描述,然后再检查
        temp_text = response_text
        # 移除类似"已为您设置提醒:2025年12月30日下午3点半"这样的内容
        temp_text = re.sub(r'(提醒|计划|任务|待办)[^。！？\n]*\d{4}年\d{1,2}月\d{1,2}日[^。！？\n]*', '', temp_text)
        temp_text = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日[^。！？\n]*(提醒|计划|任务|待办)', '', temp_text)

        # 检查是否包含敏感信息
        has_sensitive = False
        for pattern in sensitive_patterns:
            if re.search(pattern, temp_text):
                has_sensitive = True
                break

        if not has_sensitive:
            return None  # 不包含敏感信息，正常返回

        # ✨ 新逻辑：检查内存中的验证状态（使用session_id）
        if session_id and session_id in self.session_security_status:
            if self.session_security_status[session_id].get('verified'):
                return None  # 已验证，正常返回

        # 包含敏感信息但未验证，检查用户是否设置了验证码（决定提示信息）
        try:
            result = self.memory.db.query(
                "SELECT security_code FROM users WHERE id = %s",
                (user_id,)
            )

            has_custom_code = bool(result and result[0].get('security_code'))

            # 保存原始结果
            if not hasattr(self, 'pending_responses'):
                self.pending_responses = {}
            self.pending_responses[user_id] = response_text

            if has_custom_code:
                verification_prompt = '🔒 查询结果包含敏感信息，需要验证码验证\n\n请直接输入您的验证码'
            else:
                # ✨ 未设置验证码，提示使用默认验证码000000
                verification_prompt = '🔒 查询结果包含敏感信息，需要验证码验证\n\n您还未设置验证码，默认验证码为：000000\n\n请输入验证码（建议设置后输入自定义验证码）'

            return {
                'response': verification_prompt,
                'detected_plans': [],
                'detected_reminders': [],
                'completed_plans': [],
                'needs_verification': True
            }
        except Exception as e:
            print(f"❌ 安全检查出错: {e}")
            return None

    def process_confirmation_command(self, user_message, user_id=None):
        """处理确认命令（保存计划、保存提醒等）"""
        user_key = user_id or 'default'

        # 检查当前状态是否为等待确认
        current_state = self.get_conversation_state(user_id)
        if current_state != ConversationState.WAITING_CONFIRMATION:
            return None

        # 检查是否有待确认的内容
        if user_key not in self.pending_confirmations:
            return None

        pending = self.pending_confirmations[user_key]
        pending_plans = pending.get('plans', [])
        pending_reminders = pending.get('reminders', [])

        if not pending_plans and not pending_reminders:
            return None

        # 检查确认命令
        msg_lower = user_message.lower().strip()

        # 全部保存
        if msg_lower in ['全部保存', '全保存', '都保存', '保存全部', '确认', '是的', '是', 'yes', 'y']:
            saved_plans = []
            saved_reminders = []

            # 保存所有计划
            for plan in pending_plans:
                try:
                    # 使用work_task_manager保存到work_tasks表
                    task_id = self.work_task_manager.add_task(
                        user_id=user_id,
                        title=plan['title'],
                        content=plan.get('deadline', ''),
                        priority=plan.get('priority', '中'),
                        category='工作'
                    )
                    if task_id:
                        saved_plans.append(plan)
                except Exception as e:
                    print(f"⚠️ 保存计划失败: {e}")

            # 保存所有提醒
            for reminder in pending_reminders:
                try:
                    scheduler = get_global_scheduler()
                    if scheduler:
                        scheduler.add_reminder(
                            content=reminder['content'],
                            remind_time=reminder['remind_time'],
                            user_id=user_id,
                            repeat_type=reminder.get('repeat_type', 'once')
                        )
                        saved_reminders.append(reminder)
                except Exception as e:
                    print(f"⚠️ 保存提醒失败: {e}")

            # 清除待确认内容和状态
            del self.pending_confirmations[user_key]
            self.clear_conversation_state(user_id)

            response = "✅ 已保存：\n\n"
            if saved_plans:
                response += f"📋 计划（{len(saved_plans)}个）：\n"
                for i, plan in enumerate(saved_plans, 1):
                    response += f"{i}. {plan['title']}\n"
                response += "\n"
            if saved_reminders:
                response += f"⏰ 提醒（{len(saved_reminders)}个）：\n"
                for i, reminder in enumerate(saved_reminders, 1):
                    response += f"{i}. {reminder['content']} ({reminder['remind_time']})\n"

            return {
                'response': response,
                'detected_plans': [],
                'detected_reminders': [],
                'completed_plans': []
            }

        # 选择性保存（如"保存1,2"或"保存1"）
        save_pattern = r'保存\s*(\d+(?:\s*[,，]\s*\d+)*)'
        match = re.search(save_pattern, user_message)
        if match:
            numbers_str = match.group(1)
            numbers = [int(n.strip()) for n in re.split(r'[,，]', numbers_str)]

            saved_items = []
            total_items = pending_plans + pending_reminders

            for num in numbers:
                if 1 <= num <= len(total_items):
                    item = total_items[num - 1]

                    # 判断是计划还是提醒
                    if num <= len(pending_plans):
                        # 是计划
                        plan = item
                        try:
                            task_id = self.work_task_manager.add_task(
                                user_id=user_id,
                                title=plan['title'],
                                content=plan.get('deadline', ''),
                                priority=plan.get('priority', '中'),
                                category='工作'
                            )
                            if task_id:
                                saved_items.append(('计划', plan['title']))
                        except Exception as e:
                            print(f"⚠️ 保存计划失败: {e}")
                    else:
                        # 是提醒
                        reminder = item
                        try:
                            scheduler = get_global_scheduler()
                            if scheduler:
                                scheduler.add_reminder(
                                    content=reminder['content'],
                                    remind_time=reminder['remind_time'],
                                    user_id=user_id,
                                    repeat_type=reminder.get('repeat_type', 'once')
                                )
                                saved_items.append(('提醒', reminder['content']))
                        except Exception as e:
                            print(f"⚠️ 保存提醒失败: {e}")

            # 清除待确认内容和状态
            del self.pending_confirmations[user_key]
            self.clear_conversation_state(user_id)

            response = f"✅ 已保存{len(saved_items)}项：\n\n"
            for i, (item_type, content) in enumerate(saved_items, 1):
                response += f"{i}. [{item_type}] {content}\n"

            return {
                'response': response,
                'detected_plans': [],
                'detected_reminders': [],
                'completed_plans': []
            }

        # 取消保存
        if msg_lower in ['取消', '不保存', '不用', '算了', 'no', 'n']:
            del self.pending_confirmations[user_key]
            self.clear_conversation_state(user_id)
            return {
                'response': "❌ 已取消保存",
                'detected_plans': [],
                'detected_reminders': [],
                'completed_plans': []
            }

        return None

    def process_ai_name_command(self, user_message, user_id=None):
        """处理设置AI助理名字的命令 - 使用智能检测而非死板的正则"""
        if not user_id:
            return None

        print(f"🔍 [名字设置] 检查消息: '{user_message}'")

        # ✨ 先检查是否是疑问句，如果是疑问句则不处理为设置名字命令
        question_indicators = ['什么', '啥', '哪个', '哪', '吗', '呢', '？', '?']
        if any(indicator in user_message for indicator in question_indicators):
            print(f"🔍 [名字设置] 检测到疑问句，跳过")
            return None  # 是疑问句，不处理为设置名字命令

        # ✨ 智能检测：检查是否包含设置名字的关键词组合
        # 关键词1：表示"称呼"的词
        name_keywords = ['叫', '名字', '称呼', '取名', '起名', '改名']
        # 关键词2：表示"你"（AI）的词
        target_keywords = ['你', '助理', '助手']

        # 检查是否同时包含这两类关键词
        has_name_keyword = any(kw in user_message for kw in name_keywords)
        has_target_keyword = any(kw in user_message for kw in target_keywords)

        print(f"🔍 [名字设置] 关键词检测: name={has_name_keyword}, target={has_target_keyword}")

        if not (has_name_keyword and has_target_keyword):
            print(f"🔍 [名字设置] 关键词不匹配，跳过")
            return None  # 不是设置名字的命令

        # ✨ 使用更灵活的正则表达式模式提取名字
        patterns = [
            # 直接命令式
            r'^你叫(.+)$',
            r'^叫你(.+)$',
            r'^改名为(.+)$',
            r'^改名叫(.+)$',
            r'^你的名字是(.+)$',
            r'^你的名字叫(.+)$',
            r'^设置助理名字[：:](.+)$',
            r'^设置助理名[：:](.+)$',
            r'^助理名字[：:](.+)$',
            # ✨ 新增：更灵活的模式
            r'.*叫你(.+)[！!。\.]?$',  # "以后就叫你小马！"
            r'.*就叫(.+)[！!。\.]?$',   # "就叫小明"
            r'.*取名(.+)[！!。\.]?$',   # "给你取名小红"
            r'.*起名(.+)[！!。\.]?$',   # "给你起名小蓝"
            r'.*名字是(.+)[！!。\.]?$', # "你的名字是小绿"
            r'.*称呼你(.+)[！!。\.]?$', # "我称呼你小黄"
        ]

        for pattern in patterns:
            match = re.match(pattern, user_message.strip())
            if match:
                new_name = match.group(1).strip()

                print(f"🔍 [名字设置] 匹配到模式，原始提取: '{new_name}'")

                # ✨ 清理名字：去除标点符号、语气词和多余字符
                new_name = re.sub(r'[！!。\.，,、？?；;：:]+$', '', new_name)  # 去除末尾标点
                new_name = re.sub(r'(吧|呗|啊|呀|哦|哈|嘛|啦|哟|喽|咯)$', '', new_name)  # 去除末尾语气词
                new_name = new_name.strip()

                print(f"🔍 [名字设置] 清理后的名字: '{new_name}'")

                # 验证名字长度
                if len(new_name) < 1 or len(new_name) > 20:
                    return {
                        'response': '❌ 名字长度应该在1-20个字符之间',
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }

                # 更新数据库中的AI助理名字
                try:
                    from user_manager import UserManager
                    user_manager = UserManager(self.db)  # 使用self.db作为参数
                    success = user_manager.update_ai_assistant_name(user_id, new_name)

                    if success:
                        response = f"✅ 好的！从现在开始，我就叫「{new_name}」了。\n\n"
                        response += f"你可以随时通过以下方式修改我的名字：\n"
                        response += f"• 你叫xxx\n"
                        response += f"• 改名为xxx\n"
                        response += f"• 设置助理名字：xxx"

                        return {
                            'response': response,
                            'detected_plans': [],
                            'detected_reminders': [],
                            'completed_plans': []
                        }
                    else:
                        return {
                            'response': '❌ 设置名字失败，请稍后重试',
                            'detected_plans': [],
                            'detected_reminders': [],
                            'completed_plans': []
                        }
                except Exception as e:
                    print(f"⚠️ 设置AI助理名字失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return {
                        'response': f'❌ 设置名字时出错：{str(e)}',
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }

        return None

    def parse_time_range(self, time_text, user_message):
        """
        解析时间范围表达式
        返回: (start_time, end_time) 或 None
        """
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        print(f"🔍 [时间解析] 输入: time_text='{time_text}', user_message='{user_message}'")
        print(f"🔍 [时间解析] 当前时间: {now}")

        # ✨ 优先处理相对时间（N分钟内、N小时内、半小时内等）
        # 匹配 "刚才" 或 "刚刚"
        if '刚才' in user_message or '刚刚' in user_message:
            start_time = now - timedelta(minutes=5)
            result = (start_time, now)
            print(f"🔍 [时间解析] 匹配: 刚才/刚刚 -> {result}")
            return result

        # 匹配 "N分钟内" 或 "N分钟"
        minutes_match = re.search(r'(\d+)\s*分钟', user_message)
        if minutes_match:
            minutes = int(minutes_match.group(1))
            start_time = now - timedelta(minutes=minutes)
            result = (start_time, now)
            print(f"🔍 [时间解析] 匹配: {minutes}分钟内 -> {result}")
            return result

        # 匹配 "半小时内" 或 "半小时"
        if '半小时' in user_message:
            start_time = now - timedelta(minutes=30)
            result = (start_time, now)
            print(f"🔍 [时间解析] 匹配: 半小时内 -> {result}")
            return result

        # 匹配 "N小时内" 或 "N小时"
        hours_match = re.search(r'(\d+)\s*小时', user_message)
        if hours_match:
            hours = int(hours_match.group(1))
            start_time = now - timedelta(hours=hours)
            result = (start_time, now)
            print(f"🔍 [时间解析] 匹配: {hours}小时内 -> {result}")
            return result

        # ✨ 处理具体时间点范围（如"下午3点至4点"、"15:00到16:00"）
        # 匹配模式1: "下午3点至4点" / "下午3点到4点"
        time_range_match = re.search(r'(上午|下午|晚上|中午)?(\d+)\s*[点:：]\s*(\d+)?\s*[至到]\s*(\d+)\s*[点:：]\s*(\d+)?', user_message)
        if time_range_match:
            period = time_range_match.group(1)  # 上午/下午/晚上
            start_hour = int(time_range_match.group(2))
            start_minute = int(time_range_match.group(3)) if time_range_match.group(3) else 0
            end_hour = int(time_range_match.group(4))
            end_minute = int(time_range_match.group(5)) if time_range_match.group(5) else 0

            # 转换为24小时制
            if period == '下午' and start_hour < 12:
                start_hour += 12
                end_hour += 12 if end_hour < 12 else 0
            elif period == '晚上' and start_hour < 12:
                start_hour += 12
                end_hour += 12 if end_hour < 12 else 0
            elif period == '上午' and start_hour == 12:
                start_hour = 0

            # 确定日期（默认今天）
            base_date = today_start
            if '昨天' in user_message or '昨日' in user_message:
                base_date = today_start - timedelta(days=1)

            start_time = base_date.replace(hour=start_hour, minute=start_minute)
            end_time = base_date.replace(hour=end_hour, minute=end_minute)

            result = (start_time, end_time)
            print(f"🔍 [时间解析] 匹配: 具体时间点范围 {period if period else ''}({start_hour}:{start_minute:02d}-{end_hour}:{end_minute:02d}) -> {result}")
            return result

        # ✨ 处理更细粒度的时段（早上、中午、傍晚、深夜）
        # 今天的细分时段
        if '今天' in user_message or '今日' in user_message:
            if '早上' in user_message or '早晨' in user_message or '今早' in user_message:
                result = (today_start.replace(hour=6), today_start.replace(hour=9))
                print(f"🔍 [时间解析] 匹配: 今天早上 -> {result}")
                return result
            elif '中午' in user_message:
                result = (today_start.replace(hour=11), today_start.replace(hour=13))
                print(f"🔍 [时间解析] 匹配: 今天中午 -> {result}")
                return result
            elif '傍晚' in user_message:
                result = (today_start.replace(hour=17), today_start.replace(hour=19))
                print(f"🔍 [时间解析] 匹配: 今天傍晚 -> {result}")
                return result
            elif '深夜' in user_message or '凌晨' in user_message:
                # 深夜：今天23:00到明天5:59
                result = (today_start.replace(hour=23), (today_start + timedelta(days=1)).replace(hour=5, minute=59))
                print(f"🔍 [时间解析] 匹配: 今天深夜 -> {result}")
                return result

        # 昨天的细分时段
        if '昨天' in user_message or '昨日' in user_message:
            yesterday_start = today_start - timedelta(days=1)
            if '早上' in user_message or '早晨' in user_message:
                result = (yesterday_start.replace(hour=6), yesterday_start.replace(hour=9))
                print(f"🔍 [时间解析] 匹配: 昨天早上 -> {result}")
                return result
            elif '中午' in user_message:
                result = (yesterday_start.replace(hour=11), yesterday_start.replace(hour=13))
                print(f"🔍 [时间解析] 匹配: 昨天中午 -> {result}")
                return result
            elif '傍晚' in user_message:
                result = (yesterday_start.replace(hour=17), yesterday_start.replace(hour=19))
                print(f"🔍 [时间解析] 匹配: 昨天傍晚 -> {result}")
                return result

        # 前天、大前天
        if '前天' in user_message:
            day_before_yesterday = today_start - timedelta(days=2)
            result = (day_before_yesterday, day_before_yesterday.replace(hour=23, minute=59))
            print(f"🔍 [时间解析] 匹配: 前天 -> {result}")
            return result

        if '大前天' in user_message:
            three_days_ago = today_start - timedelta(days=3)
            result = (three_days_ago, three_days_ago.replace(hour=23, minute=59))
            print(f"🔍 [时间解析] 匹配: 大前天 -> {result}")
            return result

        # 本月、上月
        if '本月' in user_message or '这个月' in user_message:
            month_start = today_start.replace(day=1)
            result = (month_start, now)
            print(f"🔍 [时间解析] 匹配: 本月 -> {result}")
            return result

        if '上月' in user_message or '上个月' in user_message:
            # 计算上个月的第一天和最后一天
            first_day_this_month = today_start.replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            first_day_last_month = last_day_last_month.replace(day=1)
            result = (first_day_last_month, last_day_last_month.replace(hour=23, minute=59))
            print(f"🔍 [时间解析] 匹配: 上月 -> {result}")
            return result

        # 星期表达
        weekday_map = {
            '周一': 0, '星期一': 0, '礼拜一': 0,
            '周二': 1, '星期二': 1, '礼拜二': 1,
            '周三': 2, '星期三': 2, '礼拜三': 2,
            '周四': 3, '星期四': 3, '礼拜四': 3,
            '周五': 4, '星期五': 4, '礼拜五': 4,
            '周六': 5, '星期六': 5, '礼拜六': 5,
            '周日': 6, '星期日': 6, '礼拜日': 6, '周天': 6, '星期天': 6
        }

        for weekday_name, weekday_num in weekday_map.items():
            if weekday_name in user_message:
                current_weekday = now.weekday()
                # 计算本周该天
                days_diff = weekday_num - current_weekday
                target_day = today_start + timedelta(days=days_diff)

                # 如果是"上周X"
                if '上周' in user_message or '上星期' in user_message:
                    target_day = target_day - timedelta(days=7)
                    result = (target_day, target_day.replace(hour=23, minute=59))
                    print(f"🔍 [时间解析] 匹配: 上{weekday_name} -> {result}")
                    return result
                else:
                    # 本周该天
                    result = (target_day, target_day.replace(hour=23, minute=59))
                    print(f"🔍 [时间解析] 匹配: {weekday_name} -> {result}")
                    return result

        # 具体日期（如"2月20日"）
        date_match = re.search(r'(\d+)\s*月\s*(\d+)\s*[日号]', user_message)
        if date_match:
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            # 默认使用今年
            year = now.year
            try:
                target_date = datetime(year, month, day)
                target_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)

                # 检查是否有时段限定
                if '上午' in user_message:
                    result = (target_start.replace(hour=0), target_start.replace(hour=12))
                    print(f"🔍 [时间解析] 匹配: {month}月{day}日上午 -> {result}")
                    return result
                elif '下午' in user_message:
                    result = (target_start.replace(hour=12), target_start.replace(hour=18))
                    print(f"🔍 [时间解析] 匹配: {month}月{day}日下午 -> {result}")
                    return result
                elif '晚上' in user_message:
                    result = (target_start.replace(hour=18), target_start.replace(hour=23, minute=59))
                    print(f"🔍 [时间解析] 匹配: {month}月{day}日晚上 -> {result}")
                    return result
                else:
                    # 全天
                    result = (target_start, target_start.replace(hour=23, minute=59))
                    print(f"🔍 [时间解析] 匹配: {month}月{day}日 -> {result}")
                    return result
            except ValueError:
                print(f"⚠️ [时间解析] 无效日期: {year}-{month}-{day}")

        # 今天的时间段
        if '今天' in time_text or '今日' in time_text:
            if '上午' in time_text:
                result = (today_start.replace(hour=0), today_start.replace(hour=12))
                print(f"🔍 [时间解析] 匹配: 今天上午 -> {result}")
                return result
            elif '下午' in time_text:
                if '到现在' in user_message or '至今' in user_message:
                    result = (today_start.replace(hour=12), now)
                    print(f"🔍 [时间解析] 匹配: 今天下午到现在 -> {result}")
                    return result
                else:
                    result = (today_start.replace(hour=12), today_start.replace(hour=18))
                    print(f"🔍 [时间解析] 匹配: 今天下午 -> {result}")
                    return result
            elif '晚上' in time_text or '夜间' in time_text:
                result = (today_start.replace(hour=18), today_start.replace(hour=23, minute=59))
                print(f"🔍 [时间解析] 匹配: 今天晚上 -> {result}")
                return result
            else:
                # 今天全天
                if '到现在' in user_message or '至今' in user_message:
                    result = (today_start, now)
                    print(f"🔍 [时间解析] 匹配: 今天到现在 -> {result}")
                    return result
                else:
                    result = (today_start, today_start.replace(hour=23, minute=59))
                    print(f"🔍 [时间解析] 匹配: 今天全天 -> {result}")
                    return result

        # 昨天
        if '昨天' in time_text or '昨日' in time_text:
            yesterday_start = today_start - timedelta(days=1)
            if '上午' in time_text:
                result = (yesterday_start.replace(hour=0), yesterday_start.replace(hour=12))
                print(f"🔍 [时间解析] 匹配: 昨天上午 -> {result}")
                return result
            elif '下午' in time_text:
                result = (yesterday_start.replace(hour=12), yesterday_start.replace(hour=18))
                print(f"🔍 [时间解析] 匹配: 昨天下午 -> {result}")
                return result
            else:
                result = (yesterday_start, yesterday_start.replace(hour=23, minute=59))
                print(f"🔍 [时间解析] 匹配: 昨天全天 -> {result}")
                return result

        # YYYY年MM月DD日至YYYY年MM月DD日（自定义时间区间，最具体的格式先匹配）
        date_range_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日至(\d{4})年(\d{1,2})月(\d{1,2})日', time_text)
        if date_range_match:
            start_year = int(date_range_match.group(1))
            start_month = int(date_range_match.group(2))
            start_day = int(date_range_match.group(3))
            end_year = int(date_range_match.group(4))
            end_month = int(date_range_match.group(5))
            end_day = int(date_range_match.group(6))
            try:
                # 创建开始和结束时间
                start_time = datetime(start_year, start_month, start_day, 0, 0, 0)
                end_time = datetime(end_year, end_month, end_day, 23, 59, 59)
                result = (start_time, end_time)
                print(f"🔍 [时间解析] 匹配: {start_year}年{start_month}月{start_day}日至{end_year}年{end_month}月{end_day}日 -> {result}")
                return result
            except ValueError as e:
                print(f"⚠️ [时间解析] 日期无效: {start_year}年{start_month}月{start_day}日至{end_year}年{end_month}月{end_day}日 - {e}")
                return None

        # 最近N天 或 近N天
        days_match = re.search(r'(?:最近|近)(\d+)天', time_text)
        if days_match:
            days = int(days_match.group(1))
            start_time = now - timedelta(days=days)
            result = (start_time, now)
            print(f"🔍 [时间解析] 匹配: 近{days}天 -> {result}")
            return result

        # 最近N个月 或 近N个月
        months_match = re.search(r'(?:最近|近)(\d+)(?:个)?月', time_text)
        if months_match:
            months = int(months_match.group(1))
            # 计算N个月前的日期（简化处理：1个月=30天）
            days = months * 30
            start_time = now - timedelta(days=days)
            result = (start_time, now)
            print(f"🔍 [时间解析] 匹配: 近{months}个月 -> {result}")
            return result

        # 最近N年 或 近N年
        years_match = re.search(r'(?:最近|近)(\d+)年', time_text)
        if years_match:
            years = int(years_match.group(1))
            # 计算N年前的日期（简化处理：1年=365天）
            days = years * 365
            start_time = now - timedelta(days=days)
            result = (start_time, now)
            print(f"🔍 [时间解析] 匹配: 近{years}年 -> {result}")
            return result
        # YYYY年MM月DD日以来（更具体的格式先匹配）
        year_month_day_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日以来', time_text)
        if year_month_day_match:
            year = int(year_month_day_match.group(1))
            month = int(year_month_day_match.group(2))
            day = int(year_month_day_match.group(3))
            try:
                # 创建指定年月日的开始时间
                start_time = datetime(year, month, day, 0, 0, 0)
                result = (start_time, now)
                print(f"🔍 [时间解析] 匹配: {year}年{month}月{day}日以来 -> {result}")
                return result
            except ValueError as e:
                print(f"⚠️ [时间解析] 日期无效: {year}年{month}月{day}日 - {e}")
                return None

        # YYYY年MM月以来 或 YYYY年M月以来
        year_month_match = re.search(r'(\d{4})年(\d{1,2})月以来', time_text)
        if year_month_match:
            year = int(year_month_match.group(1))
            month = int(year_month_match.group(2))
            try:
                # 创建指定年月的第一天
                start_time = datetime(year, month, 1, 0, 0, 0)
                result = (start_time, now)
                print(f"🔍 [时间解析] 匹配: {year}年{month}月以来 -> {result}")
                return result
            except ValueError as e:
                print(f"⚠️ [时间解析] 日期无效: {year}年{month}月 - {e}")
                return None

        # 本周
        if '本周' in time_text or '这周' in time_text:
            # 获取本周一
            weekday = now.weekday()
            week_start = today_start - timedelta(days=weekday)
            result = (week_start, now)
            print(f"🔍 [时间解析] 匹配: 本周 -> {result}")
            return result

        # 上周
        if '上周' in time_text:
            weekday = now.weekday()
            last_week_start = today_start - timedelta(days=weekday + 7)
            last_week_end = last_week_start + timedelta(days=6, hours=23, minutes=59)
            result = (last_week_start, last_week_end)
            print(f"🔍 [时间解析] 匹配: 上周 -> {result}")
            return result

        print(f"🔍 [时间解析] 未匹配到任何时间模式")
        return None

    def process_query_intent(self, user_message, user_id):
        """
        智能查询意图识别和处理
        识别"显示"、"查询"、"查看"等查询请求，直接执行数据库查询
        """
        # 查询关键词
        query_keywords = ['显示', '查询', '查看', '列出', '给我看', '找一下', '搜索']

        # 时间关键词
        time_keywords = ['今天', '昨天', '前天', '本周', '上周', '最近', '这周']

        # 检查是否包含查询关键词或时间关键词
        has_query_keyword = any(keyword in user_message for keyword in query_keywords)
        has_time_keyword = any(keyword in user_message for keyword in time_keywords)

        # ✨ 改进：如果包含时间关键词，也触发查询
        if not has_query_keyword and not has_time_keyword:
            return None

        print(f"🔍 [智能查询] 检测到查询意图: {user_message}")

        # 识别查询目标
        query_target = None
        if any(word in user_message for word in ['对话', '聊天', '记录', '消息', '说过']):
            query_target = 'messages'
        elif any(word in user_message for word in ['工作', '任务', '计划']):
            query_target = 'work'
        elif any(word in user_message for word in ['提醒', '待办']):
            query_target = 'reminders'

        if not query_target:
            # 默认查询对话记录
            query_target = 'messages'

        print(f"🔍 [智能查询] 查询目标: {query_target}")

        # ✨ 提取查询关键词（去除查询动词）
        keywords = self._extract_keywords_from_message(user_message)
        print(f"🔍 [智能查询] 提取的关键词: {keywords}")

        # 解析时间范围
        time_range = self.parse_time_range(user_message, user_message)

        # ✨ 改进：有关键词时搜索全部历史，无关键词时限制24小时
        if time_range:
            start_time, end_time = time_range
            print(f"🔍 [智能查询] 时间范围: {start_time} 到 {end_time}")
            use_time_filter = True
        elif keywords:
            # 有关键词：搜索全部历史数据
            start_time = None
            end_time = None
            use_time_filter = False
            print(f"🔍 [智能查询] 使用关键词搜索全部历史数据")
        else:
            # 无关键词：默认查询最近24小时
            start_time = datetime.now() - timedelta(hours=24)
            end_time = datetime.now()
            use_time_filter = True
            print(f"🔍 [智能查询] 使用默认时间范围（最近24小时）")

        # 执行查询
        try:
            if query_target == 'messages':
                # ✨ 改进：根据关键词查询对话记录（只查询用户消息）
                if keywords:
                    # 有关键词：使用关键词搜索
                    all_results = []
                    for keyword in keywords[:5]:  # 最多使用5个关键词
                        if use_time_filter:
                            keyword_results = self.db.query(
                                "SELECT * FROM messages WHERE user_id = %s AND role = 'user' AND content LIKE %s AND timestamp >= %s AND timestamp <= %s ORDER BY timestamp DESC",
                                (user_id, f'%{keyword}%', start_time, end_time)
                            )
                        else:
                            # 不限制时间范围，搜索全部历史
                            keyword_results = self.db.query(
                                "SELECT * FROM messages WHERE user_id = %s AND role = 'user' AND content LIKE %s ORDER BY timestamp DESC LIMIT 100",
                                (user_id, f'%{keyword}%')
                            )
                        all_results.extend(keyword_results)
                        print(f"🔍 [智能查询] 关键词'{keyword}'找到{len(keyword_results)}条记录")

                    # 去重（根据id）
                    seen_ids = set()
                    results = []
                    for msg in all_results:
                        msg_id = msg.get('id')
                        if msg_id not in seen_ids:
                            seen_ids.add(msg_id)
                            results.append(msg)

                    # 按时间排序
                    results.sort(key=lambda x: x.get('timestamp', ''), reverse=False)
                else:
                    # 无关键词：查询时间范围内所有用户消息
                    results = self.db.query(
                        "SELECT * FROM messages WHERE user_id = %s AND role = 'user' AND timestamp >= %s AND timestamp <= %s ORDER BY timestamp ASC",
                        (user_id, start_time, end_time)
                    )

                if not results:
                    keyword_hint = f"关键词：{', '.join(keywords)}" if keywords else ""
                    if use_time_filter:
                        time_hint = f"\n时间范围：{start_time.strftime('%Y-%m-%d %H:%M')} 到 {end_time.strftime('%Y-%m-%d %H:%M')}"
                    else:
                        time_hint = "\n搜索范围：全部历史记录"
                    return {
                        'response': f'📭 没有找到匹配的对话记录。\n\n{keyword_hint}{time_hint}',
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }

                # 格式化输出
                response = f'📝 找到 {len(results)} 条对话记录：\n\n'
                if use_time_filter:
                    response += f'⏰ 时间范围：{start_time.strftime("%Y-%m-%d %H:%M")} 到 {end_time.strftime("%Y-%m-%d %H:%M")}\n\n'
                else:
                    response += f'🔍 搜索范围：全部历史记录（最多显示100条）\n\n'

                for msg in results:
                    timestamp = msg.get('timestamp', '')
                    if isinstance(timestamp, datetime):
                        time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        time_str = str(timestamp)

                    role = msg.get('role', '')
                    content = msg.get('content', '')

                    # ✨ 清理命令前缀
                    content = self._clean_command_prefix(content)

                    # ✨ 只显示用户消息，使用 👤 图标
                    role_icon = '👤'
                    response += f'{role_icon} [{time_str}] {content}\n\n'

                return {
                    'response': response,
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }

            elif query_target == 'work':
                # 查询工作任务
                pending_items = self.get_all_work_items(user_id, status_filter='pending')

                # ✨ 应用时间范围过滤
                if time_range:
                    start_time, end_time = time_range
                    filtered_items = []
                    for item in pending_items:
                        # 检查创建时间或更新时间是否在范围内
                        created_at = item.get('created_at')
                        updated_at = item.get('updated_at')

                        # 转换为 datetime 对象
                        item_time = None
                        if updated_at:
                            if isinstance(updated_at, str):
                                try:
                                    item_time = datetime.strptime(updated_at[:19], '%Y-%m-%d %H:%M:%S')
                                except:
                                    pass
                            elif isinstance(updated_at, datetime):
                                item_time = updated_at

                        if not item_time and created_at:
                            if isinstance(created_at, str):
                                try:
                                    item_time = datetime.strptime(created_at[:19], '%Y-%m-%d %H:%M:%S')
                                except:
                                    pass
                            elif isinstance(created_at, datetime):
                                item_time = created_at

                        # 检查是否在时间范围内
                        if item_time and start_time <= item_time <= end_time:
                            filtered_items.append(item)

                    pending_items = filtered_items
                    print(f"🔍 [智能查询] 时间范围过滤后剩余 {len(pending_items)} 个工作任务")

                if not pending_items:
                    time_hint = ""
                    if time_range:
                        time_hint = f"\n⏰ 时间范围：{start_time.strftime('%Y-%m-%d %H:%M')} 到 {end_time.strftime('%Y-%m-%d %H:%M')}"
                    return {
                        'response': f'📭 没有找到未完成的工作任务。{time_hint}',
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }

                response = f'📋 找到 {len(pending_items)} 个未完成的工作任务：\n\n'
                if time_range:
                    response += f'⏰ 时间范围：{start_time.strftime("%Y-%m-%d %H:%M")} 到 {end_time.strftime("%Y-%m-%d %H:%M")}\n\n'

                for idx, item in enumerate(pending_items, 1):
                    title = item.get('title', '')
                    deadline = item.get('deadline', '')
                    priority = item.get('priority', 'medium')

                    priority_icon = '🔴' if priority == 'high' else '🟡' if priority == 'medium' else '🟢'
                    response += f'{idx}. {priority_icon} {title}'
                    if deadline:
                        response += f' (截止: {deadline})'
                    response += '\n'

                return {
                    'response': response,
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }

            elif query_target == 'reminders':
                # 查询提醒
                reminders = self.reminder.list_reminders(user_id=user_id)

                if not reminders:
                    return {
                        'response': '📭 没有找到提醒。',
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }

                response = f'⏰ 找到 {len(reminders)} 个提醒：\n\n'
                for idx, reminder in enumerate(reminders, 1):
                    content = reminder.get('content', '')
                    remind_time = reminder.get('remind_time', '')
                    response += f'{idx}. {content} (时间: {remind_time})\n'

                return {
                    'response': response,
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }

        except Exception as e:
            print(f"❌ [智能查询] 查询失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': f'❌ 查询时出错：{str(e)}',
                'detected_plans': [],
                'detected_reminders': [],
                'completed_plans': []
            }

        return None

    def process_ai_name_query(self, user_message, ai_assistant_name='小助手'):
        """处理询问AI名字的问题 - 直接回答，不交给AI模型"""
        # 检测询问AI名字的模式
        query_patterns = [
            '你叫什么',
            '你的名字',
            '你叫啥',
            '你是谁',
            '叫什么名字',
            '什么名字',
        ]

        # 检查是否是询问名字的问题
        is_name_query = any(pattern in user_message for pattern in query_patterns)

        if is_name_query:
            print(f"🔍 [名字查询] 检测到询问名字的问题，直接回答")
            print(f"🔍 [名字查询] ai_assistant_name = '{ai_assistant_name}'")
            response = {
                'response': f'我叫{ai_assistant_name}。',
                'detected_plans': [],
                'detected_reminders': [],
                'completed_plans': []
            }
            print(f"🔍 [名字查询] 返回响应: {response['response']}")
            return response

        # ✨ 检测确认名字的模式（如"你不是叫小马吗？"）
        confirm_patterns = [
            f'你不是叫{ai_assistant_name}',
            f'你是{ai_assistant_name}',
            f'你叫{ai_assistant_name}',
        ]

        is_name_confirm = any(pattern in user_message for pattern in confirm_patterns)

        if is_name_confirm:
            print(f"🔍 [名字确认] 检测到确认名字的问题，直接回答")
            print(f"🔍 [名字确认] ai_assistant_name = '{ai_assistant_name}'")
            response = {
                'response': f'是的，我叫{ai_assistant_name}。',
                'detected_plans': [],
                'detected_reminders': [],
                'completed_plans': []
            }
            print(f"🔍 [名字确认] 返回响应: {response['response']}")
            return response

        return None

    def chat(self, user_message, user_id=None, file_id=None, token=None, session_id=None, ai_assistant_name='小助手'):
        """处理用户消息（✨新增session_id参数用于浏览器会话验证）"""
        # ✨ 新增：智能查询意图识别（优先级最高，在其他处理之前）
        query_result = self.process_query_intent(user_message, user_id)
        if query_result:
            return query_result

        # 检查是否是安全验证相关命令
        security_result = self.process_security_command(user_message, user_id, token, session_id)
        if security_result:
            return security_result

        # ✨ 新增：检查是否是确认命令
        confirmation_result = self.process_confirmation_command(user_message, user_id)
        if confirmation_result:
            return confirmation_result

        # ✨ 新增：检查是否是设置AI助理名字的命令
        ai_name_result = self.process_ai_name_command(user_message, user_id)
        if ai_name_result:
            return ai_name_result

        # ✨ 新增：检查是否是询问AI名字的问题
        ai_name_query_result = self.process_ai_name_query(user_message, ai_assistant_name)
        if ai_name_query_result:
            return ai_name_query_result

        # ✨ 上下文检查：优先检查用户输入是否引用了上一次显示的内容
        context_result = self.check_context_reference(user_message, user_id)
        if context_result:
            print(f"🔍 检测到上下文引用，自动路由到: {context_result}")
            # 递归调用chat处理转换后的命令
            return self.chat(context_result, user_id, file_id, token, session_id, ai_assistant_name)

        # ✨ 新增：检查"X相关"、"X所有"和纯"X"模式
        if '相关' in user_message or '所有' in user_message:
            # ✨ 修复：无论是"相关"还是"所有"，都包含聊天记录，让搜索范围更广
            # 之前的设计是"相关"不包含聊天记录，这导致"X相关"的搜索范围比纯"X"还窄
            fuzzy_result = self._fuzzy_match_subcategory(user_message, user_id, include_chat=True)

            if fuzzy_result:
                # 检查是否是全面搜索结果（字典格式）
                if isinstance(fuzzy_result, dict) and fuzzy_result.get('is_comprehensive_search'):
                    print(f"🔍 返回全面搜索结果")
                    return fuzzy_result
                else:
                    # 是子类别命令，递归调用
                    print(f"🔍 检测到模糊匹配，转换为: {fuzzy_result}")
                    return self.chat(fuzzy_result, user_id, file_id, token, session_id, ai_assistant_name)
        else:
            # ✨ 纯"X"模式：只搜索分类记录（daily_records），不包含聊天记录
            # 检查是否是简单的关键词查询（不包含特殊符号和命令词）
            stripped_message = user_message.strip()
            # 排除已知的命令词和特殊模式
            command_words = ['工作', '计划', '财务', '账号', '提醒', '记录', '类别', '帮助', '日记', '随想', '信息', '学习笔记', '完成', '删除', '标记']
            is_command = any(stripped_message.startswith(word) for word in command_words)

            # 如果不是命令，且是简单的关键词（2-10个字符），尝试作为分类查询
            if not is_command and 2 <= len(stripped_message) <= 10 and not any(c in stripped_message for c in ['？', '?', '吗', '呢', '：', ':']):
                print(f"🔍 检测到纯分类查询模式: '{stripped_message}'")
                # 尝试在子类别中查找（包括用户自定义的）
                from category_system import CategoryManager
                category_mgr = CategoryManager()
                all_categories = category_mgr.get_all_categories()
                matched_subcategories = []

                for category in all_categories:
                    # 获取该类别下的所有子类别（包括系统预设和用户自定义）
                    subcategories = category_mgr.get_subcategories(category['id'], user_id=user_id)
                    for sub in subcategories:
                        if stripped_message in sub['name']:
                            matched_subcategories.append(sub['name'])

                if matched_subcategories:
                    # 找到匹配的子类别，返回该子类别的记录
                    subcategory_name = matched_subcategories[0]
                    print(f"🔍 找到匹配的子类别: {subcategory_name}")
                    return self.chat(subcategory_name, user_id, file_id, token, session_id, ai_assistant_name)

        # ✨ 新增：检查是否是新命令系统的命令
        try:
            command_router = get_command_router()
            command_result = command_router.execute(user_message, user_id)
            if command_result:
                # ✨ 检查命令结果是否包含列表，如果是则保存上下文
                response_text = command_result.get('response', '')

                # 检查是否是工作任务列表
                if '未完成的工作任务' in response_text and '个）：' in response_text:
                    work_mgr = WorkTaskManager('mysql_config.json')
                    pending_tasks = work_mgr.list_tasks(user_id, status='pending')
                    if pending_tasks:
                        # ✨ 改进：使用新的上下文格式
                        if user_id not in self.last_response_context:
                            self.last_response_context[user_id] = {}

                        self.last_response_context[user_id]['工作'] = {
                            'type': 'work_list',
                            'data': pending_tasks,
                            'subcategory_name': '工作',
                            'timestamp': datetime.now()
                        }

                        self.last_response_context[user_id]['_latest'] = '工作'
                        print(f"🔍 保存工作列表上下文，共{len(pending_tasks)}个任务")

                # ✨ 新增：检查是否是记录列表（如"未完成ai助理（共5项）："）
                elif '未完成' in response_text and '（共' in response_text and '项）：' in response_text:
                    # ✨ 使用命令返回的 context 字段（包含 subcategory_name）
                    if 'context' in command_result:
                        context = command_result['context']
                        subcategory_name = context.get('subcategory_name', 'unknown')

                        # ✨ 改进：支持多个子类别上下文同时存在
                        if user_id not in self.last_response_context:
                            self.last_response_context[user_id] = {}

                        # 使用子类别名称作为key，避免覆盖
                        self.last_response_context[user_id][subcategory_name] = {
                            'type': 'daily_records',
                            'data': context.get('data', []),
                            'subcategory_name': subcategory_name,
                            'timestamp': datetime.now()
                        }

                        # 同时保存一个"最近"的引用，用于简单的上下文引用
                        self.last_response_context[user_id]['_latest'] = subcategory_name

                        print(f"🔍 保存记录列表上下文：{subcategory_name}，共{len(context.get('data', []))}条记录")

                return command_result
        except Exception as e:
            print(f"⚠️ 命令系统执行错误: {e}")

        # 检查是否是快捷命令
        shortcut_result = self.process_shortcut_command(user_message, user_id)
        if shortcut_result:
            return shortcut_result

        # ✨ 新增：检查是否是工作任务操作指令（修改、置顶）
        task_operation_result = self.process_task_operation(user_message, user_id)
        if task_operation_result:
            return task_operation_result

        # ✨ 新增：过滤过短的无意义输入（防止关键词搜索返回不相关结果）
        stripped_message = user_message.strip()
        # 如果输入只有1-2个英文字符（非中文），且不是数字，返回提示
        # 中文2字词（如"工资"、"会议"）仍然允许搜索
        if len(stripped_message) <= 2 and not stripped_message.isdigit():
            # 检查是否全是ASCII字符（英文字母等）
            if all(ord(c) < 128 for c in stripped_message):
                return {
                    'response': f'💡 您输入的内容"{stripped_message}"过短，我无法理解。\n\n您可以：\n• 输入"帮助"查看可用命令\n• 输入"类别"查看所有类别\n• 输入完整的问题或命令',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }

        # ✨ 先检查是否是"标记为已完成"的意图（避免被"已完成工作查询"误判）
        # 判断标准：包含序号格式（X.、第X、X项等）+ 完成关键词
        complete_keywords_check = ['完成', '做完', '做好', '已完成', '搞定', '弄好', '结束', '标注']
        has_complete_intent = any(kw in user_message for kw in complete_keywords_check)

        # 检查是否包含序号格式（而不是简单的数字）
        # 序号格式：5.、第5、5项、任务5、完成 5等
        # 排除时间表达：X个月、X天、X周等
        has_task_number = False
        if not re.search(r'\d+\s*[个](月|年|星期|周|天)', user_message):  # 排除时间表达
            # 匹配序号格式，包括：
            # - 数字后跟点号：1.、2。
            # - 第X：第1、第2
            # - 数字后跟"项"：1项、2项
            # - 工作/任务后跟数字：工作1、任务2
            # - ✨ 操作词+空格+数字：完成 1、删除 2
            has_task_number = bool(re.search(r'(\d+[\.。、]|第\s*\d+|\d+\s*项|[工作任务]\s*\d+|(完成|删除|标记|做完|搞定)\s+\d+)', user_message))

        print(f"🔍 DEBUG: has_complete_intent={has_complete_intent}, has_task_number={has_task_number}, message='{user_message}'")

        if has_complete_intent and has_task_number:
            # 这是标记完成的意图，先执行完成检测
            completed_plans = self.detect_and_complete_plans(user_message, user_id)
            if completed_plans:
                # 成功标记了计划，返回成功消息
                response = f"✅ 已标记{len(completed_plans)}个工作为已完成：\n\n"
                for idx, plan in enumerate(completed_plans, 1):
                    response += f"{idx}. {plan['title']}\n"

                try:
                    self.memory.add_message('user', user_message, user_id=user_id, file_id=file_id)
                except Exception as e:
                    print(f"⚠️ 保存聊天记录失败: {e}")

                return {
                    'response': response,
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': completed_plans
                }

        # ✨ 直接处理"当前工作"/"未完成工作"查询（不通过AI，避免token限制导致显示不全）
        if any(w in user_message for w in ['当前工作', '未完成工作', '未完成', '待办']) or user_message.strip() == '工作':
            # 使用合并查询获取所有未完成的工作（work_plans + work_tasks）
            pending_items = self.get_all_work_items(user_id, status_filter='pending')

            if pending_items:
                response = f"📋 未完成的工作（共{len(pending_items)}项）：\n\n"
                for idx, item in enumerate(pending_items, 1):
                    # 所有数据现在都来自 work_tasks 表
                    title = item['title']
                    content = item.get('content', '') or item.get('description', '')

                    # 如果有内容，显示标题和内容；否则只显示标题
                    if content and content.strip():
                        response += f"{idx}. {title}\n{content}\n\n"
                    else:
                        response += f"{idx}. {title}\n\n"

                # ✨ 保存上下文：记录显示了工作列表
                if user_id not in self.last_response_context:
                    self.last_response_context[user_id] = {}

                self.last_response_context[user_id]['工作'] = {
                    'type': 'work_list',
                    'data': pending_items,
                    'subcategory_name': '工作',
                    'timestamp': datetime.now()
                }

                self.last_response_context[user_id]['_latest'] = '工作'
            else:
                response = "✅ 目前没有未完成的工作"

            # 保存到对话历史
            try:
                self.memory.add_message('user', user_message, user_id=user_id, file_id=file_id)
            except Exception as e:
                print(f"⚠️ 保存聊天记录失败: {e}")

            return {
                'response': response,
                'detected_plans': [],
                'detected_reminders': [],
                'completed_plans': []
            }

        # ✨ 直接处理"已完成工作"查询（不通过AI，避免token限制导致显示不全）
        if any(w in user_message for w in ['已完成工作', '已完成', '完成的工作', '显示已完成']):
            # 使用合并查询获取所有已完成的工作（work_plans + work_tasks）
            completed_items = self.get_all_work_items(user_id, status_filter='completed')

            # 判断是否是精确日期查询（今天、昨天、前天、X月X日/号）
            exact_date = None
            time_desc = ""

            if '今天' in user_message:
                exact_date = datetime.now().strftime('%Y-%m-%d')
                time_desc = "今天"
            elif '昨天' in user_message:
                from datetime import timedelta
                exact_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                time_desc = "昨天"
            elif '前天' in user_message:
                from datetime import timedelta
                exact_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
                time_desc = "前天"
            else:
                # 尝试匹配"X月X日"或"X月X号"格式
                date_match = re.search(r'(\d{1,2})月(\d{1,2})[日号]', user_message)
                if date_match:
                    month = int(date_match.group(1))
                    day = int(date_match.group(2))
                    current_year = datetime.now().year
                    try:
                        exact_date = f"{current_year}-{month:02d}-{day:02d}"
                        time_desc = f"{month}月{day}日"
                    except:
                        pass  # 日期无效，继续使用范围查询

            # 如果是精确日期查询，使用精确匹配
            if exact_date:
                recent_completed = [p for p in completed_items
                                  if p.get('updated_at') and p['updated_at'][:10] == exact_date]
            else:
                # 提取时间范围（如"3个月"、"1周"、"30天"、"近2天"）
                days = 30  # 默认1个月
                if '3个月' in user_message or '三个月' in user_message:
                    days = 90
                    time_desc = "最近3个月"
                elif '2个月' in user_message or '两个月' in user_message:
                    days = 60
                    time_desc = "最近2个月"
                elif '1个月' in user_message or '一个月' in user_message:
                    days = 30
                    time_desc = "最近1个月"
                elif '1周' in user_message or '一周' in user_message:
                    days = 7
                    time_desc = "最近1周"
                else:
                    # 尝试提取"近X天"或"X天"格式
                    day_match = re.search(r'近?(\d+)天', user_message)
                    if day_match:
                        days = int(day_match.group(1))
                        time_desc = f"近{days}天" if days > 1 else "今天"
                    else:
                        time_desc = "最近1个月"

                # 过滤指定时间范围内完成的工作
                from datetime import timedelta
                time_ago = datetime.now() - timedelta(days=days)
                time_ago_str = time_ago.strftime('%Y-%m-%d')
                recent_completed = []
                for p in completed_items:
                    if p.get('updated_at'):
                        # 统一转换为字符串进行比较
                        updated_at = p['updated_at']
                        if isinstance(updated_at, datetime):
                            updated_at = updated_at.strftime('%Y-%m-%d')
                        elif isinstance(updated_at, str):
                            updated_at = updated_at[:10]  # 只取日期部分
                        if updated_at >= time_ago_str:
                            recent_completed.append(p)

            if recent_completed:
                response = f"✅ {time_desc}已完成的工作（共{len(recent_completed)}个）：\n\n"
                for idx, item in enumerate(recent_completed, 1):
                    # 所有数据现在都来自 work_tasks 表
                    title = item['title']
                    content = item.get('content', '') or item.get('description', '')
                    completed_time = ""
                    if item.get('updated_at'):
                        if isinstance(item['updated_at'], str):
                            completed_time = f" (完成于: {item['updated_at'][:10]})"
                        elif isinstance(item['updated_at'], datetime):
                            completed_time = f" (完成于: {item['updated_at'].strftime('%Y-%m-%d')})"

                    # 如果有内容，显示标题和内容；否则只显示标题
                    if content and content.strip():
                        response += f"{idx}. {title}{completed_time}\n{content}\n\n"
                    else:
                        response += f"{idx}. {title}{completed_time}\n\n"
            else:
                response = f"✅ {time_desc}没有已完成的工作"

            # 保存到对话历史
            try:
                self.memory.add_message('user', user_message, user_id=user_id, file_id=file_id)
            except Exception as e:
                print(f"⚠️ 保存聊天记录失败: {e}")

            return {
                'response': response,
                'detected_plans': [],
                'detected_reminders': [],
                'completed_plans': []
            }

        # 检查是否需要安全验证（查询敏感信息时）
        print(f"🔍 DEBUG chat: 准备调用check_security_verification, session_id={session_id[:20] if session_id else None}...")
        verification_check = self.check_security_verification(user_message, user_id, session_id)
        print(f"🔍 DEBUG chat: verification_check返回值 = {verification_check}")
        if verification_check:
            print(f"🔍 DEBUG chat: 需要验证，返回拦截消息")
            return verification_check

        # ✨ 如果有file_id，获取文件信息并添加到消息中
        if file_id:
            try:
                file_info = self.file_manager.get_file(file_id, user_id)
                if file_info:
                    file_type = file_info.get('category', 'file')
                    file_name = file_info.get('original_name', '文件')
                    if file_type == 'image':
                        user_message = f"{user_message}\n[用户发送了图片: {file_name}]"
                    else:
                        user_message = f"{user_message}\n[用户发送了文件: {file_name}]"
                    print(f"📎 添加文件信息到消息: {file_name}, 类型: {file_type}")
            except Exception as e:
                print(f"⚠️ 获取文件信息失败: {e}")

        context = self.get_smart_context(user_message, user_id, ai_assistant_name)

        try:
            if self.model_type == 'openai':
                response = self.chat_with_openai_compatible(user_message, context, user_id)
            else:
                response = self._fallback_response(user_message, user_id)
        except Exception as e:
            print(f"⚠️ AI调用失败: {e}")
            # ✨ 优雅降级：使用 fallback 响应，不显示错误信息
            response = self._fallback_response(user_message, user_id)

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
            self.memory.add_message('user', user_message, user_id=user_id, file_id=file_id)
        except Exception as e:
            print(f"⚠️ 保存聊天记录失败: {e}")

        # 从用户消息中提取计划信息
        detected_plans = self.extract_plans_from_message(user_message)

        # 从用户消息中提取提醒信息（不直接创建）
        detected_reminders = self.extract_reminders_from_message(user_message, user_id)

        # ✨ 修改：直接保存提醒和计划，不需要用户确认
        user_key = user_id or 'default'
        if detected_plans or detected_reminders:
            # 直接保存提醒到数据库
            saved_reminders = []
            if detected_reminders:
                for reminder in detected_reminders:
                    try:
                        result = self.reminder.add_reminder(
                            content=reminder['content'],
                            remind_time=reminder['remind_time'],
                            repeat_type=reminder.get('repeat_type', 'once'),
                            user_id=user_id
                        )
                        saved_reminders.append(result)
                        print(f"✅ 已自动保存提醒: {reminder['content']} at {reminder['remind_time']}")
                    except Exception as e:
                        print(f"❌ 保存提醒失败: {e}")

            # 直接保存计划到数据库
            saved_plans = []
            if detected_plans:
                for plan in detected_plans:
                    try:
                        result = self.planner.add_plan(
                            title=plan['title'],
                            content=plan.get('content', ''),
                            priority=plan.get('priority', '中'),
                            deadline=plan.get('deadline'),
                            user_id=user_id
                        )
                        saved_plans.append(result)
                        print(f"✅ 已自动保存计划: {plan['title']}")
                    except Exception as e:
                        print(f"❌ 保存计划失败: {e}")

            # 构建保存成功的提示（不再询问确认）
            save_response = response + "\n\n"

            if saved_plans:
                save_response += "✅ 已为您保存以下计划：\n"
                for i, plan in enumerate(saved_plans, 1):
                    deadline_str = f"截止:{plan.get('deadline', '无')}" if plan.get('deadline') else "无截止日期"
                    save_response += f"{i}. {plan.get('title', '未命名')} ({deadline_str})\n"
                save_response += "\n"

            if saved_reminders:
                save_response += "✅ 已为您设置以下提醒：\n"
                start_idx = len(saved_plans) + 1
                for i, reminder in enumerate(saved_reminders, start_idx):
                    save_response += f"{i}. {reminder.get('content', '未命名')} (时间:{reminder.get('remind_time', '未知')})\n"
                save_response += "\n"

            # 更新response
            response = save_response

        # 检测并完成工作计划
        completed_plans = self.detect_and_complete_plans(user_message, user_id)

        # ✨ 自动检测和记录开发需求
        if self.dev_log:
            try:
                self.auto_detect_dev_requirement(user_message, response, user_id)
            except Exception as e:
                print(f"⚠️ 自动记录开发日志失败: {e}")

        # ✨ 安全检查：在返回前检查输出内容（使用session_id）
        security_result = self.check_output_security(response, user_id, session_id)
        if security_result:
            return security_result

        # ✨ 保存列表上下文（用于后续的修改、置顶指令）
        list_data = None  # 用于传递给前端
        # 检测是否是列表查询（包括工作、财务、学习等所有类别）
        list_keywords = ['工作', '当前工作', '未完成工作', '未完成', '待办', '计划', '财务', '学习', '健康', '生活']
        if user_message.strip() in list_keywords or any(kw in user_message for kw in list_keywords):
            try:
                # 获取未完成的工作任务
                pending_items = self.get_all_work_items(user_id, status_filter='pending')
                if pending_items:
                    if user_id not in self.last_response_context:
                        self.last_response_context[user_id] = {}

                    self.last_response_context[user_id]['工作'] = {
                        'type': 'work_list',
                        'data': pending_items,
                        'subcategory_name': '工作',
                        'timestamp': datetime.now()
                    }

                    self.last_response_context[user_id]['_latest'] = '工作'
                    list_data = pending_items  # 传递给前端
                    print(f"🔍 保存列表上下文，共{len(pending_items)}个项目")
            except Exception as e:
                print(f"⚠️ 保存列表上下文失败: {e}")

        return {
            'response': response,
            'detected_plans': detected_plans,
            'detected_reminders': detected_reminders,
            'completed_plans': completed_plans,
            'list_data': list_data  # 新增：通用列表数据
        }


    def process_security_command(self, user_message, user_id=None, token=None, session_id=None):
        """处理安全验证相关命令（✨新增session_id参数）"""
        import hashlib
        from mysql_manager import MySQLManager

        message = user_message.strip()

        # 检查是否是"设置验证码"命令
        if message.startswith('设置验证码:') or message.startswith('设置验证码：'):
            code = message.split(':', 1)[-1].split('：', 1)[-1].strip()

            if not code or len(code) < 4:
                return {
                    'response': '❌ 验证码至少需要4个字符\n\n请使用格式：设置验证码：你的验证码',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }

            # 加密验证码
            hashed_code = hashlib.sha256(code.encode()).hexdigest()

            try:
                # 检查用户是否已设置验证码
                existing = self.memory.db.query(
                    "SELECT security_code FROM users WHERE id = %s",
                    (user_id,)
                )
                
                if existing and existing[0]['security_code']:
                    return {
                        'response': '⚠️ 您已设置过验证码\n\n如需修改，请使用：修改验证码：旧密码：新密码',
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }
                
                self.memory.db.execute(
                    "UPDATE users SET security_code = %s WHERE id = %s",
                    (hashed_code, user_id)
                )
                

                return {
                    'response': '✅ 安全验证码设置成功！\n\n现在查询敏感信息时需要验证码。',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }
            except Exception as e:
                return {
                    'response': f'❌ 设置失败：{str(e)}',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }
        
        # 检查是否是"修改验证码"命令
        if message.startswith('修改验证码:') or message.startswith('修改验证码：'):
            parts = message.split(':', 2) if ':' in message else message.split('：', 2)
            
            if len(parts) < 3:
                return {
                    'response': '❌ 格式错误\n\n请使用：修改验证码：旧密码：新密码',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }
            
            old_code = parts[1].strip()
            new_code = parts[2].strip()
            
            if not old_code or not new_code:
                return {
                    'response': '❌ 旧密码和新密码不能为空\n\n请使用：修改验证码：旧密码：新密码',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }
            
            if len(new_code) < 4:
                return {
                    'response': '❌ 新验证码至少需要4个字符',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }
            
            try:
                # 验证旧密码
                result = self.memory.db.query(
                    "SELECT security_code FROM users WHERE id = %s",
                    (user_id,)
                )
                
                if not result or not result[0]['security_code']:
                    return {
                        'response': '❌ 您还未设置验证码\n\n请先使用：设置验证码：你的验证码',
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }
                
                # 验证旧密码是否正确
                old_hashed = hashlib.sha256(old_code.encode()).hexdigest()
                if old_hashed != result[0]['security_code']:
                    return {
                        'response': '❌ 旧验证码错误，请重新输入',
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }
                
                # 更新为新密码
                new_hashed = hashlib.sha256(new_code.encode()).hexdigest()
                self.memory.db.execute(
                    "UPDATE users SET security_code = %s WHERE id = %s",
                    (new_hashed, user_id)
                )
                
                # 清除所有session的验证状态（需要重新验证）
                self.memory.db.execute(
                    "UPDATE user_sessions SET security_verified = 0, security_verified_at = NULL WHERE user_id = %s",
                    (user_id,)
                )
                
                return {
                    'response': f'✅ 验证码修改成功！\n\n您当前的验证码已修改为{new_code}。',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }
            except Exception as e:
                return {
                    'response': f'❌ 修改失败：{str(e)}',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }

        # 检查是否是"验证"命令（支持直接输入验证码）
        code = None
        if message.startswith('验证:') or message.startswith('验证：'):
            code = message.split(':', 1)[-1].split('：', 1)[-1].strip()

            if not code:
                return {
                    'response': '❌ 请输入验证码\n\n格式：验证：你的验证码',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }
        # 智能识别：如果消息看起来像验证码（纯数字，4-20位），尝试验证
        elif len(message) >= 4 and len(message) <= 20 and message.replace(' ', '').isdigit():
            # ✨ 新逻辑：检查内存中的验证状态，如果已验证则不处理数字消息（使用session_id）
            if session_id and session_id in self.session_security_status:
                if self.session_security_status[session_id].get('verified'):
                    return None  # 已验证，不把数字当作验证码

            # 未验证状态，当作验证码处理
            code = message.strip()
            print(f"🔍 DEBUG: 智能识别到验证码: {code}")
        else:
            # 不是验证相关命令
            return None
        
        # 如果识别到验证码（无论是"验证："格式还是智能识别），执行验证
        if code:
            # ✨ 新逻辑：获取用户设置的验证码，如果未设置则使用默认验证码000000
            try:
                result = self.memory.db.query(
                    "SELECT security_code FROM users WHERE id = %s",
                    (user_id,)
                )

                # ✨ 新逻辑：支持默认验证码000000
                is_using_default_code = False
                if not result or not result[0].get('security_code'):
                    # 未设置验证码，使用默认验证码000000
                    default_code_hash = hashlib.sha256('000000'.encode()).hexdigest()
                    user_security_code = default_code_hash
                    is_using_default_code = True
                    print(f"🔍 DEBUG: 用户未设置验证码，使用默认验证码000000")
                else:
                    user_security_code = result[0]['security_code']
                    # 检查用户设置的是否也是000000
                    default_code_hash = hashlib.sha256('000000'.encode()).hexdigest()
                    is_using_default_code = (user_security_code == default_code_hash)
                    print(f"🔍 DEBUG: 用户已设置验证码，is_default={is_using_default_code}")

                # 验证密码
                hashed_input = hashlib.sha256(code.encode()).hexdigest()

                if hashed_input == user_security_code:
                    # ✨ 验证成功，存储到内存而不是数据库（使用session_id，关闭浏览器后失效）
                    if session_id:
                        self.session_security_status[session_id] = {
                            'verified': True,
                            'is_default_code': is_using_default_code
                        }
                        print(f"🔍 DEBUG: 验证成功，已存储到内存，session_id={session_id[:20]}")

                    # 检查是否有待验证的查询（先从内存，再从数据库）
                    original_query = None
                    if user_id in self.pending_verification_queries:
                        original_query = self.pending_verification_queries.pop(user_id)
                        print(f"🔍 DEBUG: 从内存中找到待验证查询: {original_query}")
                    else:
                        # ✨ 从数据库中读取待验证查询
                        try:
                            user_result = self.memory.db.query(
                                "SELECT pending_query FROM users WHERE id = %s",
                                (user_id,)
                            )
                            if user_result and user_result[0].get('pending_query'):
                                original_query = user_result[0]['pending_query']
                                print(f"🔍 DEBUG: 从数据库中找到待验证查询: {original_query}")
                                # 清空数据库中的待验证查询
                                self.memory.db.execute(
                                    "UPDATE users SET pending_query = NULL WHERE id = %s",
                                    (user_id,)
                                )
                        except Exception as e:
                            print(f"⚠️ 从数据库读取待验证查询失败: {e}")

                    if original_query:
                        print(f"🔍 DEBUG: 验证成功，自动执行原查询: {original_query}")

                        # ✨ 递归调用chat方法处理原查询（传递session_id）
                        result = self.chat(original_query, user_id=user_id, token=token, session_id=session_id)

                        # 检查result是否为有效的dict
                        if not isinstance(result, dict):
                            result = {'response': str(result), 'detected_plans': [], 'detected_reminders': [], 'completed_plans': []}

                        # 如果AI返回"没有找到"，尝试使用直接搜索
                        if isinstance(result, dict) and 'response' in result:
                            if '没有找到' in result['response'] or '找不到' in result['response']:
                                print(f"🔍 DEBUG: AI未找到结果，尝试直接搜索关键词")
                                # 提取关键词直接搜索
                                keywords = []
                                for word in ['稿定', '淘宝', '支付宝', '微信', '抖音', 'verve',
                                           '账号', '密码', '生日', '手机', '电话']:
                                    if word in original_query:
                                        keywords.append(word)

                                if keywords:
                                    search_results = []
                                    for kw in keywords[:2]:  # 最多搜索2个关键词
                                        results = self.memory.search_by_keyword(kw, user_id=user_id)
                                        search_results.extend(results)

                                    # 去重
                                    seen = set()
                                    unique_results = []
                                    for r in search_results:
                                        key = f"{r['timestamp']}{r['content']}"
                                        if key not in seen:
                                            seen.add(key)
                                            unique_results.append(r)

                                    if unique_results:
                                        response = f"根据记录，找到以下信息：\n\n"
                                        for chat in unique_results[:5]:
                                            if chat['role'] == 'user':
                                                response += f"- {chat['content']}\n"
                                        result['response'] = response

                            # ✨ 在结果前添加验证成功提示（如果使用默认验证码，提示修改）
                            if is_using_default_code:
                                result['response'] = '✅ 验证成功！\n\n⚠️ 为确保您的隐私安全，请及时修改验证码\n修改方法：设置验证码：您的新密码（至少4个字符）\n\n' + result['response']
                            else:
                                result['response'] = '✅ 验证成功！\n\n' + result['response']

                        return result
                    else:
                        # ✨ 没有待验证查询，返回成功提示（如果使用默认验证码，提示修改）
                        if is_using_default_code:
                            return {
                                'response': '✅ 验证成功！\n\n⚠️ 您正在使用默认验证码，为确保您的隐私安全，请及时修改验证码\n\n修改方法：\n设置验证码：您的新密码\n\n格式：至少4个字符，建议使用6位以上数字或字母组合',
                                'detected_plans': [],
                                'detected_reminders': [],
                                'completed_plans': []
                            }
                        else:
                            return {
                                'response': '✅ 验证成功！\n\n您现在可以查询敏感信息了。\n（关闭网页后需重新验证）',
                                'detected_plans': [],
                                'detected_reminders': [],
                                'completed_plans': []
                            }
                else:
                    return {
                        'response': '❌ 验证码错误，请重新输入',
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }
            except Exception as e:
                return {
                    'response': f'❌ 验证失败：{str(e)}',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }

        return None

    def contains_sensitive_keywords(self, message):
        """检查消息是否包含敏感关键词"""
        message_lower = message.lower()
        for keyword in self.sensitive_keywords:
            if keyword in message_lower or keyword in message:
                return True
        return False

    def check_security_verification(self, user_message, user_id, session_id=None):
        """检查是否需要安全验证（✨改进：使用session_id而不是token）"""
        print(f"🔍 DEBUG verification check: message='{user_message}', user_id={user_id}, session_id={session_id[:20] if session_id else None}...")

        # 如果消息不包含敏感关键词，不需要验证
        has_sensitive = self.contains_sensitive_keywords(user_message)
        print(f"🔍 DEBUG contains_sensitive_keywords: {has_sensitive}")
        if not has_sensitive:
            return None

        # ✨ 新逻辑：检查内存中的验证状态（使用session_id，关闭浏览器后失效）
        if session_id and session_id in self.session_security_status:
            if self.session_security_status[session_id].get('verified'):
                print(f"🔍 DEBUG: 内存中找到已验证状态，允许查询")
                return None

        # ✨ 新逻辑：检查用户是否设置了验证码（决定提示信息）
        try:
            result = self.memory.db.query(
                "SELECT security_code FROM users WHERE id = %s",
                (user_id,)
            )

            has_custom_code = bool(result and result[0].get('security_code'))

            if has_custom_code:
                print(f"🔍 DEBUG: 用户 {user_id} 已设置自定义验证码")
                verification_prompt = '🔒 该查询涉及敏感信息，需要验证码验证\n\n请直接输入您的验证码'
            else:
                # ✨ 未设置验证码，使用默认验证码000000
                print(f"🔍 DEBUG: 用户 {user_id} 未设置验证码，使用默认验证码000000")
                verification_prompt = '🔒 该查询涉及敏感信息，需要验证码验证\n\n您还未设置验证码，默认验证码为：000000\n\n请输入验证码（建议设置后输入自定义验证码）'

            # 需要验证 - 保存原始查询（同时保存到内存和数据库）
            print(f"🔍 DEBUG: 准备返回拦截消息，保存原始查询: {user_message}")
            self.pending_verification_queries[user_id] = user_message

            # ✨ 新增：同时保存到数据库，防止刷新页面后丢失
            try:
                self.memory.db.execute(
                    "UPDATE users SET pending_query = %s WHERE id = %s",
                    (user_message, user_id)
                )
            except Exception as e:
                print(f"⚠️ 保存待验证查询到数据库失败: {e}")

            return {
                'response': verification_prompt,
                'detected_plans': [],
                'detected_reminders': [],
                'completed_plans': [],
                'needs_verification': True
            }
        except Exception as e:
            print(f"🔍 DEBUG: 验证检查出错: {e}")
            return None

    def check_context_reference(self, user_message, user_id):
        """检查用户输入是否引用了上一次显示的内容

        如果用户说"删除1."、"完成2."等，且上一次显示了列表，
        则自动转换为完整命令，如"工作 删除 1"
        """
        print(f"🔍 DEBUG check_context_reference: user_id={user_id}, message='{user_message}'")

        if not user_id or user_id not in self.last_response_context:
            print(f"🔍 DEBUG: 没有找到上下文 (user_id={user_id}, has_context={user_id in self.last_response_context if user_id else False})")
            return None

        # ✨ 防止无限递归：如果消息已经包含操作词和序号，且格式像完整命令，不再转换
        # 检查消息是否匹配 "XXX 操作词 数字" 的格式
        import re
        action_pattern = r'^[\u4e00-\u9fa5a-zA-Z0-9]+\s+(完成|删除|标记|做完|搞定)\s+[\d\.\s]+$'
        if re.match(action_pattern, user_message.strip()):
            print(f"🔍 DEBUG: 消息已是完整命令格式，跳过转换")
            return None

        # ✨ 改进：支持多个子类别上下文
        user_contexts = self.last_response_context[user_id]

        # 如果是旧格式（直接是上下文对象），兼容处理
        if 'type' in user_contexts:
            context = user_contexts
            context_type = context.get('type')
            print(f"🔍 DEBUG: 找到上下文类型={context_type}（旧格式）")
        else:
            # 新格式：使用最近的上下文
            latest_subcategory = user_contexts.get('_latest')
            if not latest_subcategory or latest_subcategory not in user_contexts:
                print(f"🔍 DEBUG: 没有找到最近的上下文")
                return None

            context = user_contexts[latest_subcategory]
            context_type = context.get('type')
            print(f"🔍 DEBUG: 找到最近的上下文类型={context_type}，子类别={latest_subcategory}")

        # 检测引用模式：操作词 + 序号
        # 支持：删除1. / 删除1 / 完成2. / 完成2 / 第3个删除 等
        import re

        # 操作关键词映射
        action_keywords = {
            '删除': '删除',
            '完成': '完成',
            '标记': '完成',
            '做完': '完成',
            '搞定': '完成',
        }

        # 检查是否包含操作词
        detected_action = None
        for keyword, action in action_keywords.items():
            if keyword in user_message:
                detected_action = action
                print(f"🔍 DEBUG: 检测到操作词='{keyword}' -> '{action}'")
                break

        # 提取序号
        numbers = re.findall(r'\d+', user_message)
        print(f"🔍 DEBUG: 提取到的序号={numbers}")

        # 如果有操作词和序号，且上下文是列表类型
        if detected_action and numbers:
            # ✨ 保留所有序号，用点号连接（支持批量操作）
            numbers_str = '.'.join(numbers)

            # 根据上下文类型转换为完整命令
            if context_type == 'work_list':
                result = f"工作 {detected_action} {numbers_str}"
                print(f"🔍 DEBUG: 转换为完整命令='{result}'")
                return result
            elif context_type == 'plan_list':
                result = f"计划 {detected_action} {numbers_str}"
                print(f"🔍 DEBUG: 转换为完整命令='{result}'")
                return result
            elif context_type == 'daily_records':
                # ✨ 对于daily_records，优先使用子类别名称
                subcategory_name = context.get('subcategory_name')
                if subcategory_name:
                    result = f"{subcategory_name} {detected_action} {numbers_str}"
                    print(f"🔍 DEBUG: 转换为完整命令='{result}' (使用子类别名称)")
                else:
                    # 兼容旧版本，使用通用的"记录"命令
                    result = f"记录 {detected_action} {numbers_str}"
                    print(f"🔍 DEBUG: 转换为完整命令='{result}' (使用通用命令)")
                return result

        print(f"🔍 DEBUG: 未匹配到上下文引用模式")
        return None

    def _fuzzy_match_subcategory(self, user_message, user_id, include_chat=True):
        """模糊匹配子类别名称

        支持格式：
        - "ai" → 查找包含"ai"的子类别，返回该子类别的记录
        - "ai相关" → 查找包含"ai"的所有记录（包含聊天记录）
        - "ai所有" → 查找包含"ai"的所有记录（包含聊天记录）

        参数：
        - include_chat: 是否包含聊天记录（默认True，让搜索范围更广）

        ✨ 新增逻辑：
        - 如果找到子类别，返回子类别命令
        - 如果没找到子类别，进行全面搜索并返回搜索结果
        """
        # 提取关键词（处理"X相关"和"X所有"格式）
        match = re.search(r'(.+?)(?:相关|所有)?$', user_message)
        if not match:
            return None

        keyword = match.group(1).strip()
        # 移除"相关"或"所有"后缀
        keyword = re.sub(r'(?:相关|所有)$', '', keyword).strip()

        if not keyword:
            return None

        # 查询数据库中包含该关键词的子类别
        from category_system import CategoryManager
        category_mgr = CategoryManager()

        # 获取所有子类别（包括用户自定义的）
        all_categories = category_mgr.get_all_categories()
        matched_subcategories = []

        for category in all_categories:
            # 获取该类别下的所有子类别（包括系统预设和用户自定义）
            subcategories = category_mgr.get_subcategories(category['id'], user_id=user_id)

            for sub in subcategories:
                # 检查子类别名称是否包含关键词
                if keyword in sub['name']:
                    matched_subcategories.append(sub['name'])

        if len(matched_subcategories) == 0:
            # ✨ 没有找到匹配的子类别，进行全面搜索
            print(f"🔍 未找到子类别匹配'{keyword}'，进行全面搜索...")
            search_results = self._comprehensive_search_related(keyword, user_id, include_chat=include_chat)
            formatted_results = self._format_comprehensive_search_results(keyword, search_results)

            # 返回搜索结果而不是None
            return {
                'response': formatted_results,
                'is_comprehensive_search': True,
                'detected_plans': [],
                'detected_reminders': [],
                'completed_plans': []
            }
        elif len(matched_subcategories) == 1:
            # 找到唯一匹配，转换为该子类别命令
            subcategory_name = matched_subcategories[0]
            # 提取"相关"或"所有"后面的内容（如果有）
            remaining = user_message.split(keyword, 1)[1].strip() if keyword in user_message else ''
            if remaining:
                return f"{subcategory_name} {remaining}"
            else:
                return subcategory_name
        else:
            # 找到多个匹配，暂时返回第一个（未来可以改进为让用户选择）
            subcategory_name = matched_subcategories[0]
            remaining = user_message.split(keyword, 1)[1].strip() if keyword in user_message else ''
            if remaining:
                return f"{subcategory_name} {remaining}"
            else:
                return subcategory_name

    def _comprehensive_search_related(self, keyword, user_id, include_chat=True):
        """
        ✨ 全面搜索相关数据

        参数：
        - include_chat: 是否包含聊天记录（默认True）
          - True: 搜索messages + daily_records + guestbook + work_plans（推荐）
          - False: 搜索daily_records + guestbook + work_plans
        """
        print(f"🔍 开始全面搜索: keyword='{keyword}', user_id={user_id}, include_chat={include_chat}")
        all_results = []

        # 1. 搜索聊天记录 (messages) - 仅当 include_chat=True 时
        if include_chat:
            try:
                chat_results = self.memory.search_by_keyword(keyword, user_id=user_id)
                if chat_results:
                    print(f"🔍 在messages中找到{len(chat_results)}条结果")
                    for chat in chat_results:
                        all_results.append({
                            'type': '聊天记录',
                            'content': chat.get('content', ''),
                            'timestamp': chat.get('timestamp', ''),
                            'source': 'messages'
                        })
            except Exception as e:
                print(f"❌ 搜索messages出错: {e}")
        else:
            print(f"🔍 跳过聊天记录搜索（include_chat=False）")

        # 2. 搜索日常记录 (daily_records)
        try:
            daily_results = self._search_daily_records(keyword, user_id)
            if daily_results:
                print(f"🔍 在daily_records中找到{len(daily_results)}条结果")
                for record in daily_results:
                    # 使用子类别名称作为分类，如果没有则使用"日常记录"
                    subcategory_name = record.get('subcategory_name') or '日常记录'
                    all_results.append({
                        'type': f'{subcategory_name}记录',
                        'content': f"{record.get('title', '')} - {record.get('content', '')}",
                        'timestamp': record.get('created_at', ''),
                        'source': 'daily_records'
                    })
            else:
                print(f"🔍 在daily_records中未找到结果")
        except Exception as e:
            print(f"❌ 搜索daily_records出错: {e}")

        # 3. 搜索留言墙 (guestbook_messages)
        try:
            guestbook_results = self._search_guestbook(keyword, user_id)
            if guestbook_results:
                print(f"🔍 在guestbook中找到{len(guestbook_results)}条结果")
                for record in guestbook_results:
                    all_results.append({
                        'type': '留言墙',
                        'content': record.get('content', ''),
                        'timestamp': record.get('created_at', ''),
                        'source': 'guestbook'
                    })
            else:
                print(f"🔍 在guestbook中未找到结果")
        except Exception as e:
            print(f"❌ 搜索guestbook出错: {e}")

        # 4. 搜索工作计划 (work_plans)
        try:
            plans = self.planner.list_plans(user_id=user_id)
            plan_results = [p for p in plans if keyword in p.get('title', '') or keyword in p.get('description', '')]
            if plan_results:
                print(f"🔍 在work_plans中找到{len(plan_results)}条结果")
                for plan in plan_results:
                    all_results.append({
                        'type': '工作计划',
                        'content': f"{plan.get('title', '')} - {plan.get('description', '')}",
                        'timestamp': plan.get('created_at', ''),
                        'source': 'work_plans'
                    })
            else:
                print(f"🔍 在work_plans中未找到结果")
        except Exception as e:
            print(f"❌ 搜索work_plans出错: {e}")

        print(f"🔍 全面搜索完成，共找到{len(all_results)}条结果")

        # ✨ 新增：计算相关性评分并排序
        for result in all_results:
            result['relevance_score'] = self.calculate_relevance_score(
                content=result.get('content', ''),
                keyword=keyword,
                timestamp=result.get('timestamp')
            )

        # 按相关性评分降序排序
        all_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        print(f"🔍 已按相关性排序，最高分: {all_results[0]['relevance_score']:.2f}" if all_results else "")

        return all_results

    def _format_comprehensive_search_results(self, keyword, results):
        """
        ✨ 格式化全面搜索结果（带关键词高亮）
        """
        if not results:
            return f"没有记录'{keyword}'相关信息"

        response = f"🔍 找到 {len(results)} 条与'{keyword}'相关的信息：\n\n"

        # 按类型分组显示
        grouped = {}
        for result in results:
            result_type = result['type']
            if result_type not in grouped:
                grouped[result_type] = []
            grouped[result_type].append(result)

        idx = 1
        for result_type, items in grouped.items():
            response += f"📌 {result_type}（共{len(items)}条）：\n"
            for item in items:
                content = item['content'][:80] if item['content'] else '（无内容）'  # 截断长内容

                # ✨ 高亮关键词
                content = self.highlight_keywords(content, [keyword])

                # 处理timestamp，可能是datetime对象或字符串
                timestamp = item['timestamp']
                if timestamp:
                    if isinstance(timestamp, str):
                        timestamp = timestamp[:10]  # 字符串，取前10个字符
                    else:
                        # datetime对象，转换为字符串
                        timestamp = str(timestamp)[:10]
                else:
                    timestamp = '未知'

                response += f"  {idx}. {content}\n     [{timestamp}]\n"
                idx += 1
            response += "\n"

        return response

    def _handle_query_other_category(self, user_id):
        """处理"其他"查询命令

        显示"其他类"（原"记录类"）下面的所有数据
        """
        if not user_id:
            return {
                'response': '❌ 请先登录后再使用此功能',
                'detected_plans': [],
                'is_shortcut': True
            }

        try:
            from category_system import DailyRecordManager, CategoryManager

            category_mgr = CategoryManager()

            # 查询"其他类"类别（code='record'）
            query = "SELECT id, name FROM categories WHERE code = %s"
            result = category_mgr.query(query, ('record',))

            if not result:
                return {
                    'response': '❌ 未找到"其他类"类别',
                    'detected_plans': [],
                    'is_shortcut': True
                }

            category_id = result[0]['id']
            category_name = result[0]['name']

            # 查询该类别下的所有子类别
            sub_query = "SELECT id, name FROM subcategories WHERE category_id = %s ORDER BY id"
            subcategories = category_mgr.query(sub_query, (category_id,))

            if not subcategories:
                return {
                    'response': f'📭 "{category_name}"类别下没有子类别',
                    'detected_plans': [],
                    'is_shortcut': True
                }

            # 查询所有子类别下的记录
            record_mgr = DailyRecordManager()
            all_records = []

            for subcategory in subcategories:
                sub_id = subcategory['id']
                sub_name = subcategory['name']

                # 查询该子类别下的所有记录
                records_query = """
                    SELECT id, title, content, created_at FROM daily_records
                    WHERE subcategory_id = %s AND user_id = %s
                    ORDER BY created_at DESC
                """
                records = category_mgr.query(records_query, (sub_id, user_id))

                if records:
                    all_records.extend(records)

            if not all_records:
                return {
                    'response': f'📭 "{category_name}"类别下没有记录',
                    'detected_plans': [],
                    'is_shortcut': True
                }

            # 格式化输出
            response = f"📋 最近的{category_name}：\n\n"

            # 按创建时间分组显示
            for idx, record in enumerate(all_records, 1):
                title = record['title']
                # 限制标题长度
                if len(title) > 50:
                    title = title[:50] + '...'

                response += f"{idx}. {title}\n"

            # 保存到聊天记录
            self.memory.add_message('user', '其他', user_id=user_id)

            return {
                'response': response,
                'detected_plans': [],
                'is_shortcut': True
            }

        except Exception as e:
            print(f"❌ 查询失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': f"❌ 查询失败: {str(e)}",
                'detected_plans': [],
                'is_shortcut': True
            }

    def _handle_save_record(self, content, user_id, cmd='保存'):
        """处理保存/记录命令

        将内容保存到对应类别下的daily_records表
        - "保存"和"记录"命令 → 保存到"记录"类别（兼容旧数据）
        """
        if not user_id:
            return {
                'response': '❌ 请先登录后再使用此功能',
                'detected_plans': [],
                'is_shortcut': True
            }

        try:
            from category_system import DailyRecordManager, CategoryManager

            category_mgr = CategoryManager()

            # 查询"记录"类别（code='record'）
            category_code = 'record'
            category_name = '记录'
            display_name = '记录'

            # 查询对应类别
            query = "SELECT id FROM categories WHERE code = %s"
            result = category_mgr.query(query, (category_code,))

            if not result:
                # 如果类别不存在，创建它
                print(f"⚠️ '{category_name}'类别不存在，正在创建...")
                category_mgr.add_category(
                    name=category_name,
                    code=category_code,
                    icon='📝',
                    description='日常记录'
                )
                # 重新查询
                result = category_mgr.query(query, (category_code,))

            category_id = result[0]['id']

            # 查询类别下是否有"默认"子类别
            query = "SELECT id FROM subcategories WHERE category_id = %s AND code = %s"
            sub_result = category_mgr.query(query, (category_id, 'default'))

            if not sub_result:
                # 如果"默认"子类别不存在，创建它
                print(f"⚠️ '{category_name}'类别下的'默认'子类别不存在，正在创建...")
                category_mgr.add_subcategory(
                    category_id=category_id,
                    name='默认',
                    code='default',
                    description='默认记录'
                )
                # 重新查询
                sub_result = category_mgr.query(query, (category_id, 'default'))

            subcategory_id = sub_result[0]['id']

            # 保存记录到daily_records表
            record_mgr = DailyRecordManager()

            # 提取标题（第一行或前50个字符）
            lines = content.split('\n')
            title = lines[0][:50] if lines[0] else '无标题'

            # 保存记录
            record_mgr.add_record(
                user_id=user_id,
                title=title,
                content=content,
                subcategory_id=subcategory_id,
                tags=cmd  # 使用命令名作为标签
            )

            # 保存到聊天记录
            self.memory.add_message('user', f"{cmd}: {content}", user_id=user_id)

            response = f"✅ 已保存到'{display_name}'类别\n\n📝 标题：{title}"
            if len(content) > 50:
                response += f"\n📄 内容：{content[:50]}..."
            else:
                response += f"\n📄 内容：{content}"

            return {
                'response': response,
                'detected_plans': [],
                'is_shortcut': True
            }
        except Exception as e:
            print(f"❌ 保存记录失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': f"❌ 保存失败: {str(e)}",
                'detected_plans': [],
                'is_shortcut': True
            }

    def process_task_operation(self, user_message, user_id=None):
        """处理记录操作指令：修改、置顶（支持工作任务和所有分类记录）"""
        message = user_message.strip()

        # 检查是否是"修改 序号 内容"指令
        modify_pattern = r'^修改\s*(\d+)\s*[:：]?\s*(.+)$'
        modify_match = re.match(modify_pattern, message)

        if modify_match:
            index = int(modify_match.group(1))
            new_content = modify_match.group(2).strip()

            # 检查是否有上下文
            if user_id not in self.last_response_context:
                return {
                    'response': '❌ 请先查询列表（如"工作"、"财务"等），然后再使用修改指令',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }

            context = self.last_response_context[user_id]
            context_type = context.get('type')
            data = context.get('data', [])

            if index < 1 or index > len(data):
                return {
                    'response': f'❌ 序号 {index} 超出范围，当前有 {len(data)} 条记录',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }

            # 获取要修改的记录
            item = data[index - 1]
            item_id = item['id']
            old_content = item.get('title') or item.get('content', '')[:50]

            try:
                # 根据类型选择不同的更新方法
                if context_type == 'work_list':
                    # 工作任务：更新 work_tasks 表
                    from mysql_manager import WorkPlanManagerMySQL
                    planner = WorkPlanManagerMySQL(self.db)
                    success = planner.update_plan(item_id, user_id=user_id, title=new_content)
                elif context_type == 'daily_records':
                    # 分类记录：更新 daily_records 表
                    update_sql = "UPDATE daily_records SET title = %s WHERE id = %s AND user_id = %s"
                    self.db.execute(update_sql, (new_content, item_id, user_id))
                    success = True
                else:
                    return {
                        'response': f'❌ 不支持的记录类型：{context_type}',
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }

                if success:
                    return {
                        'response': f'✅ 已修改第 {index} 项：\n\n原内容：{old_content}\n新内容：{new_content}',
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }
                else:
                    return {
                        'response': f'❌ 修改失败，可能没有权限或记录不存在',
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }
            except Exception as e:
                print(f"❌ 修改记录失败: {e}")
                import traceback
                traceback.print_exc()
                return {
                    'response': f'❌ 修改失败: {str(e)}',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }

        # 检查是否是"置顶 序号列表"指令
        pin_pattern = r'^置顶\s+([\d,，\s]+)$'
        pin_match = re.match(pin_pattern, message)

        if pin_match:
            # 提取序号列表
            numbers_str = pin_match.group(1)
            numbers_str = numbers_str.replace('，', ',').replace(' ', ',')
            try:
                indices = [int(n.strip()) for n in numbers_str.split(',') if n.strip()]
            except ValueError:
                return {
                    'response': '❌ 序号格式错误，请使用数字，例如：置顶 5,8',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }

            # 检查是否有上下文
            if user_id not in self.last_response_context:
                return {
                    'response': '❌ 请先查询列表（如"工作"、"财务"等），然后再使用置顶指令',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }

            context = self.last_response_context[user_id]
            context_type = context.get('type')
            data = context.get('data', [])

            # 验证所有序号
            for idx in indices:
                if idx < 1 or idx > len(data):
                    return {
                        'response': f'❌ 序号 {idx} 超出范围，当前有 {len(data)} 条记录',
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }

            try:
                # 根据类型选择不同的表和字段
                if context_type == 'work_list':
                    table_name = 'work_tasks'
                elif context_type == 'daily_records':
                    table_name = 'daily_records'
                else:
                    return {
                        'response': f'❌ 不支持的记录类型：{context_type}',
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }

                # 获取当前最大的 sort_order
                max_order_sql = f"SELECT MAX(sort_order) as max_order FROM {table_name} WHERE user_id = %s"
                result = self.db.query_one(max_order_sql, (user_id,))
                max_order = result['max_order'] if result and result['max_order'] else 0

                # 按用户指定的顺序置顶
                pinned_titles = []
                for i, idx in enumerate(indices):
                    item = data[idx - 1]
                    item_id = item['id']
                    new_sort_order = max_order + len(indices) - i

                    update_sql = f"UPDATE {table_name} SET sort_order = %s WHERE id = %s AND user_id = %s"
                    self.db.execute(update_sql, (new_sort_order, item_id, user_id))

                    item_title = item.get('title') or item.get('content', '')[:50]
                    pinned_titles.append(f"{idx}. {item_title}")

                type_name = "工作" if context_type == 'work_list' else "记录"
                return {
                    'response': f'✅ 已按顺序置顶以下{type_name}：\n\n' + '\n'.join(pinned_titles) + f'\n\n下次查看时将按此顺序显示在最前面',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }
            except Exception as e:
                print(f"❌ 置顶记录失败: {e}")
                import traceback
                traceback.print_exc()
                return {
                    'response': f'❌ 置顶失败: {str(e)}',
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                }

        # 不是记录操作指令
        return None

    def process_shortcut_command(self, user_message, user_id=None):
        """处理快捷命令 - 工作: 和 计划: 和 保存: 和 记录:（兼容中文冒号和空格）"""
        message = user_message.strip()

        # ✨ 新增：检查是否是"其他"查询命令（单独处理）
        if message == '其他':
            return self._handle_query_other_category(user_id)

        # ✨ 新增：检查是否是"保存"或"记录"命令（支持多种格式）
        # 支持格式：保存 xxx、保存：xxx、保存:xxx、记录 xxx、记录：xxx、记录:xxx
        save_commands = ['保存', '记录']
        for cmd in save_commands:
            # 检查"保存 xxx"格式（空格分隔）
            if message.startswith(f'{cmd} '):
                content = message[len(cmd)+1:].strip()
                if content:
                    return self._handle_save_record(content, user_id, cmd)
                else:
                    return {
                        'response': f"⚠️ 请提供{cmd}内容：{cmd} (你的内容)",
                        'detected_plans': [],
                        'is_shortcut': True
                    }
            # 检查"保存：xxx"或"保存:xxx"格式（冒号分隔）
            elif message.startswith(f'{cmd}：') or message.startswith(f'{cmd}:'):
                if message.startswith(f'{cmd}：'):
                    content = message[len(cmd)+1:].strip()
                else:
                    content = message[len(cmd)+1:].strip()
                if content:
                    return self._handle_save_record(content, user_id, cmd)
                else:
                    return {
                        'response': f"⚠️ 请提供{cmd}内容：{cmd}：(你的内容)",
                        'detected_plans': [],
                        'is_shortcut': True
                    }

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

                    # 存储带有绝对日期的工作记录
                    formatted_content = content
                    if absolute_date:
                        formatted_content = f"[{absolute_date}] {work_data['task']}"

                    self.memory.add_message('user', f"工作: {formatted_content}", user_id=user_id)

                    # **始终保存到工作计划表（无论是否有截止日期）**
                    try:
                        # 如果没有截止日期，使用今天的日期
                        plan_deadline = absolute_date if absolute_date else datetime.now().strftime('%Y-%m-%d')

                        self.planner.add_plan(
                            title=work_data['task'],
                            description='通过"工作:"命令记录',
                            deadline=plan_deadline,
                            priority='medium',
                            status='pending',
                            user_id=user_id
                        )
                        print(f"✅ 工作已同步到计划表: {work_data['task']}")
                    except Exception as e:
                        print(f"⚠️ 同步到工作计划失败: {e}")

                    response = f"✅ 工作内容已记录：{work_data['task']}"
                    if absolute_date:
                        # 显示时显示原始相对时间，但也注明绝对日期
                        if work_data['deadline'] != absolute_date:
                            response += f"\n⏰ 时间：{work_data['deadline']} ({absolute_date})"
                        else:
                            response += f"\n⏰ 时间：{absolute_date}"

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
        """

        result = {
            'task': content,
            'deadline': ''
        }

        # 时间关键词列表
        time_keywords = ['明天', '后天', '大后天', '今天', '今晚', '今天晚上',
                        '这周', '下周', '周末', '本周', '下月', '本月',
                        '月底', '年底', '周一', '周二', '周三', '周四',
                        '周五', '周六', '周日']

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

    def extract_reminders_from_message(self, user_message, user_id=None):
        """从用户消息中提取提醒信息（不创建提醒，仅返回提醒列表）"""
        reminders = []

        # 提醒关键词
        reminder_keywords = ['提醒', '提示', '通知', '叫我', '告诉我']

        # 检查是否包含提醒意图
        has_reminder = any(kw in user_message for kw in reminder_keywords)

        # 如果没有明确的提醒关键词,检查是否有"时间+动作"模式
        # 例如: "15点开会"、"晚上9点打牌"、"下午3点半上厕所"
        if not has_reminder:
            action_patterns = [
                r'(今天|明天|后天)?\s*(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})[点:：](\d{1,2})?[分半]?\s*(.{1,10})',
            ]
            for pattern in action_patterns:
                match = re.search(pattern, user_message)
                if match:
                    action = match.group(5) if len(match.groups()) >= 5 else None
                    if action and len(action.strip()) > 0:
                        if '?' not in user_message and '吗' not in user_message and '呢' not in user_message:
                            has_reminder = True
                            print(f"🔍 检测到时间+动作模式: {user_message}")
                            break

        if not has_reminder:
            return reminders

        # 完整的时间模式列表（支持所有格式）
        time_patterns = [
            r'(\d+)分钟后',
            r'(\d+)分后',
            r'(\d+)秒钟后',
            r'(\d+)秒后',
            r'(\d+)小时后',
            r'(\d+)点钟后',
            # 循环提醒格式
            r'每年\s*(\d{1,2})月(\d{1,2})日\s*(\d{1,2})\s*:\s*(\d{1,2})',
            r'每年\s*(\d{1,2})月(\d{1,2})日\s*(\d{1,2})点(\d{1,2})分',
            r'每年\s*(\d{1,2})月(\d{1,2})日\s*(\d{1,2})点',
            r'每年\s*(\d{1,2})月(\d{1,2})日',
            r'每月\s*(\d{1,2})日\s*(\d{1,2})\s*:\s*(\d{1,2})',
            r'每月\s*(\d{1,2})日\s*(\d{1,2})点(\d{1,2})分',
            r'每月\s*(\d{1,2})日\s*(\d{1,2})点',
            r'每月\s*(\d{1,2})日',
            r'每周([一二三四五六日天])\s*(\d{1,2})\s*:\s*(\d{1,2})',
            r'每周([一二三四五六日天])\s*(\d{1,2})点(\d{1,2})分',
            r'每周([一二三四五六日天])\s*(\d{1,2})点',
            r'每周([一二三四五六日天])',
            r'每[天日]\s*(\d{1,2})\s*:\s*(\d{1,2})',
            r'每[天日].*?(\d{1,2})点(\d{1,2})分',
            r'每[天日].*?(\d{1,2})点',
            r'每[天日]',
            # 具体日期格式
            r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})\s*:\s*(\d{1,2})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})\s*(\d{1,2})\s*:\s*(\d{1,2})',
            r'(\d{1,2})月(\d{1,2})日.{0,4}?(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})\s*:\s*(\d{1,2})',
            r'(\d{1,2})月(\d{1,2})日.{0,4}?(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})点(\d{1,2})分',
            r'(\d{1,2})月(\d{1,2})日.{0,4}?(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})点',
            r'(\d{1,2})月(\d{1,2})日',
            # 今天/明天/后天格式
            r'今天.{0,4}?(\d{1,2})点(\d{1,2})分',
            r'今天.{0,4}?(\d{1,2})点半',
            r'今天.{0,4}?(\d{1,2})点',
            r'明天.{0,4}?(\d{1,2})点(\d{1,2})分',
            r'明天.{0,4}?(\d{1,2})点半',
            r'明天.{0,4}?(\d{1,2})点',
            r'后天.{0,4}?(\d{1,2})点(\d{1,2})分',
            r'后天.{0,4}?(\d{1,2})点半',
            r'后天.{0,4}?(\d{1,2})点',
            r'今天\s*(\d{1,2})\s*:\s*(\d{1,2})',
            r'明天\s*(\d{1,2})\s*:\s*(\d{1,2})',
            r'后天\s*(\d{1,2})\s*:\s*(\d{1,2})',
            r'今天',
            r'明天',
            r'后天',
            # 单独时间格式（默认为今天）- 包含时间段词
            r'(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})点(\d{1,2})分',
            r'(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})点半',
            r'(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})点',
            r'(\d{1,2})\s*:\s*(\d{1,2})',
        ]

        # 提取时间
        remind_time_str = None
        for pattern in time_patterns:
            match = re.search(pattern, user_message)
            if match:
                remind_time_str = match.group(0)
                break

        if not remind_time_str:
            print(f"⚠️ 未能提取时间信息: {user_message}")
            return reminders

        # 使用reminder_scheduler的parse_reminder_time方法解析时间
        try:
            from reminder_scheduler import get_global_scheduler
            scheduler = get_global_scheduler(db_manager=self.db)

            parse_result = scheduler.parse_reminder_time(remind_time_str)
            if not parse_result:
                print(f"⚠️ 无法解析时间: {remind_time_str}")
                return reminders

            # 处理返回值：可能是tuple(datetime, recurrence_type)或直接是datetime
            if isinstance(parse_result, tuple):
                parsed_time, recurrence_type = parse_result
            else:
                parsed_time = parse_result
                recurrence_type = None

            # 提取提醒内容
            content = user_message
            for kw in reminder_keywords:
                content = content.replace(kw, '')
            content = content.replace(remind_time_str, '')

            # 清理内容
            remove_words = ['我', '你', '的', '了', '吗', '呢', '吧', '啊', '一下', '我要', '要']
            for word in remove_words:
                content = content.replace(word, '')
            content = content.strip('，。；！？、 ')

            if not content:
                content = "提醒"

            # 将datetime对象转换为ISO格式字符串
            iso_time = parsed_time.strftime('%Y-%m-%dT%H:%M:%S')

            reminder_data = {
                'content': content,
                'remind_time': iso_time,
                'repeat_type': recurrence_type if recurrence_type else 'once'
            }

            reminders.append(reminder_data)
            print(f"✅ 提取到提醒: {content} - {remind_time_str} ({iso_time})")

        except Exception as e:
            print(f"❌ 提取提醒时出错: {e}")
            import traceback
            traceback.print_exc()

        return reminders

    def extract_and_create_reminders(self, user_message, user_id=None):
        """从用户消息中提取提醒信息并创建系统提醒"""
        reminders = []

        # 提醒关键词
        reminder_keywords = ['提醒', '提示', '通知', '叫我', '告诉我']

        # 检查是否包含提醒意图
        has_reminder = any(kw in user_message for kw in reminder_keywords)

        # 如果没有明确的提醒关键词,检查是否有"时间+动作"模式
        # 例如: "15点开会"、"晚上9点打牌"、"下午3点半上厕所"
        if not has_reminder:
            # 时间+动作模式的正则匹配
            action_patterns = [
                r'(今天|明天|后天)?\s*(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})[点:：](\d{1,2})?[分半]?\s*(.{1,10})',  # 时间+动作
            ]
            for pattern in action_patterns:
                match = re.search(pattern, user_message)
                if match:
                    action = match.group(5) if len(match.groups()) >= 5 else None
                    # 检查动作是否像是需要提醒的事情(排除纯查询)
                    if action and len(action.strip()) > 0:
                        # 排除疑问句
                        if '?' not in user_message and '吗' not in user_message and '呢' not in user_message:
                            has_reminder = True
                            print(f"🔍 检测到时间+动作模式: {user_message}")
                            break

        if not has_reminder:
            return reminders

        # 提取时间信息的正则表达式
        time_patterns = [
            r'(\d+)分钟后',
            r'(\d+)分后',
            r'(\d+)秒钟后',
            r'(\d+)秒后',
            r'(\d+)小时后',
            r'(\d+)点钟后',
            # 循环提醒格式（新增）
            r'每年\s*(\d{1,2})月(\d{1,2})日\s*(\d{1,2})\s*:\s*(\d{1,2})',   # 每年10月30日9:31
            r'每年\s*(\d{1,2})月(\d{1,2})日\s*(\d{1,2})点(\d{1,2})分',      # 每年10月30日9点31分
            r'每年\s*(\d{1,2})月(\d{1,2})日\s*(\d{1,2})点',                # 每年10月30日9点
            r'每年\s*(\d{1,2})月(\d{1,2})日',                              # 每年10月30日
            r'每月\s*(\d{1,2})日\s*(\d{1,2})\s*:\s*(\d{1,2})',             # 每月3日9:00
            r'每月\s*(\d{1,2})日\s*(\d{1,2})点(\d{1,2})分',                # 每月3日9点0分
            r'每月\s*(\d{1,2})日\s*(\d{1,2})点',                           # 每月3日9点
            r'每月\s*(\d{1,2})日',                                         # 每月3日
            r'每周([一二三四五六日天])\s*(\d{1,2})\s*:\s*(\d{1,2})',        # 每周五9:00
            r'每周([一二三四五六日天])\s*(\d{1,2})点(\d{1,2})分',           # 每周五9点0分
            r'每周([一二三四五六日天])\s*(\d{1,2})点',                      # 每周五9点
            r'每周([一二三四五六日天])',                                    # 每周五
            r'每[天日]\s*(\d{1,2})\s*:\s*(\d{1,2})',                       # 每天9:00
            r'每[天日].*?(\d{1,2})点(\d{1,2})分',                          # 每天早上9点30分
            r'每[天日].*?(\d{1,2})点',                                     # 每天早上9点
            r'每[天日]',                                                   # 每天（默认9:00）
            # 具体日期格式
            r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})\s*:\s*(\d{1,2})',  # 2025年12月28日16:00
            r'(\d{4})-(\d{1,2})-(\d{1,2})\s*(\d{1,2})\s*:\s*(\d{1,2})',      # 2025-12-28 16:00
            r'(\d{1,2})月(\d{1,2})日.{0,4}?(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})\s*:\s*(\d{1,2})',  # 12月28日下午16:00
            r'(\d{1,2})月(\d{1,2})日.{0,4}?(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})点(\d{1,2})分',    # 12月28日下午16点30分
            r'(\d{1,2})月(\d{1,2})日.{0,4}?(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})点',              # 12月28日下午16点
            r'(\d{1,2})月(\d{1,2})日',                                      # 12月28日
            # 今天/明天/后天格式
            r'今天.{0,4}?(\d{1,2})点(\d{1,2})分',  # 今天早上11点5分
            r'今天.{0,4}?(\d{1,2})点半',           # 今天早上11点半
            r'今天.{0,4}?(\d{1,2})点',             # 今天早上11点 / 今天11点
            r'明天.{0,4}?(\d{1,2})点(\d{1,2})分',  # 明天早上11点5分
            r'明天.{0,4}?(\d{1,2})点半',           # 明天早上11点半
            r'明天.{0,4}?(\d{1,2})点',             # 明天早上11点
            r'后天.{0,4}?(\d{1,2})点(\d{1,2})分',  # 后天11点5分
            r'后天.{0,4}?(\d{1,2})点半',           # 后天11点半
            r'后天.{0,4}?(\d{1,2})点',             # 后天11点
            r'今天\s*(\d{1,2})\s*:\s*(\d{1,2})',  # 今天14:00（允许空格）
            r'明天\s*(\d{1,2})\s*:\s*(\d{1,2})',  # 明天14:00 或 明天14: 00（允许空格）
            r'后天\s*(\d{1,2})\s*:\s*(\d{1,2})',  # 后天14:00（允许空格）
            r'今天',
            r'明天',
            r'后天',
            # 单独时间格式（默认为今天）- 包含时间段词
            r'(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})点(\d{1,2})分',  # 下午10点30分
            r'(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})点半',           # 下午10点半
            r'(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})点',             # 下午10点
            r'(\d{1,2})\s*:\s*(\d{1,2})',  # 10:30提醒我...（默认今天）
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
                parse_result = scheduler.parse_reminder_time(remind_time)
                if not parse_result:
                    print(f"⚠️ 无法解析时间: {remind_time}")
                    return reminders

                # 处理返回值：可能是tuple(datetime, recurrence_type)或直接是datetime
                if isinstance(parse_result, tuple):
                    parsed_time, recurrence_type = parse_result
                else:
                    parsed_time = parse_result
                    recurrence_type = None

                # 调用调度器创建提醒
                remind_type = 'recurring' if recurrence_type else 'once'
                result = scheduler.add_reminder(
                    user_id=user_id,
                    message=content,
                    remind_time=parsed_time,  # 使用解析后的时间对象
                    remind_type=remind_type
                )

                if result.get('status') == 'success':
                    # 将datetime对象转换为ISO格式字符串供移动端使用
                    iso_time = parsed_time.strftime('%Y-%m-%dT%H:%M:%S')
                    reminder_data = {
                        'content': content,
                        'time': remind_time,  # 原始文本"30秒后"
                        'remind_time': iso_time,  # ISO格式时间戳
                        'created': True
                    }
                    # 如果是循环提醒，添加recurrence信息
                    if recurrence_type:
                        reminder_data['recurrence'] = recurrence_type  # 'yearly', 'monthly', 'weekly'

                    reminders.append(reminder_data)

                    if recurrence_type:
                        print(f"✅ 已创建循环提醒 ({recurrence_type}): {content} - {remind_time} ({iso_time})")
                    else:
                        print(f"✅ 已创建提醒: {content} - {remind_time} ({iso_time})")
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
        print(f"🔍 DEBUG detect_and_complete_plans 被调用: message='{user_message}', user_id={user_id}")

        if user_id is None:
            return []

        # 完成意图的关键词
        complete_keywords = ['完成', '做完', '做好', '已完成', '搞定', '弄好', '结束', '删除']

        # 检查是否包含完成意图
        has_complete_intent = any(kw in user_message for kw in complete_keywords)
        print(f"🔍 DEBUG has_complete_intent={has_complete_intent}")
        if not has_complete_intent:
            return []

        completed_plans = []

        # ✨ 修复：不再使用全局 data_type，而是根据每个 item 的 source 字段来判断
        pending_plans = []

        # 检查是否有保存的上下文
        if user_id in self.last_response_context:
            context = self.last_response_context[user_id]
            context_type = context.get('type')

            if context_type == 'work_list':
                # 工作列表上下文（可能包含 work_plans 和 work_tasks 的混合数据）
                pending_plans = [t for t in context.get('data', []) if t.get('status') in ['pending', '未完成']]
                print(f"🔍 使用work_list上下文，共{len(pending_plans)}个待完成项目")
            elif context_type == 'daily_records':
                # daily_records上下文
                pending_plans = context.get('data', [])
                print(f"🔍 使用daily_records表上下文，共{len(pending_plans)}条记录")

        # 如果没有上下文，使用合并查询获取所有未完成的工作
        if not pending_plans:
            pending_plans = self.get_all_work_items(user_id, status_filter='pending')
            print(f"🔍 使用合并查询获取未完成工作，共{len(pending_plans)}项")

        if not pending_plans:
            return []

        # 方式1: 提取序号 "第X项"、"第X个"、"2.3.5.6."（多个序号）
        number_patterns = [
            r'第\s*(\d+)\s*[项个条件]',
            r'(\d+)\s*[项个条件]',
            r'工作\s*(\d+)',
            r'任务\s*(\d+)',
        ]

        # 首先检查是否有多个序号（如"2.3.5.6."或"2、3、5、6"或"3.4.5.6.7.8.9.10.1."）
        # 改进：支持更灵活的格式，包括末尾的数字
        multi_numbers = re.findall(r'\b(\d+)\b', user_message)
        # 过滤掉"已完成"等词中可能出现的数字
        # ✨ 修复：只有当数字在关键词之前时才提取前缀（如"1.2.3.已完成"）
        # 对于"完成 1"这种格式（关键词在数字之前），不做处理
        if '已完成' in user_message or '完成' in user_message or '标注' in user_message:
            # 检查是否是"数字在关键词之前"的格式
            keyword_pos = -1
            keyword_used = ''
            if '已完成' in user_message:
                keyword_pos = user_message.find('已完成')
                keyword_used = '已完成'
            elif '标注' in user_message:
                keyword_pos = user_message.find('标注')
                keyword_used = '标注'
            else:
                keyword_pos = user_message.find('完成')
                keyword_used = '完成'

            # 检查第一个数字的位置
            first_number_match = re.search(r'\b(\d+)\b', user_message)
            if first_number_match:
                first_number_pos = first_number_match.start()
                # 只有当数字在关键词之前时，才提取前缀
                if first_number_pos < keyword_pos:
                    prefix = user_message.split(keyword_used)[0]
                    multi_numbers = re.findall(r'\b(\d+)\b', prefix)

        # ✨ 排除时间表达式中的数字（如"1个月"、"2天"）
        if multi_numbers and re.search(r'\d+\s*[个](月|年|星期|周|天)', user_message):
            # 如果包含时间表达式，清空数字列表
            multi_numbers = []

        # ✨ 改进：即使只有1个数字，也应该处理（如"5.标注为已完成"）
        if multi_numbers and len(multi_numbers) >= 1:
            # 处理多个序号
            print(f"🔍 检测到多个序号: {multi_numbers}")
            print(f"🔍 pending_plans数量={len(pending_plans)}")
            for num_str in multi_numbers:
                index = int(num_str) - 1  # 转换为0-based索引
                print(f"🔍 处理序号{num_str}, index={index}")
                if 0 <= index < len(pending_plans):
                    plan = pending_plans[index]
                    print(f"🔍 找到记录: id={plan.get('id')}, source={plan.get('source')}, title={plan.get('content', plan.get('title', ''))[:30]}")
                    # ✨ 根据 source 字段判断数据来源并调用相应的更新方法
                    success = False
                    source = plan.get('source', '')

                    if source == 'daily_records':
                        # daily_records表：更新状态为completed
                        try:
                            record_mgr = DailyRecordManager('mysql_config.json')
                            print(f"🔍 调用update_record_status: record_id={plan['id']}, user_id={user_id}")
                            success = record_mgr.update_record_status(plan['id'], 'completed', user_id)
                            print(f"🔍 update_record_status返回: {success}")
                            if success:
                                print(f"✅ 已标记记录为完成(序号{num_str}): {plan.get('content', plan.get('title', ''))[:50]}")
                            else:
                                print(f"❌ 标记记录失败(序号{num_str}): {plan.get('content', plan.get('title', ''))[:50]}")
                        except Exception as e:
                            print(f"❌ 更新daily_records失败: {e}")
                            import traceback
                            traceback.print_exc()
                            success = False
                    elif source == 'work_tasks':
                        # work_tasks表：更新状态为completed
                        success = self.work_task_manager.update_task_status(plan['id'], 'completed', user_id)
                        if success:
                            print(f"✅ 已标记任务为完成(序号{num_str}): {plan['title']}")
                    else:
                        # 兼容旧数据：默认使用work_tasks表（work_plans已迁移）
                        print(f"⚠️ 项目{num_str}没有source字段，默认使用work_tasks表")
                        success = self.work_task_manager.update_task_status(plan['id'], 'completed', user_id)
                        if success:
                            print(f"✅ 已标记任务为完成(序号{num_str}): {plan['title']}")

                    if success:
                        completed_plans.append({
                            'id': plan['id'],
                            'title': plan.get('content', plan.get('title', ''))[:50],
                            'method': 'multi_index'
                        })
                else:
                    print(f"⚠️ 序号{num_str}超出范围，总数={len(pending_plans)}")

            if completed_plans:
                # 清空该用户的对话历史，避免AI参考过时信息
                self.clear_conversation(user_id=user_id)
                return completed_plans

        # 单个序号匹配
        for pattern in number_patterns:
            match = re.search(pattern, user_message)
            if match:
                index = int(match.group(1)) - 1  # 转换为0-based索引
                if 0 <= index < len(pending_plans):
                    plan = pending_plans[index]
                    # ✨ 根据 source 字段判断数据来源并调用相应的更新方法
                    success = False
                    source = plan.get('source', '')

                    if source == 'daily_records':
                        record_mgr = DailyRecordManager('mysql_config.json')
                        success = record_mgr.update_record_status(plan['id'], 'completed', user_id)
                    elif source == 'work_tasks':
                        success = self.work_task_manager.update_task_status(plan['id'], 'completed', user_id)
                    else:
                        # 兼容旧数据：默认使用work_tasks表（work_plans已迁移）
                        print(f"⚠️ 项目没有source字段，默认使用work_tasks表")
                        success = self.work_task_manager.update_task_status(plan['id'], 'completed', user_id)

                    if success:
                        completed_plans.append({
                            'id': plan['id'],
                            'title': plan.get('content', plan.get('title', ''))[:50],
                            'method': 'index'
                        })
                        print(f"✅ 已标记为完成: {plan.get('content', plan.get('title', ''))[:50]}")
                        self.clear_conversation(user_id=user_id)
                        if source != 'daily_records':
                            self.memory.delete_messages_by_keywords([plan.get('title', '')], user_id=user_id)
                    return completed_plans

        # 方式2: 通过关键词匹配标题
        msg_clean = user_message
        for kw in complete_keywords + ['第', '项', '个', '工作', '任务', '了', '的', '我', '要', '在']:
            msg_clean = msg_clean.replace(kw, ' ')

        keywords = [w.strip() for w in msg_clean.split() if len(w.strip()) >= 2]

        # 尝试匹配计划标题
        for keyword in keywords:
            for plan in pending_plans:
                title = plan.get('content', plan.get('title', ''))
                if keyword in title or title in user_message:
                    # ✨ 根据数据类型调用不同的处理方法
                    success = False
                    if data_type == 'daily_records':
                        record_mgr = DailyRecordManager('mysql_config.json')
                        success = record_mgr.update_record_status(plan['id'], 'completed', user_id)
                    elif data_type == 'work_tasks':
                        work_mgr = WorkTaskManager('mysql_config.json')
                        success = work_mgr.update_task_status(plan['id'], 'completed', user_id)
                    else:
                        success = self.planner.update_plan(plan['id'], user_id=user_id, status='completed')
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
                    for i, chat in enumerate(results, 1):
                        response += f"{i}. [{chat['timestamp']}] {chat['content']}\n"

                    return response
                else:
                    return f"没有找到包含「{keyword}」的记录"
            else:
                recent = self.memory.get_recent_conversations(10, user_id=user_id)
                response = f"📝 最近10条聊天:\n\n"
                for i, chat in enumerate(recent, 1):
                    response += f"{i}. [{chat['timestamp']}] {chat['content']}\n"
                return response
        
        elif any(w in message_lower for w in ['计划', '工作', '任务', '待办']):
            plans = self.planner.list_plans(user_id=user_id)

            if keywords:
                keyword = keywords[0]
                plans = [p for p in plans if keyword in p['title'] or keyword in p['description']]

            # 如果用户问的是"工作"、"当前工作"、"未完成工作"等，显示未完成的工作
            if any(w in message_lower for w in ['未完成', '当前', '工作', '待办']):
                plans = [p for p in plans if p['status'] not in ['已完成', '已取消', 'completed']]

            if plans:
                response = f"📅 找到 {len(plans)} 个计划:\n\n"
                for plan in plans:
                    response += f"• [{plan['status']}] {plan['title']}\n"
                    response += f"  截止: {plan['deadline']} | {plan['priority']}\n\n"
                return response
            else:
                if any(w in message_lower for w in ['当前', '工作', '未完成']):
                    return "✅ 目前没有未完成的工作"
                else:
                    return "没有找到相关计划"
        
        else:
            return """👋 你好！我可以帮你：

📝 查聊天: "我说过XX吗"
📅 查计划: "我有XX计划吗"
⏰ 查提醒: "我有什么待办"
📊 总结: "帮我总结"

试试问我具体问题吧！"""

    def auto_detect_dev_requirement(self, user_message, ai_response, user_id):
        """自动检测和记录开发需求

        检测规则：
        1. 用户提出开发需求（包含：修复、添加、实现、开发、优化等关键词）
        2. AI回复表示理解并开始工作
        3. 自动创建开发日志

        完成检测：
        1. AI回复包含"已完成"、"修复完成"、"实现完成"等
        2. 自动更新最近的进行中日志为已完成
        """
        if not self.dev_log:
            return

        # 开发需求关键词
        requirement_keywords = [
            '修复', '添加', '实现', '开发', '优化', '改进', '增加',
            '创建', '设计', '调整', '更新', '完善', '解决', '处理'
        ]

        # 完成关键词
        completion_keywords = [
            '已完成', '修复完成', '实现完成', '开发完成', '优化完成',
            '已修复', '已实现', '已添加', '已创建', '已优化',
            '完成了', '搞定了', '弄好了', '做完了'
        ]

        # 检测是否是开发需求
        has_requirement = any(kw in user_message for kw in requirement_keywords)

        # 检测AI是否表示开始工作（回复中包含"让我"、"我来"、"开始"等）
        ai_start_keywords = ['让我', '我来', '开始', '好的', '我会', '我将']
        ai_starts_work = any(kw in ai_response for kw in ai_start_keywords)

        # 如果是开发需求且AI开始工作，创建开发日志
        if has_requirement and ai_starts_work:
            # 提取需求描述（取用户消息的前50个字符）
            requirement = user_message[:50]
            if len(user_message) > 50:
                requirement += '...'

            # 检查是否已有相同的进行中任务
            in_progress = self.dev_log.get_in_progress_logs()
            # 避免重复创建（如果最近5分钟内有相似的任务）
            from datetime import datetime, timedelta
            now = datetime.now()
            for log in in_progress:
                log_time = datetime.strptime(log['start_time'], '%Y-%m-%d %H:%M:%S')
                if (now - log_time).total_seconds() < 300:  # 5分钟内
                    if log['requirement'][:30] == requirement[:30]:
                        print(f"⚠️ 跳过重复的开发需求: {requirement[:30]}")
                        return

            # 创建开发日志
            log_id = self.dev_log.add_requirement(requirement, user_message)
            print(f"✅ 自动创建开发日志 #{log_id}: {requirement}")

        # 检测是否完成了开发任务
        has_completion = any(kw in ai_response for kw in completion_keywords)

        if has_completion:
            # 获取最近的进行中任务
            in_progress = self.dev_log.get_in_progress_logs()
            if in_progress:
                # 取最新的一个任务
                latest = in_progress[-1]

                # 提取完成情况描述（从AI回复中提取关键信息）
                # 尝试提取"已XXX"或"完成了XXX"的部分
                completion_desc = ""
                for line in ai_response.split('\n'):
                    if any(kw in line for kw in completion_keywords):
                        completion_desc = line.strip()
                        break

                if not completion_desc:
                    completion_desc = ai_response[:100]
                    if len(ai_response) > 100:
                        completion_desc += '...'

                # 更新为已完成
                self.dev_log.update_completion(latest['id'], completion_desc)
                print(f"✅ 自动标记开发日志 #{latest['id']} 为已完成: {completion_desc[:50]}")

