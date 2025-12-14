#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""个人助手 - Web版本（优化版）"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import webbrowser
import threading
import base64
import uuid
import os
import re
from datetime import datetime, timedelta

# 初始化数据库和管理器
from mysql_manager import MySQLManager
from ai_chat_assistant import AIAssistant
from user_manager import UserManager
from notification_service import get_notification_service, get_notification_queue
from reminder_scheduler import get_global_scheduler

db_manager = MySQLManager('mysql_config.json')
ai_assistant = AIAssistant()
user_manager = UserManager(db_manager)

# 从AI助手获取管理器
memory = ai_assistant.memory
reminder_sys = ai_assistant.reminder
image_manager = ai_assistant.image_manager
planner = ai_assistant.planner

class AssistantHandler(BaseHTTPRequestHandler):

    def get_current_user(self):
        """获取当前登录用户ID，如果未登录返回None"""
        token = self.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return None

        result = user_manager.verify_token(token)
        if result['success']:
            return result['user_id']
        return None

    def require_auth(self):
        """要求用户认证，返回user_id或None"""
        user_id = self.get_current_user()
        if user_id is None:
            self.send_json({'success': False, 'message': '请先登录'}, status=401)
        return user_id

    def parse_relative_time(self, time_str):
        """将相对时间转换为绝对日期

        支持的格式：
        - 明天、后天、大后天
        - 明早、明日
        - 今天、今日
        - 下周X、本周X
        - X天后
        """
        if not time_str or time_str == '':
            return datetime.now().strftime('%Y-%m-%d')

        # 如果已经是日期格式，直接返回
        if re.match(r'\d{4}-\d{2}-\d{2}', time_str):
            return time_str

        now = datetime.now()
        time_str = time_str.strip()
        current_hour = now.hour

        # 处理"明早" - 智能判断
        # 如果现在是凌晨（0-6点），"明早"指今天早上
        # 如果现在是白天或晚上（6-24点），"明早"指明天早上
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

        # 处理"今天"、"今日"、"今早"、"今晚"
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
            # 计算到本周日的天数
            days_until_sunday = (6 - now.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7  # 如果今天是周日，指向下周日
            return (now + timedelta(days=days_until_sunday)).strftime('%Y-%m-%d')

        # 如果无法解析，返回今天
        return now.strftime('%Y-%m-%d')


    def do_GET(self):
        """处理GET请求"""
        if self.path == '/' or self.path == '/index.html':
            # 允许加载主页HTML，前端会通过checkLogin()检查Token
            # 如果Token无效会重定向到/login
            self.send_html()
        elif self.path == '/login' or self.path == '/login.html':
            self.send_login_html()
        elif self.path == '/image-gallery' or self.path == '/image-gallery.html':
            # 图片库也允许加载，前端会检查Token
            self.send_image_gallery_html()
        elif self.path == '/api/chats':
            user_id = self.require_auth()
            if user_id is None:
                return
            chats = memory.get_recent_conversations(100, user_id=user_id)
            self.send_json(chats)
        elif self.path == '/api/chat/history':
            # 获取最近24小时的对话历史
            user_id = self.require_auth()
            if user_id is None:
                return
            
            # 使用新添加的方法
            history = memory.get_messages_last_24h(user_id)
            self.send_json({'success': True, 'history': history})
        elif self.path == '/api/plans':
            user_id = self.require_auth()
            if user_id is None:
                return
            plans = planner.list_plans(user_id=user_id)
            self.send_json(plans)
        elif self.path == '/api/reminders':
            user_id = self.require_auth()
            if user_id is None:
                return
            reminders = reminder_sys.list_reminders(user_id=user_id)
            self.send_json(reminders)
        elif self.path == '/api/images':
            user_id = self.require_auth()
            if user_id is None:
                return
            images = image_manager.list_images(user_id=user_id)
            self.send_json(images)
        elif self.path == '/api/auth/verify':
            # Token验证（GET请求）
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            result = user_manager.verify_token(token)
            self.send_json(result)
        elif self.path == '/api/user/profile':
            # 获取当前用户信息
            user_id = self.require_auth()
            if user_id is None:
                return
            user = user_manager.get_user_by_id(user_id)
            if user:
                # 移除敏感信息
                user_profile = {
                    'id': user['id'],
                    'username': user['username'],
                    'phone': user['phone'],
                    'avatar_url': user.get('avatar_url', ''),
                    'chat_background': user.get('chat_background', ''),
                    'created_at': user.get('created_at', '').strftime('%Y-%m-%d %H:%M:%S') if hasattr(user.get('created_at', ''), 'strftime') else str(user.get('created_at', ''))
                }
                self.send_json({'success': True, 'user': user_profile})
            else:
                self.send_json({'success': False, 'message': '用户不存在'}, status=404)
        elif self.path.startswith('/api/image/'):
            # 获取单个图片信息
            image_id = int(self.path.split('/')[-1])
            img = image_manager.get_image_by_id(image_id)
            if img:
                self.send_json(img)
            else:
                self.send_json({'error': '图片不存在'}, status=404)
        elif self.path.startswith('/uploads/images/'):
            # 直接serve图片文件
            self.serve_image(self.path[1:])  # 去掉开头的 /
        elif self.path.startswith('/uploads/avatars/'):
            # serve头像图片文件
            self.serve_image(self.path[1:])  # 去掉开头的 /
        elif self.path == '/api/ai/get_mode':
            self.send_json({'mode': ai_assistant.model_type, 'config': ai_assistant.config})
        elif self.path == '/api/work-records':
            # 获取工作记录（工作:开头的消息，兼容中文冒号）
            user_id = self.require_auth()
            if user_id is None:
                return

            # 从最近的对话中筛选出工作记录
            all_chats = memory.get_recent_conversations(200, user_id=user_id)
            work_records = [
                chat for chat in all_chats
                if chat['content'].startswith('工作:') or chat['content'].startswith('工作：')  # 兼容英文和中文冒号
            ]

            # 整理工作记录格式，提取时间信息
            formatted_records = []
            import re
            for record in work_records:
                # 移除"工作:"或"工作："前缀（兼容中英文冒号）
                content = record['content']
                if content.startswith('工作:'):
                    content = content[3:].strip()
                elif content.startswith('工作：'):
                    content = content[3:].strip()

                # 尝试从content中提取时间信息 (格式: [时间] 任务 或直接的任务)
                time_match = re.match(r'\[([^\]]+)\]\s*(.*)', content)
                if time_match:
                    deadline = time_match.group(1)
                    task = time_match.group(2)
                else:
                    deadline = ''
                    task = content

                formatted_records.append({
                    'id': record['id'],
                    'content': task,
                    'deadline': deadline,
                    'timestamp': record['timestamp'],
                    'status': '已记录'
                })

            self.send_json({
                'success': True,
                'count': len(formatted_records),
                'records': formatted_records
            })
        elif self.path == '/api/scheduler/reminder/list':
            # 获取用户的所有提醒
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                scheduler = get_global_scheduler(db_manager=db_manager)
                reminders = scheduler.list_reminders(user_id=user_id)
                self.send_json({'success': True, 'reminders': reminders})
            except Exception as e:
                self.send_json({'success': False, 'message': f'错误: {str(e)}'})
        else:
            self.send_error(404)
    
    def do_POST(self):
        """处理POST请求"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(post_data)

        # 认证相关API
        if self.path == '/api/auth/register':
            # 用户注册
            username = data.get('username', '')
            password = data.get('password', '')
            phone = data.get('phone', '')

            if not username or not password:
                self.send_json({'success': False, 'message': '用户名和密码不能为空'})
                return

            result = user_manager.register(username, password, phone)
            self.send_json(result)

        elif self.path == '/api/auth/login':
            # 用户登录
            username = data.get('username', '')
            password = data.get('password', '')

            if not username or not password:
                self.send_json({'success': False, 'message': '用户名和密码不能为空'})
                return

            result = user_manager.login(username, password)
            self.send_json(result)

        elif self.path == '/api/auth/logout':
            # 退出登录
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            result = user_manager.logout(token)
            self.send_json(result)

        elif self.path == '/api/auth/verify':
            # 验证Token
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            result = user_manager.verify_token(token)
            self.send_json(result)

        elif self.path == '/api/ai/chat':
            user_id = self.require_auth()
            if user_id is None:
                return
            chat_result = ai_assistant.chat(data.get('message', ''), user_id=user_id)
            # 处理新的返回格式（包含response、detected_plans、detected_reminders和completed_plans）
            if isinstance(chat_result, dict):
                response_data = {
                    'response': chat_result.get('response', ''),
                    'detected_plans': chat_result.get('detected_plans', []),
                    'detected_reminders': chat_result.get('detected_reminders', []),
                    'completed_plans': chat_result.get('completed_plans', [])
                }

                # 如果有完成的计划，在响应中添加提示
                if response_data['completed_plans']:
                    completed_titles = [p['title'] for p in response_data['completed_plans']]
                    completion_msg = f"\n\n✅ 已标记为完成：{'、'.join(completed_titles)}"
                    response_data['response'] += completion_msg

                self.send_json(response_data)
            else:
                # 向后兼容：如果返回的是字符串
                self.send_json({'response': chat_result, 'detected_plans': [], 'detected_reminders': [], 'completed_plans': []})

        elif self.path == '/api/ai/clear':
            user_id = self.require_auth()
            if user_id is None:
                return
            ai_assistant.clear_conversation(user_id=user_id)
            self.send_json({'success': True, 'message': '对话已清空'})
        
        elif self.path == '/api/ai/switch_mode':
            mode = data.get('mode', 'simple')
            ai_assistant.config['model_type'] = mode
            ai_assistant.model_type = mode
            # 保存到配置文件
            with open('ai_config.json', 'w', encoding='utf-8') as f:
                json.dump(ai_assistant.config, f, ensure_ascii=False, indent=2)
            self.send_json({'success': True, 'mode': mode, 'message': f'已切换到{mode}模式'})
        
        elif self.path == '/api/chat/add':
            user_id = self.require_auth()
            if user_id is None:
                return
            memory.add_message(
                data.get('role', 'user'),
                data.get('content', ''),
                data.get('tags', []),
                user_id=user_id
            )
            self.send_json({'success': True, 'message': '记录已添加'})

        elif self.path == '/api/plan/add':
            user_id = self.require_auth()
            if user_id is None:
                return

            # 从前端获取数据
            title = data.get('title', '')
            description = data.get('description', '')
            deadline = data.get('deadline', '')
            priority = data.get('priority', '中')
            status = data.get('status', '未开始')

            # 解析相对时间转换为绝对日期
            deadline = self.parse_relative_time(deadline)

            # 将中文优先级转换为英文
            priority_map = {'高': 'high', '中': 'medium', '低': 'low', '紧急': 'urgent'}
            priority = priority_map.get(priority, 'medium')

            # 将中文状态转换为英文
            status_map = {'未开始': 'pending', '进行中': 'in_progress', '已完成': 'completed', '已取消': 'cancelled'}
            status = status_map.get(status, 'pending')

            # 添加到计划
            try:
                planner.add_plan(
                    title=title,
                    description=description,
                    deadline=deadline,
                    priority=priority,
                    status=status,
                    user_id=user_id
                )
                self.send_json({'success': True, 'message': '计划已添加'})
            except Exception as e:
                print(f"❌ 添加计划异常: {e}")
                self.send_json({'success': False, 'message': f'计划添加失败: {str(e)}'}, status=500)

        elif self.path == '/api/plan/add-detected':
            """快速保存AI识别到的计划"""
            user_id = self.require_auth()
            if user_id is None:
                return
            title = data.get('title', '')
            if not title:
                self.send_json({'success': False, 'message': '标题不能为空'}, status=400)
                return

            # 优先级转换：中文 -> 英文
            priority_map = {'高': 'high', '中': 'medium', '低': 'low', '紧急': 'urgent'}
            priority = data.get('priority', '中')
            priority = priority_map.get(priority, 'medium')

            # 状态转换：中文 -> 英文
            status_map = {'未开始': 'pending', '进行中': 'in_progress', '已完成': 'completed', '已取消': 'cancelled'}
            status = data.get('status', '未开始')
            status = status_map.get(status, 'pending')

            # 处理deadline - 解析相对时间
            deadline = data.get('deadline', '')
            deadline = self.parse_relative_time(deadline)

            try:
                planner.add_plan(
                    title=title,
                    description=data.get('description', ''),
                    deadline=deadline,
                    priority=priority,
                    status=status,
                    user_id=user_id
                )
                self.send_json({'success': True, 'message': '计划已保存到工作计划'})
            except Exception as e:
                print(f"❌ 保存识别的计划失败: {e}")
                self.send_json({'success': False, 'message': f'保存失败: {str(e)}'}, status=500)

        elif self.path == '/api/plan/update':
            user_id = self.require_auth()
            if user_id is None:
                return
            success = planner.update_plan(data.get('id'), user_id=user_id, status=data.get('status'))
            if success:
                self.send_json({'success': True, 'message': '计划已更新'})
            else:
                self.send_json({'success': False, 'message': '更新失败或权限不足'}, status=403)
        
        elif self.path == '/api/plan/delete':
            user_id = self.require_auth()
            if user_id is None:
                return
            success = planner.delete_plan(data.get('id'), user_id=user_id)
            if success:
                self.send_json({'success': True, 'message': '计划已删除'})
            else:
                self.send_json({'success': False, 'message': '删除失败或权限不足'}, status=403)
        
        elif self.path == '/api/reminder/add':
            user_id = self.require_auth()
            if user_id is None:
                return
            reminder_sys.add_reminder(
                data.get('title', ''),
                data.get('message', ''),
                data.get('remind_time', ''),
                data.get('repeat', '不重复'),
                data.get('sound', 'Ping'),
                user_id=user_id
            )
            self.send_json({'success': True, 'message': '提醒已添加'})
        
        elif self.path == '/api/reminder/delete':
            user_id = self.require_auth()
            if user_id is None:
                return
            success = reminder_sys.delete_reminder(data.get('id'), user_id=user_id)
            if success:
                self.send_json({'success': True, 'message': '提醒已删除'})
            else:
                self.send_json({'success': False, 'message': '删除失败或权限不足'}, status=403)
        
        elif self.path == '/api/chat/create_reminder':
            user_id = self.require_auth()
            if user_id is None:
                return
            reminder_sys.add_reminder(
                data.get('title', '聊天提醒'),
                data.get('content', ''),
                data.get('remind_time', ''),
                data.get('repeat', '不重复'),
                data.get('sound', 'Ping'),
                user_id=user_id
            )
            self.send_json({'success': True, 'message': '提醒已创建'})
        
        elif self.path == '/api/image/upload':
            # 上传图片
            user_id = self.require_auth()
            if user_id is None:
                return
            try:
                image_data = data.get('image_data', '') or data.get('image', '')  # 兼容两种参数名
                description = data.get('description', '')
                tags = data.get('tags', [])
                chat_id = data.get('chat_id', None)
                original_name = data.get('original_name', 'image.jpg')

                # 解码base64图片
                if ',' in image_data:
                    image_data = image_data.split(',')[1]  # 去掉 "data:image/png;base64," 前缀

                image_bytes = base64.b64decode(image_data)

                # 生成唯一文件名
                file_ext = original_name.split('.')[-1] if '.' in original_name else 'jpg'
                filename = f"{uuid.uuid4().hex}.{file_ext}"
                file_path = os.path.join(image_manager.upload_dir, filename)

                # 保存文件
                with open(file_path, 'wb') as f:
                    f.write(image_bytes)

                # 获取文件大小
                file_size = len(image_bytes)

                # 添加到数据库
                img_id = image_manager.add_image(
                    filename=filename,
                    original_name=original_name,
                    file_path=file_path,
                    description=description,
                    tags=tags,
                    chat_id=chat_id,
                    file_size=file_size,
                    user_id=user_id
                )

                # 返回图片信息
                img = {
                    'id': img_id,
                    'filename': filename,
                    'original_name': original_name,
                    'file_path': file_path,
                    'description': description,
                    'tags': tags,
                    'file_size': file_size
                }

                self.send_json({'success': True, 'message': '图片上传成功', 'image': img})
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, status=500)
        
        elif self.path == '/api/image/delete':
            # 删除图片
            user_id = self.require_auth()
            if user_id is None:
                return
            image_id = data.get('id')
            success = image_manager.delete_image(image_id, user_id=user_id)
            if success:
                self.send_json({'success': True, 'message': '图片已删除'})
            else:
                self.send_json({'success': False, 'message': '删除失败或权限不足'}, status=403)
        
        elif self.path == '/api/image/update':
            # 更新图片信息
            user_id = self.require_auth()
            if user_id is None:
                return
            image_id = data.get('id')
            description = data.get('description')
            tags = data.get('tags')
            success = image_manager.update_image(image_id, description, tags, user_id=user_id)
            if success:
                self.send_json({'success': True, 'message': '更新成功'})
            else:
                self.send_json({'success': False, 'message': '更新失败或权限不足'}, status=403)
        
        elif self.path == '/api/image/search':
            # 搜索图片
            user_id = self.require_auth()
            if user_id is None:
                return
            
            # 支持多种搜索参数
            keyword = data.get('keyword') or data.get('description', '')
            tags = data.get('tags', [])
            
            # 如果有标签，将标签加入关键词
            if tags:
                if isinstance(tags, list):
                    keyword = keyword + ' ' + ' '.join(tags) if keyword else ' '.join(tags)
                else:
                    keyword = keyword + ' ' + str(tags) if keyword else str(tags)
            
            results = image_manager.search_images(keyword=keyword.strip(), user_id=user_id)
            self.send_json({'results': results})

        # ============ 用户头像相关API ============

        elif self.path == '/api/user/avatar':
            # 上传/更换头像
            user_id = self.require_auth()
            if user_id is None:
                return
            try:
                image_data = data.get('avatar_data', '') or data.get('image_data', '')

                if not image_data:
                    self.send_json({'success': False, 'error': '缺少头像数据'}, status=400)
                    return

                # 解码base64图片
                if ',' in image_data:
                    image_data = image_data.split(',')[1]  # 去掉 "data:image/png;base64," 前缀

                image_bytes = base64.b64decode(image_data)

                # 生成唯一文件名
                file_ext = 'jpg'  # 默认jpg
                filename = f"avatar_{user_id}_{uuid.uuid4().hex}.{file_ext}"

                # 确保avatars目录存在
                avatars_dir = 'uploads/avatars'
                os.makedirs(avatars_dir, exist_ok=True)

                file_path = os.path.join(avatars_dir, filename)

                # 保存文件
                with open(file_path, 'wb') as f:
                    f.write(image_bytes)

                # 构建相对URL路径
                avatar_url = f'uploads/avatars/{filename}'

                # 更新数据库中的用户头像
                success = user_manager.update_avatar(user_id, avatar_url)

                if success:
                    self.send_json({
                        'success': True,
                        'message': '头像上传成功',
                        'avatar_url': avatar_url
                    })
                else:
                    self.send_json({'success': False, 'error': '更新头像失败'}, status=500)

            except Exception as e:
                print(f"头像上传错误: {e}")
                self.send_json({'success': False, 'error': str(e)}, status=500)

        elif self.path == '/api/user/settings':
            # 更新用户设置（如背景颜色）
            user_id = self.require_auth()
            if user_id is None:
                return

            chat_background = data.get('chat_background')
            
            success = user_manager.update_settings(user_id, chat_background=chat_background)
            
            if success:
                self.send_json({'success': True, 'message': '设置已更新'})
            else:
                self.send_json({'success': False, 'message': '更新设置失败'}, status=500)

        elif self.path == '/api/user/change-password':
            # 修改密码
            user_id = self.require_auth()
            if user_id is None:
                return

            old_password = data.get('old_password')
            new_password = data.get('new_password')

            if not old_password or not new_password:
                self.send_json({'success': False, 'message': '密码不能为空'}, status=400)
                return

            result = user_manager.change_password(user_id, old_password, new_password)
            self.send_json(result)

        # ============ 新增：提醒调度器相关API ============

        elif self.path == '/api/scheduler/reminder/add':
            # 通过调度器添加定时提醒
            user_id = self.require_auth()
            if user_id is None:
                return

            message = data.get('message', '')
            remind_time = data.get('remind_time', '')  # 例如："明天14:30"、"1小时后"
            remind_type = data.get('remind_type', 'once')  # 'once', 'daily', 'weekly'

            if not message or not remind_time:
                self.send_json({'success': False, 'message': '消息和提醒时间不能为空'})
                return

            try:
                scheduler = get_global_scheduler(db_manager=db_manager)
                # 先解析自然语言时间
                parsed_time = scheduler.parse_reminder_time(remind_time)
                if parsed_time is None:
                    self.send_json({'success': False, 'message': f'无法解析时间: {remind_time}'})
                    return

                result = scheduler.add_reminder(user_id, message, parsed_time, remind_type)
                if result['status'] == 'success':
                    self.send_json({
                        'success': True,
                        'message': '提醒已添加',
                        'reminder': result.get('reminder')
                    })
                else:
                    self.send_json({'success': False, 'message': result.get('message', '添加失败')})
            except Exception as e:
                self.send_json({'success': False, 'message': f'错误: {str(e)}'})

        elif self.path == '/api/scheduler/reminder/list':
            # 获取用户的所有提醒
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                scheduler = get_global_scheduler(db_manager=db_manager)
                reminders = scheduler.list_reminders(user_id=user_id)
                self.send_json({'success': True, 'reminders': reminders})
            except Exception as e:
                self.send_json({'success': False, 'message': f'错误: {str(e)}'})

        elif self.path == '/api/scheduler/reminder/cancel':
            # 取消提醒
            user_id = self.require_auth()
            if user_id is None:
                return

            reminder_id = data.get('reminder_id')

            if not reminder_id:
                self.send_json({'success': False, 'message': '提醒ID不能为空'})
                return

            try:
                scheduler = get_global_scheduler(db_manager=db_manager)
                success = scheduler.cancel_reminder(reminder_id, user_id=user_id)
                if success:
                    self.send_json({'success': True, 'message': '提醒已取消'})
                else:
                    self.send_json({'success': False, 'message': '取消失败或权限不足'}, status=403)
            except Exception as e:
                self.send_json({'success': False, 'message': f'错误: {str(e)}'})

        elif self.path == '/api/scheduler/parse-time':
            # 解析自然语言时间字符串（测试端点）
            user_id = self.require_auth()
            if user_id is None:
                return

            time_string = data.get('time_string', '')

            if not time_string:
                self.send_json({'success': False, 'message': '时间字符串不能为空'})
                return

            try:
                scheduler = get_global_scheduler(db_manager=db_manager)
                parsed_time = scheduler.parse_reminder_time(time_string)
                if parsed_time:
                    self.send_json({
                        'success': True,
                        'input': time_string,
                        'parsed': parsed_time.isoformat(),
                        'formatted': parsed_time.strftime('%Y年%m月%d日 %H:%M')
                    })
                else:
                    self.send_json({
                        'success': False,
                        'message': '无法解析时间字符串',
                        'examples': [
                            '明天 14:30',
                            '后天 09:00',
                            '1小时后',
                            '5分钟后',
                            '30秒后'
                        ]
                    })
            except Exception as e:
                self.send_json({'success': False, 'message': f'错误: {str(e)}'})

        else:
            self.send_error(404)
    
    def send_json(self, data, status=200):
        """发送JSON响应"""
        self.send_response(status)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def serve_image(self, filepath):
        """发送图片文件"""
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            
            # 根据文件扩展名设置Content-Type
            if filepath.endswith('.jpg') or filepath.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif filepath.endswith('.png'):
                content_type = 'image/png'
            elif filepath.endswith('.gif'):
                content_type = 'image/gif'
            elif filepath.endswith('.webp'):
                content_type = 'image/webp'
            else:
                content_type = 'application/octet-stream'
            
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, 'Image not found')
        except Exception as e:
            self.send_error(500, 'Failed to read image')
    
    def do_DELETE(self):
        """处理DELETE请求"""
        # 删除图片: /api/image/{id}
        if self.path.startswith('/api/image/'):
            user_id = self.require_auth()
            if user_id is None:
                return
            
            # 提取图片ID
            try:
                image_id = int(self.path.split('/')[-1])
            except ValueError:
                self.send_json({'success': False, 'message': '无效的图片ID'}, status=400)
                return
            
            # 删除图片
            success = image_manager.delete_image(image_id, user_id=user_id)
            if success:
                self.send_json({'success': True, 'message': '图片已删除'})
            else:
                self.send_json({'success': False, 'message': '删除失败或权限不足'}, status=403)
        else:
            self.send_error(404, 'Not found')
    
    def send_login_html(self):
        """发送登录页面"""
        html_content = self.get_login_template()
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def send_html(self):
        """发送HTML页面"""
        html_content = self.get_html_template()
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def send_image_gallery_html(self):
        """发送图片管理页面"""
        html_content = self.get_image_gallery_template()
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def get_login_template(self):
        """获取登录页面模板"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, viewport-fit=cover, interactive-widget=resizes-visual">
    <title>登录 - 个人AI助理</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0099FF;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .login-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 400px;
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }

        .header p {
            opacity: 0.9;
            font-size: 14px;
        }

        .tabs {
            display: flex;
            background: #f5f5f5;
        }

        .tab {
            flex: 1;
            padding: 15px;
            text-align: center;
            cursor: pointer;
            font-weight: 600;
            color: #666;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }

        .tab.active {
            background: white;
            color: #667eea;
            border-bottom-color: #667eea;
        }

        .form-container {
            padding: 30px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
            font-size: 14px;
        }

        .form-group input {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s;
            -webkit-appearance: none;
            -moz-appearance: none;
            appearance: none;
        }

        .form-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }

        .btn:active {
            transform: translateY(0);
        }

        .message {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
            font-size: 14px;
        }

        .message.error {
            background: #fee;
            color: #c33;
            border: 1px solid #fcc;
            display: block;
        }

        .message.success {
            background: #efe;
            color: #3c3;
            border: 1px solid #cfc;
            display: block;
        }

        #registerForm {
            display: none;
        }

        .footer {
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="header">
            <h1>🤖 个人AI助理</h1>
            <p>您的智能工作伙伴</p>
        </div>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('login')">登录</div>
            <div class="tab" onclick="switchTab('register')">注册</div>
        </div>

        <div class="form-container">
            <div id="message" class="message"></div>

            <!-- 登录表单 -->
            <form id="loginForm">
                <div class="form-group">
                    <label for="login-username">用户名</label>
                    <input type="text" id="login-username" required autocomplete="username">
                </div>
                <div class="form-group">
                    <label for="login-password">密码</label>
                    <input type="password" id="login-password" required autocomplete="current-password">
                </div>
                <button type="submit" class="btn">登录</button>
            </form>

            <!-- 注册表单 -->
            <form id="registerForm">
                <div class="form-group">
                    <label for="register-username">用户名</label>
                    <input type="text" id="register-username" required autocomplete="username">
                </div>
                <div class="form-group">
                    <label for="register-password">密码</label>
                    <input type="password" id="register-password" required autocomplete="new-password">
                </div>
                <div class="form-group">
                    <label for="register-phone">手机号（可选）</label>
                    <input type="tel" id="register-phone" autocomplete="tel">
                </div>
                <button type="submit" class="btn">注册</button>
            </form>
        </div>

        <div class="footer">
            © 2025 个人AI助理系统
        </div>
    </div>

    <script>
        function switchTab(tab) {
            const loginForm = document.getElementById('loginForm');
            const registerForm = document.getElementById('registerForm');
            const tabs = document.querySelectorAll('.tab');

            tabs.forEach(t => t.classList.remove('active'));

            if (tab === 'login') {
                tabs[0].classList.add('active');
                loginForm.style.display = 'block';
                registerForm.style.display = 'none';
            } else {
                tabs[1].classList.add('active');
                loginForm.style.display = 'none';
                registerForm.style.display = 'block';
            }

            hideMessage();
        }

        function showMessage(text, type) {
            const msg = document.getElementById('message');
            msg.textContent = text;
            msg.className = 'message ' + type;
        }

        function hideMessage() {
            const msg = document.getElementById('message');
            msg.className = 'message';
        }

        // 登录
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('login-username').value;
            const password = document.getElementById('login-password').value;

            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();

                if (data.success) {
                    localStorage.setItem('token', data.token);
                    localStorage.setItem('username', data.username);
                    localStorage.setItem('user_id', data.user_id);

                    showMessage('登录成功！正在跳转...', 'success');
                    setTimeout(() => {
                        window.location.href = '/ai/';
                    }, 1000);
                } else {
                    showMessage(data.message || '登录失败', 'error');
                }
            } catch (error) {
                showMessage('网络错误，请重试', 'error');
            }
        });

        // 注册
        document.getElementById('registerForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('register-username').value;
            const password = document.getElementById('register-password').value;
            const phone = document.getElementById('register-phone').value;

            try {
                const response = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ username, password, phone })
                });

                const data = await response.json();

                if (data.success) {
                    showMessage('注册成功！请登录', 'success');
                    setTimeout(() => {
                        switchTab('login');
                        document.getElementById('login-username').value = username;
                    }, 1500);
                } else {
                    showMessage(data.message || '注册失败', 'error');
                }
            } catch (error) {
                showMessage('网络错误，请重试', 'error');
            }
        });

        // 检查是否已登录
        window.addEventListener('DOMContentLoaded', () => {
            const token = localStorage.getItem('token');
            if (token) {
                // 验证token是否有效
                fetch('/api/auth/verify', {
                    headers: {
                        'Authorization': 'Bearer ' + token
                    }
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        // 已登录，跳转到主页
                        window.location.href = '/ai/';
                    }
                });
            }
        });
    </script>
</body>
</html>
'''

    def get_html_template(self):
        """获取HTML模板"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, viewport-fit=cover, interactive-widget=resizes-visual">
    <title>个人助手</title>
    <style>
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box; 
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #0099FF;
            min-height: 100vh;
            color: #1a1a1a;
            position: relative;
            overflow-x: hidden;
            display: flex;
        }
        
        /* 左侧图标栏 */
        .sidebar {
            width: 72px;
            background: rgba(26, 26, 26, 0.95);
            backdrop-filter: blur(20px);
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px 0;
            gap: 20px;
            position: fixed;
            left: 0;
            top: 0;
            bottom: 0;
            z-index: 100;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .sidebar-icon {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.1);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s;
            color: #fff;
            font-size: 20px;
        }
        
        .sidebar-icon:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: scale(1.1);
        }
        
        .sidebar-icon.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        .new-chat-btn {
            width: 48px;
            height: 48px;
            border-radius: 16px;
            background: rgba(60, 60, 60, 0.9);
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s;
            border: none;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            font-size: 22px;
        }
        
        .new-chat-btn:hover {
            background: rgba(80, 80, 80, 0.95);
            transform: scale(1.05);
        }
        
        .app-header {
            background: rgba(20, 20, 20, 0.8);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding: 16px 24px;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .logo {
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .container {
            flex: 1;
            margin-left: 72px;
            display: flex;
            flex-direction: column;
            height: 100vh;
            position: relative;
        }
        
        header {
            display: none;
        }
        
        header h1 {
            display: none;
        }
        
        header p {
            display: none;
        }
        
        .tabs {
            display: none;
        }
        
        .tab {
            display: none;
        }
        
        .tab:hover { 
            display: none;
        }
        
        .tab.active {
            display: none;
        }
        
        .tab-content { 
            display: flex; 
            flex-direction: column;
            flex: 1;
            padding: 0;
            background: transparent;
            backdrop-filter: none;
            border-radius: 0;
            border: none;
            height: 100%;
        }
        
        .tab-content.active { 
            display: flex; 
            flex-direction: column; 
        }

        /* 聊天容器 */
        #aiChatBox {
            flex: 1;
            overflow-y: auto;
            padding: 40px 80px;
            background: transparent !important;
            border: none !important;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        /* 移动端优化：宽度≤768px（平板竖屏和手机） */
        @media (max-width: 768px) {
            #aiChatBox {
                padding: 80px 20px 20px;
                gap: 20px;
            }
        }

        /* 超小屏幕优化：宽度≤480px（小手机） */
        @media (max-width: 480px) {
            #aiChatBox {
                padding: 80px 16px 20px;
                gap: 20px;
            }
        }

        /* 消息气泡 */
        .message {
            display: flex;
            gap: 12px;
            max-width: 85%;
            animation: slideIn 0.3s ease-out;
            margin-bottom: 4px;
        }

        /* 移动端优化 */
        @media (max-width: 768px) {
            .message {
                max-width: 90%;
                gap: 10px;
            }
        }

        @media (max-width: 480px) {
            .message {
                max-width: 92%;
                gap: 8px;
            }
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .message.user {
            align-self: flex-end;
            flex-direction: row-reverse;
        }
        
        .message.assistant {
            align-self: flex-start;
        }
        
        .message-content {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 14px 18px;
            border-radius: 18px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
            color: #1a1a1a;
            line-height: 1.65;
            font-size: 15.5px;
            word-break: break-word;
            overflow-wrap: break-word;
            white-space: normal;
            max-width: 100%;
        }

        .message.user .message-content {
            background: linear-gradient(135deg, #0084ff 0%, #0073ea 100%);
            color: #ffffff;
            border-bottom-right-radius: 6px;
            box-shadow: 0 1px 3px rgba(0, 132, 255, 0.3);
        }

        .message.assistant .message-content {
            background: #f0f0f0;
            color: #1a1a1a;
            border-bottom-left-radius: 6px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
        }

        /* 移动端优化：消息内容框 */
        @media (max-width: 768px) {
            .message-content {
                padding: 12px 16px;
                font-size: 15px;
                line-height: 1.6;
                border-radius: 16px;
            }
        }

        @media (max-width: 480px) {
            .message-content {
                padding: 11px 15px;
                font-size: 15px;
                line-height: 1.55;
                border-radius: 16px;
            }
        }

        .message-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
        }

        .message.user .message-avatar {
            background: linear-gradient(135deg, #0084ff 0%, #0073ea 100%);
            color: #fff;
        }

        .message.assistant .message-avatar {
            background: #19c37d;
            color: #ffffff;
            font-weight: 600;
            font-size: 22px;
        }

        /* 移动端头像优化 */
        @media (max-width: 768px) {
            .message-avatar {
                width: 32px;
                height: 32px;
                font-size: 18px;
            }

            .message.assistant .message-avatar {
                font-size: 20px;
            }
        }

        @media (max-width: 480px) {
            .message-avatar {
                width: 30px;
                height: 30px;
                font-size: 16px;
            }

            .message.assistant .message-avatar {
                font-size: 18px;
            }
        }
        
        /* 欢迎消息 */
        .welcome-message {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 100px 40px;
            color: rgba(255, 255, 255, 0.9);
        }
        
        .welcome-message h3 {
            font-size: 2em;
            margin-bottom: 12px;
            font-weight: 600;
            color: #fff;
        }
        
        .welcome-message p {
            font-size: 1.1em;
            color: rgba(255, 255, 255, 0.8);
            min-height: 1.5em;
            text-align: left;
            max-width: 600px;
        }
        
        /* 打字机光标效果 */
        .typing-cursor::after {
            content: '|';
            animation: blink 0.7s infinite;
            margin-left: 2px;
        }
        
        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0; }
        }
        
        .form-group { margin-bottom: 20px; }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #ccc;
            font-size: 0.95em;
        }
        
        /* 输入区域容器 */
        .input-container {
            padding: 20px 80px 30px;
            background: transparent;
        }

        /* 移动端优化 */
        @media (max-width: 768px) {
            .input-container {
                padding: 20px 16px 30px;
            }
        }

        @media (max-width: 480px) {
            .input-container {
                padding: 20px 12px 30px;
            }
        }

        .input-wrapper {
            background: rgba(40, 40, 40, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 4px 4px 4px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .input-icon {
            color: #888;
            font-size: 20px;
            cursor: pointer;
            transition: color 0.3s;
        }
        
        .input-icon:hover {
            color: #fff;
        }

        .mic-active {
            color: #ff4444 !important;
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.2); opacity: 0.7; }
            100% { transform: scale(1); opacity: 1; }
        }
        
        input[type="text"], select, textarea {
            width: 100%;
            padding: 0;
            border: none;
            border-radius: 0;
            font-size: 16px;
            background: transparent;
            color: #fff;
            transition: all 0.3s;
            -webkit-appearance: none;
            -moz-appearance: none;
            appearance: none;
        }
        
        input[type="text"]:focus, select:focus, textarea:focus {
            outline: none;
            border: none;
            background: transparent;
            box-shadow: none;
        }
        
        textarea { 
            resize: none; 
            min-height: 24px; /* 初始高度 */
            max-height: 120px; /* JS会覆盖此最大高度 */
            font-family: inherit;
            line-height: 1.5em; /* 确保 line-height 为 em 单位，方便计算 */
            padding: 10px 0; /* 调整 padding，确保垂直居中并计算准确 */
            overflow-y: hidden; /* 隐藏滚动条 */
        }
        
        textarea::placeholder {
            color: #666;
        }
        
        button {
            background: #fff;
            color: #1a1a1a;
            padding: 10px 24px;
            border: none;
            border-radius: 20px;
            font-size: 14px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        
        button:hover { 
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        
        button:active {
            transform: scale(0.98);
        }
        
        .send-button {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #fff;
            flex-shrink: 0;
        }
        
        .send-button:hover {
            background: #f0f0f0;
        }
        
        .card {
            background: rgba(30, 30, 30, 0.6);
            backdrop-filter: blur(10px);
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 4px solid #667eea;
            transition: all 0.3s;
        }
        
        .card:hover {
            border-color: rgba(102, 126, 234, 0.5);
            transform: translateX(4px);
        }
        
        .badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            margin-right: 5px;
            color: white;
            font-weight: 500;
        }
        
        .list-container { 
            max-height: 500px; 
            overflow-y: auto;
            scrollbar-width: thin;
            scrollbar-color: rgba(102, 126, 234, 0.5) rgba(255, 255, 255, 0.05);
        }
        
        .list-container::-webkit-scrollbar {
            width: 8px;
        }
        
        .list-container::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        }
        
        .list-container::-webkit-scrollbar-thumb {
            background: rgba(102, 126, 234, 0.5);
            border-radius: 10px;
        }
        
        .list-container::-webkit-scrollbar-thumb:hover {
            background: rgba(102, 126, 234, 0.7);
        }
        
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.8);
            backdrop-filter: blur(10px);
        }
        
        .modal-content {
            background: rgba(20, 20, 20, 0.95);
            backdrop-filter: blur(20px);
            margin: 10% auto;
            padding: 30px;
            border-radius: 20px;
            width: 90%;
            max-width: 500px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .close {
            color: #888;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            transition: color 0.3s;
        }
        
        .close:hover {
            color: #fff;
        }
        
        /* 自定义滚动条样式 */
        ::-webkit-scrollbar {
            width: 12px;
            height: 12px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            border: 2px solid rgba(255, 255, 255, 0.05);
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        }
        
        /* Firefox滚动条 */
        * {
            scrollbar-width: thin;
            scrollbar-color: #667eea rgba(255, 255, 255, 0.05);
        }
        
        h2 {
            color: #fff;
            margin-bottom: 20px;
            font-size: 1.8em;
            font-weight: 700;
        }
        
        h3 {
            color: #ccc;
        }
        
        .filter-btn {
            flex: 1;
            padding: 10px 15px;
            background: rgba(255,255,255,0.1);
            color: #fff;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
        }
        
        .filter-btn:hover {
            background: rgba(255,255,255,0.2);
            transform: translateY(-2px);
        }
        
        .filter-btn.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-color: #667eea;
        }
        
        .plan-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s;
        }
        
        .plan-card:hover {
            background: rgba(255,255,255,0.08);
            transform: translateY(-2px);
        }
        
        .plan-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .plan-title {
            font-size: 16px;
            font-weight: 600;
            color: #fff;
            margin: 0;
        }
        
        .plan-status {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .status-未开始, .status-pending {
            background: rgba(108, 117, 125, 0.3);
            color: #adb5bd;
        }
        
        .status-进行中, .status-in_progress {
            background: rgba(0, 123, 255, 0.3);
            color: #007bff;
        }
        
        .status-已完成, .status-completed {
            background: rgba(40, 167, 69, 0.3);
            color: #28a745;
        }
        
        .status-已取消, .status-cancelled {
            background: rgba(220, 53, 69, 0.3);
            color: #dc3545;
        }
        
        .plan-meta {
            display: flex;
            gap: 15px;
            font-size: 13px;
            color: #999;
            margin-bottom: 10px;
        }
        
        .plan-actions {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        
        .plan-btn {
            flex: 1;
            padding: 8px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.3s;
        }
        
        .plan-btn-status {
            background: #007bff;
            color: white;
        }
        
        .plan-btn-status:hover {
            background: #0056b3;
        }
        
        .plan-btn-delete {
            background: rgba(220, 53, 69, 0.2);
            color: #dc3545;
        }
        
        .plan-btn-delete:hover {
            background: #dc3545;
            color: white;
        }

        /* 隐藏右上角装饰元素 */
        .header-right {
            display: none;
        }

        .top-right-avatar,
        .header-avatar,
        .user-avatar-top,
        .decoration-avatar {
            display: none !important;
        }

        /* ========== 手机端专用UI ========== */

        /* 手机端顶部栏 - 默认隐藏 */
        .mobile-header {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 56px;
            background: rgba(0, 153, 255, 0.98);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            z-index: 10000;
            align-items: center;
            padding: 0 16px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            /* iOS Safari键盘适配 */
            transform: translateZ(0);
            -webkit-transform: translateZ(0);
        }

        .menu-btn {
            background: none;
            border: none;
            padding: 12px;
            cursor: pointer;
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            position: absolute;
            left: 8px;
            top: 50%;
            transform: translateY(-50%);
            z-index: 10;
            width: 44px;
            height: 44px;
            border-radius: 8px;
            transition: background-color 0.2s;
            -webkit-tap-highlight-color: transparent;
        }
        
        .app-logo-text {
            position: absolute;
            left: 60px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 18px;
            font-weight: 600;
            color: #ffffff;
        }
        
        .menu-btn:active {
            background-color: rgba(0, 0, 0, 0.05);
        }


        /* 侧滑抽屉菜单 - 默认隐藏 */
        .drawer-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 10001;
            opacity: 0;
            transition: opacity 0.3s;
        }

        .drawer-overlay.open {
            display: block;
            opacity: 1;
        }

        .side-drawer {
            display: none;
            position: fixed;
            top: 0;
            left: -280px;
            bottom: 0;
            width: 280px;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            z-index: 10002;
            transition: left 0.3s ease-out;
            flex-direction: column;
            box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
        }

        .side-drawer.active {
            display: flex !important;
            left: 0 !important;
        }

        .drawer-header {
            padding: 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }

        .new-chat-drawer {
            width: 100%;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 8px;
            padding: 10px 16px;
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            font-size: 15px;
            color: white;
            transition: background 0.2s;
        }

        .new-chat-drawer:hover {
            background: rgba(255, 255, 255, 0.2);
        }

        .drawer-content {
            flex: 1;
            overflow-y: auto;
            padding: 12px 0;
        }
        
        /* 添加分隔线 */
        .drawer-divider {
            height: 1px;
            background: rgba(255, 255, 255, 0.2);
            margin: 8px 16px;
        }

        .drawer-item {
            padding: 16px 20px;
            cursor: pointer;
            font-size: 15px;
            color: white;
            transition: background 0.2s;
            display: flex;
            align-items: center;
            border-radius: 8px;
            margin: 4px 12px;
        }

        .drawer-item:hover {
            background: rgba(255, 255, 255, 0.15);
        }

        .drawer-item:active {
            background: rgba(255, 255, 255, 0.25);
        }

        .drawer-footer {
            border-top: 1px solid rgba(255, 255, 255, 0.2);
            padding: 16px;
            background: rgba(0, 0, 0, 0.2);
        }

        .drawer-user {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.15);
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .drawer-avatar {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            color: white;
            flex-shrink: 0;
            overflow: hidden;
        }
        
        .drawer-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .drawer-user-info {
            flex: 1;
        }

        .drawer-user-label {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.7);
            margin-bottom: 2px;
        }

        .drawer-username {
            font-size: 16px;
            color: white;
            font-weight: 600;
        }
        
        .drawer-logout-btn {
            background: #ff4444;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            cursor: pointer;
            margin-top: 12px;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: background 0.2s;
        }
        
        .drawer-logout-btn:hover {
            background: #dd3333;
        }

        /* ========== 手机端响应式 ========== */

        @media screen and (max-width: 768px) {
            /* 修改body背景为天蓝色 */
            body {
                /* background: #0099FF !important; */ /* 已移除，由JS控制 */
            }

            /* 显示手机端顶部栏 - fixed定位 */
            .mobile-header {
                display: flex;
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                height: 56px;
                z-index: 10000;
            }

            /* 显示侧滑菜单和遮罩层 */
            .side-drawer {
                display: flex !important;
            }

            .drawer-overlay {
                display: block !important;
                pointer-events: none;
                opacity: 0;
            }

            .drawer-overlay.open {
                pointer-events: auto;
                opacity: 1 !important;
            }

            /* 隐藏桌面端侧边栏 */
            .sidebar {
                display: none !important;
            }

            /* 容器布局 */
            .container {
                margin-left: 0;
                margin-top: 56px;
                min-height: calc(100vh - 56px);
                display: flex;
                flex-direction: column;
            }

            /* 调整聊天区域 */
            #aiChatBox {
                padding: 16px;
                padding-bottom: 120px;
                flex: 1;
                overflow-y: auto;
                -webkit-overflow-scrolling: touch;
            }

            /* 调整输入区域 - fixed在底部 */
            .input-container {
                padding: 12px 16px;
                padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px));
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                z-index: 9999;
                background: #0099FF;
            }

            /* 移动端欢迎消息居中 */
            .welcome-message {
                min-height: calc(100vh - 56px - 120px);
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }

            .welcome-message p {
                font-size: 1.2em;
                text-align: center;
                line-height: 1.8;
            }

            /* 图片库手机端2列布局 */
            #galleryImagesList {
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 10px !important;
                padding: 10px !important;
            }

            .image-card {
                margin-bottom: 0 !important;
            }

            .image-card img {
                height: 120px !important;
            }

            /* 图片库模态框手机端适配 */
            #imageGalleryModal .modal-content {
                max-width: 100% !important;
                width: 100% !important;
                padding: 15px !important;
                max-height: 95vh !important;
            }

            /* 年月标题手机端样式 */
            .month-group-title {
                font-size: 14px !important;
                padding: 8px !important;
                margin: 10px 0 8px 0 !important;
            }
        }

        .message-time {
            font-size: 0.75em;
            margin-top: 4px;
            text-align: right;
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <!-- 手机端顶部栏 -->
    <div class="mobile-header">
        <button class="menu-btn" onclick="toggleMobileMenu()">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="3" y1="12" x2="21" y2="12"></line>
                <line x1="3" y1="6" x2="21" y2="6"></line>
                <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
        </button>
        <div class="app-logo-text">Verve</div>
    </div>

    <!-- 侧滑抽屉菜单 -->
    <div class="drawer-overlay" onclick="closeMobileMenu()"></div>
    <div class="side-drawer" id="mobileMenu">
        <div class="drawer-header">
            <button class="new-chat-drawer" onclick="startNewChat(); closeMobileMenu();">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 5v14M5 12h14"/>
                </svg>
                新聊天
            </button>
        </div>
        <div class="drawer-content">
            <div class="drawer-item" onclick="showPlans(); closeMobileMenu();">
                <span style="margin-right: 12px; font-size: 18px;">📋</span>工作计划
            </div>
            <div class="drawer-item" onclick="showImages(); closeMobileMenu();">
                <span style="margin-right: 12px; font-size: 18px;">🖼️</span>图片管理
            </div>
            
            <div class="drawer-divider"></div>
            
            <div class="drawer-item" style="cursor: default;">
                <span style="margin-right: 12px; font-size: 18px;">📄</span>使用条款
            </div>
            <div class="drawer-item" style="cursor: default;">
                <span style="margin-right: 12px; font-size: 18px;">🔒</span>隐私政策
            </div>
            <div class="drawer-item" onclick="openSettings(); closeMobileMenu();">
                <span style="margin-right: 12px; font-size: 18px;">⚙️</span>设置
            </div>
        </div>
        <div class="drawer-footer">
            <div class="drawer-user">
                <div class="drawer-avatar" id="menuAvatar">👤</div>
                <div class="drawer-user-info">
                    <div class="drawer-user-label">用户ID</div>
                    <div class="drawer-username" id="menuUsername">加载中...</div>
                </div>
            </div>
            <button class="drawer-logout-btn" onclick="handleLogout()">
                <span style="font-size: 16px;">📤</span>
                退出登录
            </button>
        </div>
    </div>

    <!-- 左侧图标栏 -->
    <div class="sidebar">
        <button class="new-chat-btn" onclick="clearConversation()">
            ✏️
        </button>
        <div class="sidebar-icon" onclick="openWorkPlans()" title="工作计划" style="margin-bottom:20px;">📋</div>
        <div class="sidebar-icon" onclick="window.open('/image-gallery', '_blank')" title="图片管理（新窗口）" style="margin-bottom:20px;">🖼️</div>
        <div class="sidebar-icon" onclick="openSettings()" title="设置" style="margin-top: auto; margin-bottom:20px;">⚙️</div>
        <div class="sidebar-icon" onclick="toggleUserPanel()" title="用户菜单" style="margin-top: 0; cursor: pointer; padding:0; overflow:hidden;" id="userAvatarIcon">
            <img id="sidebarUserAvatar" src="" alt="头像" style="width:100%; height:100%; object-fit:cover; display:none;" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
            <span id="sidebarDefaultAvatar" style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; font-size:20px;">👤</span>
        </div>

        <!-- 用户菜单面板 -->
        <div id="userPanel" style="display: none; position: fixed; bottom: 80px; left: 10px; background: #1a1a2e; border-radius: 12px; padding: 12px 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); color: white; min-width: 200px; z-index: 1001;">
            <div style="display: flex; align-items: center; margin-bottom: 12px; gap: 10px;">
                <div style="position:relative; width:40px; height:40px; flex-shrink:0;">
                    <img id="panelUserAvatar" src="" alt="头像" style="width:100%; height:100%; border-radius:50%; object-fit:cover; display:none;" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                    <span id="panelDefaultAvatar" style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; font-size:24px; background:#4A90E2; border-radius:50%;">👤</span>
                </div>
                <div style="flex: 1;">
                    <div style="font-size: 12px; color: #999;">用户ID</div>
                    <div id="userIdDisplay" style="font-size: 16px; font-weight: 600; color: #fff;">-</div>
                </div>
            </div>
            <button onclick="logout()" style="width: 100%; padding: 8px 12px; background: #ff6b6b; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 14px;">
                🚪 退出登录
            </button>
        </div>
        </div>
        
    <div class="container">
        <!-- AI助手 -->
        <div id="ai" class="tab-content active">
            
            <!-- 聊天区域 -->
            <div id="aiChatBox">
                <div class="welcome-message">
                    <p id="welcomeText"></p>
            </div>
        </div>
        
                        <!-- 输入区域 -->
                        <div class="input-container">
                            <div class="input-wrapper">
                                <span class="input-icon" onclick="triggerImageUpload()" title="上传图片（支持多选）">📎</span>
                                <span class="input-icon" id="voiceBtn" onclick="toggleVoiceInput()" title="语音输入" style="margin-left: 8px;">🎤</span>
                                <input type="file" id="imageUpload" accept="image/*" multiple style="display:none" onchange="handleImageSelect(event)">
                                <textarea id="aiInput" rows="1" placeholder="How can I help you?" onkeydown="handleAIKeyPress(event)" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" inputmode="text" data-form-type="other"></textarea>
                                <button class="send-button" onclick="sendAI()">
                                    <span style="font-size: 20px;">🎙️</span>
                                </button>
                            </div>        
                <!-- 图片预览区域 -->
                <div id="imagePreviewContainer" style="display:none; margin-top:15px;">
                    <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:10px;" id="imagePreviewList">
                        <!-- 动态添加图片预览 -->
            </div>
                    <div style="margin-top:10px;">
                        <input type="text" id="imageDescription" placeholder="添加图片描述（可选）" style="width:100%; padding:8px; margin-bottom:8px; background:rgba(40,40,40,0.9); border:1px solid rgba(255,255,255,0.2); border-radius:8px; color:#fff;">
                        <input type="text" id="imageTags" placeholder="添加标签，用逗号分隔（可选）" style="width:100%; padding:8px; margin-bottom:8px; background:rgba(40,40,40,0.9); border:1px solid rgba(255,255,255,0.2); border-radius:8px; color:#fff;">
                        <button onclick="uploadSelectedImages()" style="width:100%; padding:12px; background:#28a745; color:white; border:none; border-radius:8px; cursor:pointer; font-size:16px; font-weight:600;">
                            ✅ 上传图片到图片库
                        </button>
            </div>
            </div>
            </div>
        </div>
    </div>
    
    <!-- 弹窗 -->
    <div id="reminderModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <h3>⏰ 设置提醒</h3>
            <div class="form-group">
                <label>标题</label>
                <input type="text" id="modalTitle">
            </div>
            <div class="form-group">
                <label>内容</label>
                <textarea id="modalContent" readonly></textarea>
            </div>
            <div class="form-group">
                <label>时间</label>
                <input type="text" id="modalTime">
            </div>
            <div class="form-group">
                <label>重复</label>
                <select id="modalRepeat">
                    <option value="不重复">不重复</option>
                    <option value="每天">每天</option>
                </select>
            </div>
            <div class="form-group">
                <label>🎵 提示音</label>
                <select id="modalSound">
                    <option value="Ping" selected>Ping - 最清脆</option>
                    <option value="Glass">Glass - 玻璃声</option>
                    <option value="Bottle">Bottle - 瓶子声</option>
                </select>
            </div>
            <button onclick="createReminder()">创建</button>
        </div>
    </div>

    <!-- 工作计划模态框 -->
    <div id="workPlansModal" class="modal">
        <div class="modal-content" style="max-width: 900px; max-height: 90vh; display: flex; flex-direction: column; overflow: hidden;">
            <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 15px; border-bottom: 1px solid #ddd; flex-shrink: 0;">
                <h3 style="margin: 0;">📋 工作计划管理</h3>
                <span class="close" onclick="closeWorkPlans()" style="margin: 0;">&times;</span>
            </div>

            <!-- 标签页 -->
            <div style="display:flex; gap:10px; margin-top:15px; margin-bottom:15px; border-bottom:2px solid #ddd; flex-shrink: 0;">
                <button onclick="switchWorkTab('plans')" id="plansTab" class="work-tab active" style="padding:12px 20px; background:none; border:none; cursor:pointer; border-bottom:3px solid #007bff; color:#007bff; font-weight:600; font-size:15px;">📅 工作计划</button>
                <button onclick="switchWorkTab('records')" id="recordsTab" class="work-tab" style="padding:12px 20px; background:none; border:none; cursor:pointer; border-bottom:3px solid transparent; color:#999; font-weight:600; font-size:15px;">📝 工作记录</button>
            </div>

            <!-- 可滚动内容区域 -->
            <div style="flex: 1; overflow-y: auto; overflow-x: hidden; padding-right: 10px;">
                <!-- 工作计划标签页 -->
                <div id="plansTabContent" class="work-tab-content" style="display:block;">

                <!-- 添加工作计划表单 -->
                <div style="background:#f8f9fa; padding:20px; border-radius:8px; margin-bottom:20px;">
                    <h4>📝 新建工作计划</h4>
                    <input type="text" id="newPlanTitle" placeholder="工作标题" style="width:100%; margin-bottom:10px; padding:10px; border:1px solid #ddd; border-radius:4px;">
                    <textarea id="newPlanDesc" placeholder="工作描述（选填）" style="width:100%; height:60px; margin-bottom:10px; padding:10px; border:1px solid #ddd; border-radius:4px; resize:vertical;"></textarea>
                    <div style="display:flex; gap:10px; margin-bottom:10px; flex-wrap: wrap;">
                        <input type="datetime-local" id="newPlanDeadline" style="flex:1; min-width:150px; padding:10px; border:1px solid #ddd; border-radius:4px;">
                        <select id="newPlanPriority" style="flex:1; min-width:120px; padding:10px; border:1px solid #ddd; border-radius:4px;">
                            <option value="low">优先级：低</option>
                            <option value="medium" selected>优先级：中</option>
                            <option value="high">优先级：高</option>
                            <option value="urgent">优先级：紧急</option>
                        </select>
                        <select id="newPlanStatus" style="flex:1; min-width:120px; padding:10px; border:1px solid #ddd; border-radius:4px;">
                            <option value="pending" selected>状态：未开始</option>
                            <option value="in_progress">状态：进行中</option>
                            <option value="completed">状态：已完成</option>
                            <option value="cancelled">状态：已取消</option>
                        </select>
                    </div>
                    <button onclick="createWorkPlan()" style="width:100%; padding:12px; background:#28a745; color:white; border:none; border-radius:4px; cursor:pointer; font-size:16px;">
                        ➕ 添加工作计划
                    </button>
                </div>
                
                <!-- 过滤器 -->
                <div style="display:flex; gap:10px; margin-bottom:20px; flex-wrap: wrap;">
                    <button onclick="filterWorkPlans('all')" class="filter-btn active" data-filter="all">📋 全部</button>
                    <button onclick="filterWorkPlans('pending')" class="filter-btn" data-filter="pending">⭕ 未开始</button>
                    <button onclick="filterWorkPlans('in_progress')" class="filter-btn" data-filter="in_progress">🔄 进行中</button>
                    <button onclick="filterWorkPlans('completed')" class="filter-btn" data-filter="completed">✅ 已完成</button>
                    <button onclick="filterWorkPlans('cancelled')" class="filter-btn" data-filter="cancelled">❌ 已取消</button>
                </div>
                
                <!-- 工作计划列表 -->
                <div id="workPlansList">
                    <p style="text-align:center; color:#666; padding:40px;">暂无工作计划</p>
                </div>
                </div>

                <!-- 工作记录标签页 -->
                <div id="recordsTabContent" class="work-tab-content" style="display:none;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                        <h4>📝 已记录的工作内容</h4>
                        <button onclick="loadWorkRecords()" style="padding:8px 16px; background:#007bff; color:white; border:none; border-radius:4px; cursor:pointer; font-size:14px;">🔄 刷新</button>
                    </div>
                    <div id="workRecordsList">
                        <p style="text-align:center; color:#666; padding:40px;">暂无工作记录</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- 图片库模态框 -->
    <div id="imageGalleryModal" class="modal">
        <div class="modal-content" style="max-width: 95%; width:1200px; max-height: 90vh; display:flex; flex-direction:column; padding:25px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h3 style="color:#fff; margin:0;">🖼️ 图片库 (<span id="imageCount">0</span> 张)</h3>
                <span class="close" onclick="closeImageGallery()" style="margin:0;">&times;</span>
            </div>
            
            <!-- 顶部操作栏 -->
            <div style="display:flex; gap:15px; margin-bottom:20px; flex-wrap:wrap; align-items:center;">
                <!-- 批量上传按钮 -->
                <input type="file" id="bulkImageUpload" accept="image/*" multiple style="display:none" onchange="handleBulkImageUpload(event)">
                <button onclick="document.getElementById('bulkImageUpload').click()" style="padding:12px 24px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; border:none; border-radius:8px; cursor:pointer; font-size:15px; font-weight:600;">
                    📤 批量上传
                </button>
                
                <!-- 批量删除模式切换 -->
                <button id="batchModeBtn" onclick="toggleBatchMode()" style="padding:12px 24px; background:#6c757d; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:600; transition:all 0.3s;">
                    ☑️ 批量选择
                </button>
                
                <!-- 批量删除按钮（默认隐藏） -->
                <button id="batchDeleteBtn" onclick="batchDeleteImages()" style="display:none; padding:12px 24px; background:#dc3545; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:600;">
                    🗑️ 删除选中 (<span id="selectedCount">0</span>)
                </button>
                
                <!-- 搜索框 -->
                <input type="text" id="imageSearchDesc" placeholder="搜索描述或文件名" style="flex:1; min-width:200px; padding:10px; background:rgba(40,40,40,0.9); border:1px solid rgba(255,255,255,0.2); border-radius:8px; color:#fff;">
                <input type="text" id="imageSearchTag" placeholder="搜索标签" style="flex:1; min-width:150px; padding:10px; background:rgba(40,40,40,0.9); border:1px solid rgba(255,255,255,0.2); border-radius:8px; color:#fff;">
                <button onclick="searchGalleryImages()" style="padding:12px 24px; background:#007bff; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:600;">🔍</button>
                <button onclick="loadAllImages()" style="padding:12px 24px; background:#6c757d; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:600;">全部</button>
            </div>
            
            <!-- 批量上传预览（折叠式） -->
            <div id="bulkUploadPreview" style="display:none; background:rgba(102, 126, 234, 0.1); padding:15px; border-radius:8px; margin-bottom:20px; border:1px solid rgba(102, 126, 234, 0.3);">
                <div id="bulkImageList" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap:8px; margin-bottom:12px; max-height:150px; overflow-y:auto;"></div>
                <div style="display:flex; gap:10px; margin-bottom:10px;">
                    <input type="text" id="bulkImageDesc" placeholder="图片描述" style="flex:1; padding:8px; background:rgba(40,40,40,0.9); border:1px solid rgba(255,255,255,0.2); border-radius:4px; color:#fff; font-size:13px;">
                    <input type="text" id="bulkImageTags" placeholder="标签" style="flex:1; padding:8px; background:rgba(40,40,40,0.9); border:1px solid rgba(255,255,255,0.2); border-radius:4px; color:#fff; font-size:13px;">
                </div>
                <button onclick="uploadBulkImages()" style="width:100%; padding:10px; background:#28a745; color:white; border:none; border-radius:6px; cursor:pointer; font-size:14px; font-weight:600;">
                    ✅ 上传 <span id="bulkCount">0</span> 张
                </button>
            </div>
            
            <!-- 图片网格（可滚动） -->
            <div id="galleryImagesList" style="flex:1; display:grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap:20px; overflow-y:auto; background:rgba(0,0,0,0.2); padding:20px; border-radius:12px; border:1px solid rgba(255,255,255,0.05);">
                <p style="text-align:center; color:#fff; padding:60px 20px; grid-column: 1/-1; font-size:16px;">📭 正在加载图片...</p>
            </div>
        </div>
    </div>

    <!-- 图片查看大图模态框 -->
    <div id="imageViewModal" class="modal" onclick="closeImageViewIfBackdrop(event)">
        <div class="modal-content" style="max-width: 90%; max-height: 90vh; background:rgba(20,20,20,0.98); border:2px solid rgba(102, 126, 234, 0.5); padding:20px;" onclick="event.stopPropagation();">
            <span class="close" onclick="closeImageView()" style="color:#fff; font-size:32px; position:absolute; right:20px; top:10px; z-index:10;">&times;</span>
            
            <div style="display:flex; flex-direction:column; height:100%;">
                <!-- 图片显示区 -->
                <div style="flex:1; display:flex; align-items:center; justify-content:center; min-height:400px; margin-bottom:20px;">
                    <img id="viewImageSrc" src="" alt="查看图片" style="max-width:100%; max-height:70vh; object-fit:contain; border-radius:8px; box-shadow:0 4px 20px rgba(0,0,0,0.5);">
                </div>
                
                <!-- 图片信息 -->
                <div style="background:rgba(40,40,40,0.8); padding:20px; border-radius:12px; color:#fff;">
                    <div style="display:flex; justify-content:space-between; align-items:start; margin-bottom:15px;">
                        <div style="flex:1;">
                            <h4 id="viewImageName" style="margin:0 0 10px 0; font-size:18px; color:#667eea;">文件名</h4>
                            <div id="viewImageDesc" style="font-size:14px; color:#ddd; margin-bottom:8px;"></div>
                            <div id="viewImageTags" style="font-size:13px; color:#667eea;"></div>
                            <div id="viewImageMeta" style="font-size:12px; color:#999; margin-top:8px;"></div>
                        </div>
                        <div style="display:flex; gap:10px; flex-wrap:wrap;">
                            <button id="downloadBtn" ontouchend="handleDownload(event)" onclick="handleDownload(event)" style="padding:12px 24px; background:#28a745; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:600; font-size:16px; min-width:100px; -webkit-tap-highlight-color: transparent;">
                                📥 下载
                            </button>
                            <button id="deleteBtn" ontouchend="handleDeleteCurrent(event)" onclick="handleDeleteCurrent(event)" style="padding:12px 24px; background:#dc3545; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:600; font-size:16px; min-width:100px; -webkit-tap-highlight-color: transparent;">
                                🗑️ 删除
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div id="settingsModal" class="modal">
        <div class="modal-content" style="max-width: 600px; max-height: 90vh; overflow-y: auto;">
            <span class="close" onclick="closeSettings()">&times;</span>
            <h3>⚙️ 设置</h3>
            
            <!-- 用户头像管理 -->
            <div class="form-group" style="background:#f8f9fa; padding:20px; border-radius:8px; margin-bottom:20px;">
                <label style="font-size:1.1em; margin-bottom:15px; display:block;">👤 我的头像</label>
                <div style="display:flex; align-items:center; gap:20px;">
                    <div style="position:relative;">
                        <img id="currentAvatar" src="" alt="当前头像"
                             style="width:80px; height:80px; border-radius:50%; object-fit:cover; border:3px solid #007bff; background:#e9ecef; display:none;">
                        <div id="defaultAvatarIcon" style="width:80px; height:80px; border-radius:50%; background:#007bff; display:flex; align-items:center; justify-content:center; font-size:36px; color:white; border:3px solid #007bff;">
                            👤
                        </div>
                    </div>
                    <div style="flex:1;">
                        <input type="file" id="avatarUpload" accept="image/*" style="display:none" onchange="handleAvatarSelect(event)">
                        <button onclick="document.getElementById('avatarUpload').click()"
                                style="width:100%; padding:10px; background:#007bff; color:white; border:none; border-radius:6px; cursor:pointer; font-size:14px; margin-bottom:8px;">
                            📁 选择新头像
                        </button>
                        <div id="avatarPreview" style="display:none;">
                            <img id="avatarPreviewImg" src="" alt="预览" style="width:60px; height:60px; border-radius:50%; object-fit:cover; margin-bottom:8px;">
                            <button onclick="uploadAvatar()"
                                    style="width:100%; padding:8px; background:#28a745; color:white; border:none; border-radius:6px; cursor:pointer; font-size:13px;">
                                ✅ 上传
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 账号信息 -->
            <div class="form-group" style="background:#f8f9fa; padding:15px; border-radius:8px; margin-bottom:20px;">
                <div style="font-size:0.9em; color:#333;">
                    <div style="margin-bottom:8px;"><strong>用户名：</strong><span id="settingsUsername">-</span></div>
                    <div style="margin-bottom:8px;"><strong>手机号：</strong><span id="settingsPhone">-</span></div>
                    <div><strong>注册时间：</strong><span id="settingsCreatedAt">-</span></div>
                </div>
            </div>

            <!-- 修改密码 -->
            <div class="form-group" style="background:#f8f9fa; padding:15px; border-radius:8px; margin-bottom:20px;">
                <div onclick="togglePasswordForm()" style="cursor:pointer; display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <label style="font-size:1.1em; margin:0; cursor:pointer;">🔐 修改密码</label>
                    <span id="passwordToggleIcon" style="color:#666;">▼</span>
                </div>
                <div id="passwordForm" style="display:none; padding-top:10px; border-top:1px solid #eee;">
                    <input type="password" id="oldPassword" placeholder="原密码" style="width:100%; padding:10px; margin-bottom:10px; border:1px solid #ddd; border-radius:6px; background:white;">
                    <input type="password" id="newPassword" placeholder="新密码" style="width:100%; padding:10px; margin-bottom:10px; border:1px solid #ddd; border-radius:6px; background:white;">
                    <input type="password" id="confirmPassword" placeholder="确认新密码" style="width:100%; padding:10px; margin-bottom:10px; border:1px solid #ddd; border-radius:6px; background:white;">
                    <button onclick="changePassword()" style="width:100%; padding:10px; background:#ffc107; color:#333; border:none; border-radius:6px; font-weight:600; cursor:pointer;">
                        更新密码
                    </button>
                </div>
            </div>
            
            <div class="form-group" style="background:#f8f9fa; padding:15px; border-radius:8px; margin-bottom:20px;">
                <label style="font-size:1.1em; margin-bottom:15px; display:block;">🎨 聊天背景颜色</label>
                <div style="display:flex; gap:10px; flex-wrap:wrap; align-items: center;">
                    <input type="color" id="bgColorPicker" value="#0099FF" oninput="previewBackgroundColor(this.value)" style="height:40px; width:60px; padding:0; border:none; cursor:pointer; background:none;">
                    <button onclick="previewBackgroundColor('#0099FF'); document.getElementById('bgColorPicker').value='#0099FF'" style="padding:8px 12px; background:#0099FF; color:white; border:none; border-radius:4px; cursor:pointer;">默认蓝</button>
                    <button onclick="previewBackgroundColor('#202124'); document.getElementById('bgColorPicker').value='#202124'" style="padding:8px 12px; background:#202124; color:white; border:none; border-radius:4px; cursor:pointer;">深邃黑</button>
                    <button onclick="previewBackgroundColor('#1e3c72'); document.getElementById('bgColorPicker').value='#1e3c72'" style="padding:8px 12px; background:#1e3c72; color:white; border:none; border-radius:4px; cursor:pointer;">星空蓝</button>
                    <button onclick="previewBackgroundColor('#11998e'); document.getElementById('bgColorPicker').value='#11998e'" style="padding:8px 12px; background:#11998e; color:white; border:none; border-radius:4px; cursor:pointer;">清新绿</button>
                    <button onclick="previewBackgroundColor('#8E2DE2'); document.getElementById('bgColorPicker').value='#8E2DE2'" style="padding:8px 12px; background:#8E2DE2; color:white; border:none; border-radius:4px; cursor:pointer;">神秘紫</button>
                </div>
                <p style="color:#666; font-size:0.8em; margin-top:10px;">选择颜色后，点击下方保存按钮生效</p>
            </div>
            
            <div class="form-group">
                <label style="font-size:1.1em; margin-bottom:15px; display:block;">👔 更换AI秘书</label>
                <p style="color:#aaa; font-size:0.9em; margin-bottom:20px;">选择您喜欢的AI助理形象</p>
                
                <div style="display:grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap:15px;">
                    <!-- 马斯克 -->
                    <div class="assistant-option" onclick="selectAssistant('musk')" id="assistant-musk"
                         style="background:rgba(40,40,40,0.9); border:2px solid rgba(255,255,255,0.2); border-radius:16px; padding:15px; text-align:center; cursor:pointer; transition:all 0.3s;">
                        <img src="/ai/uploads/avatars/musk.jpg" style="width:48px; height:48px; border-radius:50%; object-fit:cover; margin-bottom:8px;">
                        <p style="margin:0; font-weight:600; color:#fff; font-size:0.9em;">马斯克</p>
                        <p style="margin:3px 0 0 0; font-size:0.75em; color:#aaa;">科技·创新</p>
                    </div>
                    
                    <!-- 机器猫 -->
                    <div class="assistant-option" onclick="selectAssistant('jqm')" id="assistant-jqm"
                         style="background:rgba(40,40,40,0.9); border:2px solid rgba(255,255,255,0.2); border-radius:16px; padding:15px; text-align:center; cursor:pointer; transition:all 0.3s;">
                        <img src="/ai/uploads/avatars/jqm.jpg" style="width:48px; height:48px; border-radius:50%; object-fit:cover; margin-bottom:8px;">
                        <p style="margin:0; font-weight:600; color:#fff; font-size:0.9em;">机器猫</p>
                        <p style="margin:3px 0 0 0; font-size:0.75em; color:#aaa;">万能·神奇</p>
                    </div>
                    
                    <!-- 大黄蜂 -->
                    <div class="assistant-option" onclick="selectAssistant('dhf')" id="assistant-dhf"
                         style="background:rgba(40,40,40,0.9); border:2px solid rgba(255,255,255,0.2); border-radius:16px; padding:15px; text-align:center; cursor:pointer; transition:all 0.3s;">
                        <img src="/ai/uploads/avatars/dhf.jpg" style="width:48px; height:48px; border-radius:50%; object-fit:cover; margin-bottom:8px;">
                        <p style="margin:0; font-weight:600; color:#fff; font-size:0.9em;">大黄蜂</p>
                        <p style="margin:3px 0 0 0; font-size:0.75em; color:#aaa;">勇敢·守护</p>
                    </div>
                    
                    <!-- 助理1 -->
                    <div class="assistant-option" onclick="selectAssistant('ns1')" id="assistant-ns1"
                         style="background:rgba(40,40,40,0.9); border:2px solid rgba(255,255,255,0.2); border-radius:16px; padding:15px; text-align:center; cursor:pointer; transition:all 0.3s;">
                        <img src="/ai/uploads/avatars/ns1.jpg" style="width:48px; height:48px; border-radius:50%; object-fit:cover; margin-bottom:8px;">
                        <p style="margin:0; font-weight:600; color:#fff; font-size:0.9em;">助理1号</p>
                        <p style="margin:3px 0 0 0; font-size:0.75em; color:#aaa;">专业·可靠</p>
                    </div>
                    
                    <!-- 助理2 -->
                    <div class="assistant-option" onclick="selectAssistant('lbxx')" id="assistant-lbxx"
                         style="background:rgba(40,40,40,0.9); border:2px solid rgba(255,255,255,0.2); border-radius:16px; padding:15px; text-align:center; cursor:pointer; transition:all 0.3s;">
                        <img src="/ai/uploads/avatars/lbxx.jpg" style="width:48px; height:48px; border-radius:50%; object-fit:cover; margin-bottom:8px;">
                        <p style="margin:0; font-weight:600; color:#fff; font-size:0.9em;">助理2号</p>
                        <p style="margin:3px 0 0 0; font-size:0.75em; color:#aaa;">智慧·温柔</p>
                    </div>
                    
                    <!-- 可爱女生 -->
                    <div class="assistant-option" onclick="selectAssistant('girl')" id="assistant-girl" 
                         style="background:rgba(40,40,40,0.9); border:2px solid rgba(255,255,255,0.2); border-radius:16px; padding:15px; text-align:center; cursor:pointer; transition:all 0.3s;">
                        <div style="font-size:48px; margin-bottom:8px;">👧</div>
                        <p style="margin:0; font-weight:600; color:#fff; font-size:0.9em;">可爱女生</p>
                        <p style="margin:3px 0 0 0; font-size:0.75em; color:#aaa;">活泼·贴心</p>
                    </div>
                    
                    <!-- 阳光男生 -->
                    <div class="assistant-option" onclick="selectAssistant('boy')" id="assistant-boy"
                         style="background:rgba(40,40,40,0.9); border:2px solid rgba(255,255,255,0.2); border-radius:16px; padding:15px; text-align:center; cursor:pointer; transition:all 0.3s;">
                        <div style="font-size:48px; margin-bottom:8px;">👦</div>
                        <p style="margin:0; font-weight:600; color:#fff; font-size:0.9em;">阳光男生</p>
                        <p style="margin:3px 0 0 0; font-size:0.75em; color:#aaa;">热情·开朗</p>
                    </div>
                    
                    <!-- 喵星人 -->
                    <div class="assistant-option" onclick="selectAssistant('cat')" id="assistant-cat"
                         style="background:rgba(40,40,40,0.9); border:2px solid rgba(255,255,255,0.2); border-radius:16px; padding:15px; text-align:center; cursor:pointer; transition:all 0.3s;">
                        <div style="font-size:48px; margin-bottom:8px;">🐱</div>
                        <p style="margin:0; font-weight:600; color:#fff; font-size:0.9em;">喵星人</p>
                        <p style="margin:3px 0 0 0; font-size:0.75em; color:#aaa;">软萌·灵动</p>
                    </div>
                </div>
                
                <button onclick="saveAssistantSettings()" style="margin-top:30px; width:100%; padding:12px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:#fff; border:none; border-radius:12px; font-size:1.1em; cursor:pointer;">
                    ✅ 保存设置
                </button>
            </div>
        </div>
    </div>
    
    <script>
        // Version: 20251215-fix-final
        // 自动扩展文本框逻辑
        let MAX_TEXTAREA_HEIGHT = 150; // 默认最大高度（约5-6行）

        function calculateMaxHeight() {
            try {
                const tempTextarea = document.createElement('textarea');
                tempTextarea.style.position = 'absolute';
                tempTextarea.style.visibility = 'hidden';
                tempTextarea.style.height = 'auto'; // 让高度自适应
                tempTextarea.style.width = '200px';
                tempTextarea.style.padding = '10px 0';
                tempTextarea.style.lineHeight = '1.5em';
                tempTextarea.style.fontSize = '16px';
                tempTextarea.value = '1\\n2\\n3\\n4\\n5'; // 5行
                document.body.appendChild(tempTextarea);
                
                const height = tempTextarea.scrollHeight;
                if (height > 50) { // 确保计算出的高度合理
                    MAX_TEXTAREA_HEIGHT = height;
                }
                
                document.body.removeChild(tempTextarea);
            } catch (e) {
                console.error('计算最大高度失败，使用默认值', e);
            }
        }

        function autoExpandTextarea(textarea) {
            if (!textarea) return;
            
            textarea.style.height = 'auto';
            const currentScrollHeight = textarea.scrollHeight;
            
            // 获取 minHeight，如果获取失败则默认为 24
            let minHeight = 24;
            try {
                const style = getComputedStyle(textarea);
                minHeight = parseFloat(style.minHeight) || 24;
            } catch (e) {}

            // 确保 MAX_TEXTAREA_HEIGHT 有效
            if (!MAX_TEXTAREA_HEIGHT || MAX_TEXTAREA_HEIGHT < minHeight) {
                MAX_TEXTAREA_HEIGHT = minHeight * 5; 
            }

            if (currentScrollHeight <= minHeight) {
                textarea.style.height = minHeight + 'px';
                textarea.style.overflowY = 'hidden';
            } else if (currentScrollHeight > MAX_TEXTAREA_HEIGHT) {
                textarea.style.height = MAX_TEXTAREA_HEIGHT + 'px';
                textarea.style.overflowY = 'auto';
            } else {
                textarea.style.height = currentScrollHeight + 'px';
                textarea.style.overflowY = 'hidden';
            }
            
            // 自动滚动到底部
            if (textarea.scrollHeight > textarea.clientHeight) {
                textarea.scrollTop = textarea.scrollHeight;
            }
        }

        function showTab(evt, tabName) {
            const tabs = document.querySelectorAll('.tab');
            const contents = document.querySelectorAll('.tab-content');
            tabs.forEach(t => t.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));
            evt.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
        }

        // 输入历史记录管理
        let inputHistory = [];
        try {
            inputHistory = JSON.parse(localStorage.getItem('chatInputHistory') || '[]');
        } catch (e) {
            console.error('加载输入历史失败', e);
            inputHistory = [];
        }
        let historyIndex = -1; // -1 表示当前新输入状态
        let currentDraft = ''; // 保存用户当前未发送的输入

        // 语音识别变量
        let recognition = null;
        let isRecording = false;

        function toggleVoiceInput() {
            const btn = document.getElementById('voiceBtn');
            const input = document.getElementById('aiInput');

            // 检查浏览器支持
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                alert('抱歉，您的浏览器不支持语音识别。请尝试使用 Chrome, Edge 或 Safari。');
                return;
            }

            if (isRecording) {
                // 停止录音
                if (recognition) recognition.stop();
                return;
            }

            // 开始录音
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.lang = 'zh-CN'; // 设置为中文
            recognition.continuous = false; // 说完一句自动停止
            recognition.interimResults = true; // 显示临时结果

            recognition.onstart = function() {
                isRecording = true;
                btn.classList.add('mic-active');
                input.placeholder = "正在聆听...";
            };

            recognition.onend = function() {
                isRecording = false;
                btn.classList.remove('mic-active');
                input.placeholder = "How can I help you?";
            };

            recognition.onresult = function(event) {
                let finalTranscript = '';
                let interimTranscript = '';

                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript;
                    } else {
                        interimTranscript += event.results[i][0].transcript;
                    }
                }

                // 将结果追加到输入框（如果是临时结果，可能需要更复杂的逻辑，这里简化为只追加最终结果）
                if (finalTranscript) {
                    // 在光标处插入文本
                    const startPos = input.selectionStart;
                    const endPos = input.selectionEnd;
                    const text = input.value;
                    input.value = text.substring(0, startPos) + finalTranscript + text.substring(endPos, text.length);
                    
                    // 自动扩展
                    if (typeof autoExpandTextarea === 'function') {
                        autoExpandTextarea(input);
                    }
                    
                    // 保存到历史草稿
                    currentDraft = input.value;
                }
            };

            recognition.onerror = function(event) {
                console.error('语音识别错误:', event.error);
                if (event.error === 'not-allowed') {
                    alert('无法访问麦克风。请检查浏览器权限，或确认是否使用了HTTPS连接。');
                }
                isRecording = false;
                btn.classList.remove('mic-active');
            };

            try {
                recognition.start();
            } catch (e) {
                console.error(e);
            }
        }

        function saveInputHistory(text) {
            if (!text || !text.trim()) return;
            text = text.trim();
            
            // 避免保存重复的连续消息
            if (inputHistory.length > 0 && inputHistory[inputHistory.length - 1] === text) {
                return;
            }
            
            inputHistory.push(text);
            // 只保留最近5条
            if (inputHistory.length > 5) {
                inputHistory = inputHistory.slice(inputHistory.length - 5);
            }
            
            localStorage.setItem('chatInputHistory', JSON.stringify(inputHistory));
            historyIndex = -1; // 重置索引
        }
        
        // AI助手 - 处理按键
        function handleAIKeyPress(event) {
            const input = event.target;
            
            // Enter键发送
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendAI();
                return;
            }
            
            // 上键：查看上一条历史
            if (event.key === 'ArrowUp') {
                // 只有当光标在开头时才触发，避免影响多行编辑
                if (input.selectionStart === 0 && input.selectionEnd === 0) {
                    if (historyIndex === -1) {
                        // 如果是从新输入状态开始，先保存当前草稿
                        // 只有当历史记录不为空时才进入历史模式
                        if (inputHistory.length > 0) {
                            currentDraft = input.value;
                            historyIndex = inputHistory.length - 1;
                            event.preventDefault(); // 阻止光标移动
                            input.value = inputHistory[historyIndex];
                        }
                    } else if (historyIndex > 0) {
                        historyIndex--;
                        event.preventDefault();
                        input.value = inputHistory[historyIndex];
                    }
                }
            }
            
            // 下键：查看下一条历史
            if (event.key === 'ArrowDown') {
                // 只有当光标在末尾时才触发
                if (input.selectionStart === input.value.length) {
                    if (historyIndex !== -1) {
                        event.preventDefault();
                        if (historyIndex < inputHistory.length - 1) {
                            historyIndex++;
                            input.value = inputHistory[historyIndex];
                        } else {
                            // 回到最新草稿
                            historyIndex = -1;
                            input.value = currentDraft;
                        }
                    }
                }
            }
        }
        
        // AI助手
            
        function appendAI(role, text, timestamp = null) {
            const box = document.getElementById('aiChatBox');
            
            // 移除欢迎消息
            const welcome = box.querySelector('.welcome-message');
            if (welcome) welcome.remove();
            
            // 检查是否是图片搜索结果
            if (text.includes('[[IMAGE_SEARCH_RESULTS]]')) {
                renderImageSearchResults(text);
                return;
            }
            
            // 创建消息气泡
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            
            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';

            if (role === 'user') {
                // 显示用户头像
                const userAvatarUrl = window.currentUserAvatar;
                if (userAvatarUrl) {
                    const img = document.createElement('img');
                    img.src = userAvatarUrl;
                    img.style.width = '100%';
                    img.style.height = '100%';
                    img.style.borderRadius = '50%';
                    img.style.objectFit = 'cover';
                    img.onerror = function() {
                        this.parentElement.textContent = '👤';
                    };
                    avatar.appendChild(img);
                } else {
                    avatar.textContent = '👤';
                }
            } else {
                const avatarContent = getAssistantAvatar();
                if (avatarContent && avatarContent.startsWith('IMG:')) {
                    // 使用图片
                    const imgSrc = avatarContent.substring(4);
                    const img = document.createElement('img');
                    img.src = imgSrc;
                    img.style.width = '100%';
                    img.style.height = '100%';
                    img.style.borderRadius = '50%';
                    img.style.objectFit = 'cover';

                    // 根据不同助理设置不同的降级emoji
                    const fallbackEmojis = {
                        'musk': '🚀',
                        'jqm': '🤖',
                        'dhf': '🐝',
                        'ns1': '👧',
                        'lbxx': '👦'
                    };
                    const currentType = localStorage.getItem('assistantType') || 'musk';
                    const fallback = fallbackEmojis[currentType] || '🤖';

                    img.onerror = function() {
                        this.parentElement.textContent = fallback;
                    };
                    avatar.appendChild(img);
                } else {
                    // 使用emoji
                    avatar.textContent = avatarContent || '🤖';
                }
            }
            
            // 生成时间戳
            const timeStr = timestamp || new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute:'2-digit'});

            const content = document.createElement('div');
            content.className = 'message-content';
            
            const textDiv = document.createElement('div');
            textDiv.style.whiteSpace = 'pre-wrap';
            textDiv.textContent = text;
            
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = timeStr;
            
            content.appendChild(textDiv);
            content.appendChild(timeDiv);
            
            messageDiv.appendChild(avatar);
            messageDiv.appendChild(content);
            box.appendChild(messageDiv);
            box.scrollTop = box.scrollHeight;
        }

        function displayDetectedPlans(plans) {
            if (!plans || plans.length === 0) return;

            const box = document.getElementById('aiChatBox');
            const plansDiv = document.createElement('div');
            plansDiv.className = 'detected-plans';
            plansDiv.style.cssText = `
                margin: 16px 0;
                padding: 12px;
                background: #f0f7ff;
                border-left: 4px solid #4A90E2;
                border-radius: 6px;
            `;

            const title = document.createElement('div');
            title.style.cssText = 'font-weight: bold; color: #4A90E2; margin-bottom: 8px; font-size: 14px;';
            title.textContent = '📝 识别到以下工作计划:';
            plansDiv.appendChild(title);

            plans.forEach((plan, index) => {
                const planItem = document.createElement('div');
                planItem.style.cssText = `
                    margin: 8px 0;
                    padding: 8px;
                    background: white;
                    border-radius: 4px;
                    font-size: 13px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                `;

                const planInfo = document.createElement('div');
                let infoHTML = `<strong>${plan.title}</strong>`;
                if (plan.deadline) {
                    infoHTML += `<br><span style="color:#666; font-size:12px;">📅 ${plan.deadline}</span>`;
                }
                if (plan.priority) {
                    const priorityColor = plan.priority === 'high' ? '#e74c3c' : (plan.priority === 'medium' ? '#f39c12' : '#95a5a6');
                    infoHTML += `<br><span style="color:${priorityColor}; font-size:12px;">优先级: ${plan.priority}</span>`;
                }
                planInfo.innerHTML = infoHTML;
                planItem.appendChild(planInfo);

                const saveBtn = document.createElement('button');
                saveBtn.textContent = '✓ 保存';
                saveBtn.style.cssText = `
                    padding: 4px 12px;
                    background: #4A90E2;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 12px;
                    white-space: nowrap;
                    margin-left: 8px;
                    transition: background 0.2s;
                `;
                saveBtn.onmouseover = () => saveBtn.style.background = '#357abd';
                saveBtn.onmouseout = () => saveBtn.style.background = '#4A90E2';
                saveBtn.onclick = () => savePlanFromAI(plan, saveBtn);

                planItem.appendChild(saveBtn);
                plansDiv.appendChild(planItem);
            });

            box.appendChild(plansDiv);
            box.scrollTop = box.scrollHeight;
        }

        function savePlanFromAI(plan, btn) {
            const token = localStorage.getItem('token');
            if (!token) {
                alert('请先登录');
                return;
            }

            const saveData = {
                title: plan.title,
                description: plan.source || '从AI对话中识别',
                deadline: plan.deadline || '',
                priority: plan.priority,  // 直接使用，已经是中文
                status: '未开始'
            };

            fetch('/api/plan/add-detected', {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(saveData)
            })
            .then(resp => resp.json())
            .then(data => {
                if (data.success) {
                    btn.textContent = '✓ 已保存';
                    btn.style.background = '#27ae60';
                    btn.disabled = true;
                    btn.onmouseover = null;
                    btn.onmouseout = null;
                    btn.style.cursor = 'default';
                } else {
                    alert('保存失败: ' + data.message);
                }
            })
            .catch(e => {
                alert('保存失败: ' + e);
            });
        }

        function renderImageSearchResults(text) {
            const box = document.getElementById('aiChatBox');
            
            // 提取图片数据
            const startMarker = '[[IMAGE_SEARCH_RESULTS]]';
            const endMarker = '[[/IMAGE_SEARCH_RESULTS]]';
            const startIdx = text.indexOf(startMarker) + startMarker.length;
            const endIdx = text.indexOf(endMarker);
            const imagesJson = text.substring(startIdx, endIdx);
            const images = JSON.parse(imagesJson);
            
            // 提取标题文本
            const titleText = text.substring(0, text.indexOf(startMarker)).trim();
            
            // 创建消息容器
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant';
            messageDiv.innerHTML = `
                <div class="user-message" style="max-width:90%; background:rgba(255,255,255,0.95);">
                    <p style="color:#1a1a1a; font-weight:600; margin-bottom:15px;">${titleText}</p>
                    <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(180px, 1fr)); gap:12px;">
                        ${images.map(img => `
                            <div onclick="viewImageDetails(${img.id})" style="background:rgba(40,40,40,0.05); border-radius:12px; overflow:hidden; cursor:pointer; transition:transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                <img src="/ai/uploads/images/${img.filename}" 
                                     style="width:100%; height:120px; object-fit:cover;" 
                                     onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22><text y=%2250%25%22 x=%2250%25%22>❌</text></svg>'">
                                <div style="padding:8px;">
                                    <p style="margin:0; font-size:0.85em; color:#1a1a1a; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-weight:500;">${img.description || img.original_name}</p>
                                    ${img.tags && img.tags.length > 0 ? `
                                        <div style="margin-top:4px;">
                                            ${img.tags.slice(0, 2).map(t => `<span style="background:rgba(0,0,0,0.1); padding:2px 6px; border-radius:8px; font-size:0.7em; margin-right:4px; color:#666;">${t}</span>`).join('')}
                                        </div>
                                    ` : ''}
                                    <p style="margin:4px 0 0 0; font-size:0.7em; color:#888;">${img.created_at ? img.created_at.substring(0, 16) : ''}</p>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            box.appendChild(messageDiv);
            box.scrollTop = box.scrollHeight;
        }

        // 移动端菜单控制
        function toggleMobileMenu() {
            console.log('toggleMobileMenu called');
            const menu = document.getElementById('mobileMenu');
            const overlay = document.querySelector('.drawer-overlay');

            console.log('menu:', menu);
            console.log('overlay:', overlay);

            if (menu && overlay) {
                const isActive = menu.classList.contains('active');
                console.log('Current active state:', isActive);
                
                menu.classList.toggle('active');
                overlay.classList.toggle('open');

                console.log('New active state:', menu.classList.contains('active'));

                // 防止背景滚动
                if (menu.classList.contains('active')) {
                    document.body.style.overflow = 'hidden';
                } else {
                    document.body.style.overflow = '';
                }
            } else {
                console.error('Menu or overlay not found!');
            }
        }

        function closeMobileMenu() {
            console.log('closeMobileMenu called');
            const menu = document.getElementById('mobileMenu');
            const overlay = document.querySelector('.drawer-overlay');

            if (menu && overlay) {
                menu.classList.remove('active');
                overlay.classList.remove('open');
                document.body.style.overflow = '';
            }
        }
        
        // 确保函数在全局作用域
        window.toggleMobileMenu = toggleMobileMenu;
        window.closeMobileMenu = closeMobileMenu;

        function startNewChat() {
            clearConversation();
        }
        
        // 显示工作计划（手机端）
        function showPlans() {
            openWorkPlans();
        }
        
        // 显示图片管理（手机端）
        function showImages() {
            openImageGallery();
        }
        
        // 处理退出登录
        async function handleLogout() {
            if (!confirm('确定要退出登录吗？')) return;
            
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + token,
                        'Content-Type': 'application/json'
                    }
                });
                
                const data = await response.json();
                
                if (data.success || response.status === 401) {
                    // 清除本地存储
                    localStorage.removeItem('token');
                    localStorage.removeItem('username');
                    localStorage.removeItem('user_id');
                    
                    // 跳转到登录页
                    window.location.href = '/ai/login';
                } else {
                    alert('退出失败：' + (data.message || '未知错误'));
                }
            } catch (error) {
                console.error('退出登录错误:', error);
                // 即使出错也清除本地数据并跳转
                localStorage.removeItem('token');
                localStorage.removeItem('username');
                localStorage.removeItem('user_id');
                window.location.href = '/ai/login';
            }
        }

        async function clearConversation() {
            if (!confirm('确定要开始新对话吗？当前对话历史将被清空。')) return;
            
            try {
                await fetch('/api/ai/clear', {
                    method: 'POST',
                    body: JSON.stringify({})
                });
                
                const box = document.getElementById('aiChatBox');
                box.innerHTML = `
                    <div class="welcome-message">
                        <h3>✨ 新对话已开始</h3>
                    </div>
                `;
            } catch(e) {
                alert('操作失败：' + e);
            }
        }
        
        async function switchAIMode() {
            const select = document.getElementById('aiModeSelect');
            if (!select) return;
            
            const mode = select.value;
            const indicator = document.getElementById('modeIndicator');
            
            try {
                const resp = await fetch('/api/ai/switch_mode', {
                    method: 'POST',
                    body: JSON.stringify({mode: mode})
                });
                
                const data = await resp.json();
                
                if (data.success && indicator) {
                    if (mode === 'simple') {
                        indicator.style.background = '#e3f2fd';
                        indicator.style.color = '#1976d2';
                        indicator.innerHTML = '⚡ 当前模式：<b>简单模式</b> - 瞬间响应，不发热';
                    } else {
                        indicator.style.background = '#f3e5f5';
                        indicator.style.color = '#7b1fa2';
                        indicator.innerHTML = '🤖 当前模式：<b>智能模式</b> - AI理解，需要5-15秒';
                    }
                    }
                    
                    // 清空对话框提示用户
                    const box = document.getElementById('aiChatBox');
                if (box) {
                    box.innerHTML = `
                        <div class="welcome-message">
                            <h3>🔄 已切换到${mode === 'simple' ? '简单' : '智能'}模式</h3>
                            <p>${mode === 'simple' ? '⚡ 快速搜索，瞬间响应' : '🤖 AI智能理解，耐心等待'}</p>
                        </div>
                    `;
                }
            } catch(e) {
                console.log('切换模式失败', e);
            }
        }
        
        // 聊天记忆
        async function addChat() {
            const role = document.getElementById('chatRole');
            const contentElem = document.getElementById('chatContent');
            const tagsElem = document.getElementById('chatTags');
            
            if (!role || !contentElem || !tagsElem) return;
            
            const content = contentElem.value.trim();
            const tags = tagsElem.value.trim().split(',').map(t => t.trim()).filter(t => t);
            
            if (!content) { alert('请输入内容'); return; }

            const token = localStorage.getItem('token');
            await fetch('/api/chat/add', {
                method: 'POST',
                headers: token ? {'Authorization': 'Bearer ' + token} : {},
                body: JSON.stringify({role: role.value, content, tags})
            });
            
            alert('已添加');
            contentElem.value = '';
            tagsElem.value = '';
            loadChats();
        }
        
        async function loadChats() {
            const list = document.getElementById('chatList');
            if (!list) return; // 元素不存在则跳过

            const token = localStorage.getItem('token');
            const res = await fetch('/api/chats', {
                headers: token ? {'Authorization': 'Bearer ' + token} : {}
            });
            const chats = await res.json();
            
            list.innerHTML = chats.slice().reverse().map(c => `
                <div class="card">
                    <div><b>[${c.timestamp}] ${c.role}</b></div>
                    <div style="margin-top:10px">${c.content}</div>
                    ${c.tags?.length ? '<div style="margin-top:10px">' + c.tags.map(t => 
                        `<span class="badge" style="background:#667eea">${t}</span>`
                    ).join('') + '</div>' : ''}
                    <button onclick='openModal(${JSON.stringify(c)})' style="margin-top:10px;padding:6px 15px;font-size:0.9em;background:#fa709a">⏰ 设置提醒</button>
                </div>
            `).join('');
        }
        
        // 工作计划
        async function addPlan() {
            const titleElem = document.getElementById('planTitle');
            const descElem = document.getElementById('planDesc');
            const deadlineElem = document.getElementById('planDeadline');
            const priorityElem = document.getElementById('planPriority');
            
            if (!titleElem || !descElem || !deadlineElem || !priorityElem) return;
            
            const title = titleElem.value.trim();
            const description = descElem.value.trim();
            const deadline = deadlineElem.value.trim();
            const priority = priorityElem.value;
            
            if (!title) { alert('请输入标题'); return; }

            const token = localStorage.getItem('token');
            await fetch('/api/plan/add', {
                method: 'POST',
                headers: token ? {'Authorization': 'Bearer ' + token} : {},
                body: JSON.stringify({title, description, deadline, priority})
            });
            
            alert('已添加');
            titleElem.value = '';
            descElem.value = '';
            loadPlans();
        }
        
        async function loadPlans() {
            const list = document.getElementById('planList');
            if (!list) return; // 元素不存在则跳过

            const token = localStorage.getItem('token');
            const res = await fetch('/api/plans', {
                headers: token ? {'Authorization': 'Bearer ' + token} : {}
            });
            const plans = await res.json();
            
            list.innerHTML = plans.map(p => `
                <div class="card">
                    <div><b>${p.title}</b>
                        <span class="badge" style="background:${p.priority==='高'?'#f5576c':p.priority==='中'?'#feca57':'#48dbfb'}">${p.priority}</span>
                        <span class="badge" style="background:${p.status==='已完成'?'#1dd1a1':'#feca57'}">${p.status}</span>
                    </div>
                    <div style="margin-top:10px">${p.description}</div>
                    <div style="margin-top:10px"><b>截止:</b> ${p.deadline}</div>
                    ${p.status !== '已完成' ? `
                        <button onclick="completePlan(${p.id})" style="margin-top:10px;padding:6px 15px;font-size:0.9em">完成</button>
                        <button onclick="deletePlan(${p.id})" style="margin-top:10px;padding:6px 15px;font-size:0.9em;background:#f5576c">删除</button>
                    ` : ''}
                </div>
            `).join('');
        }
        
        async function completePlan(id) {
            const token = localStorage.getItem('token');
            await fetch('/api/plan/update', {
                method: 'POST',
                headers: token ? {'Authorization': 'Bearer ' + token} : {},
                body: JSON.stringify({id, status: '已完成'})
            });
            loadPlans();
        }

        async function deletePlan(id) {
            if (!confirm('确定删除?')) return;
            const token = localStorage.getItem('token');
            await fetch('/api/plan/delete', {
                method: 'POST',
                headers: token ? {'Authorization': 'Bearer ' + token} : {},
                body: JSON.stringify({id})
            });
            loadPlans();
        }
        
        // 提醒
        async function addReminder() {
            const titleElem = document.getElementById('reminderTitle');
            const messageElem = document.getElementById('reminderMessage');
            const timeElem = document.getElementById('reminderTime');
            const repeatElem = document.getElementById('reminderRepeat');
            const soundElem = document.getElementById('reminderSound');
            
            if (!titleElem || !messageElem || !timeElem || !repeatElem || !soundElem) return;
            
            const title = titleElem.value.trim();
            const message = messageElem.value.trim();
            const remind_time = timeElem.value.trim();
            const repeat = repeatElem.value;
            const sound = soundElem.value;
            
            if (!title) { alert('请输入标题'); return; }

            const token = localStorage.getItem('token');
            await fetch('/api/reminder/add', {
                method: 'POST',
                headers: token ? {'Authorization': 'Bearer ' + token} : {},
                body: JSON.stringify({title, message, remind_time, repeat, sound})
            });
            
            alert('已添加');
            titleElem.value = '';
            messageElem.value = '';
            loadReminders();
        }
        
        async function loadReminders() {
            const list = document.getElementById('reminderList');
            if (!list) return; // 元素不存在则跳过

            const token = localStorage.getItem('token');
            const res = await fetch('/api/reminders', {
                headers: token ? {'Authorization': 'Bearer ' + token} : {}
            });
            const reminders = await res.json();
            
            list.innerHTML = reminders.map(r => `
                <div class="card">
                    <div><b>${r.title}</b>
                        <span class="badge" style="background:#48dbfb">${r.repeat}</span>
                        <span class="badge" style="background:#fa709a">🎵 ${r.sound || 'Ping'}</span>
                    </div>
                    <div style="margin-top:10px">${r.message}</div>
                    <div style="margin-top:10px"><b>时间:</b> ${r.remind_time}</div>
                    <button onclick="deleteReminder(${r.id})" style="margin-top:10px;padding:6px 15px;font-size:0.9em;background:#f5576c">删除</button>
                </div>
            `).join('');
        }
        
        async function deleteReminder(id) {
            if (!confirm('确定删除?')) return;
            const token = localStorage.getItem('token');
            await fetch('/api/reminder/delete', {
                method: 'POST',
                headers: token ? {'Authorization': 'Bearer ' + token} : {},
                body: JSON.stringify({id})
            });
            loadReminders();
        }
        
        // 弹窗
        function openModal(chat) {
            const titleElem = document.getElementById('modalTitle');
            const contentElem = document.getElementById('modalContent');
            const timeElem = document.getElementById('modalTime');
            const modalElem = document.getElementById('reminderModal');
            
            if (!titleElem || !contentElem || !timeElem || !modalElem) return;
            
            titleElem.value = '关于：' + chat.content.substring(0, 20);
            contentElem.value = chat.content;
            const now = new Date();
            now.setHours(now.getHours() + 1);
            timeElem.value = now.toISOString().slice(0,16).replace('T', ' ');
            modalElem.style.display = 'block';
        }
        
        function closeModal() {
            const modalElem = document.getElementById('reminderModal');
            if (modalElem) modalElem.style.display = 'none';
        }
        
        async function createReminder() {
            const titleElem = document.getElementById('modalTitle');
            const contentElem = document.getElementById('modalContent');
            const timeElem = document.getElementById('modalTime');
            const repeatElem = document.getElementById('modalRepeat');
            const soundElem = document.getElementById('modalSound');
            
            if (!titleElem || !contentElem || !timeElem || !repeatElem || !soundElem) return;
            
            const title = titleElem.value;
            const content = contentElem.value;
            const time = timeElem.value;
            const repeat = repeatElem.value;
            const sound = soundElem.value;
            
            await fetch('/api/chat/create_reminder', {
                method: 'POST',
                body: JSON.stringify({title, content, remind_time: time, repeat, sound})
            });
            
            alert('提醒已创建');
            closeModal();
            loadReminders();
            const tabElem = document.querySelectorAll('.tab')[3];
            if (tabElem) tabElem.click();
        }
        
        // 打字机效果函数
        function typeWriter(element, text, speed = 100) {
            if (!element) return;
            
            let index = 0;
            element.textContent = '';
            element.classList.add('typing-cursor');
            
            function type() {
                if (index < text.length) {
                    element.textContent += text.charAt(index);
                    index++;
                    setTimeout(type, speed);
                } else {
                    // 打字完成后移除光标
                    setTimeout(() => {
                        element.classList.remove('typing-cursor');
                    }, 500);
                }
            }
            
            type();
        }
        
        // === 图片上传功能 ===
        let selectedImage = null;
        let selectedImages = []; // 改为数组以支持多张图片
        let selectedImageData = null;
        
        function triggerImageUpload() {
            document.getElementById('imageUpload').click();
        }
        
        function handleImageSelect(event) {
            const files = event.target.files;
            if (!files || files.length === 0) return;
            
            // 清空之前的选择
            selectedImages = [];
            const previewList = document.getElementById('imagePreviewList');
            previewList.innerHTML = '';
            document.getElementById('imagePreviewContainer').style.display = 'block';
            
            // 处理每个选中的文件
            Array.from(files).forEach((file, index) => {
                if (!file.type.startsWith('image/')) {
                    alert(`文件 ${file.name} 不是图片，已跳过`);
                    return;
                }
                
                // 读取文件
                const reader = new FileReader();
                reader.onload = function(e) {
                    const imageData = e.target.result;
                    selectedImages.push({
                        file: file,
                        data: imageData,
                        name: file.name
                    });
                    
                    // 创建预览卡片
                    const previewCard = document.createElement('div');
                    previewCard.style.cssText = 'position:relative; display:inline-block;';
                    previewCard.innerHTML = `
                        <img src="${imageData}" style="width:120px; height:120px; object-fit:cover; border-radius:8px; border:2px solid rgba(255,255,255,0.2);">
                        <button onclick="removeImage(${index})" style="position:absolute; top:-8px; right:-8px; width:24px; height:24px; border-radius:50%; background:#dc3545; color:white; border:none; cursor:pointer; font-size:16px; line-height:1;">×</button>
                        <div style="font-size:11px; color:#999; margin-top:4px; text-align:center; max-width:120px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${file.name}</div>
                    `;
                    previewList.appendChild(previewCard);
                };
                reader.readAsDataURL(file);
            });
        }
        
        function removeImage(index) {
            selectedImages.splice(index, 1);
            
            // 重新渲染预览
            const previewList = document.getElementById('imagePreviewList');
            if (selectedImages.length === 0) {
                document.getElementById('imagePreviewContainer').style.display = 'none';
                previewList.innerHTML = '';
            } else {
                previewList.innerHTML = '';
                selectedImages.forEach((img, idx) => {
                    const previewCard = document.createElement('div');
                    previewCard.style.cssText = 'position:relative; display:inline-block;';
                    previewCard.innerHTML = `
                        <img src="${img.data}" style="width:120px; height:120px; object-fit:cover; border-radius:8px; border:2px solid rgba(255,255,255,0.2);">
                        <button onclick="removeImage(${idx})" style="position:absolute; top:-8px; right:-8px; width:24px; height:24px; border-radius:50%; background:#dc3545; color:white; border:none; cursor:pointer; font-size:16px; line-height:1;">×</button>
                        <div style="font-size:11px; color:#999; margin-top:4px; text-align:center; max-width:120px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${img.name}</div>
                    `;
                    previewList.appendChild(previewCard);
                });
            }
        }
        
        function clearImagePreview() {
            selectedImages = [];
            document.getElementById('imagePreviewContainer').style.display = 'none';
            document.getElementById('imageUpload').value = '';
            document.getElementById('imageDescription').value = '';
            document.getElementById('imageTags').value = '';
        }
        
        async function uploadCurrentImage() {
            if (selectedImages.length === 0) return null;

            const description = document.getElementById('imageDescription').value.trim();
            const tags = document.getElementById('imageTags').value.trim().split(',').map(t => t.trim()).filter(t => t);

            // 上传第一张图片（保持原有行为）
            const firstImage = selectedImages[0];

            try {
                const token = localStorage.getItem('token');
                const resp = await fetch('/api/image/upload', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? {'Authorization': 'Bearer ' + token} : {})
                    },
                    body: JSON.stringify({
                        image_data: firstImage.data,
                        original_name: firstImage.name,
                        description: description,
                        tags: tags
                    })
                });

                if (resp.ok) {
                    const result = await resp.json();
                    return result;
                }
            } catch (e) {
                console.error('上传图片失败:', e);
            }
            return null;
        }
        
        // 单独上传选中的图片（不发送聊天消息）
        async function uploadSelectedImages() {
            if (selectedImages.length === 0) {
                alert('请先选择图片！');
                return;
            }

            const description = document.getElementById('imageDescription').value.trim();
            const tags = document.getElementById('imageTags').value.trim().split(',').map(t => t.trim()).filter(t => t);

            let successCount = 0;
            let failCount = 0;

            const token = localStorage.getItem('token');

            for (let i = 0; i < selectedImages.length; i++) {
                try {
                    const response = await fetch('/api/image/upload', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            ...(token ? {'Authorization': 'Bearer ' + token} : {})
                        },
                        body: JSON.stringify({
                            image_data: selectedImages[i].data,
                            original_name: selectedImages[i].name,
                            description: description,
                            tags: tags
                        })
                    });

                    if (response.ok) {
                        successCount++;
                    } else {
                        failCount++;
                    }
                } catch (e) {
                    console.error(`上传失败 ${selectedImages[i].name}:`, e);
                    failCount++;
                }
            }

            if (successCount > 0) {
                alert(`✅ 上传完成！\n成功: ${successCount} 张\n失败: ${failCount} 张`);
                clearImagePreview();
            } else {
                alert('❌ 上传失败，请重试');
            }
        }
        
        // 修改原有的sendAI函数以支持图片上传
        async function sendAI() {
            const input = document.getElementById('aiInput');
            const msg = input.value.trim();
            
            // 如果有选中的图片，先上传
            let uploadedImage = null;
            if (selectedImages.length > 0) {
                uploadedImage = await uploadCurrentImage();
                if (uploadedImage) {
                    // 在聊天框中显示图片
                    appendImageToChat(uploadedImage);
                }
            }
            
            if (!msg && !uploadedImage) return;
            
            if (msg) {
                appendAI('user', msg);
                saveInputHistory(msg);
                input.value = '';
                // 重置草稿
                currentDraft = '';
            }
            
            const box = document.getElementById('aiChatBox');
            const welcome = box.querySelector('.welcome-message');
            if (welcome) welcome.remove();
            
            if (!msg) return;  // 如果只上传图片，不发送AI请求
            
            const loading = document.createElement('div');
            loading.id = 'loading';
            loading.className = 'message assistant';
            loading.innerHTML = `
                <div style="padding: 16px 20px; border-radius: 20px; background: rgba(255, 255, 255, 0.9); color: #1a1a1a; max-width: 70%; border-bottom-left-radius: 4px;">
                    <span style="font-size: 1.5em; letter-spacing: 2px;">...</span>
                </div>
            `;
            box.appendChild(loading);
            box.scrollTop = box.scrollHeight;
            
            try {
                const token = localStorage.getItem('token');
                const headers = {
                    'Content-Type': 'application/json'
                };
                if (token) {
                    headers['Authorization'] = 'Bearer ' + token;
                }

                const resp = await fetch('/api/ai/chat', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({message: msg})
                });

                // 检查响应状态
                if (!resp.ok) {
                    const text = await resp.text();
                    throw new Error(`HTTP ${resp.status}: ${text}`);
                }

                // 检查是否是JSON响应
                const contentType = resp.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    const text = await resp.text();
                    console.error('非JSON响应:', text);
                    throw new Error('服务器返回了非JSON响应，可能需要重新登录');
                }

                const data = await resp.json();
                loading.remove();

                // 检查响应中是否有错误
                if (!data.success && data.message) {
                    throw new Error(data.message);
                }

                appendAI('assistant', data.response || data.message);

                // 处理识别到的计划
                if (data.detected_plans && data.detected_plans.length > 0) {
                    displayDetectedPlans(data.detected_plans);
                }
            } catch(e) {
                loading.remove();
                console.error('AI请求错误:', e);
                appendAI('assistant', '❌ 请求失败：' + e.message);

                // 如果是认证错误，提示用户重新登录
                if (e.message.includes('登录') || e.message.includes('401')) {
                    setTimeout(() => {
                        if (confirm('会话已过期，是否重新登录？')) {
                            window.location.href = '/ai/login';
                        }
                    }, 1000);
                }
            }
        }
        
        function appendImageToChat(imageResult) {
            const box = document.getElementById('aiChatBox');
            const welcome = box.querySelector('.welcome-message');
            if (welcome) welcome.remove();

            // 从返回结果中获取图片信息
            const image = imageResult.image || imageResult;

            const messageDiv = document.createElement('div');
            messageDiv.className = 'message user';
            messageDiv.innerHTML = `
                <div class="user-message">
                    <img src="/${image.file_path || 'uploads/images/' + image.filename}"
                         style="max-width:300px; max-height:300px; border-radius:12px; display:block; margin-bottom:8px;"
                         onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22300%22 height=%22300%22><text y=%2250%25%22 x=%2250%25%22 text-anchor=%22middle%22 fill=%22%23999%22>图片加载失败</text></svg>'">
                    ${image.description ? `<p style="margin-top:8px;">${image.description}</p>` : ''}
                    ${image.tags && image.tags.length > 0 ? `
                        <div style="margin-top:8px;">
                            ${(Array.isArray(image.tags) ? image.tags : image.tags.split(',')).map(t => `<span style="background:rgba(255,255,255,0.2); padding:4px 8px; border-radius:12px; font-size:0.9em; margin-right:4px;">${typeof t === 'string' ? t.trim() : t}</span>`).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
            box.appendChild(messageDiv);
            box.scrollTop = box.scrollHeight;

            // 清除图片预览
            clearImagePreview();
        }
        
// DEPRECATED:         // === 图片库管理功能 ===
// DEPRECATED:         function openImageGallery() {
// DEPRECATED:             document.getElementById('imageGalleryModal').style.display = 'block';
// DEPRECATED:             loadAllImages();
// DEPRECATED:         }
// DEPRECATED:         
// DEPRECATED:         function closeImageGallery() {
// DEPRECATED:             document.getElementById('imageGalleryModal').style.display = 'none';
// DEPRECATED:         }
// DEPRECATED:         
// DEPRECATED:         async function loadAllImages() {
// DEPRECATED:             try {
// DEPRECATED:                 const resp = await fetch('/api/images');
// DEPRECATED:                 const images = await resp.json();
// DEPRECATED:                 displayImages(images);
// DEPRECATED:             } catch (e) {
// DEPRECATED:                 alert('加载图片失败：' + e);
// DEPRECATED:             }
// DEPRECATED:         }
// DEPRECATED:         
// DEPRECATED:         async function searchImages() {
// DEPRECATED:             const keyword = document.getElementById('imageSearchKeyword').value.trim();
// DEPRECATED:             const tag = document.getElementById('imageSearchTag').value.trim();
// DEPRECATED:             
// DEPRECATED:             try {
// DEPRECATED:                 const resp = await fetch('/api/image/search', {
// DEPRECATED:                     method: 'POST',
// DEPRECATED:                     body: JSON.stringify({keyword, tag})
// DEPRECATED:                 });
// DEPRECATED:                 const data = await resp.json();
// DEPRECATED:                 displayImages(data.results);
// DEPRECATED:             } catch (e) {
// DEPRECATED:                 alert('搜索失败：' + e);
// DEPRECATED:             }
// DEPRECATED:         }
// DEPRECATED:         
// DEPRECATED:         function displayImages(images) {
// DEPRECATED:             const grid = document.getElementById('imageGrid');
// DEPRECATED:             
// DEPRECATED:             if (images.length === 0) {
// DEPRECATED:                 grid.innerHTML = '<p style="text-align:center; color:#888; grid-column:1/-1; padding:40px;">暂无图片</p>';
// DEPRECATED:                 return;
// DEPRECATED:             }
// DEPRECATED:             
// DEPRECATED:             grid.innerHTML = images.map(img => `
// DEPRECATED:                 <div class="image-card" style="background:rgba(40,40,40,0.9); border-radius:12px; overflow:hidden; position:relative; cursor:pointer;">
// DEPRECATED:                     <img src="/uploads/images/${img.filename}" 
// DEPRECATED:                          style="width:100%; height:150px; object-fit:cover;" 
// DEPRECATED:                          onclick="viewImageDetails(${img.id})"
// DEPRECATED:                          onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22><text y=%2250%25%22 x=%2250%25%22>❌</text></svg>'">
// DEPRECATED:                     <div style="padding:10px;">
// DEPRECATED:                         <p style="margin:0; font-size:0.9em; color:#fff; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${img.description || img.original_name}</p>
// DEPRECATED:                         ${img.tags && img.tags.length > 0 ? `
// DEPRECATED:                             <div style="margin-top:5px;">
// DEPRECATED:                                 ${img.tags.map(t => `<span style="background:rgba(255,255,255,0.1); padding:2px 6px; border-radius:8px; font-size:0.75em; margin-right:4px;">${t}</span>`).join('')}
// DEPRECATED:                             </div>
// DEPRECATED:                         ` : ''}
// DEPRECATED:                         <p style="margin:5px 0 0 0; font-size:0.75em; color:#888;">${img.created_at || ''}</p>
// DEPRECATED:                     </div>
// DEPRECATED:                     <button onclick="deleteImage(${img.id}); event.stopPropagation();" 
// DEPRECATED:                             style="position:absolute; top:8px; right:8px; width:28px; height:28px; border-radius:50%; background:rgba(245,87,108,0.9); color:white; border:none; cursor:pointer; font-size:16px;">×</button>
// DEPRECATED:                 </div>
// DEPRECATED:             `).join('');
// DEPRECATED:         }
// DEPRECATED:         
// DEPRECATED:         function viewImageDetails(imageId) {
// DEPRECATED:             fetch(`/api/image/${imageId}`)
// DEPRECATED:                 .then(r => r.json())
// DEPRECATED:                 .then(img => {
// DEPRECATED:                     const modal = document.createElement('div');
// DEPRECATED:                     modal.style = 'position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.9); z-index:10000; display:flex; align-items:center; justify-content:center;';
// DEPRECATED:                     modal.innerHTML = `
// DEPRECATED:                         <div style="max-width:80%; max-height:80%; background:rgba(40,40,40,0.95); border-radius:20px; padding:20px; position:relative;">
// DEPRECATED:                             <button onclick="this.parentElement.parentElement.remove()" style="position:absolute; top:10px; right:10px; width:36px; height:36px; border-radius:50%; background:#f5576c; color:white; border:none; cursor:pointer; font-size:20px;">×</button>
// DEPRECATED:                             <img src="/uploads/images/${img.filename}" style="max-width:100%; max-height:60vh; border-radius:12px; display:block; margin:20px auto;">
// DEPRECATED:                             <div style="margin-top:20px; color:#fff;">
// DEPRECATED:                                 <p><strong>描述：</strong>${img.description || '无'}</p>
// DEPRECATED:                                 <p><strong>标签：</strong>${img.tags && img.tags.length > 0 ? img.tags.join(', ') : '无'}</p>
// DEPRECATED:                                 <p><strong>上传时间：</strong>${img.created_at || '未知'}</p>
// DEPRECATED:                                 <p><strong>文件大小：</strong>${(img.file_size / 1024).toFixed(2)} KB</p>
// DEPRECATED:                             </div>
// DEPRECATED:                         </div>
// DEPRECATED:                     `;
// DEPRECATED:                     document.body.appendChild(modal);
// DEPRECATED:                 })
// DEPRECATED:                 .catch(e => alert('加载图片详情失败：' + e));
// DEPRECATED:         }
// DEPRECATED:         
// DEPRECATED:         async function deleteImage(imageId) {
// DEPRECATED:             if (!confirm('确定要删除这张图片吗？')) return;
// DEPRECATED:             
// DEPRECATED:             try {
// DEPRECATED:                 const resp = await fetch('/api/image/delete', {
// DEPRECATED:                     method: 'POST',
// DEPRECATED:                     body: JSON.stringify({id: imageId})
// DEPRECATED:                 });
// DEPRECATED:                 const data = await resp.json();
// DEPRECATED:                 if (data.success) {
// DEPRECATED:                     loadAllImages();  // 刷新列表
// DEPRECATED:                 } else {
// DEPRECATED:                     alert('删除失败');
// DEPRECATED:                 }
// DEPRECATED:             } catch (e) {
// DEPRECATED:                 alert('删除失败：' + e);
// DEPRECATED:             }
// DEPRECATED:         }
        
        // === 设置功能 ===
        let currentAssistant = 'musk';  // 默认马斯克
        
        function openSettings() {
            document.getElementById('settingsModal').style.display = 'block';
            loadAssistantSettings();
        }
        
        function closeSettings() {
            document.getElementById('settingsModal').style.display = 'none';
        }
        
        function loadAssistantSettings() {
            // 从localStorage加载设置
            const saved = localStorage.getItem('assistantType');
            if (saved) {
                currentAssistant = saved;
            }
            updateAssistantSelection();
        }
        
        function selectAssistant(type) {
            currentAssistant = type;
            updateAssistantSelection();
        }
        
        function updateAssistantSelection() {
            // 移除所有选中样式
            document.querySelectorAll('.assistant-option').forEach(opt => {
                opt.style.border = '2px solid rgba(255,255,255,0.2)';
                opt.style.background = 'rgba(40,40,40,0.9)';
            });
            
            // 添加选中样式
            const selected = document.getElementById(`assistant-${currentAssistant}`);
            if (selected) {
                selected.style.border = '2px solid #667eea';
                selected.style.background = 'linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%)';
            }
        }
        
        async function saveAssistantSettings() {
            // 1. 保存助理类型到本地
            localStorage.setItem('assistantType', currentAssistant);
            
            // 2. 保存背景颜色到服务器
            const picker = document.getElementById('bgColorPicker');
            const bgColor = picker ? picker.value : null;
            
            if (bgColor) {
                try {
                    const response = await fetchWithAuth('/api/user/settings', {
                        method: 'POST',
                        body: JSON.stringify({
                            chat_background: bgColor
                        })
                    });
                    const data = await response.json();
                    if (!data.success) {
                        console.error('保存背景颜色失败:', data.message);
                    }
                } catch (e) {
                    console.error('保存设置出错:', e);
                }
            }

            closeSettings();
            alert('✅ 设置已保存！');
        }

        function togglePasswordForm() {
            const form = document.getElementById('passwordForm');
            const icon = document.getElementById('passwordToggleIcon');
            if (form.style.display === 'none') {
                form.style.display = 'block';
                icon.textContent = '▲';
            } else {
                form.style.display = 'none';
                icon.textContent = '▼';
            }
        }

        async function changePassword() {
            const oldPassword = document.getElementById('oldPassword').value;
            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;

            if (!oldPassword || !newPassword || !confirmPassword) {
                alert('请填写所有密码字段');
                return;
            }

            if (newPassword !== confirmPassword) {
                alert('两次输入的新密码不一致');
                return;
            }

            if (newPassword.length < 6) {
                alert('新密码长度至少需要6位');
                return;
            }

            try {
                const response = await fetchWithAuth('/api/user/change-password', {
                    method: 'POST',
                    body: JSON.stringify({
                        old_password: oldPassword,
                        new_password: newPassword
                    })
                });

                const data = await response.json();

                if (data.success) {
                    alert('✅ 密码修改成功！请重新登录');
                    logout();
                } else {
                    alert('❌ 修改失败: ' + data.message);
                }
            } catch (e) {
                console.error('修改密码错误:', e);
                alert('修改密码时出错');
            }
        }
        
        function getAssistantAvatar() {
            const type = localStorage.getItem('assistantType') || 'musk';
            const avatars = {
                'musk': 'IMG:/ai/uploads/avatars/musk.jpg',
                'jqm': 'IMG:/ai/uploads/avatars/jqm.jpg',
                'dhf': 'IMG:/ai/uploads/avatars/dhf.jpg',
                'ns1': 'IMG:/ai/uploads/avatars/ns1.jpg',
                'lbxx': 'IMG:/ai/uploads/avatars/lbxx.jpg',
                'girl': '👧',
                'boy': '👦',
                'cat': '🐱',
                'panda': '🐼',
                'doraemon': '🤖',
                'datou': '👶',
                'bumblebee': '🐝',
                'female': '👧',
                'male': '👦'
            };
            return avatars[type] || 'IMG:/uploads/avatars/musk.jpg';
        }

        // ==================== 用户认证 ====================
        function fetchWithAuth(url, options = {}) {
            const token = localStorage.getItem('token');
            const headers = options.headers || {};

            if (token) {
                headers['Authorization'] = 'Bearer ' + token;
            }

            return fetch(url, {
                ...options,
                headers: {
                    ...headers,
                    'Content-Type': 'application/json'
                }
            });
        }

        function checkLogin() {
            const token = localStorage.getItem('token');
            const username = localStorage.getItem('username');

            // 如果有token，验证有效性
            if (token) {
                fetch('/api/auth/verify', {
                    headers: {
                        'Authorization': 'Bearer ' + token
                    }
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        // ✅ Token有效，显示用户信息和聊天界面
                        showUserInfo(username || data.username);
                        // 加载历史记录
                        loadChatHistory();
                    } else {
                        // ❌ Token无效，清除数据并重定向到登录页
                        clearLoginData();
                        window.location.href = '/ai/login';
                    }
                })
                .catch(() => {
                    // 网络错误，如果有用户名则允许离线使用
                    if (username) {
                        showUserInfo(username);
                    } else {
                        // 没有用户信息，重定向到登录
                        window.location.href = '/ai/login';
                    }
                });
            } else {
                // ❌ 没有token，重定向到登录页
                window.location.href = '/ai/login';
            }
        }

        function showLoginButton() {
            // 显示登录按钮
            const loginBtn = document.createElement('div');
            loginBtn.id = 'loginButton';
            loginBtn.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 24px;
                border-radius: 20px;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                z-index: 1000;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s;
            `;
            loginBtn.innerHTML = '🔐 登录/注册';
            loginBtn.onclick = () => {
                window.location.href = '/ai/login';
            };
            loginBtn.onmouseover = () => {
                loginBtn.style.transform = 'translateY(-2px)';
                loginBtn.style.boxShadow = '0 6px 16px rgba(102, 126, 234, 0.5)';
            };
            loginBtn.onmouseout = () => {
                loginBtn.style.transform = 'translateY(0)';
                loginBtn.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
            };

            // 如果已存在，先删除
            const existing = document.getElementById('loginButton');
            if (existing) existing.remove();

            document.body.appendChild(loginBtn);
        }

        function showUserInfo(username) {
            // 用户信息现在只显示在左下角的菜单中
            // 更新左下角的用户ID显示
            updateUserPanelId(username);
            
            // 更新移动端抽屉菜单的用户信息
            const menuUsername = document.getElementById('menuUsername');
            if (menuUsername) {
                menuUsername.textContent = username || '未登录';
            }
            
            // 更新抽屉菜单的用户头像
            const menuAvatar = document.getElementById('menuAvatar');
            if (menuAvatar && window.currentUserAvatar) {
                menuAvatar.innerHTML = `<img src="${window.currentUserAvatar}" alt="用户头像">`;
            }
        }

        // 切换左下角用户菜单面板
        function toggleUserPanel() {
            const userPanel = document.getElementById('userPanel');
            if (userPanel) {
                userPanel.style.display = userPanel.style.display === 'none' ? 'block' : 'none';
            }
        }

        // 关闭用户菜单面板（点击外部时）
        function closeUserPanel() {
            const userPanel = document.getElementById('userPanel');
            if (userPanel) {
                userPanel.style.display = 'none';
            }
        }

        // 更新左下角用户ID显示
        function updateUserPanelId(username) {
            const userIdDisplay = document.getElementById('userIdDisplay');
            if (userIdDisplay && username) {
                userIdDisplay.textContent = username;
            }
        }

        // 在页面加载时初始化用户菜单
        function initUserPanel() {
            const username = localStorage.getItem('username') || '未登录';
            updateUserPanelId(username);

            // 加载用户头像
            loadUserAvatarForPanel();

            // 点击外部区域时关闭菜单
            document.addEventListener('click', function(event) {
                const userPanel = document.getElementById('userPanel');
                const sidebarIcon = event.target.closest('[onclick="toggleUserPanel()"]');

                if (!sidebarIcon && userPanel && userPanel.style.display === 'block') {
                    closeUserPanel();
                }
            });
        }

        async function loadUserAvatarForPanel() {
            try {
                const response = await fetchWithAuth('/api/user/profile');
                const data = await response.json();

                if (data.success && data.user && data.user.avatar_url) {
                    // 保存到全局变量供聊天消息使用
                    const avatarUrl = data.user.avatar_url.startsWith('/') ? '/ai' + data.user.avatar_url : '/ai/' + data.user.avatar_url;
                    window.currentUserAvatar = avatarUrl;

                    // 更新侧边栏头像
                    const sidebarAvatar = document.getElementById('sidebarUserAvatar');
                    const sidebarDefault = document.getElementById('sidebarDefaultAvatar');
                    if (sidebarAvatar && sidebarDefault) {
                        sidebarAvatar.src = avatarUrl;
                        sidebarAvatar.style.display = 'block';
                        sidebarDefault.style.display = 'none';
                    }

                    // 更新面板头像
                    const panelAvatar = document.getElementById('panelUserAvatar');
                    const panelDefault = document.getElementById('panelDefaultAvatar');
                    if (panelAvatar && panelDefault) {
                        panelAvatar.src = avatarUrl;
                        panelAvatar.style.display = 'block';
                        panelDefault.style.display = 'none';
                    }

                    // 更新抽屉菜单头像
                    const menuAvatar = document.getElementById('menuAvatar');
                    if (menuAvatar) {
                        menuAvatar.innerHTML = `<img src="${avatarUrl}" alt="用户头像">`;
                    }
                    
                    // 应用用户自定义背景颜色
                    if (data.user.chat_background) {
                        applyBackgroundColor(data.user.chat_background);
                    }
                } else {
                    // 没有头像时清空全局变量
                    window.currentUserAvatar = null;
                }
            } catch (error) {
                console.log('加载用户头像失败:', error);
                // 失败时清空全局变量
                window.currentUserAvatar = null;
            }
        }


        function logout() {
            if (!confirm('确定要退出登录吗？')) return;

            const token = localStorage.getItem('token');

            // 调用退出API
            if (token) {
                fetch('/api/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + token,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({})
                }).catch(() => {});
            }

            clearLoginData();
            window.location.href = '/ai/login';
        }

        // ============ 设置相关函数 ============

        function applyBackgroundColor(color) {
            // 1. 设置 body 背景
            document.body.style.background = color;
            
            // 2. 设置移动端顶部栏背景
            const mobileHeader = document.querySelector('.mobile-header');
            if (mobileHeader) {
                mobileHeader.style.background = color;
            }
            
            // 3. 设置移动端底部输入框背景
            // 注意：仅在移动端应用颜色，桌面端保持透明
            const inputContainer = document.querySelector('.input-container');
            if (inputContainer) {
                if (window.innerWidth <= 768) {
                    inputContainer.style.background = color;
                } else {
                    inputContainer.style.background = 'transparent';
                }
            }
            
            // 如果是深色背景，调整文字颜色 (预留逻辑)
            const isDark = color !== '#ffffff' && color !== '#f5f5f5';
        }

        // 添加窗口大小改变时的自适应处理
        window.addEventListener('resize', function() {
            // 获取当前 body 的背景色作为基准
            const currentColor = document.body.style.background;
            if (currentColor) {
                const inputContainer = document.querySelector('.input-container');
                if (inputContainer) {
                    if (window.innerWidth <= 768) {
                        inputContainer.style.background = currentColor;
                    } else {
                        inputContainer.style.background = 'transparent';
                    }
                }
            }
        });

        function previewBackgroundColor(color) {
            applyBackgroundColor(color);
            const picker = document.getElementById('bgColorPicker');
            if (picker) picker.value = color;
        }

        let selectedAvatarFile = null;

        function openSettings() {
            const modal = document.getElementById('settingsModal');
            modal.style.display = 'block';
            loadUserProfile();
        }

        function closeSettings() {
            const modal = document.getElementById('settingsModal');
            modal.style.display = 'none';
            selectedAvatarFile = null;
            document.getElementById('avatarPreview').style.display = 'none';
        }

        async function loadUserProfile() {
            try {
                const response = await fetchWithAuth('/api/user/profile');
                console.log('Profile response status:', response.status);
                
                if (!response.ok) {
                    console.error('Profile API error:', response.status, response.statusText);
                    if (response.status === 401) {
                        alert('登录已过期，请重新登录');
                        window.location.href = '/ai/login';
                        return;
                    }
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const data = await response.json();
                console.log('Profile data:', data);

                if (data.success && data.user) {
                    const user = data.user;

                    // 显示用户信息
                    document.getElementById('settingsUsername').textContent = user.username || '-';
                    document.getElementById('settingsPhone').textContent = user.phone || '-';
                    document.getElementById('settingsCreatedAt').textContent = user.created_at || '-';

                    // 显示头像
                    const currentAvatar = document.getElementById('currentAvatar');
                    const defaultIcon = document.getElementById('defaultAvatarIcon');

                    if (user.avatar_url) {
                        const avatarUrl = user.avatar_url.startsWith('/') ? '/ai' + user.avatar_url : '/ai/' + user.avatar_url;
                        console.log('Setting avatar URL:', avatarUrl);
                        currentAvatar.src = avatarUrl;
                        currentAvatar.style.display = 'block';
                        defaultIcon.style.display = 'none';
                    } else {
                        currentAvatar.style.display = 'none';
                        defaultIcon.style.display = 'flex';
                    }

                    // 高亮当前选中的助理头像
                    highlightCurrentAssistantAvatar();
                    
                    // 初始化背景颜色选择器
                    if (user.chat_background) {
                        const picker = document.getElementById('bgColorPicker');
                        if (picker) {
                            picker.value = user.chat_background;
                        }
                    }
                } else {
                    console.error('Invalid profile data:', data);
                    alert('加载用户信息失败: ' + (data.message || '未知错误'));
                }
            } catch (error) {
                console.error('加载用户信息失败:', error);
                alert('加载用户信息失败: ' + error.message);
            }
        }

        function changeAssistantAvatar(type) {
            // 保存到localStorage
            localStorage.setItem('assistantType', type);

            // 高亮选中的头像
            highlightCurrentAssistantAvatar();

            // 提示用户
            alert('助理头像已更换！刷新聊天记录生效');
        }

        function highlightCurrentAssistantAvatar() {
            const currentType = localStorage.getItem('assistantType') || 'musk';

            // 移除所有高亮
            document.querySelectorAll('.avatar-option').forEach(option => {
                option.style.border = '2px solid transparent';
                option.style.background = 'transparent';
            });

            // 高亮当前选中的
            const selected = document.querySelector(`.avatar-option[data-type="${currentType}"]`);
            if (selected) {
                selected.style.border = '2px solid #007bff';
                selected.style.background = '#e3f2fd';
            }
        }


        function handleAvatarSelect(event) {
            const file = event.target.files[0];
            if (!file) return;

            // 检查文件类型
            if (!file.type.startsWith('image/')) {
                alert('请选择图片文件');
                return;
            }

            // 检查文件大小（限制5MB）
            if (file.size > 5 * 1024 * 1024) {
                alert('图片大小不能超过5MB');
                return;
            }

            selectedAvatarFile = file;

            // 显示预览
            const reader = new FileReader();
            reader.onload = (e) => {
                document.getElementById('avatarPreviewImg').src = e.target.result;
                document.getElementById('avatarPreview').style.display = 'block';
            };
            reader.readAsDataURL(file);
        }

        async function uploadAvatar() {
            if (!selectedAvatarFile) {
                alert('请先选择图片');
                return;
            }

            try {
                // 读取文件为base64
                const reader = new FileReader();
                reader.onload = async (e) => {
                    const base64Data = e.target.result;

                    // 上传头像
                    const response = await fetchWithAuth('/api/user/avatar', {
                        method: 'POST',
                        body: JSON.stringify({
                            avatar_data: base64Data
                        })
                    });

                    const data = await response.json();

                    if (data.success) {
                        alert('头像上传成功！');
                        // 刷新用户信息
                        loadUserProfile();
                        // 刷新侧边栏和面板头像
                        loadUserAvatarForPanel();
                        // 隐藏预览
                        document.getElementById('avatarPreview').style.display = 'none';
                        selectedAvatarFile = null;
                    } else {
                        alert('头像上传失败: ' + (data.error || '未知错误'));
                    }
                };
                reader.readAsDataURL(selectedAvatarFile);
            } catch (error) {
                console.error('上传头像失败:', error);
                alert('上传头像失败');
            }
        }

        // ============ 设置相关函数结束 ============


        function clearLoginData() {
            localStorage.removeItem('token');
            localStorage.removeItem('username');
            localStorage.removeItem('user_id');
        }

        async function loadChatHistory() {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/chat/history', {
                    headers: token ? {'Authorization': 'Bearer ' + token} : {}
                });
                
                if (!response.ok) return;
                
                const data = await response.json();
                if (data.success && data.history && data.history.length > 0) {
                    // 移除欢迎消息
                    const box = document.getElementById('aiChatBox');
                    const welcome = box.querySelector('.welcome-message');
                    if (welcome) welcome.remove();
                    
                    // 遍历显示消息
                    data.history.forEach(msg => {
                        // 提取时间 HH:mm
                        let timeStr = '';
                        if (msg.timestamp) {
                            const date = new Date(msg.timestamp.replace(/-/g, '/')); // 兼容性处理
                            timeStr = date.toLocaleTimeString('zh-CN', {hour: '2-digit', minute:'2-digit'});
                        }
                        
                        appendAI(msg.role, msg.content, timeStr);
                    });
                    
                    // 滚动到底部
                    setTimeout(() => {
                        box.scrollTop = box.scrollHeight;
                    }, 100);
                }
            } catch (e) {
                console.error('加载历史记录失败:', e);
            }
        }

        window.onload = () => {
            // 1. 检查登录状态 (核心功能)
            try {
                checkLogin();
            } catch (e) {
                console.error('Check login failed:', e);
            }

            // 2. 初始化用户菜单
            try {
                initUserPanel();
            } catch (e) {
                console.error('Init user panel failed:', e);
            }

            // 3. 计算文本框最大高度 (新功能)
            try {
                calculateMaxHeight();
            } catch (e) {
                console.error('Calculate max height failed:', e);
            }

            // 4. 打字机效果
            try {
                const welcomeTextElem = document.getElementById('welcomeText');
                if (welcomeTextElem) {
                    const username = localStorage.getItem('username') || '访客';
                    typeWriter(welcomeTextElem, `你好，${username}！我是你的私人助理，有什么可以帮你的吗？`, 80);
                }
            } catch (e) {}

            // 5. 加载其他数据
            try {
                if (document.getElementById('chatList')) loadChats();
                if (document.getElementById('planList')) loadPlans();
                if (document.getElementById('reminderList')) loadReminders();
            } catch (e) {}

            // 6. 加载AI模式
            fetch('/api/ai/get_mode')
                .then(r => r.json())
                .then(data => {
                    const select = document.getElementById('aiModeSelect');
                    const indicator = document.getElementById('modeIndicator');
                    if (select) select.value = data.mode || 'simple';

                    if (indicator && data.mode === 'ollama') {
                        indicator.style.background = '#f3e5f5';
                        indicator.style.color = '#7b1fa2';
                        indicator.innerHTML = '🤖 当前模式：<b>智能模式</b> - AI理解，需要5-15秒';
                    }
                })
                .catch(e => console.log('加载模式失败', e));

            // 7. 初始化 aiInput 的自动扩展功能
            try {
                const aiInput = document.getElementById('aiInput');
                if (aiInput) {
                    aiInput.addEventListener('input', () => autoExpandTextarea(aiInput));
                    // 确保页面加载时输入框高度正确
                    setTimeout(() => autoExpandTextarea(aiInput), 100);
                }
            } catch (e) {
                console.error('Init auto expand failed:', e);
            }

            // 8. 移动端键盘弹出优化
            if (window.innerWidth <= 768) {
                try {
                    const aiInput = document.getElementById('aiInput');
                    const chatBox = document.getElementById('aiChatBox');
                    const mobileHeader = document.querySelector('.mobile-header');

                    if (aiInput && chatBox && mobileHeader) {
                        if (window.visualViewport) {
                            const updateHeaderPosition = () => {
                                const viewport = window.visualViewport;
                                mobileHeader.style.transform = `translateY(${viewport.offsetTop}px)`;
                            };
                            window.visualViewport.addEventListener('scroll', updateHeaderPosition);
                            window.visualViewport.addEventListener('resize', updateHeaderPosition);
                        }

                        aiInput.addEventListener('focus', function() {
                            setTimeout(() => {
                                chatBox.scrollTop = chatBox.scrollHeight;
                            }, 300);
                        });

                        aiInput.addEventListener('blur', function() {
                            mobileHeader.style.transform = '';
                            setTimeout(() => {
                                window.scrollTo(0, 0);
                            }, 100);
                        });
                    }
                } catch (e) {
                    console.error('Mobile optimization failed:', e);
                }
            }
        };
        
        // ==================== 工作计划管理 ====================
        let currentFilter = 'all';
        
        // 中英文映射
        const statusMap = {
            'pending': '未开始',
            'in_progress': '进行中',
            'completed': '已完成',
            'cancelled': '已取消'
        };
        
        const priorityMap = {
            'low': '低',
            'medium': '中',
            'high': '高',
            'urgent': '紧急'
        };
        
        const priorityIconMap = {
            'low': '🔵',
            'medium': '🟡',
            'high': '🔴',
            'urgent': '🚨'
        };
        
        function openWorkPlans() {
            document.getElementById('workPlansModal').style.display = 'block';
            loadWorkPlans();
            loadWorkRecords();
        }
        
        function closeWorkPlans() {
            document.getElementById('workPlansModal').style.display = 'none';
        }
        
        async function loadWorkPlans() {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/plans', {
                    headers: token ? {'Authorization': 'Bearer ' + token} : {}
                });
                const plans = await response.json();
                displayWorkPlans(plans);
            } catch (e) {
                console.error('加载工作计划失败:', e);
            }
        }
        
        function displayWorkPlans(plans) {
            const container = document.getElementById('workPlansList');
            
            // 根据当前过滤器过滤
            let filteredPlans = plans;
            if (currentFilter !== 'all') {
                filteredPlans = plans.filter(p => p.status === currentFilter);
            }
            
            if (filteredPlans.length === 0) {
                container.innerHTML = '<p style="text-align:center; color:#666; padding:40px;">暂无工作计划</p>';
                return;
            }
            
            container.innerHTML = filteredPlans.map(plan => {
                const priorityIcon = priorityIconMap[plan.priority] || '🟡';
                const statusText = statusMap[plan.status] || plan.status;
                const description = plan.description || plan.content || '';
                
                return `
                    <div class="plan-card">
                        <div class="plan-header">
                            <h4 class="plan-title">${priorityIcon} ${plan.title}</h4>
                            <span class="plan-status status-${statusText.replace(/\\s+/g, '')}">${statusText}</span>
                        </div>
                        ${description ? `<p style="color:#aaa; font-size:14px; margin:8px 0;">${description}</p>` : ''}
                        <div class="plan-meta">
                            ${plan.deadline || plan.due_date ? `<span>⏰ ${plan.deadline || plan.due_date}</span>` : ''}
                            <span>📅 创建: ${plan.created_at ? plan.created_at.substring(0, 10) : ''}</span>
                        </div>
                        <div class="plan-actions">
                            ${plan.status !== 'completed' ? `
                                <button class="plan-btn plan-btn-status" onclick="updatePlanStatus(${plan.id}, 'completed')">
                                    ✅ 标记完成
                                </button>
                            ` : ''}
                            ${plan.status === 'pending' ? `
                                <button class="plan-btn plan-btn-status" onclick="updatePlanStatus(${plan.id}, 'in_progress')">
                                    🔄 开始工作
                                </button>
                            ` : ''}
                            <button class="plan-btn plan-btn-delete" onclick="deleteWorkPlan(${plan.id})">
                                🗑️ 删除
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function filterWorkPlans(status) {
            currentFilter = status;
            
            // 更新按钮状态
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            loadWorkPlans();
        }
        
        async function createWorkPlan() {
            const title = document.getElementById('newPlanTitle').value.trim();
            const description = document.getElementById('newPlanDesc').value.trim();
            const deadline = document.getElementById('newPlanDeadline').value;
            const priority = document.getElementById('newPlanPriority').value;
            const status = document.getElementById('newPlanStatus').value;
            
            if (!title) {
                alert('请输入工作标题');
                return;
            }
            
            try {
                const response = await fetch('/api/plan/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        title,
                        description,
                        deadline: deadline || null,
                        priority,
                        status
                    })
                });
                
                if (response.ok) {
                    // 清空表单
                    document.getElementById('newPlanTitle').value = '';
                    document.getElementById('newPlanDesc').value = '';
                    document.getElementById('newPlanDeadline').value = '';
                    document.getElementById('newPlanPriority').value = 'medium';
                    document.getElementById('newPlanStatus').value = 'pending';
                    
                    // 重新加载列表
                    loadWorkPlans();
                    alert('✅ 工作计划已创建');
                } else {
                    alert('❌ 创建失败');
                }
            } catch (e) {
                console.error('创建工作计划失败:', e);
                alert('❌ 创建失败: ' + e.message);
            }
        }
        
        async function updatePlanStatus(planId, newStatus) {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/plan/update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? {'Authorization': 'Bearer ' + token} : {})
                    },
                    body: JSON.stringify({
                        id: planId,
                        status: newStatus
                    })
                });
                
                if (response.ok) {
                    loadWorkPlans();
                } else {
                    const error = await response.text();
                    console.error('更新失败:', error);
                    alert('❌ 更新失败');
                }
            } catch (e) {
                console.error('更新工作计划失败:', e);
                alert('❌ 更新失败: ' + e.message);
            }
        }
        
        async function deleteWorkPlan(planId) {
            if (!confirm('确定要删除这个工作计划吗？')) {
                return;
            }

            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/plan/delete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? {'Authorization': 'Bearer ' + token} : {})
                    },
                    body: JSON.stringify({id: planId})
                });

                if (response.ok) {
                    loadWorkPlans();
                } else {
                    const error = await response.text();
                    console.error('删除失败:', error);
                    alert('❌ 删除失败');
                }
            } catch (e) {
                console.error('删除工作计划失败:', e);
                alert('❌ 删除失败: ' + e.message);
            }
        }

        // ==================== 工作记录管理 ====================
        function switchWorkTab(tabName) {
            // 隐藏所有标签页
            document.getElementById('plansTabContent').style.display = 'none';
            document.getElementById('recordsTabContent').style.display = 'none';

            // 隐藏所有标签页按钮的下划线
            document.getElementById('plansTab').style.borderBottom = '3px solid transparent';
            document.getElementById('plansTab').style.color = '#999';
            document.getElementById('recordsTab').style.borderBottom = '3px solid transparent';
            document.getElementById('recordsTab').style.color = '#999';

            // 显示选中的标签页
            if (tabName === 'plans') {
                document.getElementById('plansTabContent').style.display = 'block';
                document.getElementById('plansTab').style.borderBottom = '3px solid #007bff';
                document.getElementById('plansTab').style.color = '#007bff';
                loadWorkPlans();
            } else if (tabName === 'records') {
                document.getElementById('recordsTabContent').style.display = 'block';
                document.getElementById('recordsTab').style.borderBottom = '3px solid #007bff';
                document.getElementById('recordsTab').style.color = '#007bff';
                loadWorkRecords();
            }
        }

        async function loadWorkRecords() {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/work-records', {
                    headers: token ? {'Authorization': 'Bearer ' + token} : {}
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                displayWorkRecords(data.records || []);
            } catch (e) {
                console.error('加载工作记录失败:', e);
                const container = document.getElementById('workRecordsList');
                container.innerHTML = '<p style="text-align:center; color:#ff6b6b; padding:20px;">❌ 加载失败: ' + e.message + '</p>';
            }
        }

        function displayWorkRecords(records) {
            const container = document.getElementById('workRecordsList');

            if (!records || records.length === 0) {
                container.innerHTML = '<p style="text-align:center; color:#666; padding:40px;">暂无工作记录</p>';
                return;
            }

            container.innerHTML = records.map(record => `
                <div class="card" style="background:#f0f7ff; border-left:4px solid #007bff; margin-bottom:15px;">
                    <div style="display:flex; justify-content:space-between; align-items:start;">
                        <div style="flex:1;">
                            <div style="color:#007bff; font-size:14px; margin-bottom:8px;">
                                📝 ${record.timestamp}
                                ${record.deadline ? `<span style="margin-left:15px; background:#fff3cd; color:#856404; padding:2px 8px; border-radius:6px; font-size:12px;">⏰ ${record.deadline}</span>` : ''}
                            </div>
                            <div style="color:#333; font-size:15px; line-height:1.6;">
                                ${record.content}
                            </div>
                        </div>
                        <span style="background:#e7f3ff; color:#0056b3; padding:4px 12px; border-radius:12px; font-size:12px; font-weight:600; white-space:nowrap; margin-left:10px;">
                            ✓ ${record.status}
                        </span>
                    </div>
                </div>
            `).join('');
        }

        // ==================== 图片库（批量上传） ====================
        let bulkImages = [];
        
        function openImageGallery() {
            document.getElementById('imageGalleryModal').style.display = 'block';
            loadAllImages();
        }
        
        function closeImageGallery() {
            document.getElementById('imageGalleryModal').style.display = 'none';
        }
        
        function handleBulkImageUpload(event) {
            const files = event.target.files;
            if (!files || files.length === 0) return;
            
            bulkImages = [];
            const listContainer = document.getElementById('bulkImageList');
            listContainer.innerHTML = '';
            document.getElementById('bulkUploadPreview').style.display = 'block';
            document.getElementById('bulkCount').textContent = files.length;
            
            Array.from(files).forEach((file, index) => {
                if (!file.type.startsWith('image/')) {
                    return;
                }
                
                const reader = new FileReader();
                reader.onload = function(e) {
                    bulkImages.push({
                        data: e.target.result,
                        name: file.name
                    });
                    
                    const imgCard = document.createElement('div');
                    imgCard.style.cssText = 'position:relative;';
                    imgCard.innerHTML = `
                        <img src="${e.target.result}" style="width:100%; height:100px; object-fit:cover; border-radius:4px;">
                        <button onclick="removeBulkImage(${index})" style="position:absolute; top:2px; right:2px; width:20px; height:20px; border-radius:50%; background:#dc3545; color:white; border:none; cursor:pointer; font-size:12px; line-height:1;">×</button>
                    `;
                    listContainer.appendChild(imgCard);
                };
                reader.readAsDataURL(file);
            });
        }
        
        function removeBulkImage(index) {
            bulkImages.splice(index, 1);
            document.getElementById('bulkCount').textContent = bulkImages.length;
            
            if (bulkImages.length === 0) {
                document.getElementById('bulkUploadPreview').style.display = 'none';
            } else {
                const listContainer = document.getElementById('bulkImageList');
                listContainer.innerHTML = '';
                bulkImages.forEach((img, idx) => {
                    const imgCard = document.createElement('div');
                    imgCard.style.cssText = 'position:relative;';
                    imgCard.innerHTML = `
                        <img src="${img.data}" style="width:100%; height:100px; object-fit:cover; border-radius:4px;">
                        <button onclick="removeBulkImage(${idx})" style="position:absolute; top:2px; right:2px; width:20px; height:20px; border-radius:50%; background:#dc3545; color:white; border:none; cursor:pointer; font-size:12px; line-height:1;">×</button>
                    `;
                    listContainer.appendChild(imgCard);
                });
            }
        }
        
        async function uploadBulkImages() {
            if (bulkImages.length === 0) {
                alert('请先选择图片！');
                return;
            }
            
            const description = document.getElementById('bulkImageDesc').value.trim();
            const tagsInput = document.getElementById('bulkImageTags').value.trim();
            const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()).filter(t => t) : [];
            
            let successCount = 0;
            let failCount = 0;
            
            const token = localStorage.getItem('token');
            
            for (let i = 0; i < bulkImages.length; i++) {
                try {
                    const response = await fetch('/api/image/upload', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            ...(token ? {'Authorization': 'Bearer ' + token} : {})
                        },
                        body: JSON.stringify({
                            image_data: bulkImages[i].data,
                            original_name: bulkImages[i].name,
                            description: description,
                            tags: tags
                        })
                    });
                    
                    if (response.ok) {
                        successCount++;
                    } else {
                        console.error(`上传失败 ${bulkImages[i].name}:`, response.status, response.statusText);
                        failCount++;
                    }
                } catch (e) {
                    console.error(`上传失败 ${bulkImages[i].name}:`, e);
                    failCount++;
                }
            }
            
            alert(`✅ 上传完成！\n成功: ${successCount} 张\n失败: ${failCount} 张`);
            
            // 清空
            bulkImages = [];
            document.getElementById('bulkUploadPreview').style.display = 'none';
            document.getElementById('bulkImageDesc').value = '';
            document.getElementById('bulkImageTags').value = '';
            document.getElementById('bulkImageUpload').value = '';
            
            // 重新加载图片列表
            loadAllImages();
        }
        
        async function loadAllImages() {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/images', {
                    headers: token ? {'Authorization': 'Bearer ' + token} : {}
                });
                const images = await response.json();
                displayGalleryImages(images);
            } catch (e) {
                console.error('加载图片失败:', e);
            }
        }
        
        async function searchGalleryImages() {
            const desc = document.getElementById('imageSearchDesc').value.trim();
            const tag = document.getElementById('imageSearchTag').value.trim();
            
            if (!desc && !tag) {
                alert('请输入搜索关键词或标签');
                return;
            }
            
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/image/search', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? {'Authorization': 'Bearer ' + token} : {})
                    },
                    body: JSON.stringify({
                        description: desc,
                        tags: tag ? [tag] : []
                    })
                });
                
                if (!response.ok) {
                    throw new Error('搜索失败');
                }
                
                const result = await response.json();
                const images = result.results || result;
                displayGalleryImages(images);
                
                console.log(`搜索完成，找到 ${images.length} 张图片`);
            } catch (e) {
                console.error('搜索图片失败:', e);
                alert('搜索失败: ' + e.message);
            }
        }
        
        function displayGalleryImages(images) {
            console.log('displayGalleryImages called with', images ? images.length : 0, 'images');
            const container = document.getElementById('galleryImagesList');
            const countElem = document.getElementById('imageCount');
            console.log('Container element:', container);

            if (!container) {
                console.error('galleryImagesList container not found!');
                return;
            }

            if (!images || images.length === 0) {
                console.log('No images to display');
                container.innerHTML = '<p style="text-align:center; color:#fff; padding:40px; grid-column: 1/-1; font-size:16px;">📭 暂无图片</p>';
                if (countElem) countElem.textContent = '0';
                return;
            }

            console.log('Displaying', images.length, 'images');
            if (countElem) countElem.textContent = images.length;

            // 按时间排序（最新的在前）
            const sortedImages = [...images].sort((a, b) => {
                const dateA = new Date(a.created_at || a.uploaded_at || 0);
                const dateB = new Date(b.created_at || b.uploaded_at || 0);
                return dateB - dateA; // 降序排列
            });

            // 按年月分组
            const groupedByMonth = {};
            sortedImages.forEach(img => {
                const date = new Date(img.created_at || img.uploaded_at || Date.now());
                const year = date.getFullYear();
                const month = date.getMonth() + 1; // 月份从0开始
                const key = `${year}-${month.toString().padStart(2, '0')}`;

                if (!groupedByMonth[key]) {
                    groupedByMonth[key] = {
                        year: year,
                        month: month,
                        images: []
                    };
                }
                groupedByMonth[key].images.push(img);
            });

            // 生成HTML
            const monthKeys = Object.keys(groupedByMonth).sort().reverse(); // 最新的月份在前

            let html = '';
            monthKeys.forEach(monthKey => {
                const group = groupedByMonth[monthKey];
                const monthName = `${group.year}年${group.month}月`;

                // 月份标题
                html += `
                    <div class="month-group-title" style="grid-column: 1/-1; background:linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%); padding:12px 20px; border-radius:8px; margin:20px 0 15px 0; border-left:4px solid #667eea;">
                        <h4 style="margin:0; color:#fff; font-size:18px; font-weight:600;">📅 ${monthName} (${group.images.length}张)</h4>
                    </div>
                `;

                // 该月份的图片
                html += group.images.map(img => {
                    const imgPath = img.file_path || img.path || '';
                    const tags = Array.isArray(img.tags) ? img.tags.join(', ') : '';
                    const desc = img.description || '';

                    return `
                        <div class="image-card" data-image-id="${img.id}" style="background:linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); border-radius:12px; overflow:hidden; border:2px solid rgba(102, 126, 234, 0.3); transition:all 0.3s; position:relative;"
                             onmouseover="this.style.borderColor='rgba(102, 126, 234, 0.6)'; this.style.transform='scale(1.05)';"
                             onmouseout="this.style.borderColor='rgba(102, 126, 234, 0.3)'; this.style.transform='scale(1)';">
                            <!-- 批量选择复选框 -->
                            <input type="checkbox" class="batch-checkbox" data-id="${img.id}"
                                   onchange="updateBatchSelection()"
                                   style="display:none; position:absolute; top:8px; left:8px; width:24px; height:24px; cursor:pointer; z-index:5;
                                          accent-color:#667eea; transform:scale(1.5);">

                            <div onclick="handleImageClick(${img.id}, event)" style="cursor:pointer;">
                                <img src="/ai/${imgPath}" style="width:100%; height:150px; object-fit:cover; background:#1a1a1a;" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22150%22 height=%22150%22><rect fill=%22%23333%22 width=%22150%22 height=%22150%22/><text x=%2250%25%22 y=%2250%25%22 fill=%22%23999%22 text-anchor=%22middle%22 dy=%22.3em%22>图片加载失败</text></svg>'">
                                <div style="padding:12px; background:rgba(0,0,0,0.4);">
                                    <div style="font-size:13px; color:#fff; margin-bottom:6px; font-weight:600;">${img.original_name || img.filename || ''}</div>
                                    ${desc ? `<div style="font-size:12px; color:#ddd; margin-bottom:4px;">📝 ${desc}</div>` : ''}
                                    ${tags ? `<div style="font-size:11px; color:#667eea; margin-top:4px;">🏷️ ${tags}</div>` : ''}
                                </div>
                            </div>
                            <button class="single-delete-btn" onclick="event.stopPropagation(); deleteImage(${img.id})"
                                    style="position:absolute; top:8px; right:8px; background:rgba(220,53,69,0.9); color:white; border:none; border-radius:50%; width:32px; height:32px; cursor:pointer; font-size:16px; display:flex; align-items:center; justify-content:center; box-shadow:0 2px 8px rgba(0,0,0,0.3); transition:all 0.2s;"
                                    onmouseover="this.style.background='rgba(220,53,69,1)'; this.style.transform='scale(1.1)';"
                                    onmouseout="this.style.background='rgba(220,53,69,0.9)'; this.style.transform='scale(1)';"
                                    title="删除图片">
                                🗑️
                            </button>
                        </div>
                    `;
                }).join('');
            });

            container.innerHTML = html;
            console.log('Images displayed successfully with month grouping');
        }
        
        // 全局变量存储当前查看的图片
        let currentViewImage = null;
        let allImagesData = [];
        let batchMode = false;
        let selectedImageIds = new Set();
        
        // 批量选择模式切换
        function toggleBatchMode() {
            batchMode = !batchMode;
            const checkboxes = document.querySelectorAll('.batch-checkbox');
            const deleteButtons = document.querySelectorAll('.single-delete-btn');
            const batchModeBtn = document.getElementById('batchModeBtn');
            const batchDeleteBtn = document.getElementById('batchDeleteBtn');
            
            if (batchMode) {
                // 进入批量模式
                checkboxes.forEach(cb => cb.style.display = 'block');
                deleteButtons.forEach(btn => btn.style.display = 'none');
                batchModeBtn.style.background = '#667eea';
                batchModeBtn.innerHTML = '✅ 完成选择';
                batchDeleteBtn.style.display = 'inline-block';
            } else {
                // 退出批量模式
                checkboxes.forEach(cb => {
                    cb.style.display = 'none';
                    cb.checked = false;
                });
                deleteButtons.forEach(btn => btn.style.display = 'flex');
                batchModeBtn.style.background = '#6c757d';
                batchModeBtn.innerHTML = '☑️ 批量选择';
                batchDeleteBtn.style.display = 'none';
                selectedImageIds.clear();
                updateBatchSelection();
            }
        }
        
        // 更新批量选择状态
        function updateBatchSelection() {
            const checkboxes = document.querySelectorAll('.batch-checkbox:checked');
            selectedImageIds.clear();
            checkboxes.forEach(cb => selectedImageIds.add(parseInt(cb.dataset.id)));
            
            const selectedCount = document.getElementById('selectedCount');
            if (selectedCount) {
                selectedCount.textContent = selectedImageIds.size;
            }
            
            // 更新选中图片的边框
            document.querySelectorAll('.image-card').forEach(card => {
                const id = parseInt(card.dataset.imageId);
                if (selectedImageIds.has(id)) {
                    card.style.borderColor = '#667eea';
                    card.style.borderWidth = '3px';
                } else {
                    card.style.borderColor = 'rgba(102, 126, 234, 0.3)';
                    card.style.borderWidth = '2px';
                }
            });
        }
        
        // 批量删除图片
        async function batchDeleteImages() {
            if (selectedImageIds.size === 0) {
                alert('请先选择要删除的图片');
                return;
            }
            
            if (!confirm(`确定要删除选中的 ${selectedImageIds.size} 张图片吗？\n\n⚠️ 此操作不可恢复！`)) {
                return;
            }
            
            const ids = Array.from(selectedImageIds);
            let successCount = 0;
            let failCount = 0;
            
            console.log('Batch deleting images:', ids);
            
            for (let id of ids) {
                try {
                    const token = localStorage.getItem('token');
                    const response = await fetch(`/api/image/${id}`, {
                        method: 'DELETE',
                        headers: token ? {'Authorization': 'Bearer ' + token} : {}
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        successCount++;
                        console.log(`✅ Deleted image ${id}`);
                    } else {
                        failCount++;
                        console.error(`❌ Failed to delete image ${id}:`, result.message);
                    }
                } catch (error) {
                    failCount++;
                    console.error(`❌ Error deleting image ${id}:`, error);
                }
            }
            
            alert(`批量删除完成！\n✅ 成功: ${successCount} 张\n❌ 失败: ${failCount} 张`);
            
            // 退出批量模式并刷新列表
            toggleBatchMode();
            loadAllImages();
        }
        
        // 处理图片点击（批量模式下选择，普通模式下查看）
        function handleImageClick(id, event) {
            if (batchMode) {
                // 批量模式：切换复选框
                const card = event.currentTarget.closest('.image-card');
                const checkbox = card.querySelector('.batch-checkbox');
                if (checkbox) {
                    checkbox.checked = !checkbox.checked;
                    updateBatchSelection();
                }
            } else {
                // 普通模式：查看大图
                viewGalleryImage(id);
            }
        }
        
        async function viewGalleryImage(id) {
            try {
                console.log('Opening image view for ID:', id);
                const token = localStorage.getItem('token');
                const response = await fetch(`/api/image/${id}`, {
                    headers: token ? {'Authorization': 'Bearer ' + token} : {}
                });
                
                console.log('Fetch response status:', response.status);
                
                if (!response.ok) {
                    throw new Error('获取图片信息失败');
                }
                
                const data = await response.json();
                console.log('Image data received:', data);
                currentViewImage = data;
                console.log('currentViewImage set to:', currentViewImage);
                
                // 显示图片
                const imgPath = data.file_path || data.path || '';
                const fullPath = imgPath.startsWith('/') ? '/ai' + imgPath : '/ai/' + imgPath;
                document.getElementById('viewImageSrc').src = fullPath;
                
                // 显示信息
                document.getElementById('viewImageName').textContent = data.original_name || data.filename || '未命名';
                document.getElementById('viewImageDesc').textContent = data.description ? `📝 ${data.description}` : '';
                
                const tags = Array.isArray(data.tags) ? data.tags.join(', ') : (data.tags || '');
                document.getElementById('viewImageTags').textContent = tags ? `🏷️ ${tags}` : '';
                
                const uploadTime = data.created_at || data.upload_time || '';
                const fileSize = data.file_size ? `${(data.file_size / 1024).toFixed(2)} KB` : '';
                document.getElementById('viewImageMeta').innerHTML = `
                    ${uploadTime ? `⏰ ${uploadTime}` : ''}
                    ${fileSize ? ` | 📦 ${fileSize}` : ''}
                `;
                
                // 显示模态框
                document.getElementById('imageViewModal').style.display = 'block';
            } catch (error) {
                console.error('查看图片失败:', error);
                alert('查看图片失败: ' + error.message);
            }
        }
        
        function closeImageView() {
            document.getElementById('imageViewModal').style.display = 'none';
            currentViewImage = null;
        }
        
        function closeImageViewIfBackdrop(event) {
            if (event.target.id === 'imageViewModal') {
                closeImageView();
            }
        }
        
        async function deleteImage(id, skipConfirm = false) {
            // skipConfirm参数：如果已经在调用方确认过，则跳过二次确认
            if (!skipConfirm && !confirm('确定要删除这张图片吗？')) {
                console.log('Delete cancelled by user');
                return;
            }
            
            console.log('=== Starting delete process ===');
            console.log('Image ID:', id);
            console.log('Skip confirm:', skipConfirm);
            
            try {
                const token = localStorage.getItem('token');
                console.log('Token exists:', !!token);
                console.log('Token value:', token ? token.substring(0, 20) + '...' : 'null');
                
                if (!token) {
                    alert('⚠️ 未登录，请先登录');
                    window.location.href = '/ai/login';
                    return;
                }
                
                console.log(`Sending DELETE request to /api/image/${id}`);
                
                const response = await fetch(`/api/image/${id}`, {
                    method: 'DELETE',
                    headers: {'Authorization': 'Bearer ' + token}
                });
                
                console.log('Response received');
                console.log('Status:', response.status);
                console.log('Status text:', response.statusText);
                console.log('OK:', response.ok);
                
                const responseText = await response.text();
                console.log('Response body:', responseText);
                
                let result;
                try {
                    result = JSON.parse(responseText);
                } catch (e) {
                    console.error('Failed to parse JSON:', e);
                    throw new Error('服务器响应格式错误');
                }
                
                console.log('Parsed result:', result);
                
                if (!response.ok) {
                    if (response.status === 401) {
                        alert('⚠️ 登录已过期，请重新登录');
                        window.location.href = '/ai/login';
                        return;
                    }
                    throw new Error(result.message || `删除失败 (HTTP ${response.status})`);
                }
                
                if (result.success) {
                    console.log('✅ Delete successful!');
                    alert('✅ 删除成功！');
                    loadAllImages(); // 重新加载列表
                } else {
                    console.error('❌ Delete failed:', result.message);
                    throw new Error(result.message || '删除失败');
                }
            } catch (error) {
                console.error('=== Delete error ===');
                console.error('Error type:', error.name);
                console.error('Error message:', error.message);
                console.error('Error stack:', error.stack);
                alert('❌ 删除图片失败: ' + error.message);
            } finally {
                console.log('=== Delete process completed ===');
            }
        }
        
        function deleteCurrentImage() {
            if (currentViewImage && currentViewImage.id) {
                closeImageView();
                deleteImage(currentViewImage.id);
            }
        }
        
        function handleDeleteCurrent(event) {
            event.preventDefault();
            event.stopPropagation();
            console.log('Delete button clicked, current image:', currentViewImage);
            
            if (currentViewImage && currentViewImage.id) {
                if (confirm('确定要删除这张图片吗？')) {
                    console.log('User confirmed deletion');
                    const imageId = currentViewImage.id; // ✅ 先保存ID
                    closeImageView(); // 关闭窗口（会清空currentViewImage）
                    deleteImage(imageId, true); // ✅ 使用保存的ID
                } else {
                    console.log('User cancelled deletion');
                }
            } else {
                console.error('No current image to delete');
                alert('没有选中的图片');
            }
            return false;
        }
        
        function downloadImage() {
            if (currentViewImage) {
                const imgPath = currentViewImage.file_path || currentViewImage.path || '';
                const fullPath = imgPath.startsWith('/') ? '/ai' + imgPath : '/ai/' + imgPath;
                const filename = currentViewImage.original_name || currentViewImage.filename || 'image.jpg';
                
                // 创建下载链接
                const a = document.createElement('a');
                a.href = fullPath;
                a.download = filename;
                a.click();
            }
        }
        
        function handleDownload(event) {
            event.preventDefault();
            event.stopPropagation();
            console.log('Download button clicked');
            downloadImage();
            return false;
        }
    </script>
</body>
</html>'''
    
    def get_image_gallery_template(self):
        """获取图片管理页面模板"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, viewport-fit=cover, interactive-widget=resizes-visual">
    <title>🖼️ 图片管理 - 个人助手</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 36px;
            margin-bottom: 10px;
        }
        
        .back-link {
            display: inline-block;
            padding: 10px 20px;
            background: rgba(255,255,255,0.1);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            margin-top: 15px;
            transition: all 0.3s;
        }
        
        .back-link:hover {
            background: rgba(255,255,255,0.2);
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        
        .toolbar {
            display: flex;
            gap: 15px;
            margin-bottom: 25px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .toolbar input[type="file"] {
            display: none;
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 15px;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn-success {
            background: #28a745;
            color: white;
        }
        
        .btn-success:hover {
            background: #218838;
        }
        
        .search-box {
            flex: 1;
            min-width: 200px;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
        }
        
        .search-box:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .upload-preview {
            display: none;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 25px;
            border: 2px dashed #667eea;
        }
        
        .upload-preview.active {
            display: block;
        }
        
        .preview-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .preview-item {
            position: relative;
            aspect-ratio: 1;
            border-radius: 8px;
            overflow: hidden;
            background: #e0e0e0;
        }
        
        .preview-item img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .preview-item .remove {
            position: absolute;
            top: 5px;
            right: 5px;
            width: 24px;
            height: 24px;
            background: rgba(255,0,0,0.8);
            color: white;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            font-size: 14px;
        }
        
        .upload-controls {
            display: flex;
            gap: 10px;
        }
        
        .upload-controls input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        
        .stats {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 15px;
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            border-radius: 10px;
        }
        
        .stats-item {
            text-align: center;
        }
        
        .stats-item .number {
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
        }
        
        .stats-item .label {
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }
        
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 25px;
        }
        
        .image-card {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transition: all 0.3s;
            border: 1px solid #e0e0e0;
        }
        
        .image-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        .image-card .image-wrapper {
            position: relative;
            aspect-ratio: 4/3;
            background: #f0f0f0;
            overflow: hidden;
        }
        
        .image-card img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s;
        }
        
        .image-card:hover img {
            transform: scale(1.05);
        }
        
        .image-card .info {
            padding: 15px;
        }
        
        .image-card .filename {
            font-size: 14px;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .image-card .description {
            font-size: 13px;
            color: #666;
            margin-bottom: 8px;
            line-height: 1.4;
            max-height: 40px;
            overflow: hidden;
        }
        
        .image-card .tags {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 12px;
        }
        
        .tag {
            padding: 4px 10px;
            background: #e3f2fd;
            color: #1976d2;
            font-size: 12px;
            border-radius: 12px;
        }
        
        .image-card .meta {
            font-size: 11px;
            color: #999;
            margin-bottom: 12px;
        }
        
        .image-card .actions {
            display: flex;
            gap: 8px;
        }
        
        .image-card .actions button {
            flex: 1;
            padding: 8px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }
        
        .btn-view {
            background: #667eea;
            color: white;
        }
        
        .btn-view:hover {
            background: #5568d3;
        }
        
        .btn-delete {
            background: #ff4444;
            color: white;
        }
        
        .btn-delete:hover {
            background: #cc0000;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
        
        .empty-state svg {
            width: 120px;
            height: 120px;
            margin-bottom: 20px;
            opacity: 0.3;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        
        .modal.active {
            display: flex;
        }
        
        .modal-content {
            background: white;
            border-radius: 12px;
            max-width: 90%;
            max-height: 90%;
            overflow: auto;
            position: relative;
        }
        
        .modal-content img {
            max-width: 100%;
            display: block;
        }
        
        .modal-close {
            position: absolute;
            top: 15px;
            right: 15px;
            width: 40px;
            height: 40px;
            background: rgba(0,0,0,0.6);
            color: white;
            border: none;
            border-radius: 50%;
            font-size: 24px;
            cursor: pointer;
            z-index: 1;
        }
        
        .modal-info {
            padding: 20px;
            background: white;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🖼️ 图片管理中心</h1>
        <a href="/" class="back-link">← 返回主页</a>
    </div>
    
    <div class="container">
        <!-- 工具栏 -->
        <div class="toolbar">
            <input type="file" id="bulkUpload" accept="image/*" multiple>
            <button class="btn btn-primary" onclick="document.getElementById('bulkUpload').click()">
                📤 批量上传图片
            </button>
            <input type="text" id="searchKeyword" class="search-box" placeholder="搜索描述或文件名...">
            <input type="text" id="searchTag" class="search-box" placeholder="搜索标签...">
            <button class="btn btn-primary" onclick="searchImages()">🔍 搜索</button>
            <button class="btn" onclick="loadAllImages()">📋 显示全部</button>
        </div>
        
        <!-- 批量上传预览 -->
        <div id="uploadPreview" class="upload-preview">
            <h3 style="margin-bottom: 15px;">📤 准备上传的图片</h3>
            <div id="previewGrid" class="preview-grid"></div>
            <div class="upload-controls">
                <input type="text" id="bulkDesc" placeholder="图片描述（可选）">
                <input type="text" id="bulkTags" placeholder="标签（用逗号分隔）">
                <button class="btn btn-success" onclick="uploadBulkImages()">
                    ✅ 开始上传 (<span id="uploadCount">0</span> 张)
                </button>
            </div>
        </div>
        
        <!-- 统计信息 -->
        <div class="stats">
            <div class="stats-item">
                <div class="number" id="totalImages">0</div>
                <div class="label">总图片数</div>
            </div>
            <div class="stats-item">
                <div class="number" id="totalSize">0 MB</div>
                <div class="label">总大小</div>
            </div>
            <div class="stats-item">
                <div class="number" id="todayUploads">0</div>
                <div class="label">今日上传</div>
            </div>
        </div>
        
        <!-- 图片画廊 -->
        <div id="gallery" class="gallery">
            <div class="loading">正在加载图片...</div>
        </div>
    </div>
    
    <!-- 查看大图模态框 -->
    <div id="viewModal" class="modal">
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <img id="modalImage" src="">
            <div class="modal-info">
                <h3 id="modalFilename"></h3>
                <p id="modalDescription"></p>
                <div id="modalTags"></div>
                <p id="modalMeta"></p>
            </div>
        </div>
    </div>
    
    <script>
        let selectedFiles = [];
        let allImages = [];
        
        // 页面加载时获取所有图片
        window.onload = function() {
            loadAllImages();
        };
        
        // 监听文件选择
        document.getElementById('bulkUpload').addEventListener('change', function(e) {
            selectedFiles = Array.from(e.target.files);
            if (selectedFiles.length > 0) {
                showUploadPreview();
            }
        });
        
        // 显示上传预览
        function showUploadPreview() {
            const preview = document.getElementById('uploadPreview');
            const grid = document.getElementById('previewGrid');
            const count = document.getElementById('uploadCount');
            
            grid.innerHTML = '';
            selectedFiles.forEach((file, index) => {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const item = document.createElement('div');
                    item.className = 'preview-item';
                    item.innerHTML = `
                        <img src="${e.target.result}">
                        <button class="remove" onclick="removeFile(${index})">×</button>
                    `;
                    grid.appendChild(item);
                };
                reader.readAsDataURL(file);
            });
            
            count.textContent = selectedFiles.length;
            preview.classList.add('active');
        }
        
        // 移除文件
        function removeFile(index) {
            selectedFiles.splice(index, 1);
            if (selectedFiles.length === 0) {
                document.getElementById('uploadPreview').classList.remove('active');
            } else {
                showUploadPreview();
            }
        }
        
        // 批量上传
        async function uploadBulkImages() {
            const description = document.getElementById('bulkDesc').value;
            const tags = document.getElementById('bulkTags').value;

            const token = localStorage.getItem('token');

            for (let i = 0; i < selectedFiles.length; i++) {
                const file = selectedFiles[i];
                const reader = new FileReader();

                reader.onload = async function(e) {
                    const base64 = e.target.result.split(',')[1];
                    try {
                        const response = await fetch('/api/image/upload', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                ...(token ? {'Authorization': 'Bearer ' + token} : {})
                            },
                            body: JSON.stringify({
                                image: base64,
                                filename: file.name,
                                description: description,
                                tags: tags
                            })
                        });

                        const result = await response.json();
                        if (result.success) {
                            console.log(`上传成功: ${file.name}`);
                        }

                        // 最后一张上传完成后刷新
                        if (i === selectedFiles.length - 1) {
                            setTimeout(() => {
                                loadAllImages();
                                document.getElementById('uploadPreview').classList.remove('active');
                                selectedFiles = [];
                                document.getElementById('bulkDesc').value = '';
                                document.getElementById('bulkTags').value = '';
                                alert('✅ 批量上传完成！');
                            }, 500);
                        }
                    } catch (error) {
                        console.error('上传失败:', error);
                    }
                };

                reader.readAsDataURL(file);
            }
        }
        
        // 加载所有图片
        async function loadAllImages() {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/images', {
                    headers: token ? {'Authorization': 'Bearer ' + token} : {}
                });
                allImages = await response.json();
                displayImages(allImages);
                updateStats(allImages);
            } catch (error) {
                console.error('加载图片失败:', error);
                document.getElementById('gallery').innerHTML = '<div class="empty-state"><p>加载失败，请刷新重试</p></div>';
            }
        }
        
        // 搜索图片
        async function searchImages() {
            const keyword = document.getElementById('searchKeyword').value;
            const tag = document.getElementById('searchTag').value;

            if (!keyword && !tag) {
                loadAllImages();
                return;
            }

            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/image/search', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? {'Authorization': 'Bearer ' + token} : {})
                    },
                    body: JSON.stringify({ keyword, tag })
                });
                const data = await response.json();
                displayImages(data.results || data);
            } catch (error) {
                console.error('搜索失败:', error);
            }
        }
        
        // 显示图片
        function displayImages(images) {
            const gallery = document.getElementById('gallery');
            
            if (!images || images.length === 0) {
                gallery.innerHTML = `
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" fill="currentColor">
                            <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/>
                        </svg>
                        <h3>暂无图片</h3>
                        <p>点击上方按钮上传图片</p>
                    </div>
                `;
                return;
            }
            
            gallery.innerHTML = images.map(img => {
                const tagsHtml = (img.tags && typeof img.tags === 'string') ? img.tags.split(',').map(tag => 
                    `<span class="tag">${tag.trim()}</span>`
                ).join('') : '';
                
                const fileSize = img.file_size ? formatFileSize(img.file_size) : '未知';
                const uploadTime = img.created_at || '未知时间';
                
                return `
                    <div class="image-card">
                        <div class="image-wrapper">
                            <img src="/${img.file_path}" alt="${img.original_name || img.filename}">
                        </div>
                        <div class="info">
                            <div class="filename" title="${img.original_name || img.filename}">
                                ${img.original_name || img.filename}
                            </div>
                            ${img.description ? `<div class="description">${img.description}</div>` : ''}
                            ${tagsHtml ? `<div class="tags">${tagsHtml}</div>` : ''}
                            <div class="meta">
                                📅 ${uploadTime.split(' ')[0]} | 💾 ${fileSize}
                            </div>
                            <div class="actions">
                                <button class="btn-view" onclick="viewImage(${img.id})">👁️ 查看</button>
                                <button class="btn-delete" onclick="deleteImage(${img.id})">🗑️ 删除</button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        // 更新统计信息
        function updateStats(images) {
            document.getElementById('totalImages').textContent = images.length;
            
            const totalSize = images.reduce((sum, img) => sum + (img.file_size || 0), 0);
            document.getElementById('totalSize').textContent = formatFileSize(totalSize);
            
            const today = new Date().toISOString().split('T')[0];
            const todayCount = images.filter(img => 
                img.created_at && img.created_at.startsWith(today)
            ).length;
            document.getElementById('todayUploads').textContent = todayCount;
        }
        
        // 格式化文件大小
        function formatFileSize(bytes) {
            if (!bytes) return '0 B';
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }
        
        // 查看大图
        function viewImage(id) {
            const img = allImages.find(i => i.id === id);
            if (!img) return;
            
            document.getElementById('modalImage').src = '/' + img.file_path;
            document.getElementById('modalFilename').textContent = img.original_name || img.filename;
            document.getElementById('modalDescription').textContent = img.description || '无描述';
            
            const tagsHtml = (img.tags && typeof img.tags === 'string') ? img.tags.split(',').map(tag => 
                `<span class="tag">${tag.trim()}</span>`
            ).join('') : '无标签';
            document.getElementById('modalTags').innerHTML = tagsHtml;
            
            const fileSize = formatFileSize(img.file_size);
            document.getElementById('modalMeta').textContent = 
                `上传时间: ${img.created_at || '未知'} | 文件大小: ${fileSize}`;
            
            document.getElementById('viewModal').classList.add('active');
        }
        
        // 关闭模态框
        function closeModal() {
            document.getElementById('viewModal').classList.remove('active');
        }
        
        // 删除图片
        async function deleteImage(id) {
            if (!confirm('确定要删除这张图片吗？')) return;

            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/image/delete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? {'Authorization': 'Bearer ' + token} : {})
                    },
                    body: JSON.stringify({ id })
                });

                const result = await response.json();
                if (result.success) {
                    loadAllImages();
                } else {
                    alert('删除失败：' + result.message);
                }
            } catch (error) {
                console.error('删除失败:', error);
                alert('删除失败，请重试');
            }
        }
        
        // 按Esc关闭模态框
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeModal();
            }
        });
    </script>
</body>
</html>'''
    
    def log_message(self, format, *args):
        """日志"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format%args}")

def run_server(port=8000):
    """运行服务器"""
    reminder_sys.start_monitoring()

    # 初始化提醒调度器
    scheduler = get_global_scheduler(db_manager=db_manager)
    scheduler.start()

    server = HTTPServer(('', port), AssistantHandler)

    print(f"\n{'='*60}")
    print(f"🤖 个人助手系统 - Web版")
    print(f"{'='*60}")
    print(f"\n✅ 服务器已启动: http://localhost:{port}")
    print(f"✅ 提醒调度器已启动（30秒检查间隔）")
    print(f"\n💡 按 Ctrl+C 停止")
    print(f"{'='*60}\n")

    threading.Timer(1.0, lambda: webbrowser.open(f'http://localhost:{port}')).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n关闭中...")
        reminder_sys.stop_monitoring()
        scheduler.stop()
        server.shutdown()

if __name__ == '__main__':
    run_server()
