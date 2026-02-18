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
import subprocess
from datetime import datetime, timedelta
from email import message_from_bytes
from io import BytesIO
from decimal import Decimal

# 初始化数据库和管理器
from mysql_manager import MySQLManager, DeviceTokenManager
from ai_chat_assistant import AIAssistant
from user_manager import UserManager
from notification_service import get_notification_service, get_notification_queue
from reminder_scheduler import get_global_scheduler
from verification_service import get_verification_manager
from fcm_push_service import get_fcm_service
from category_system import (
    CategoryManager,
    WorkTaskManager,
    FinanceManager,
    AccountManager,
    DailyRecordManager
)
from command_system import get_command_router
from friendship_manager import FriendshipManager
from private_message_manager import PrivateMessageManager
from shared_content_manager import SharedContentManager
from guestbook_manager import GuestbookManager

db_manager = MySQLManager('mysql_config.json')
ai_assistant = AIAssistant()
user_manager = UserManager(db_manager)
verification_manager = get_verification_manager(db_manager)
friendship_manager = FriendshipManager(db_manager)
private_message_manager = PrivateMessageManager(db_manager, friendship_manager)
shared_content_manager = SharedContentManager(db_manager, friendship_manager)
guestbook_manager = GuestbookManager(db_manager, friendship_manager)

# 初始化FCM推送服务和设备Token管理器
device_token_manager = DeviceTokenManager(db_manager)
fcm_service = get_fcm_service()

# 从AI助手获取管理器
memory = ai_assistant.memory
reminder_sys = ai_assistant.reminder
image_manager = ai_assistant.image_manager
file_manager = ai_assistant.file_manager
planner = ai_assistant.planner

# 初始化类别系统管理器
category_manager = CategoryManager()
work_task_manager = WorkTaskManager()
finance_manager = FinanceManager()
account_manager = AccountManager()
daily_record_manager = DailyRecordManager()

def extract_video_thumbnail(video_path, thumbnail_path, size="200x200"):
    """提取视频第一帧作为缩略图

    Args:
        video_path: 视频文件路径
        thumbnail_path: 缩略图保存路径
        size: 缩略图尺寸，默认 200x200

    Returns:
        bool: 成功返回 True，失败返回 False
    """
    try:
        # 确保缩略图目录存在
        thumbnail_dir = os.path.dirname(thumbnail_path)
        if not os.path.exists(thumbnail_dir):
            os.makedirs(thumbnail_dir, exist_ok=True)

        # 使用 FFmpeg 提取视频第一帧
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', '00:00:01',
            '-vframes', '1',
            '-vf', f'scale={size}',
            '-y',  # 覆盖已存在的文件
            thumbnail_path
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30  # 30秒超时
        )

        if result.returncode == 0 and os.path.exists(thumbnail_path):
            print(f"✅ 视频缩略图生成成功: {thumbnail_path}")
            return True
        else:
            print(f"❌ 视频缩略图生成失败: {result.stderr.decode('utf-8', errors='ignore')}")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ 视频缩略图生成超时: {video_path}")
        return False
    except FileNotFoundError:
        print("❌ FFmpeg 未安装，无法生成视频缩略图。请安装: brew install ffmpeg")
        return False
    except Exception as e:
        print(f"❌ 视频缩略图生成异常: {e}")
        return False

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
        elif self.path.startswith('/uploads/'):
            # 提供静态文件服务（图片、视频、文件等）
            try:
                # 移除开头的斜杠，获取相对路径
                file_path = self.path[1:]  # 去掉开头的 /

                # 安全检查：防止路径遍历攻击
                if '..' in file_path:
                    self.send_error(403, 'Forbidden')
                    return

                # 检查文件是否存在
                if not os.path.exists(file_path):
                    self.send_error(404, 'File not found')
                    return

                # 根据文件扩展名确定 Content-Type
                import mimetypes
                content_type, _ = mimetypes.guess_type(file_path)
                if content_type is None:
                    content_type = 'application/octet-stream'

                # 读取并发送文件
                with open(file_path, 'rb') as f:
                    file_content = f.read()

                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.send_header('Content-Length', len(file_content))
                self.send_header('Cache-Control', 'public, max-age=31536000')  # 缓存1年
                self.end_headers()
                self.wfile.write(file_content)
            except Exception as e:
                print(f"❌ 提供静态文件失败: {e}")
                self.send_error(500, f'Internal server error: {e}')
        elif self.path.startswith('/mobile_ui_patch.css'):
            # 提供手机端CSS补丁
            try:
                with open('mobile_ui_patch.css', 'r', encoding='utf-8') as f:
                    css_content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/css; charset=utf-8')
                self.send_header('Cache-Control', 'no-cache, must-revalidate')  # 禁用缓存
                self.end_headers()
                self.wfile.write(css_content.encode('utf-8'))
            except Exception as e:
                self.send_error(404, f'CSS file not found: {e}')
        elif self.path.endswith('.html') and self.path not in ['/', '/index.html', '/login.html', '/image-gallery.html', '/social.html']:
            # 提供HTML文件服务（隐私政策、用户协议等）
            try:
                file_path = self.path[1:]  # 去掉开头的 /
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    self.wfile.write(html_content.encode('utf-8'))
                else:
                    self.send_error(404, 'File not found')
            except Exception as e:
                print(f'❌ 提供HTML文件失败: {e}')
                self.send_error(500, f'Internal server error: {e}')
        elif self.path == '/login' or self.path == '/login.html':
            self.send_login_html()
        elif self.path == '/image-gallery' or self.path == '/image-gallery.html':
            # 图片库也允许加载，前端会检查Token
            self.send_image_gallery_html()
        elif self.path == '/social' or self.path == '/social.html' or self.path.startswith('/social?'):
            # 社交中心页面，前端会检查Token（支持带查询参数的URL）
            self.send_social_html()
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

            # ✨ 按优先级排序：紧急 > 重要 > 普通（与命令处理保持一致）
            from command_system import sort_by_priority
            plans = sort_by_priority(plans)

            self.send_json(plans)
        elif self.path == '/api/categories':
            # 获取所有类别树（包含子类别）
            user_id = self.require_auth()
            if user_id is None:
                return
            try:
                tree = category_manager.get_category_tree(user_id=user_id)
                self.send_json({'success': True, 'categories': tree})
            except Exception as e:
                print(f"❌ 获取类别树失败: {e}")
                self.send_json({'success': False, 'error': str(e)})
        elif self.path == '/api/work-tasks/grouped':
            # 获取按子类别分组的工作任务
            user_id = self.require_auth()
            if user_id is None:
                return
            try:
                # 获取所有任务
                all_tasks = work_task_manager.list_tasks(user_id=user_id)

                # 获取工作类别的所有子类别
                work_category = category_manager.get_category_by_code('work')
                if not work_category:
                    self.send_json({'success': False, 'error': '工作类别不存在'})
                    return

                subcategories = category_manager.get_subcategories(work_category['id'], user_id=user_id)

                # 按子类别分组
                groups = []
                subcategory_map = {sub['id']: sub for sub in subcategories}

                # 先添加有子类别的任务组
                for subcategory in subcategories:
                    tasks_in_sub = [t for t in all_tasks if t.get('subcategory_id') == subcategory['id']]
                    if tasks_in_sub:  # 只显示有内容的分组
                        groups.append({
                            'subcategory_id': subcategory['id'],
                            'subcategory_name': subcategory['name'],
                            'items': tasks_in_sub
                        })

                # 添加未分类的任务
                uncategorized_tasks = [t for t in all_tasks if not t.get('subcategory_id')]
                if uncategorized_tasks:
                    groups.append({
                        'subcategory_id': None,
                        'subcategory_name': '未分类',
                        'items': uncategorized_tasks
                    })

                self.send_json({'success': True, 'groups': groups})
            except Exception as e:
                print(f"❌ 获取分组任务失败: {e}")
                import traceback
                traceback.print_exc()
                self.send_json({'success': False, 'error': str(e)})
        elif self.path.startswith('/api/work-tasks'):
            # 获取工作任务列表（支持status过滤）
            user_id = self.require_auth()
            if user_id is None:
                return
            try:
                # 从查询参数获取status
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(self.path)
                query_params = parse_qs(parsed.query) if parsed.query else {}
                status = query_params.get('status', [None])[0]

                tasks = work_task_manager.list_tasks(user_id=user_id, status=status)

                # ✨ 按优先级排序：紧急 > 重要 > 普通（与命令处理保持一致）
                from command_system import sort_by_priority
                tasks = sort_by_priority(tasks)

                self.send_json(tasks)
            except Exception as e:
                print(f"❌ 获取任务列表失败: {e}")
                self.send_json({'success': False, 'error': str(e)})
        elif self.path.startswith('/api/records'):
            # 获取记录列表（支持subcategory_name和status过滤）
            user_id = self.require_auth()
            if user_id is None:
                return
            try:
                # 从查询参数获取subcategory_name和status
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(self.path)
                query_params = parse_qs(parsed.query) if parsed.query else {}
                subcategory_name = query_params.get('subcategory_name', [None])[0]
                status = query_params.get('status', [None])[0]

                if not subcategory_name:
                    self.send_json({'success': False, 'error': '缺少subcategory_name参数'})
                    return

                # 查找子类别ID
                query = "SELECT id FROM subcategories WHERE name = %s LIMIT 1"
                result = db_manager.query(query, (subcategory_name,))
                if not result:
                    self.send_json([])  # 子类别不存在，返回空列表
                    return

                subcategory_id = result[0]['id']

                # 获取记录列表
                # 当status不指定时，返回所有记录（已完成+未完成），前端自行过滤
                records = daily_record_manager.list_records(
                    user_id=user_id,
                    subcategory_id=subcategory_id,
                    status=status
                )

                # ✨ 按优先级排序：紧急 > 重要 > 普通（与命令处理保持一致）
                from command_system import sort_by_priority
                records = sort_by_priority(records)

                self.send_json(records)
            except Exception as e:
                print(f"❌ 获取记录列表失败: {e}")
                import traceback
                traceback.print_exc()
                self.send_json({'success': False, 'error': str(e)})
        elif self.path == '/api/finance-records/grouped':
            # 获取按子类别分组的财务记录
            user_id = self.require_auth()
            if user_id is None:
                return
            try:
                # 获取所有财务记录
                all_records = finance_manager.list_records(user_id=user_id)

                # 获取财务类别的所有子类别
                finance_category = category_manager.get_category_by_code('finance')
                if not finance_category:
                    self.send_json({'success': False, 'error': '财务类别不存在'})
                    return

                subcategories = category_manager.get_subcategories(finance_category['id'], user_id=user_id)

                # 按子类别分组
                groups = []
                for subcategory in subcategories:
                    records_in_sub = [r for r in all_records if r.get('subcategory_id') == subcategory['id']]
                    if records_in_sub:
                        groups.append({
                            'subcategory_id': subcategory['id'],
                            'subcategory_name': subcategory['name'],
                            'items': records_in_sub
                        })

                # 添加未分类的记录
                uncategorized = [r for r in all_records if not r.get('subcategory_id')]
                if uncategorized:
                    groups.append({
                        'subcategory_id': None,
                        'subcategory_name': '未分类',
                        'items': uncategorized
                    })

                self.send_json({'success': True, 'groups': groups})
            except Exception as e:
                print(f"❌ 获取分组财务记录失败: {e}")
                import traceback
                traceback.print_exc()
                self.send_json({'success': False, 'error': str(e)})
        elif self.path == '/api/daily-records/grouped':
            # 获取按子类别分组的日常记录
            user_id = self.require_auth()
            if user_id is None:
                return
            try:
                # 获取所有日常记录
                all_records = daily_record_manager.list_records(user_id=user_id)

                # 获取记录类别的所有子类别
                record_category = category_manager.get_category_by_code('record')
                if not record_category:
                    self.send_json({'success': False, 'error': '记录类别不存在'})
                    return

                subcategories = category_manager.get_subcategories(record_category['id'], user_id=user_id)

                # 按子类别分组
                groups = []
                for subcategory in subcategories:
                    records_in_sub = [r for r in all_records if r.get('subcategory_id') == subcategory['id']]
                    if records_in_sub:
                        groups.append({
                            'subcategory_id': subcategory['id'],
                            'subcategory_name': subcategory['name'],
                            'items': records_in_sub
                        })

                # 添加未分类的记录
                uncategorized = [r for r in all_records if not r.get('subcategory_id')]
                if uncategorized:
                    groups.append({
                        'subcategory_id': None,
                        'subcategory_name': '未分类',
                        'items': uncategorized
                    })

                self.send_json({'success': True, 'groups': groups})
            except Exception as e:
                print(f"❌ 获取分组日常记录失败: {e}")
                import traceback
                traceback.print_exc()
                self.send_json({'success': False, 'error': str(e)})
        elif self.path == '/api/reminders':
            user_id = self.require_auth()
            if user_id is None:
                return
            reminders = reminder_sys.list_reminders(user_id=user_id)
            self.send_json({'reminders': reminders})
        elif self.path == '/api/reminders/check':
            """检查到期的提醒（用于浏览器轮询）"""
            user_id = self.require_auth()
            if user_id is None:
                return
            try:
                # 查询到期且未触发的提醒
                now = datetime.now().isoformat()
                with db_manager.get_cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, content, remind_time, repeat_type
                        FROM reminders
                        WHERE user_id = %s
                        AND status = 'pending'
                        AND triggered = 0
                        AND remind_time <= %s
                        ORDER BY remind_time ASC
                        LIMIT 10
                        """,
                        (user_id, now)
                    )
                    due_reminders = []
                    for row in cursor.fetchall():
                        reminder = {
                            'id': row['id'],
                            'content': row['content'],
                            'remind_time': row['remind_time'].isoformat() if hasattr(row['remind_time'], 'isoformat') else str(row['remind_time'])
                        }
                        due_reminders.append(reminder)

                        # 处理循环提醒
                        repeat_type = row.get('repeat_type', 'once')
                        if repeat_type in ['minutely', 'hourly', 'daily', 'weekly', 'monthly', 'yearly']:
                            # 计算下一次提醒时间
                            from reminder_scheduler import ReminderScheduler
                            scheduler_instance = ReminderScheduler()
                            next_remind_time = scheduler_instance._calculate_next_remind_time(row['remind_time'], repeat_type)

                            if next_remind_time:
                                # 更新为下一次提醒时间，保持pending状态，重置triggered
                                cursor.execute(
                                    "UPDATE reminders SET remind_time = %s, triggered = 0 WHERE id = %s",
                                    (next_remind_time, row['id'])
                                )
                                print(f"🔄 Web端循环提醒已更新，下次提醒时间: {next_remind_time}")
                            else:
                                # 计算失败，标记为completed
                                cursor.execute(
                                    "UPDATE reminders SET triggered = 1, status = 'completed' WHERE id = %s",
                                    (row['id'],)
                                )
                        else:
                            # 单次提醒，标记为已触发和已完成
                            cursor.execute(
                                "UPDATE reminders SET triggered = 1, status = 'completed' WHERE id = %s",
                                (row['id'],)
                            )

                        print(f"✅ Web端触发提醒: {reminder['content']}")

                        # 通过 WebSocket 推送到移动端
                        scheduler = get_global_scheduler()
                        if scheduler and scheduler.ws_server:
                            try:
                                print(f"🔍 DEBUG: Web端推送 WebSocket, user_id={user_id}, content={reminder['content']}")
                                result = scheduler.ws_server.send_reminder(user_id, reminder)
                                print(f"🔍 DEBUG: Web端 send_reminder 返回值={result}")
                            except Exception as ws_e:
                                print(f"⚠️ Web端 WebSocket 推送失败: {ws_e}")
                                import traceback
                                traceback.print_exc()

                    db_manager.connection.commit()

                    if due_reminders:
                        print(f"📢 返回{len(due_reminders)}条到期提醒给前端")

                    self.send_json({'success': True, 'reminders': due_reminders})
            except Exception as e:
                import traceback
                print(f"❌ 检查提醒失败: {e}")
                print(f"详细错误: {traceback.format_exc()}")
                self.send_json({'success': False, 'reminders': [], 'error': str(e)})
        elif self.path == '/api/images':
            user_id = self.require_auth()
            if user_id is None:
                return
            images = image_manager.list_images(user_id=user_id)
            self.send_json(images)
        elif self.path == '/api/files':
            # 文件列表（GET）
            user_id = self.require_auth()
            if user_id is None:
                return
            files = file_manager.list_files(user_id=user_id)
            self.send_json(files)
        elif self.path == '/api/file/stats':
            # 存储统计（GET）
            user_id = self.require_auth()
            if user_id is None:
                return
            stats = file_manager.get_user_storage_stats(user_id)
            print(f"[DEBUG] File stats for user_id={user_id}: {stats}")
            self.send_json({'success': True, 'stats': stats})
        elif self.path.startswith('/api/file/') and '/download' in self.path:
            # 文件下载（GET） - 格式: /api/file/{id}/download?token=xxx
            # 支持从URL参数获取token（因为<a>标签下载无法设置header）
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)

            # 优先从header获取token，其次从URL参数获取
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            if not token and 'token' in query_params:
                token = query_params['token'][0]

            # 验证token
            user_id = None
            if token:
                result = user_manager.verify_token(token)
                if result['success']:
                    user_id = result['user_id']

            if user_id is None:
                self.send_error(401, '未授权：请先登录')
                return

            try:
                # 从路径中提取file_id（支持带?参数的路径）
                path_parts = parsed_url.path.split('/')
                file_id = int(path_parts[-2])
            except (ValueError, IndexError):
                self.send_error(400, '无效的文件ID')
                return

            # 获取文件信息并检查权限
            # 首先尝试获取文件（不限制user_id）
            file_info = file_manager.get_file(file_id)
            if not file_info:
                self.send_error(404, '文件不存在')
                return

            # 检查权限：文件所有者 或 通过私信接收到该文件的用户
            is_owner = file_info['user_id'] == user_id
            is_shared_to_user = False

            if not is_owner:
                # 检查是否通过私信分享给当前用户
                check_sql = """
                    SELECT COUNT(*) as count FROM private_messages
                    WHERE receiver_id = %s
                    AND (file_id = %s OR image_id = %s)
                    AND message_type IN ('file', 'image')
                """
                result = db_manager.query_one(check_sql, (user_id, file_id, file_id))
                is_shared_to_user = result and result['count'] > 0

            if not is_owner and not is_shared_to_user:
                self.send_error(403, '无权访问此文件')
                return

            # 增加下载计数
            file_manager.increment_download_count(file_id)

            # 读取文件并发送
            try:
                with open(file_info['file_path'], 'rb') as f:
                    content = f.read()

                import mimetypes
                # 使用original_name来猜测MIME类型，而不是file_path（UUID文件名）
                content_type = file_info.get('mime_type') or mimetypes.guess_type(file_info['original_name'])[0] or 'application/octet-stream'

                self.send_response(200)
                self.send_header('Content-Type', content_type)
                # 对文件名进行URL编码，支持中文文件名
                from urllib.parse import quote
                encoded_filename = quote(file_info["original_name"])
                self.send_header('Content-Disposition', f'attachment; filename*=UTF-8\'\'{encoded_filename}')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, f'下载失败: {str(e)}')
        elif self.path.startswith('/api/file/') and self.path.count('/') == 3:
            # 获取单个文件信息（GET） - 格式: /api/file/{id}
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                file_id = int(self.path.split('/')[-1])
            except ValueError:
                self.send_json({'success': False, 'message': '无效的文件ID'}, status=400)
                return

            file_info = file_manager.get_file(file_id, user_id=user_id)
            if file_info:
                self.send_json(file_info)
            else:
                self.send_json({'success': False, 'message': '文件不存在'}, status=404)
        elif self.path == '/file-manager' or self.path == '/file-manager.html':
            # 文件管理页面
            self.send_file_manager_html()
        elif self.path == '/api/auth/verify':
            # Token验证（GET请求）
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            result = user_manager.verify_token(token)
            self.send_json(result)
        elif self.path == '/api/security/status':
            # 查询安全验证状态（GET请求）
            user_id = self.require_auth()
            if user_id is None:
                return

            token = self.headers.get('Authorization', '').replace('Bearer ', '')

            # 检查是否已设置验证码
            user_result = db_manager.query(
                "SELECT security_code FROM users WHERE id = %s",
                (user_id,)
            )
            has_security_code = bool(user_result and user_result[0]['security_code'])

            # 检查session验证状态
            session_result = db_manager.query(
                "SELECT security_verified, security_verified_at FROM user_sessions WHERE session_token = %s",
                (token,)
            )

            is_verified = False
            if session_result and session_result[0]['security_verified'] == 1:
                is_verified = True

            self.send_json({
                'success': True,
                'has_security_code': has_security_code,
                'is_verified': is_verified
            })
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
                    'theme': user.get('theme', 'light'),
                    'created_at': user.get('created_at', '').strftime('%Y-%m-%d %H:%M:%S') if hasattr(user.get('created_at', ''), 'strftime') else str(user.get('created_at', ''))
                }
                self.send_json({'success': True, 'user': user_profile})
            else:
                self.send_json({'success': False, 'message': '用户不存在'}, status=404)
        elif self.path == '/api/user/settings':
            # 获取用户设置
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                with db_manager.get_cursor() as cursor:
                    cursor.execute(
                        "SELECT setting_key, setting_value FROM user_settings WHERE user_id = %s",
                        (user_id,)
                    )
                    settings = {}
                    for row in cursor.fetchall():
                        settings[row['setting_key']] = row['setting_value']

                    # 设置默认值
                    if 'reminder_sound_type' not in settings:
                        settings['reminder_sound_type'] = 'default'
                    if 'reminder_sound_volume' not in settings:
                        settings['reminder_sound_volume'] = '0.7'

                    self.send_json({'success': True, 'settings': settings})
            except Exception as e:
                print(f"获取用户设置失败: {e}")
                self.send_json({'success': False, 'message': str(e)}, status=500)
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
        elif self.path.startswith('/uploads/files/'):
            # serve通用文件
            self.serve_file(self.path[1:])
        elif self.path.startswith('/ai/uploads/files/'):
            # 适配本地开发时的 /ai/ 路径
            self.serve_file(self.path[4:])
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

        # ========================================
        # 好友系统API (GET)
        # ========================================

        elif self.path.startswith('/api/social/users/search'):
            # 搜索用户
            user_id = self.require_auth()
            if user_id is None:
                return

            # 解析查询参数
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            keyword = params.get('keyword', [''])[0]
            limit = int(params.get('limit', ['20'])[0])

            if not keyword:
                self.send_json({'success': False, 'message': '请提供搜索关键词'})
                return

            users = friendship_manager.search_users(keyword, user_id, limit)
            self.send_json({'success': True, 'users': users})

        elif self.path == '/api/social/friends/list':
            # 获取好友列表
            user_id = self.require_auth()
            if user_id is None:
                return

            friends = friendship_manager.get_friends_list(user_id)

            # 转换字段名以匹配前端期望
            formatted_friends = []
            for friend in friends:
                formatted_friends.append({
                    'friend_id': friend['id'],
                    'friend_username': friend['username'],
                    'friend_avatar': friend.get('avatar_url'),
                    'accepted_at': friend.get('accepted_at')
                })

            self.send_json({'success': True, 'friends': formatted_friends})

        elif self.path.startswith('/api/social/friends/requests'):
            # 获取好友请求列表
            user_id = self.require_auth()
            if user_id is None:
                return

            # 解析查询参数
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            status = params.get('status', ['pending'])[0]
            requests = friendship_manager.get_friend_requests(user_id, status)
            self.send_json({'success': True, 'requests': requests})

        elif self.path == '/api/social/friends/sent-requests':
            # 获取已发送的好友请求列表
            user_id = self.require_auth()
            if user_id is None:
                return

            requests = friendship_manager.get_sent_requests(user_id)
            self.send_json({'success': True, 'requests': requests})

        elif self.path.startswith('/api/social/friends/check'):
            # 检查好友关系状态
            user_id = self.require_auth()
            if user_id is None:
                return

            # 解析查询参数
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            target_id = params.get('target_id', [''])[0]
            if not target_id:
                self.send_json({'success': False, 'message': '请提供目标用户ID'})
                return

            status = friendship_manager.check_friendship(user_id, int(target_id))
            self.send_json({'success': True, 'status': status})

        # ========================================
        # 私信系统API (GET)
        # ========================================

        elif self.path == '/api/social/messages/conversations':
            # 获取会话列表（必须放在conversation之前，避免被startswith匹配）
            user_id = self.require_auth()
            if user_id is None:
                return

            conversations = private_message_manager.get_conversation_list(user_id)
            self.send_json({'success': True, 'conversations': conversations})

        elif self.path.startswith('/api/social/messages/conversation'):
            # 获取与某人的聊天记录
            user_id = self.require_auth()
            if user_id is None:
                return

            # 解析查询参数
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            friend_id = params.get('friend_id', [''])[0]
            limit = int(params.get('limit', ['50'])[0])
            offset = int(params.get('offset', ['0'])[0])

            if not friend_id:
                self.send_json({'success': False, 'message': '请提供好友ID'})
                return

            messages = private_message_manager.get_conversation(user_id, int(friend_id), limit, offset)
            self.send_json({'success': True, 'messages': messages})


        elif self.path == '/api/social/messages/unread-count':
            # 获取未读消息总数
            user_id = self.require_auth()
            if user_id is None:
                return

            count = private_message_manager.get_unread_count(user_id)
            self.send_json({'success': True, 'count': count})

        # ========================================
        # 好友提醒系统API (GET)
        # ========================================

        elif self.path == '/api/social/reminders/unconfirmed':
            # 获取未确认的好友提醒
            user_id = self.require_auth()
            if user_id is None:
                return

            reminders = reminder_sys.get_unconfirmed_friend_reminders(user_id)
            self.send_json({'success': True, 'reminders': reminders})

        elif self.path == '/api/reminders/unconfirmed':
            # 获取未确认的个人提醒
            user_id = self.require_auth()
            if user_id is None:
                return

            reminders = reminder_sys.get_unconfirmed_personal_reminders(user_id)
            self.send_json({'success': True, 'reminders': reminders})

        # ========================================
        # 内容分享系统API (GET)
        # ========================================

        elif self.path.startswith('/api/social/shares/list'):
            # 获取分享列表（好友动态）
            user_id = self.require_auth()
            if user_id is None:
                return

            # 解析查询参数
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            limit = int(params.get('limit', ['20'])[0])
            offset = int(params.get('offset', ['0'])[0])

            shares = shared_content_manager.get_share_list(user_id, None, limit, offset)
            self.send_json({'success': True, 'shares': shares})

        elif self.path.startswith('/api/social/shares/user'):
            # 获取某用户的分享列表
            user_id = self.require_auth()
            if user_id is None:
                return

            # 解析查询参数
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            target_user_id = params.get('user_id', [''])[0]
            limit = int(params.get('limit', ['20'])[0])
            offset = int(params.get('offset', ['0'])[0])

            if not target_user_id:
                self.send_json({'success': False, 'message': '请提供用户ID'})
                return

            shares = shared_content_manager.get_user_shares(user_id, int(target_user_id), limit, offset)
            self.send_json({'success': True, 'shares': shares})

        # ========================================
        # 留言板系统API (GET)
        # ========================================

        # 注意：list-v2 必须在 list 前面，否则会被 list 匹配
        elif self.path.startswith('/api/social/guestbook/list-v2'):
            # 获取便签列表（增强版 - 动态墙模式）
            user_id = self.require_auth()
            if user_id is None:
                return

            # 解析查询参数
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            # owner_id 参数已废弃，但保留兼容性
            # 新逻辑：直接使用当前用户ID查询"我的+好友的"内容
            limit = int(params.get('limit', ['50'])[0])
            offset = int(params.get('offset', ['0'])[0])

            # viewer_id 就是当前用户，owner_id 参数被忽略
            messages = guestbook_manager.get_messages_v2(owner_id=user_id, viewer_id=user_id, limit=limit, offset=offset)
            self.send_json({'success': True, 'messages': messages})

        elif self.path.startswith('/api/social/guestbook/list'):
            # 获取留言列表（旧版）
            user_id = self.require_auth()
            if user_id is None:
                return

            # 解析查询参数
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            owner_id = params.get('owner_id', [''])[0]
            limit = int(params.get('limit', ['50'])[0])
            offset = int(params.get('offset', ['0'])[0])

            if not owner_id:
                self.send_json({'success': False, 'message': '请提供留言板主人ID'})
                return

            messages = guestbook_manager.get_messages(int(owner_id), user_id, limit, offset)
            self.send_json({'success': True, 'messages': messages})

        elif self.path == '/api/social/guestbook/config':
            # 获取便签墙配置
            from guestbook_manager import MOOD_TAGS, BG_COLORS, REACTION_TYPES
            self.send_json({
                'success': True,
                'mood_tags': MOOD_TAGS,
                'bg_colors': BG_COLORS,
                'reaction_types': REACTION_TYPES
            })

        elif self.path == '/api/social/guestbook/unread-count':
            # 获取未读留言数
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                # 获取用户最后查看留言墙的时间
                last_viewed_sql = "SELECT guestbook_last_viewed_at FROM users WHERE id = %s"
                result = db_manager.query(last_viewed_sql, (user_id,))

                last_viewed_at = None
                if result and result[0]['guestbook_last_viewed_at']:
                    last_viewed_at = result[0]['guestbook_last_viewed_at']

                # 统计之后的新留言数（使用动态墙逻辑：好友发布的新内容）
                if last_viewed_at:
                    # 获取我的好友列表
                    friends_sql = """
                        SELECT friend_id
                        FROM friendships
                        WHERE user_id = %s AND status = 'accepted'
                        UNION
                        SELECT user_id as friend_id
                        FROM friendships
                        WHERE friend_id = %s AND status = 'accepted'
                    """
                    friends_result = db_manager.query(friends_sql, (user_id, user_id))
                    friend_ids = [f['friend_id'] for f in friends_result] if friends_result else []

                    if friend_ids:
                        friend_ids_str = ','.join(map(str, friend_ids))
                        # 统计好友发布的新留言和回复（排除我自己发布的）
                        # 包括：1. 顶级留言  2. 所有回复
                        count_sql = f"""
                            SELECT COUNT(*) as count FROM guestbook_messages
                            WHERE author_id IN ({friend_ids_str})
                            AND author_id != %s
                            AND created_at > %s
                            AND (
                                (
                                    parent_id IS NULL
                                    AND (
                                        visibility = 'all_friends'
                                        OR (
                                            visibility = 'specific_friends'
                                            AND JSON_CONTAINS(visible_to_users, %s)
                                        )
                                    )
                                )
                                OR parent_id IS NOT NULL
                            )
                        """
                        count_result = db_manager.query(count_sql, (user_id, last_viewed_at, str(user_id)))
                    else:
                        count_result = [{'count': 0}]
                else:
                    # 如果从未查看过，统计所有好友的留言
                    friends_sql = """
                        SELECT friend_id
                        FROM friendships
                        WHERE user_id = %s AND status = 'accepted'
                        UNION
                        SELECT user_id as friend_id
                        FROM friendships
                        WHERE friend_id = %s AND status = 'accepted'
                    """
                    friends_result = db_manager.query(friends_sql, (user_id, user_id))
                    friend_ids = [f['friend_id'] for f in friends_result] if friends_result else []

                    if friend_ids:
                        friend_ids_str = ','.join(map(str, friend_ids))
                        count_sql = f"""
                            SELECT COUNT(*) as count FROM guestbook_messages
                            WHERE author_id IN ({friend_ids_str})
                            AND author_id != %s
                            AND parent_id IS NULL
                            AND (
                                visibility = 'all_friends'
                                OR (
                                    visibility = 'specific_friends'
                                    AND JSON_CONTAINS(visible_to_users, %s)
                                )
                            )
                        """
                        count_result = db_manager.query(count_sql, (user_id, str(user_id)))
                    else:
                        count_result = [{'count': 0}]

                unread_count = count_result[0]['count'] if count_result else 0
                self.send_json({'success': True, 'unread_count': unread_count})
            except Exception as e:
                print(f"❌ 获取未读留言数失败: {e}")
                import traceback
                traceback.print_exc()
                self.send_json({'success': False, 'message': str(e)}, status=500)

        # ========== FCM推送通知相关API (GET) ==========
        elif self.path == '/api/device/list':
            # 获取用户的设备列表
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                devices = device_token_manager.get_user_device_tokens(user_id, active_only=False)

                # 转换datetime为字符串
                for device in devices:
                    for key in ['created_at', 'updated_at', 'last_used_at']:
                        if key in device and device[key]:
                            device[key] = device[key].isoformat() if hasattr(device[key], 'isoformat') else str(device[key])

                self.send_json({'status': 'success', 'devices': devices})

            except Exception as e:
                print(f"❌ 获取设备列表失败: {e}")
                self.send_json({'status': 'error', 'message': str(e)}, status=500)

        else:
            self.send_error(404)
    
    def do_POST(self):
        """处理POST请求"""
        content_type = self.headers.get('Content-Type', '')

        # 对于 multipart/form-data 请求，不在这里解析，由具体的处理函数处理
        if 'multipart/form-data' in content_type:
            # 直接路由到对应的处理函数
            if self.path == '/api/user/upload-avatar':
                self._handle_avatar_upload()
                return
            elif self.path == '/api/image/upload':
                # 需要添加 multipart 图片上传处理
                self.send_json({'success': False, 'message': '请使用base64格式上传图片'})
                return
            else:
                self.send_error(404)
                return

        # 处理 JSON 数据
        content_length = self.headers.get('Content-Length')
        if not content_length:
            self.send_json({'success': False, 'message': '缺少Content-Length头'})
            return

        content_length = int(content_length)
        post_data = self.rfile.read(content_length).decode('utf-8')

        try:
            data = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_json({'success': False, 'message': 'JSON格式错误'})
            return

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

        elif self.path == '/api/auth/set-storage-mode':
            # 设置存储模式（首次登录时必须选择）
            user_id = self.require_auth()
            if user_id is None:
                return

            storage_mode = data.get('storage_mode', '')
            if storage_mode not in ['cloud', 'local']:
                self.send_json({'success': False, 'message': '无效的存储模式，请选择cloud或local'})
                return

            result = user_manager.set_storage_mode(user_id, storage_mode)
            self.send_json(result)

        elif self.path == '/api/auth/get-storage-mode':
            # 获取存储模式
            user_id = self.require_auth()
            if user_id is None:
                return

            result = user_manager.get_storage_mode(user_id)
            self.send_json(result)

        # ========================================
        # 邮箱/手机验证码相关API
        # ========================================

        elif self.path == '/api/verification/send-code':
            """发送验证码到邮箱或手机"""
            contact_type = data.get('contact_type', '')  # 'email' | 'phone'
            contact_value = data.get('contact_value', '')
            code_type = data.get('code_type', 'register')  # 'register' | 'reset_password'

            if not contact_type or not contact_value:
                self.send_json({'success': False, 'message': '请提供联系方式'})
                return

            if contact_type not in ['email', 'phone']:
                self.send_json({'success': False, 'message': '联系方式类型错误'})
                return

            # 对于注册验证码，检查是否已注册
            if code_type == 'register':
                if contact_type == 'email':
                    existing = db_manager.query_one("SELECT id FROM users WHERE email = %s", (contact_value,))
                else:
                    existing = db_manager.query_one("SELECT id FROM users WHERE phone = %s", (contact_value,))

                if existing:
                    self.send_json({'success': False, 'message': '该联系方式已被注册'})
                    return

            # 发送验证码
            result = verification_manager.send_code(contact_type, contact_value, code_type)
            self.send_json(result)

        elif self.path == '/api/verification/verify-code':
            """验证验证码"""
            contact_type = data.get('contact_type', '')
            contact_value = data.get('contact_value', '')
            code = data.get('code', '')
            code_type = data.get('code_type', 'register')

            if not all([contact_type, contact_value, code]):
                self.send_json({'success': False, 'message': '参数不完整'})
                return

            # 验证验证码
            result = verification_manager.verify_code(contact_type, contact_value, code, code_type)
            self.send_json(result)

        elif self.path == '/api/auth/register-with-verification':
            """用户注册（需要邮箱/手机验证）"""
            username = data.get('username', '')
            password = data.get('password', '')
            email = data.get('email', '')
            phone = data.get('phone', '')
            verification_code = data.get('verification_code', '')

            # 基本验证
            if not username or not password:
                self.send_json({'success': False, 'message': '用户名和密码不能为空'})
                return

            if not email and not phone:
                self.send_json({'success': False, 'message': '请至少提供邮箱或手机号'})
                return

            if not verification_code:
                self.send_json({'success': False, 'message': '请输入验证码'})
                return

            # 验证验证码
            contact_type = 'email' if email else 'phone'
            contact_value = email or phone

            verify_result = verification_manager.verify_code(contact_type, contact_value, verification_code, 'register')

            if not verify_result['success']:
                self.send_json(verify_result)
                return

            # 创建用户（带验证状态）
            result = user_manager.register_with_verification(
                username=username,
                password=password,
                email=email,
                phone=phone,
                email_verified=bool(email),
                phone_verified=bool(phone)
            )

            if not result['success']:
                self.send_json(result)
                return

            # 自动登录
            login_result = user_manager.login(username, password)
            self.send_json(login_result)

        elif self.path == '/api/auth/reset-password':
            """重置密码（通过邮箱/手机验证码）"""
            contact_type = data.get('contact_type', '')
            contact_value = data.get('contact_value', '')
            verification_code = data.get('verification_code', '')
            new_password = data.get('new_password', '')

            if not all([contact_type, contact_value, verification_code, new_password]):
                self.send_json({'success': False, 'message': '参数不完整'})
                return

            # 验证验证码
            verify_result = verification_manager.verify_code(contact_type, contact_value, verification_code, 'reset_password')

            if not verify_result['success']:
                self.send_json(verify_result)
                return

            # 查找用户
            if contact_type == 'email':
                user = db_manager.query_one("SELECT id FROM users WHERE email = %s", (contact_value,))
            else:
                user = db_manager.query_one("SELECT id FROM users WHERE phone = %s", (contact_value,))

            if not user:
                self.send_json({'success': False, 'message': '用户不存在'})
                return

            # 更新密码
            try:
                new_password_hash = user_manager.hash_password(new_password)
                db_manager.execute("UPDATE users SET password_hash = %s WHERE id = %s",
                                  (new_password_hash, user['id']))

                # 清除所有会话
                db_manager.execute("DELETE FROM user_sessions WHERE user_id = %s", (user['id'],))

                self.send_json({'success': True, 'message': '密码重置成功，请重新登录'})
            except Exception as e:
                self.send_json({'success': False, 'message': f'重置失败: {str(e)}'})

        elif self.path == '/api/security/set-code':
            # 设置安全验证码
            user_id = self.require_auth()
            if user_id is None:
                return

            security_code = data.get('security_code', '').strip()
            if not security_code or len(security_code) < 4:
                self.send_json({'success': False, 'message': '验证码至少需要4个字符'})
                return

            # 使用SHA256加密验证码
            import hashlib
            hashed_code = hashlib.sha256(security_code.encode()).hexdigest()

            try:
                db_manager.execute(
                    "UPDATE users SET security_code = %s WHERE id = %s",
                    (hashed_code, user_id)
                )
                
                self.send_json({'success': True, 'message': '安全验证码设置成功'})
            except Exception as e:
                self.send_json({'success': False, 'message': f'设置失败：{str(e)}'})

        elif self.path == '/api/security/verify':
            # 验证安全验证码
            user_id = self.require_auth()
            if user_id is None:
                return

            security_code = data.get('security_code', '').strip()
            if not security_code:
                self.send_json({'success': False, 'message': '请输入验证码'})
                return

            # 获取用户设置的验证码
            result = db_manager.query(
                "SELECT security_code FROM users WHERE id = %s",
                (user_id,)
            )

            if not result or not result[0]['security_code']:
                self.send_json({'success': False, 'message': '您还未设置安全验证码，请先在用户菜单中设置'})
                return

            # 验证密码
            import hashlib
            hashed_input = hashlib.sha256(security_code.encode()).hexdigest()

            if hashed_input == result[0]['security_code']:
                # 验证成功，更新session状态
                token = self.headers.get('Authorization', '').replace('Bearer ', '')
                try:
                    db_manager.execute(
                        "UPDATE user_sessions SET security_verified = 1, security_verified_at = NOW() WHERE session_token = %s",
                        (token,)
                    )
                    
                    self.send_json({'success': True, 'message': '验证成功'})
                except Exception as e:
                    self.send_json({'success': False, 'message': f'验证失败：{str(e)}'})
            else:
                self.send_json({'success': False, 'message': '验证码错误'})

        elif self.path == '/api/security/status':
            # 查询当前验证状态
            user_id = self.require_auth()
            if user_id is None:
                return

            token = self.headers.get('Authorization', '').replace('Bearer ', '')

            # 检查是否已设置验证码
            user_result = db_manager.query(
                "SELECT security_code FROM users WHERE id = %s",
                (user_id,)
            )
            has_security_code = bool(user_result and user_result[0]['security_code'])

            # 检查session验证状态
            session_result = db_manager.query(
                "SELECT security_verified, security_verified_at FROM user_sessions WHERE session_token = %s",
                (token,)
            )

            is_verified = False
            if session_result and session_result[0]['security_verified'] == 1:
                is_verified = True

            self.send_json({
                'success': True,
                'has_security_code': has_security_code,
                'is_verified': is_verified
            })

        elif self.path == '/api/security/clear':
            # 清除验证状态（用于测试或用户主动退出验证）
            user_id = self.require_auth()
            if user_id is None:
                return

            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            try:
                db_manager.execute(
                    "UPDATE user_sessions SET security_verified = 0, security_verified_at = NULL WHERE session_token = %s",
                    (token,)
                )
                
                self.send_json({'success': True, 'message': '已清除验证状态'})
            except Exception as e:
                self.send_json({'success': False, 'message': f'操作失败：{str(e)}'})

        elif self.path == '/api/ai/chat':
            try:
                print(f"🔍 收到聊天请求: {data.get('message', '')[:50]}")
                user_id = self.require_auth()
                if user_id is None:
                    return
                token = self.headers.get('Authorization', '').replace('Bearer ', '')
                session_id = self.headers.get('X-Session-ID', '')  # ✨ 获取会话ID

                # 获取用户消息
                user_message = data.get('message', '')

                # ✨ 优先检查是否是命令系统的命令
                command_router = get_command_router()
                command_result = command_router.execute(user_message, user_id)

                if command_result and command_result.get('is_command'):
                    # ✨ 如果命令返回了上下文信息，保存到AI系统
                    if 'context' in command_result:
                        from datetime import datetime
                        ai_assistant.last_response_context[user_id] = {
                            'type': command_result['context']['type'],
                            'data': command_result['context']['data'],
                            'subcategory_name': command_result['context'].get('subcategory_name'),  # ✨ 保存子类别名称
                            'timestamp': datetime.now()
                        }
                        subcategory_info = f", subcategory={command_result['context'].get('subcategory_name')}" if command_result['context'].get('subcategory_name') else ""
                        print(f"✅ 已保存命令上下文: type={command_result['context']['type']}, data_count={len(command_result['context']['data'])}{subcategory_info}")

                    # 是命令，直接返回命令结果
                    response_data = {
                        'response': command_result.get('response', ''),
                        'detected_plans': [],
                        'detected_reminders': [],
                        'completed_plans': []
                    }
                    # ✨ 传递空列表相关字段（用于显示"+ 添加"按钮）
                    if 'empty_list' in command_result:
                        response_data['empty_list'] = command_result['empty_list']
                    if 'subcategory_name' in command_result:
                        response_data['subcategory_name'] = command_result['subcategory_name']
                    if 'add_action' in command_result:
                        response_data['add_action'] = command_result['add_action']

                    self.send_json(response_data)
                    return

                # 不是命令，继续使用AI处理
                print(f"🔍 不是命令，调用AI处理: {user_message[:50]}")
                # 获取用户的AI助理名字
                user_info = user_manager.get_user_by_id(user_id)
                ai_assistant_name = user_info.get('ai_assistant_name', '小助手') if user_info else '小助手'

                chat_result = ai_assistant.chat(user_message, user_id=user_id, file_id=data.get('file_id'), token=token, session_id=session_id, ai_assistant_name=ai_assistant_name)  # ✨ 传递session_id和ai_assistant_name
                print(f"🔍 AI处理完成，返回结果类型: {type(chat_result)}")
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
            except Exception as e:
                print(f"❌ /api/ai/chat 处理出错: {e}")
                import traceback
                traceback.print_exc()

                # ✨ 提供更友好的错误处理，让AI仍然能够回答
                error_response = f"抱歉，我遇到了一些技术问题。不过我还是可以帮你：\n\n"
                error_response += "• 输入「帮助」查看可用命令\n"
                error_response += "• 输入「类别」查看所有功能分类\n"
                error_response += "• 输入「工作」查看待办事项\n\n"
                error_response += f"如果问题持续，请联系管理员。错误详情：{str(e)[:100]}"

                self.send_json({
                    'response': error_response,
                    'detected_plans': [],
                    'detected_reminders': [],
                    'completed_plans': []
                })

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

            # 支持更新多个字段：status, title, description, deadline, priority, sort_order
            update_fields = {}
            if 'status' in data:
                update_fields['status'] = data['status']
            if 'title' in data:
                update_fields['title'] = data['title']
            if 'description' in data:
                update_fields['description'] = data['description']
            if 'deadline' in data:
                update_fields['deadline'] = data['deadline']
            if 'priority' in data:
                update_fields['priority'] = data['priority']

            if 'sort_order' in data:
                update_fields['sort_order'] = data['sort_order']
            success = planner.update_plan(data.get('id'), user_id=user_id, **update_fields)
            if success:
                self.send_json({'success': True, 'message': '计划已更新'})
            else:
                self.send_json({'success': False, 'message': '更新失败或权限不足'}, status=403)

        elif self.path == '/api/plan/pin':
            # 置顶计划
            user_id = self.require_auth()
            if user_id is None:
                return

            plan_id = data.get('id')
            if not plan_id:
                self.send_json({'success': False, 'message': '缺少计划ID'}, status=400)
                return

            try:
                # 获取当前最大的 sort_order
                max_order_sql = "SELECT MAX(sort_order) as max_order FROM work_tasks WHERE user_id = %s"
                result = planner.db.query_one(max_order_sql, (user_id,))
                max_order = result['max_order'] if result and result['max_order'] else 0

                # 将该计划的 sort_order 设置为最大值+1
                update_sql = "UPDATE work_tasks SET sort_order = %s WHERE id = %s AND user_id = %s"
                planner.db.execute(update_sql, (max_order + 1, plan_id, user_id))

                self.send_json({'success': True, 'message': '已置顶'})
            except Exception as e:
                print(f"❌ 置顶失败: {e}")
                self.send_json({'success': False, 'message': f'置顶失败: {str(e)}'}, status=500)

        elif self.path == '/api/plan/reorder':
            # 批量调整顺序
            user_id = self.require_auth()
            if user_id is None:
                return

            plan_orders = data.get('orders')  # 格式: [{id: 1, sort_order: 10}, {id: 2, sort_order: 9}, ...]
            if not plan_orders or not isinstance(plan_orders, list):
                self.send_json({'success': False, 'message': '缺少排序数据'}, status=400)
                return

            try:
                for item in plan_orders:
                    plan_id = item.get('id')
                    sort_order = item.get('sort_order')
                    if plan_id is not None and sort_order is not None:
                        update_sql = "UPDATE work_tasks SET sort_order = %s WHERE id = %s AND user_id = %s"
                        planner.db.execute(update_sql, (sort_order, plan_id, user_id))

                self.send_json({'success': True, 'message': '顺序已更新'})
            except Exception as e:
                print(f"❌ 调整顺序失败: {e}")
                self.send_json({'success': False, 'message': f'调整顺序失败: {str(e)}'}, status=500)

        elif self.path == '/api/plan/batch-update':
            # 批量更新计划（标题和排序）
            user_id = self.require_auth()
            if user_id is None:
                return

            updates = data.get('updates')  # 格式: [{id: 1, title: '急 任务', sort_order: 10}, ...]
            if not updates or not isinstance(updates, list):
                self.send_json({'success': False, 'message': '缺少更新数据'}, status=400)
                return

            try:
                for item in updates:
                    plan_id = item.get('id')
                    if plan_id is None:
                        continue

                    # 构建更新字段
                    update_fields = []
                    update_values = []

                    if 'title' in item:
                        update_fields.append('title = %s')
                        update_values.append(item['title'])

                    if 'sort_order' in item:
                        update_fields.append('sort_order = %s')
                        update_values.append(item['sort_order'])

                    if update_fields:
                        update_values.extend([plan_id, user_id])
                        update_sql = f"UPDATE work_tasks SET {', '.join(update_fields)} WHERE id = %s AND user_id = %s"
                        planner.db.execute(update_sql, tuple(update_values))

                self.send_json({'success': True, 'message': '批量更新成功'})
            except Exception as e:
                print(f"❌ 批量更新失败: {e}")
                self.send_json({'success': False, 'message': f'批量更新失败: {str(e)}'}, status=500)

        elif self.path == '/api/plan/delete':
            user_id = self.require_auth()
            if user_id is None:
                return
            success = planner.delete_plan(data.get('id'), user_id=user_id)
            if success:
                self.send_json({'success': True, 'message': '计划已删除'})
            else:
                self.send_json({'success': False, 'message': '删除失败或权限不足'}, status=403)

        elif self.path == '/api/work-task/update':
            # 更新工作任务（work_tasks表）
            user_id = self.require_auth()
            if user_id is None:
                return

            task_id = data.get('id')
            if not task_id:
                self.send_json({'success': False, 'message': '缺少任务ID'}, status=400)
                return

            try:
                # 目前只支持更新状态
                if 'status' in data:
                    status = data['status']
                    print(f"🔍 [DEBUG] 更新任务: task_id={task_id}, status={status}, user_id={user_id}")

                    # 先检查任务是否存在且属于当前用户
                    check_query = "SELECT status FROM work_tasks WHERE id = %s AND user_id = %s"
                    with work_task_manager.get_cursor() as cursor:
                        cursor.execute(check_query, (task_id, user_id))
                        result = cursor.fetchone()

                        if not result:
                            print(f"❌ [DEBUG] 任务不存在或权限不足")
                            self.send_json({'success': False, 'message': '任务不存在或权限不足'}, status=403)
                            return

                        current_status = result['status']
                        print(f"🔍 [DEBUG] 当前状态: {current_status}, 目标状态: {status}")

                        if current_status == status:
                            # 状态已经是目标状态，直接返回成功
                            print(f"✅ [DEBUG] 任务状态已经是 {status}，无需更新")
                            self.send_json({'success': True, 'message': '任务状态已是目标状态'})
                            return

                    # 执行更新
                    success = work_task_manager.update_task_status(task_id, status, user_id)
                    print(f"🔍 [DEBUG] 更新结果: success={success}")
                    if success:
                        self.send_json({'success': True, 'message': '任务已更新'})
                    else:
                        self.send_json({'success': False, 'message': '更新失败'}, status=500)
                else:
                    self.send_json({'success': False, 'message': '缺少更新字段'}, status=400)
            except Exception as e:
                print(f"❌ 更新任务失败: {e}")
                import traceback
                traceback.print_exc()
                self.send_json({'success': False, 'message': f'更新失败: {str(e)}'}, status=500)

        elif self.path == '/api/work-task/add':
            # 添加工作任务（work_tasks表）
            user_id = self.require_auth()
            if user_id is None:
                return

            title = data.get('title', '')
            if not title:
                self.send_json({'success': False, 'message': '缺少任务标题'}, status=400)
                return

            try:
                # 添加任务到work_tasks表
                work_task_manager.add_task(user_id, title)
                self.send_json({'success': True, 'message': '任务已添加'})
            except Exception as e:
                print(f"❌ 添加任务失败: {e}")
                self.send_json({'success': False, 'message': f'添加失败: {str(e)}'}, status=500)

        elif self.path == '/api/record/add':
            # 添加记录（daily_records表）- 用于子类别
            user_id = self.require_auth()
            if user_id is None:
                return

            title = data.get('title', '')
            subcategory_name = data.get('subcategory_name', '')

            if not title:
                self.send_json({'success': False, 'message': '缺少记录标题'}, status=400)
                return

            try:
                # 如果提供了子类别名称，查找子类别ID（子类别是全局的，不限用户）
                subcategory_id = None
                if subcategory_name:
                    query = "SELECT id FROM subcategories WHERE name = %s LIMIT 1"
                    result = db_manager.query(query, (subcategory_name,))
                    if result:
                        subcategory_id = result[0]['id']

                # 添加记录到daily_records表
                # title字段限制500字符，content字段存储完整内容
                title_truncated = title[:500] if len(title) > 500 else title
                daily_record_manager.add_record(
                    user_id=user_id,
                    content=title,  # 完整内容
                    title=title_truncated,  # 截断到500字符
                    subcategory_id=subcategory_id
                )
                self.send_json({'success': True, 'message': '记录已添加'})
            except Exception as e:
                print(f"❌ 添加记录失败: {e}")
                self.send_json({'success': False, 'message': f'添加失败: {str(e)}'}, status=500)

        elif self.path == '/api/record/update':
            # 更新记录状态或标题（daily_records表或work_tasks表）
            print(f"🔍 DEBUG /api/record/update 请求收到")
            user_id = self.require_auth()
            if user_id is None:
                return

            record_id = data.get('record_id') or data.get('id')  # 兼容两种参数名
            status = data.get('status')
            title = data.get('title')
            sort_order = data.get('sort_order')
            print(f"🔍 DEBUG 请求参数: record_id={record_id}, status={status}, title={title}, sort_order={sort_order}")

            if not record_id:
                self.send_json({'success': False, 'message': '缺少记录ID'}, status=400)
                return

            try:
                # 首先检查记录是否在daily_records表中（通过检查是否有subcategory_id）
                check_daily_sql = "SELECT id, subcategory_id FROM daily_records WHERE id = %s AND user_id = %s LIMIT 1"
                daily_record_result = db_manager.query(check_daily_sql, (record_id, user_id))

                if daily_record_result:
                    # 记录在daily_records表中，使用daily_record_manager更新
                    print(f"🔍 DEBUG 记录在daily_records表中，使用daily_record_manager更新")
                    update_attempted = False

                    if title is not None:
                        print(f"🔍 DEBUG 调用 update_record_title: record_id={record_id}, title={title}, user_id={user_id}")
                        daily_record_manager.update_record_title(record_id, title, user_id)
                        update_attempted = True

                    if status is not None:
                        print(f"🔍 DEBUG 调用 update_record_status: record_id={record_id}, status={status}, user_id={user_id}")
                        daily_record_manager.update_record_status(record_id, status, user_id)
                        update_attempted = True

                    if sort_order is not None:
                        print(f"🔍 DEBUG 更新 sort_order: record_id={record_id}, sort_order={sort_order}, user_id={user_id}")
                        update_sort_sql = "UPDATE daily_records SET sort_order = %s WHERE id = %s AND user_id = %s"
                        db_manager.execute(update_sort_sql, (sort_order, record_id, user_id))
                        update_attempted = True

                    # 只要尝试了更新就返回成功（即使标题没有变化）
                    if not update_attempted:
                        print(f"⚠️ WARNING 没有提供要更新的字段")
                        self.send_json({'success': False, 'message': '没有提供要更新的字段'}, status=400)
                        return
                else:
                    # 记录不在daily_records表中，检查是否在work_tasks表中
                    check_work_sql = "SELECT id FROM work_tasks WHERE id = %s AND user_id = %s LIMIT 1"
                    work_task_result = db_manager.query(check_work_sql, (record_id, user_id))

                    if work_task_result:
                        # 记录在work_tasks表中，使用planner更新
                        print(f"🔍 DEBUG 记录在work_tasks表中，使用planner更新")
                        if title is not None:
                            print(f"🔍 DEBUG 调用 planner.update_plan: record_id={record_id}, title={title}")
                            planner.update_plan(record_id, user_id=user_id, title=title)
                        if status is not None:
                            print(f"🔍 DEBUG 调用 planner.update_plan: record_id={record_id}, status={status}")
                            planner.update_plan(record_id, user_id=user_id, status=status)
                    else:
                        # 两个表中都找不到这个记录
                        print(f"❌ 错误: 记录ID={record_id}不存在或不属于该用户")
                        self.send_json({'success': False, 'message': '记录不存在或已被删除'}, status=404)
                        return

                print(f"✅ 记录更新成功: record_id={record_id}")
                self.send_json({'success': True, 'message': '记录已更新'})
            except Exception as e:
                print(f"❌ 更新记录失败: {e}")
                import traceback
                traceback.print_exc()
                self.send_json({'success': False, 'message': f'更新失败: {str(e)}'}, status=500)

        elif self.path == '/api/record/delete':
            # 删除记录（daily_records表）
            user_id = self.require_auth()
            if user_id is None:
                return

            record_id = data.get('id')

            if not record_id:
                self.send_json({'success': False, 'message': '缺少记录ID'}, status=400)
                return

            try:
                daily_record_manager.delete_record(record_id, user_id)
                self.send_json({'success': True, 'message': '记录已删除'})
            except Exception as e:
                print(f"❌ 删除记录失败: {e}")
                self.send_json({'success': False, 'message': f'删除失败: {str(e)}'}, status=500)

        elif self.path == '/api/record/batch-update':
            # 批量更新记录（daily_records表）- 用于排序和标记
            user_id = self.require_auth()
            if user_id is None:
                return

            updates = data.get('updates', [])
            print(f"🔍 DEBUG 批量更新记录: user_id={user_id}, updates数量={len(updates)}")

            if not updates:
                self.send_json({'success': False, 'message': '缺少更新数据'}, status=400)
                return

            try:
                updated_count = 0
                for update in updates:
                    record_id = update.get('id')
                    title = update.get('title')
                    sort_order = update.get('sort_order')
                    print(f"🔍 DEBUG 更新记录: id={record_id}, title={title}, sort_order={sort_order}")

                    if record_id:
                        # ✨ 动态构建更新字段，只更新提供的字段
                        update_fields = []
                        update_values = []

                        # 如果提供了 title，同时更新 title 和 content
                        if title is not None and title.strip() != '':
                            update_fields.append('title = %s')
                            update_fields.append('content = %s')
                            update_values.extend([title, title])

                        # 如果提供了 sort_order，更新排序
                        if sort_order is not None:
                            update_fields.append('sort_order = %s')
                            update_values.append(sort_order)

                        # 只有在有字段需要更新时才执行
                        if update_fields:
                            update_values.extend([record_id, user_id])
                            query = f"""
                                UPDATE daily_records
                                SET {', '.join(update_fields)}
                                WHERE id = %s AND user_id = %s
                            """
                            rows_affected = db_manager.execute(query, tuple(update_values))
                            print(f"🔍 DEBUG 更新结果: rows_affected={rows_affected}")
                            updated_count += rows_affected

                print(f"✅ 批量更新成功: 共更新{updated_count}条记录")
                self.send_json({'success': True, 'message': '批量更新成功'})
            except Exception as e:
                print(f"❌ 批量更新失败: {e}")
                import traceback
                traceback.print_exc()
                self.send_json({'success': False, 'message': f'批量更新失败: {str(e)}'}, status=500)

        elif self.path == '/api/reminder/add':
            user_id = self.require_auth()
            if user_id is None:
                return

            # 调试日志 - 打印原始请求数据
            print(f"🔍 [API] 收到创建提醒请求 - 原始数据:")
            print(f"  - 完整data: {data}")

            # 支持新旧两种参数格式
            content = data.get('content') or data.get('message') or data.get('title', '')
            repeat_type = data.get('repeat_type', 'once')

            # 调试日志 - 打印解析后的数据
            print(f"🔍 [API] 解析后的参数:")
            print(f"  - user_id: {user_id}")
            print(f"  - content: {content}")
            print(f"  - repeat_type: {repeat_type}")
            print(f"  - remind_time: {data.get('remind_time', '')}")

            reminder_sys.add_reminder(
                title=data.get('title', ''),
                message=data.get('message', ''),
                content=content,
                remind_time=data.get('remind_time', ''),
                repeat=data.get('repeat', '不重复'),
                sound=data.get('sound', 'Ping'),
                user_id=user_id,
                repeat_type=repeat_type
            )
            self.send_json({'success': True, 'message': '提醒已添加'})

        elif self.path == '/api/reminder/update':
            user_id = self.require_auth()
            if user_id is None:
                return

            reminder_id = data.get('id')
            if not reminder_id:
                self.send_json({'success': False, 'message': '缺少提醒ID'}, status=400)
                return

            # 更新提醒
            success = reminder_sys.update_reminder(
                reminder_id,
                content=data.get('content'),
                remind_time=data.get('remind_time'),
                repeat_type=data.get('repeat_type'),
                user_id=user_id
            )

            if success:
                self.send_json({'success': True, 'message': '提醒已更新'})
            else:
                self.send_json({'success': False, 'message': '更新失败或权限不足'}, status=403)

        elif self.path == '/api/reminder/delete':
            user_id = self.require_auth()
            if user_id is None:
                return
            # 支持 id 和 reminder_id 两种参数名
            reminder_id = data.get('id') or data.get('reminder_id')
            success = reminder_sys.delete_reminder(reminder_id, user_id=user_id)
            if success:
                self.send_json({'success': True, 'message': '提醒已删除'})
            else:
                self.send_json({'success': False, 'message': '删除失败或权限不足'}, status=403)

        elif self.path == '/api/reminder/snooze':
            # 延迟提醒（稍后再提醒）
            user_id = self.require_auth()
            if user_id is None:
                return

            reminder_id = data.get('id')
            minutes = data.get('minutes', 30)  # 默认30分钟

            if not reminder_id:
                self.send_json({'success': False, 'message': '缺少提醒ID'})
                return

            try:
                # 获取原提醒信息
                reminder = reminder_sys.get_reminder_by_id(reminder_id, user_id=user_id)
                if not reminder:
                    self.send_json({'success': False, 'message': '提醒不存在或权限不足'}, status=403)
                    return

                # 计算新的提醒时间
                from datetime import datetime, timedelta
                new_remind_time = datetime.now() + timedelta(minutes=minutes)
                new_remind_time_str = new_remind_time.strftime('%Y-%m-%d %H:%M:%S')

                # 更新提醒时间，并重置triggered状态
                success = reminder_sys.update_reminder(
                    reminder_id=reminder_id,
                    remind_time=new_remind_time_str,
                    user_id=user_id
                )

                # 重置triggered状态
                if success:
                    db_manager.execute(
                        "UPDATE reminders SET triggered = 0 WHERE id = %s",
                        (reminder_id,)
                    )

                if success:
                    self.send_json({'success': True, 'message': f'已设置{minutes}分钟后再次提醒'})
                else:
                    self.send_json({'success': False, 'message': '延迟提醒失败'}, status=500)

            except Exception as e:
                print(f"❌ 延迟提醒失败: {e}")
                self.send_json({'success': False, 'message': f'延迟提醒失败: {str(e)}'}, status=500)

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
                user_id=user_id,
                repeat_type=data.get('repeat_type', 'once')
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

                # 返回图片信息 - file_path 格式应为 /uploads/images/xxx.jpg (前端使用)
                # 注意：前端需要的是URL路径格式（以斜杠开头）
                relative_path = f"/{file_path}" if not file_path.startswith('/') else file_path

                img = {
                    'id': img_id,
                    'filename': filename,
                    'original_name': original_name,
                    'file_path': relative_path,  # 返回格式: /uploads/images/xxx.jpg
                    'description': description,
                    'tags': tags,
                    'file_size': file_size
                }

                self.send_json({'success': True, 'message': '图片上传成功', 'image': img})
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, status=500)

        elif self.path == '/api/file/upload':
            # 上传文件（通用）
            user_id = self.require_auth()
            if user_id is None:
                return
            try:
                file_data = data.get('file_data', '')
                original_name = data.get('original_name', 'unknown')
                mime_type = data.get('mime_type', 'application/octet-stream')
                description = data.get('description', '')
                tags = data.get('tags', [])

                if not file_data:
                    self.send_json({'success': False, 'message': '没有文件数据'})
                    return

                # 解码base64
                if ',' in file_data:
                    file_data = file_data.split(',')[1]

                file_bytes = base64.b64decode(file_data)
                file_size = len(file_bytes)

                # 检查大小限制 (1GB)
                if file_size > 1024 * 1024 * 1024:
                     self.send_json({'success': False, 'message': '文件过大，最大支持1GB'})
                     return

                # 使用原始文件名，处理重名情况
                import time
                filename = original_name
                file_path = os.path.join(file_manager.upload_dir, filename)

                # 如果文件已存在，添加时间戳避免冲突
                if os.path.exists(file_path):
                    name_parts = original_name.rsplit('.', 1)
                    if len(name_parts) == 2:
                        base_name, ext = name_parts
                        timestamp = int(time.time() * 1000)  # 毫秒时间戳
                        filename = f"{base_name}_{timestamp}.{ext}"
                    else:
                        timestamp = int(time.time() * 1000)
                        filename = f"{original_name}_{timestamp}"
                    file_path = os.path.join(file_manager.upload_dir, filename)

                # 保存文件
                with open(file_path, 'wb') as f:
                    f.write(file_bytes)

                # 如果是视频文件，生成缩略图
                thumbnail_path = None
                if mime_type and mime_type.startswith('video/'):
                    # 生成缩略图文件名
                    thumbnail_filename = f"{uuid.uuid4().hex}.jpg"
                    thumbnail_dir = os.path.join('uploads', 'thumbnails')
                    if not os.path.exists(thumbnail_dir):
                        os.makedirs(thumbnail_dir, exist_ok=True)
                    thumbnail_full_path = os.path.join(thumbnail_dir, thumbnail_filename)

                    # 提取视频首图
                    if extract_video_thumbnail(file_path, thumbnail_full_path):
                        thumbnail_path = thumbnail_full_path

                # 添加到数据库
                file_id = file_manager.add_file(
                    filename=filename,
                    original_name=original_name,
                    file_path=file_path,
                    file_size=file_size,
                    mime_type=mime_type,
                    description=description,
                    tags=tags,
                    thumbnail_path=thumbnail_path,
                    user_id=user_id
                )

                # ✨ 如果是图片文件，同步到images表（实现文件管理同步）
                image_id = None
                if mime_type and mime_type.startswith('image/'):
                    try:
                        # 复制文件到images目录
                        image_filename = filename
                        image_file_path = os.path.join(image_manager.upload_dir, image_filename)

                        # 如果images目录中不存在该文件，复制过去
                        if not os.path.exists(image_file_path):
                            import shutil
                            shutil.copy2(file_path, image_file_path)

                        # 添加到images表
                        image_id = image_manager.add_image(
                            filename=image_filename,
                            original_name=original_name,
                            file_path=image_file_path,
                            description=description,
                            tags=tags,
                            chat_id=None,
                            file_size=file_size,
                            user_id=user_id
                        )
                        print(f"✅ 图片已同步到文件管理，image_id={image_id}")
                    except Exception as e:
                        print(f"⚠️ 同步到images表失败: {e}")

                # 返回文件信息 - file_path 格式应为 /uploads/files/xxx.pdf (前端使用)
                relative_path = f"/{file_path}" if not file_path.startswith('/') else file_path
                relative_thumbnail = f"/{thumbnail_path}" if thumbnail_path and not thumbnail_path.startswith('/') else thumbnail_path

                file_info = {
                    'id': file_id,
                    'filename': filename,
                    'original_name': original_name,
                    'file_path': relative_path,  # 返回格式: /uploads/files/xxx.pdf
                    'file_size': file_size,
                    'mime_type': mime_type,
                    'thumbnail_path': relative_thumbnail  # 视频缩略图路径
                }

                self.send_json({'success': True, 'message': '文件上传成功', 'file': file_info})
            except Exception as e:
                print(f"上传文件出错: {e}")
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

        elif self.path == '/api/file/search':
            # 搜索文件（POST）
            user_id = self.require_auth()
            if user_id is None:
                return

            keyword = data.get('keyword', '')
            category = data.get('category')
            tags = data.get('tags', [])

            results = file_manager.search_files(
                keyword=keyword.strip() if keyword else None,
                category=category,
                tags=tags if tags else None,
                user_id=user_id
            )
            self.send_json({'results': results})

        elif self.path == '/api/file/delete':
            # 删除文件（POST）
            user_id = self.require_auth()
            if user_id is None:
                return

            file_id = data.get('id')
            if not file_id:
                self.send_json({'success': False, 'message': '缺少文件ID'}, status=400)
                return

            success = file_manager.delete_file(file_id, user_id=user_id)
            if success:
                self.send_json({'success': True, 'message': '文件已删除'})
            else:
                self.send_json({'success': False, 'message': '删除失败或权限不足'}, status=403)

        elif self.path == '/api/file/update':
            # 更新文件信息（POST）
            user_id = self.require_auth()
            if user_id is None:
                return

            file_id = data.get('id')
            description = data.get('description')
            tags = data.get('tags')

            if not file_id:
                self.send_json({'success': False, 'message': '缺少文件ID'}, status=400)
                return

            success = file_manager.update_file_info(file_id, description=description, tags=tags, user_id=user_id)
            if success:
                self.send_json({'success': True, 'message': '更新成功'})
            else:
                self.send_json({'success': False, 'message': '更新失败或权限不足'}, status=403)

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

        elif self.path == '/api/user/update-profile':
            # 更新用户资料
            user_id = self.require_auth()
            if user_id is None:
                return

            phone = data.get('phone')
            theme = data.get('theme')
            chat_background = data.get('chat_background')

            # 至少需要一个字段
            if phone is None and theme is None and chat_background is None:
                self.send_json({'success': False, 'message': '没有提供要更新的数据'}, status=400)
                return

            try:
                # 更新电话
                if phone is not None:
                    success = user_manager.update_phone(user_id, phone)
                    if not success:
                        self.send_json({'success': False, 'message': '更新电话失败'}, status=500)
                        return

                # 更新主题
                if theme is not None:
                    success = user_manager.update_theme(user_id, theme)
                    if not success:
                        self.send_json({'success': False, 'message': '更新主题失败'}, status=500)
                        return

                # 更新对话背景
                if chat_background is not None:
                    success = user_manager.update_chat_background(user_id, chat_background)
                    if not success:
                        self.send_json({'success': False, 'message': '更新对话背景失败'}, status=500)
                        return

                self.send_json({'success': True, 'message': '资料更新成功'})
            except Exception as e:
                print(f"更新用户资料错误: {e}")
                self.send_json({'success': False, 'error': str(e)}, status=500)

        elif self.path == '/api/user/upload-avatar':
            # 上传头像 (使用 base64 编码,与其他上传接口保持一致)
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                image_data = data.get('avatar') or data.get('image_data', '')

                if not image_data:
                    self.send_json({'success': False, 'error': '没有图片数据'}, status=400)
                    return

                # 解码base64图片
                if ',' in image_data:
                    image_data = image_data.split(',')[1]

                image_bytes = base64.b64decode(image_data)

                # 生成唯一文件名
                filename = f"avatar_{user_id}_{uuid.uuid4().hex}.jpg"

                # 创建 avatars 目录
                avatar_dir = 'uploads/avatars'
                os.makedirs(avatar_dir, exist_ok=True)

                file_path = os.path.join(avatar_dir, filename)

                # 保存文件
                with open(file_path, 'wb') as f:
                    f.write(image_bytes)

                # 更新用户头像URL
                avatar_url = f'/uploads/avatars/{filename}'
                success = user_manager.update_avatar(user_id, avatar_url)

                if success:
                    self.send_json({
                        'success': True,
                        'message': '头像上传成功',
                        'avatar_url': avatar_url
                    })
                else:
                    self.send_json({'success': False, 'error': '更新头像URL失败'}, status=500)
            except Exception as e:
                print(f"头像上传错误: {e}")
                import traceback
                traceback.print_exc()
                self.send_json({'success': False, 'error': str(e)}, status=500)

        elif self.path == '/api/user/update-ai-avatar':
            # 更新AI助理头像
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                ai_avatar_url = data.get('ai_avatar_url', '')

                # 更新AI头像URL
                success = user_manager.update_ai_avatar(user_id, ai_avatar_url)

                if success:
                    self.send_json({
                        'success': True,
                        'message': 'AI头像更新成功'
                    })
                else:
                    self.send_json({'success': False, 'message': 'AI头像更新失败'}, status=500)
            except Exception as e:
                print(f"更新AI头像错误: {e}")
                import traceback
                traceback.print_exc()
                self.send_json({'success': False, 'error': str(e)}, status=500)

        elif self.path == '/api/user/update-ai-assistant-name':
            # 更新AI助理名字
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                ai_assistant_name = data.get('ai_assistant_name', '小助手')

                # 更新AI助理名字
                success = user_manager.update_ai_assistant_name(user_id, ai_assistant_name)

                if success:
                    self.send_json({
                        'success': True,
                        'message': 'AI助理名字更新成功'
                    })
                else:
                    self.send_json({'success': False, 'message': 'AI助理名字更新失败'}, status=500)
            except Exception as e:
                print(f"更新AI助理名字错误: {e}")
                import traceback
                traceback.print_exc()
                self.send_json({'success': False, 'error': str(e)}, status=500)

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

        elif self.path == '/api/user/settings':
            # 更新用户设置
            user_id = self.require_auth()
            if user_id is None:
                return

            settings = data.get('settings', {})
            if not settings:
                self.send_json({'success': False, 'message': '设置不能为空'}, status=400)
                return

            try:
                with db_manager.get_cursor() as cursor:
                    for key, value in settings.items():
                        cursor.execute(
                            """
                            INSERT INTO user_settings (user_id, setting_key, setting_value)
                            VALUES (%s, %s, %s)
                            ON DUPLICATE KEY UPDATE setting_value = %s
                            """,
                            (user_id, key, value, value)
                        )
                    self.send_json({'success': True, 'message': '设置已更新'})
            except Exception as e:
                print(f"更新用户设置失败: {e}")
                self.send_json({'success': False, 'message': str(e)}, status=500)

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

        # ========================================
        # 好友系统API
        # ========================================

        elif self.path == '/api/social/friends/request':
            # 发送好友请求
            user_id = self.require_auth()
            if user_id is None:
                return

            friend_id = data.get('friend_id')
            if not friend_id:
                self.send_json({'success': False, 'message': '请提供好友ID'})
                return

            result = friendship_manager.send_friend_request(user_id, friend_id)
            self.send_json(result)

        elif self.path == '/api/social/friends/accept':
            # 接受好友请求
            user_id = self.require_auth()
            if user_id is None:
                return

            friendship_id = data.get('friendship_id')
            if not friendship_id:
                self.send_json({'success': False, 'message': '请提供好友关系ID'})
                return

            result = friendship_manager.accept_friend_request(user_id, friendship_id)
            self.send_json(result)

        elif self.path == '/api/social/friends/reject':
            # 拒绝好友请求
            user_id = self.require_auth()
            if user_id is None:
                return

            friendship_id = data.get('friendship_id')
            if not friendship_id:
                self.send_json({'success': False, 'message': '请提供好友关系ID'})
                return

            result = friendship_manager.reject_friend_request(user_id, friendship_id)
            self.send_json(result)

        elif self.path == '/api/social/friends/delete':
            # 删除好友
            user_id = self.require_auth()
            if user_id is None:
                return

            friend_id = data.get('friend_id')
            if not friend_id:
                self.send_json({'success': False, 'message': '请提供好友ID'})
                return

            result = friendship_manager.delete_friend(user_id, friend_id)
            self.send_json(result)

        elif self.path == '/api/social/friends/block':
            # 拉黑用户
            user_id = self.require_auth()
            if user_id is None:
                return

            target_id = data.get('target_id')
            if not target_id:
                self.send_json({'success': False, 'message': '请提供目标用户ID'})
                return

            result = friendship_manager.block_user(user_id, target_id)
            self.send_json(result)

        # ========================================
        # 私信系统API
        # ========================================

        elif self.path == '/api/social/messages/send':
            # 发送私信
            user_id = self.require_auth()
            if user_id is None:
                return

            receiver_id = data.get('receiver_id')
            content = data.get('content', '')
            message_type = data.get('message_type', 'text')
            image_id = data.get('image_id')
            file_id = data.get('file_id')

            if not receiver_id:
                self.send_json({'success': False, 'message': '请提供接收者ID'})
                return

            if not content:
                self.send_json({'success': False, 'message': '消息内容不能为空'})
                return

            result = private_message_manager.send_message(user_id, receiver_id, content, message_type, image_id, file_id)
            self.send_json(result)

        elif self.path == '/api/social/messages/mark-read':
            # 标记消息为已读
            user_id = self.require_auth()
            if user_id is None:
                return

            message_ids = data.get('message_ids', [])
            if not message_ids:
                self.send_json({'success': False, 'message': '请提供消息ID列表'})
                return

            result = private_message_manager.mark_as_read(user_id, message_ids)
            self.send_json(result)

        elif self.path == '/api/social/messages/delete':
            # 删除消息
            user_id = self.require_auth()
            if user_id is None:
                return

            message_id = data.get('message_id')
            if not message_id:
                self.send_json({'success': False, 'message': '请提供消息ID'})
                return

            result = private_message_manager.delete_message(user_id, message_id)
            self.send_json(result)

        elif self.path == '/api/social/messages/delete-conversation':
            # 删除整个会话
            user_id = self.require_auth()
            if user_id is None:
                return

            friend_id = data.get('friend_id')
            if not friend_id:
                self.send_json({'success': False, 'message': '请提供好友ID'})
                return

            result = private_message_manager.delete_conversation(user_id, friend_id)
            self.send_json(result)

        # ========================================
        # 好友提醒系统API (POST)
        # ========================================

        elif self.path == '/api/social/reminders/create':
            # 创建好友提醒
            user_id = self.require_auth()
            if user_id is None:
                return

            friend_id = data.get('friend_id')
            content = data.get('content')
            remind_time = data.get('remind_time')
            repeat_type = data.get('repeat_type', 'once')

            if not friend_id:
                self.send_json({'success': False, 'message': '请提供好友ID'})
                return

            if not content:
                self.send_json({'success': False, 'message': '提醒内容不能为空'})
                return

            if not remind_time:
                self.send_json({'success': False, 'message': '请提供提醒时间'})
                return

            result = reminder_sys.add_friend_reminder(user_id, friend_id, content, remind_time, repeat_type)
            self.send_json(result)

        elif self.path == '/api/social/reminders/confirm':
            # 确认好友提醒
            user_id = self.require_auth()
            if user_id is None:
                return

            reminder_id = data.get('reminder_id')
            if not reminder_id:
                self.send_json({'success': False, 'message': '请提供提醒ID'})
                return

            result = reminder_sys.confirm_friend_reminder(reminder_id, user_id)
            self.send_json(result)

        elif self.path == '/api/reminders/confirm':
            # 确认个人提醒
            user_id = self.require_auth()
            if user_id is None:
                return

            reminder_id = data.get('reminder_id')
            if not reminder_id:
                self.send_json({'success': False, 'message': '请提供提醒ID'})
                return

            result = reminder_sys.confirm_personal_reminder(reminder_id, user_id)
            self.send_json(result)

        # ========================================
        # 内容分享系统API
        # ========================================

        elif self.path == '/api/social/shares/create':
            # 创建分享
            user_id = self.require_auth()
            if user_id is None:
                return

            content_type = data.get('content_type', 'text')
            title = data.get('title')
            content = data.get('content')
            image_id = data.get('image_id')
            visibility = data.get('visibility', 'friends')
            tags = data.get('tags', [])

            if not content and not image_id:
                self.send_json({'success': False, 'message': '内容或图片至少提供一个'})
                return

            result = shared_content_manager.create_share(user_id, content_type, title, content, image_id, visibility, tags)
            self.send_json(result)

        elif self.path == '/api/social/shares/delete':
            # 删除分享
            user_id = self.require_auth()
            if user_id is None:
                return

            share_id = data.get('share_id')
            if not share_id:
                self.send_json({'success': False, 'message': '请提供分享ID'})
                return

            result = shared_content_manager.delete_share(user_id, share_id)
            self.send_json(result)

        elif self.path == '/api/social/shares/like':
            # 点赞分享
            user_id = self.require_auth()
            if user_id is None:
                return

            share_id = data.get('share_id')
            if not share_id:
                self.send_json({'success': False, 'message': '请提供分享ID'})
                return

            result = shared_content_manager.like_share(user_id, share_id)
            self.send_json(result)

        elif self.path == '/api/social/shares/unlike':
            # 取消点赞
            user_id = self.require_auth()
            if user_id is None:
                return

            share_id = data.get('share_id')
            if not share_id:
                self.send_json({'success': False, 'message': '请提供分享ID'})
                return

            result = shared_content_manager.unlike_share(user_id, share_id)
            self.send_json(result)

        elif self.path == '/api/social/shares/view':
            # 增加浏览次数
            user_id = self.require_auth()
            if user_id is None:
                return

            share_id = data.get('share_id')
            if not share_id:
                self.send_json({'success': False, 'message': '请提供分享ID'})
                return

            result = shared_content_manager.increment_view_count(share_id)
            self.send_json(result)

        # ========================================
        # 留言板系统API
        # ========================================

        elif self.path == '/api/social/guestbook/post':
            # 发表留言
            user_id = self.require_auth()
            if user_id is None:
                return

            owner_id = data.get('owner_id')
            content = data.get('content', '')
            is_public = data.get('is_public', True)
            parent_id = data.get('parent_id')

            if not owner_id:
                self.send_json({'success': False, 'message': '请提供留言板主人ID'})
                return

            if not content:
                self.send_json({'success': False, 'message': '留言内容不能为空'})
                return

            result = guestbook_manager.post_message(owner_id, user_id, content, is_public, parent_id)
            self.send_json(result)

        elif self.path == '/api/social/guestbook/delete':
            # 删除留言
            user_id = self.require_auth()
            if user_id is None:
                return

            message_id = data.get('message_id')
            if not message_id:
                self.send_json({'success': False, 'message': '请提供留言ID'})
                return

            result = guestbook_manager.delete_message(user_id, message_id)
            self.send_json(result)

        elif self.path == '/api/social/guestbook/like':
            # 点赞留言
            user_id = self.require_auth()
            if user_id is None:
                return

            message_id = data.get('message_id')
            if not message_id:
                self.send_json({'success': False, 'message': '请提供留言ID'})
                return

            result = guestbook_manager.like_message(user_id, message_id)
            self.send_json(result)

        elif self.path == '/api/social/guestbook/unlike':
            # 取消点赞
            user_id = self.require_auth()
            if user_id is None:
                return

            message_id = data.get('message_id')
            if not message_id:
                self.send_json({'success': False, 'message': '请提供留言ID'})
                return

            result = guestbook_manager.unlike_message(user_id, message_id)
            self.send_json(result)

        elif self.path == '/api/social/guestbook/unread-count':
            # 获取未读留言数
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                # 获取用户最后查看留言墙的时间
                last_viewed_sql = "SELECT guestbook_last_viewed_at FROM users WHERE id = %s"
                result = db_manager.query(last_viewed_sql, (user_id,))

                last_viewed_at = None
                if result and result[0]['guestbook_last_viewed_at']:
                    last_viewed_at = result[0]['guestbook_last_viewed_at']

                # 统计之后的新留言数（使用动态墙逻辑：好友发布的新内容）
                if last_viewed_at:
                    # 获取我的好友列表
                    friends_sql = """
                        SELECT friend_id
                        FROM friendships
                        WHERE user_id = %s AND status = 'accepted'
                        UNION
                        SELECT user_id as friend_id
                        FROM friendships
                        WHERE friend_id = %s AND status = 'accepted'
                    """
                    friends_result = db_manager.query(friends_sql, (user_id, user_id))
                    friend_ids = [f['friend_id'] for f in friends_result] if friends_result else []

                    if friend_ids:
                        friend_ids_str = ','.join(map(str, friend_ids))
                        # 统计好友发布的新留言和回复（排除我自己发布的）
                        # 包括：1. 顶级留言  2. 所有回复
                        count_sql = f"""
                            SELECT COUNT(*) as count FROM guestbook_messages
                            WHERE author_id IN ({friend_ids_str})
                            AND author_id != %s
                            AND created_at > %s
                            AND (
                                (
                                    parent_id IS NULL
                                    AND (
                                        visibility = 'all_friends'
                                        OR (
                                            visibility = 'specific_friends'
                                            AND JSON_CONTAINS(visible_to_users, %s)
                                        )
                                    )
                                )
                                OR parent_id IS NOT NULL
                            )
                        """
                        count_result = db_manager.query(count_sql, (user_id, last_viewed_at, str(user_id)))
                    else:
                        count_result = [{'count': 0}]
                else:
                    # 如果从未查看过，统计所有好友的留言
                    friends_sql = """
                        SELECT friend_id
                        FROM friendships
                        WHERE user_id = %s AND status = 'accepted'
                        UNION
                        SELECT user_id as friend_id
                        FROM friendships
                        WHERE friend_id = %s AND status = 'accepted'
                    """
                    friends_result = db_manager.query(friends_sql, (user_id, user_id))
                    friend_ids = [f['friend_id'] for f in friends_result] if friends_result else []

                    if friend_ids:
                        friend_ids_str = ','.join(map(str, friend_ids))
                        count_sql = f"""
                            SELECT COUNT(*) as count FROM guestbook_messages
                            WHERE author_id IN ({friend_ids_str})
                            AND author_id != %s
                            AND parent_id IS NULL
                            AND (
                                visibility = 'all_friends'
                                OR (
                                    visibility = 'specific_friends'
                                    AND JSON_CONTAINS(visible_to_users, %s)
                                )
                            )
                        """
                        count_result = db_manager.query(count_sql, (user_id, str(user_id)))
                    else:
                        count_result = [{'count': 0}]

                unread_count = count_result[0]['count'] if count_result else 0
                self.send_json({'success': True, 'unread_count': unread_count})
            except Exception as e:
                print(f"❌ 获取未读留言数失败: {e}")
                self.send_json({'success': False, 'message': str(e)}, status=500)

        elif self.path == '/api/social/guestbook/mark-viewed':
            # 标记留言墙为已查看
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                # 更新用户最后查看留言墙的时间
                update_sql = "UPDATE users SET guestbook_last_viewed_at = NOW() WHERE id = %s"
                db_manager.execute(update_sql, (user_id,))
                self.send_json({'success': True, 'message': '已标记为已查看'})
            except Exception as e:
                print(f"❌ 标记已查看失败: {e}")
                self.send_json({'success': False, 'message': str(e)}, status=500)

        elif self.path == '/api/social/guestbook/post-v2':
            # 发表便签（增强版 - 支持可见范围和回复）
            user_id = self.require_auth()
            if user_id is None:
                return

            owner_id = data.get('owner_id', user_id)  # 默认发布到自己的墙上
            content = data.get('content', '').strip()
            mood_tag = data.get('mood_tag')
            bg_color = data.get('bg_color', '#FFF9C4')
            image_id = data.get('image_id')
            image_ids = data.get('image_ids')  # 新增：支持多张图片
            is_public = data.get('is_public', True)
            parent_id = data.get('parent_id')  # 新增：父留言ID（用于回复）
            visibility = data.get('visibility', 'all_friends')  # 新增：可见范围
            visible_to_users = data.get('visible_to_users')  # 新增：可见用户列表

            if not content:
                self.send_json({'success': False, 'message': '请提供内容'})
                return

            result = guestbook_manager.post_message_v2(
                owner_id=owner_id,
                author_id=user_id,
                content=content,
                mood_tag=mood_tag,
                bg_color=bg_color,
                image_id=image_id,
                image_ids=image_ids,
                is_public=is_public,
                parent_id=parent_id,
                visibility=visibility,
                visible_to_users=visible_to_users
            )
            self.send_json(result)

        elif self.path == '/api/social/guestbook/reaction':
            # 添加表情回应
            user_id = self.require_auth()
            if user_id is None:
                return

            message_id = data.get('message_id')
            reaction_type = data.get('reaction_type')

            if not message_id or not reaction_type:
                self.send_json({'success': False, 'message': '请提供留言ID和表情类型'})
                return

            result = guestbook_manager.add_reaction(message_id, user_id, reaction_type)
            self.send_json(result)

        # ========================================
        # 自定义类别管理API
        # ========================================

        elif self.path == '/api/custom-category/list':
            # 获取用户自定义类别列表
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                query = """
                    SELECT s.id, s.name, s.code, s.description, s.sort_order, s.created_at
                    FROM subcategories s
                    JOIN categories c ON s.category_id = c.id
                    WHERE c.code = 'other' AND s.user_id = %s
                    ORDER BY s.sort_order ASC, s.created_at ASC
                """
                with db_manager.get_cursor() as cursor:
                    cursor.execute(query, (user_id,))
                    categories = cursor.fetchall()

                self.send_json({
                    'success': True,
                    'categories': categories,
                    'count': len(categories)
                })
            except Exception as e:
                print(f"❌ 获取自定义类别失败: {e}")
                self.send_json({'success': False, 'message': f'获取失败: {str(e)}'}, status=500)

        elif self.path == '/api/custom-category/add':
            # 添加自定义类别
            user_id = self.require_auth()
            if user_id is None:
                return

            name = data.get('name', '').strip()
            if not name:
                self.send_json({'success': False, 'message': '类别名称不能为空'}, status=400)
                return

            if len(name) > 10:
                self.send_json({'success': False, 'message': '类别名称不能超过10个字符'}, status=400)
                return

            try:
                # 获取"其他类"的ID
                with db_manager.get_cursor() as cursor:
                    cursor.execute("SELECT id FROM categories WHERE code = 'other'")
                    result = cursor.fetchone()
                    if not result:
                        self.send_json({'success': False, 'message': '系统错误：未找到其他类'}, status=500)
                        return

                    other_category_id = result['id']

                    # 检查是否已达到20个上限
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM subcategories
                        WHERE category_id = %s AND user_id = %s
                    """, (other_category_id, user_id))
                    count_result = cursor.fetchone()

                    if count_result['count'] >= 20:
                        self.send_json({'success': False, 'message': '自定义类别已达上限（最多20个）'}, status=400)
                        return

                    # 检查名称是否重复
                    cursor.execute("""
                        SELECT id FROM subcategories
                        WHERE category_id = %s AND user_id = %s AND name = %s
                    """, (other_category_id, user_id, name))
                    if cursor.fetchone():
                        self.send_json({'success': False, 'message': '类别名称已存在'}, status=400)
                        return

                    # 生成code（使用拼音或简单的编号）
                    import time
                    code = f"custom_{int(time.time() * 1000)}"

                    # 插入新类别
                    cursor.execute("""
                        INSERT INTO subcategories (category_id, name, code, user_id, sort_order)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (other_category_id, name, code, user_id, count_result['count'] + 1))

                    new_id = cursor.lastrowid

                self.send_json({
                    'success': True,
                    'message': '添加成功',
                    'category': {
                        'id': new_id,
                        'name': name,
                        'code': code
                    }
                })

                # ✨ 重置命令路由器，使新类别立即可用
                import sys
                print(f"🔄 准备重置命令路由器，新类别: {name}")
                sys.stdout.flush()

                from command_system import reset_command_router
                reset_command_router()

                print(f"✅ 已重置命令路由器，新类别 '{name}' 将在下次请求时可用")
                sys.stdout.flush()
            except Exception as e:
                print(f"❌ 添加自定义类别失败: {e}")
                self.send_json({'success': False, 'message': f'添加失败: {str(e)}'}, status=500)

        elif self.path == '/api/custom-category/delete':
            # 删除自定义类别
            user_id = self.require_auth()
            if user_id is None:
                return

            category_id = data.get('id')
            if not category_id:
                self.send_json({'success': False, 'message': '缺少类别ID'}, status=400)
                return

            try:
                with db_manager.get_cursor() as cursor:
                    # 验证类别是否属于当前用户
                    cursor.execute("""
                        SELECT s.id, s.name
                        FROM subcategories s
                        JOIN categories c ON s.category_id = c.id
                        WHERE s.id = %s AND s.user_id = %s AND c.code = 'other'
                    """, (category_id, user_id))

                    result = cursor.fetchone()
                    if not result:
                        self.send_json({'success': False, 'message': '类别不存在或权限不足'}, status=403)
                        return

                    # 检查是否有关联的任务
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM work_tasks
                        WHERE subcategory_id = %s AND user_id = %s
                    """, (category_id, user_id))
                    task_count = cursor.fetchone()['count']

                    # 删除类别（关联的任务的subcategory_id会被设置为NULL，因为外键是ON DELETE SET NULL）
                    cursor.execute("DELETE FROM subcategories WHERE id = %s", (category_id,))

                self.send_json({
                    'success': True,
                    'message': '删除成功',
                    'affected_tasks': task_count
                })

                # ✨ 重置命令路由器，使删除的类别立即失效
                import sys
                print(f"🔄 准备重置命令路由器，删除的类别: {result['name']}")
                sys.stdout.flush()

                from command_system import reset_command_router
                reset_command_router()

                print(f"✅ 已重置命令路由器，删除的类别将在下次请求时失效")
                sys.stdout.flush()
            except Exception as e:
                print(f"❌ 删除自定义类别失败: {e}")
                self.send_json({'success': False, 'message': f'删除失败: {str(e)}'}, status=500)

        # ========================================
        # 系统类别管理API
        # ========================================

        elif self.path == '/api/system-category/list':
            # 获取所有系统预设的子类别
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                query = """
                    SELECT s.id, s.name, s.code, s.description, c.name as category_name, c.code as category_code
                    FROM subcategories s
                    JOIN categories c ON s.category_id = c.id
                    WHERE s.user_id IS NULL
                    ORDER BY c.sort_order ASC, s.sort_order ASC
                """
                with db_manager.get_cursor() as cursor:
                    cursor.execute(query)
                    categories = cursor.fetchall()

                self.send_json({
                    'success': True,
                    'categories': categories
                })
            except Exception as e:
                print(f"❌ 获取系统类别失败: {e}")
                self.send_json({'success': False, 'message': f'获取失败: {str(e)}'}, status=500)

        elif self.path == '/api/system-category/enabled':
            # 获取用户已启用的系统类别
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                query = """
                    SELECT s.id, s.name, s.code, c.name as category_name
                    FROM user_enabled_categories uec
                    JOIN subcategories s ON uec.subcategory_id = s.id
                    JOIN categories c ON s.category_id = c.id
                    WHERE uec.user_id = %s
                    ORDER BY uec.enabled_at ASC
                """
                with db_manager.get_cursor() as cursor:
                    cursor.execute(query, (user_id,))
                    enabled = cursor.fetchall()

                self.send_json({
                    'success': True,
                    'enabled': enabled
                })
            except Exception as e:
                print(f"❌ 获取已启用类别失败: {e}")
                self.send_json({'success': False, 'message': f'获取失败: {str(e)}'}, status=500)

        elif self.path == '/api/system-category/enable':
            # 启用系统类别
            user_id = self.require_auth()
            if user_id is None:
                return

            subcategory_id = data.get('subcategory_id')
            if not subcategory_id:
                self.send_json({'success': False, 'message': '缺少子类别ID'}, status=400)
                return

            try:
                with db_manager.get_cursor() as cursor:
                    # 验证子类别是否存在且是系统类别
                    cursor.execute("""
                        SELECT s.id, s.name
                        FROM subcategories s
                        WHERE s.id = %s AND s.user_id IS NULL
                    """, (subcategory_id,))

                    result = cursor.fetchone()
                    if not result:
                        self.send_json({'success': False, 'message': '系统类别不存在'}, status=404)
                        return

                    # 检查是否已启用
                    cursor.execute("""
                        SELECT id FROM user_enabled_categories
                        WHERE user_id = %s AND subcategory_id = %s
                    """, (user_id, subcategory_id))

                    if cursor.fetchone():
                        self.send_json({'success': False, 'message': '该类别已启用'}, status=400)
                        return

                    # 启用类别
                    cursor.execute("""
                        INSERT INTO user_enabled_categories (user_id, subcategory_id)
                        VALUES (%s, %s)
                    """, (user_id, subcategory_id))

                self.send_json({
                    'success': True,
                    'message': '启用成功',
                    'category': result
                })
            except Exception as e:
                print(f"❌ 启用系统类别失败: {e}")
                self.send_json({'success': False, 'message': f'启用失败: {str(e)}'}, status=500)

        elif self.path == '/api/system-category/disable':
            # 禁用系统类别
            user_id = self.require_auth()
            if user_id is None:
                return

            subcategory_id = data.get('subcategory_id')
            if not subcategory_id:
                self.send_json({'success': False, 'message': '缺少子类别ID'}, status=400)
                return

            try:
                with db_manager.get_cursor() as cursor:
                    # 删除启用记录
                    cursor.execute("""
                        DELETE FROM user_enabled_categories
                        WHERE user_id = %s AND subcategory_id = %s
                    """, (user_id, subcategory_id))

                    if cursor.rowcount == 0:
                        self.send_json({'success': False, 'message': '该类别未启用'}, status=400)
                        return

                self.send_json({
                    'success': True,
                    'message': '禁用成功'
                })
            except Exception as e:
                print(f"❌ 禁用系统类别失败: {e}")
                self.send_json({'success': False, 'message': f'禁用失败: {str(e)}'}, status=500)

        elif self.path == '/api/button-usage/record':
            # 记录快捷按键使用
            user_id = self.require_auth()
            if user_id is None:
                return

            button_name = data.get('button_name')
            if not button_name:
                self.send_json({'success': False, 'message': '缺少按键名称'}, status=400)
                return

            try:
                with db_manager.get_cursor() as cursor:
                    # 使用INSERT ... ON DUPLICATE KEY UPDATE来增加计数
                    cursor.execute("""
                        INSERT INTO button_usage_stats (user_id, button_name, usage_count, last_used_at)
                        VALUES (%s, %s, 1, NOW())
                        ON DUPLICATE KEY UPDATE
                            usage_count = usage_count + 1,
                            last_used_at = NOW()
                    """, (user_id, button_name))

                self.send_json({
                    'success': True,
                    'message': '记录成功'
                })
            except Exception as e:
                print(f"❌ 记录按键使用失败: {e}")
                self.send_json({'success': False, 'message': f'记录失败: {str(e)}'}, status=500)

        elif self.path == '/api/button-usage/stats':
            # 获取快捷按键使用统计
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                with db_manager.get_cursor() as cursor:
                    cursor.execute("""
                        SELECT button_name, usage_count, last_used_at
                        FROM button_usage_stats
                        WHERE user_id = %s
                        ORDER BY usage_count DESC, last_used_at DESC
                    """, (user_id,))
                    stats = cursor.fetchall()

                self.send_json({
                    'success': True,
                    'stats': stats
                })
            except Exception as e:
                print(f"❌ 获取按键统计失败: {e}")
                self.send_json({'success': False, 'message': f'获取失败: {str(e)}'}, status=500)

        elif self.path == '/api/button/hide':
            # 隐藏快捷按键
            user_id = self.require_auth()
            if user_id is None:
                return

            button_name = data.get('button_name')
            if not button_name:
                self.send_json({'success': False, 'message': '缺少按键名称'}, status=400)
                return

            try:
                with db_manager.get_cursor() as cursor:
                    cursor.execute("""
                        INSERT IGNORE INTO hidden_buttons (user_id, button_name)
                        VALUES (%s, %s)
                    """, (user_id, button_name))

                self.send_json({
                    'success': True,
                    'message': '隐藏成功'
                })
            except Exception as e:
                print(f"❌ 隐藏按键失败: {e}")
                self.send_json({'success': False, 'message': f'隐藏失败: {str(e)}'}, status=500)

        elif self.path == '/api/button/show':
            # 显示快捷按键
            user_id = self.require_auth()
            if user_id is None:
                return

            button_name = data.get('button_name')
            if not button_name:
                self.send_json({'success': False, 'message': '缺少按键名称'}, status=400)
                return

            try:
                with db_manager.get_cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM hidden_buttons
                        WHERE user_id = %s AND button_name = %s
                    """, (user_id, button_name))

                self.send_json({
                    'success': True,
                    'message': '显示成功'
                })
            except Exception as e:
                print(f"❌ 显示按键失败: {e}")
                self.send_json({'success': False, 'message': f'显示失败: {str(e)}'}, status=500)

        elif self.path == '/api/button/hidden-list':
            # 获取隐藏的按键列表
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                with db_manager.get_cursor() as cursor:
                    cursor.execute("""
                        SELECT button_name
                        FROM hidden_buttons
                        WHERE user_id = %s
                    """, (user_id,))
                    hidden = cursor.fetchall()

                self.send_json({
                    'success': True,
                    'hidden': [h['button_name'] for h in hidden]
                })
            except Exception as e:
                print(f"❌ 获取隐藏按键列表失败: {e}")
                self.send_json({'success': False, 'message': f'获取失败: {str(e)}'}, status=500)

        # ========== FCM推送通知相关API ==========
        elif self.path == '/api/device/register-token':
            # 注册设备token
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                # 使用已经解析好的 data 变量，不要重复读取 POST 数据
                device_token = data.get('device_token')
                device_type = data.get('device_type')
                device_name = data.get('device_name')
                device_model = data.get('device_model')
                app_version = data.get('app_version')

                if not device_token or not device_type:
                    self.send_json({'status': 'error', 'message': '缺少必要参数'}, status=400)
                    return

                success = device_token_manager.save_device_token(
                    user_id=user_id,
                    device_token=device_token,
                    device_type=device_type,
                    device_name=device_name,
                    device_model=device_model,
                    app_version=app_version
                )

                if success:
                    self.send_json({'status': 'success', 'message': '设备token已注册'})
                else:
                    self.send_json({'status': 'error', 'message': '注册失败'}, status=500)

            except Exception as e:
                print(f"❌ 注册设备token失败: {e}")
                self.send_json({'status': 'error', 'message': str(e)}, status=500)

        elif self.path == '/api/device/deactivate-token':
            # 停用设备token
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                # 使用已经解析好的 data 变量
                device_token = data.get('device_token')

                if not device_token:
                    self.send_json({'status': 'error', 'message': '缺少device_token参数'}, status=400)
                    return

                success = device_token_manager.deactivate_device_token(device_token)

                if success:
                    self.send_json({'status': 'success', 'message': '设备token已停用'})
                else:
                    self.send_json({'status': 'error', 'message': '停用失败'}, status=500)

            except Exception as e:
                print(f"❌ 停用设备token失败: {e}")
                self.send_json({'status': 'error', 'message': str(e)}, status=500)

        elif self.path == '/api/device/test-push':
            # 测试推送通知
            user_id = self.require_auth()
            if user_id is None:
                return

            try:
                devices = device_token_manager.get_user_device_tokens(user_id, active_only=True)

                if not devices:
                    self.send_json({'status': 'error', 'message': '没有找到活跃的设备token'}, status=404)
                    return

                device_tokens = [d['device_token'] for d in devices]

                result = fcm_service.send_reminder_notification(
                    device_tokens=device_tokens,
                    reminder_content='这是一条测试推送通知',
                    reminder_id=None
                )

                self.send_json({
                    'status': 'success' if result.get('success') or result.get('success_count', 0) > 0 else 'error',
                    'message': '推送通知已发送',
                    'result': result
                })

            except Exception as e:
                print(f"❌ 测试推送失败: {e}")
                self.send_json({'status': 'error', 'message': str(e)}, status=500)

        else:
            self.send_error(404)

    def _handle_avatar_upload(self):
        """处理头像上传 (multipart/form-data)"""
        # 先检查认证信息
        auth_header = self.headers.get('Authorization', '')
        print(f"[DEBUG] Authorization header: {auth_header[:50] if auth_header else 'MISSING'}")

        user_id = self.require_auth()
        if user_id is None:
            print("[ERROR] Authentication failed - no valid user_id")
            return

        print(f"[DEBUG] Authenticated user_id: {user_id}")

        try:
            # 解析 multipart/form-data
            content_type = self.headers['Content-Type']
            content_length = int(self.headers['Content-Length'])

            print(f"[DEBUG] Content-Type: {content_type}")
            print(f"[DEBUG] Content-Length: {content_length}")

            # 读取原始数据
            raw_data = self.rfile.read(content_length)
            print(f"[DEBUG] Read {len(raw_data)} bytes")

            # 提取 boundary
            if 'boundary=' not in content_type:
                self.send_json({'success': False, 'error': 'Missing boundary in Content-Type'}, status=400)
                return

            boundary = content_type.split('boundary=')[1].strip()
            if boundary.startswith('"') and boundary.endswith('"'):
                boundary = boundary[1:-1]

            print(f"[DEBUG] Boundary: {boundary}")

            # boundary 的完整格式
            boundary_bytes = ('--' + boundary).encode('utf-8')
            end_boundary_bytes = ('--' + boundary + '--').encode('utf-8')

            # 分割数据
            parts = raw_data.split(boundary_bytes)
            print(f"[DEBUG] Found {len(parts)} parts")

            image_bytes = None
            for i, part in enumerate(parts):
                print(f"[DEBUG] Part {i}: {len(part)} bytes")
                if len(part) < 10:  # 跳过太小的部分
                    continue

                # 打印部分头部用于调试
                header_preview = part[:200] if len(part) > 200 else part
                print(f"[DEBUG] Part {i} header: {header_preview}")

                # 查找 Content-Disposition 和 filename
                if b'Content-Disposition' in part:
                    # 查找双换行符(标志着头部结束)
                    header_end = part.find(b'\r\n\r\n')
                    if header_end == -1:
                        header_end = part.find(b'\n\n')

                    if header_end != -1:
                        headers = part[:header_end]
                        body = part[header_end+4:] if b'\r\n\r\n' in part[:header_end+4] else part[header_end+2:]

                        print(f"[DEBUG] Found headers: {headers}")
                        print(f"[DEBUG] Body length: {len(body)}")

                        # 检查是否有文件内容
                        if b'filename=' in headers or b'name="avatar"' in headers:
                            # 移除末尾的 \r\n 或 \n
                            while body.endswith(b'\r\n') or body.endswith(b'\n') or body.endswith(b'\r'):
                                body = body.rstrip(b'\r\n')

                            # 移除结束边界
                            if end_boundary_bytes in body:
                                body = body.split(end_boundary_bytes)[0]

                            if len(body) > 0:
                                image_bytes = body
                                print(f"[DEBUG] Extracted image: {len(image_bytes)} bytes")
                                break

            if not image_bytes or len(image_bytes) < 100:
                # 收集调试信息
                debug_info = []
                debug_info.append(f"Parts found: {len(parts)}")
                for i, part in enumerate(parts):
                    if len(part) > 10 and b'Content-Disposition' in part:
                        header_end = part.find(b'\r\n\r\n')
                        if header_end == -1:
                            header_end = part.find(b'\n\n')
                        if header_end != -1:
                            headers_preview = part[:min(header_end, 300)].decode('utf-8', errors='ignore')
                            debug_info.append(f"Part {i} headers: {headers_preview}")

                error_msg = f'没有找到图片数据 (found {len(image_bytes) if image_bytes else 0} bytes). Debug: {"; ".join(debug_info)}'
                print(f"[ERROR] {error_msg}")
                self.send_json({'success': False, 'error': error_msg}, status=400)
                return

            # 生成唯一文件名
            filename = f"avatar_{user_id}_{uuid.uuid4().hex}.jpg"

            # 创建 avatars 目录
            avatar_dir = 'uploads/avatars'
            os.makedirs(avatar_dir, exist_ok=True)

            file_path = os.path.join(avatar_dir, filename)

            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(image_bytes)

            print(f"[DEBUG] Saved to {file_path}")

            # 更新用户头像URL
            avatar_url = f'/uploads/avatars/{filename}'
            success = user_manager.update_avatar(user_id, avatar_url)

            if success:
                print(f"[DEBUG] Avatar updated successfully: {avatar_url}")
                self.send_json({
                    'success': True,
                    'message': '头像上传成功',
                    'avatar_url': avatar_url
                })
            else:
                self.send_json({'success': False, 'error': '更新头像URL失败'}, status=500)
        except Exception as e:
            print(f"头像上传错误: {e}")
            import traceback
            traceback.print_exc()
            self.send_json({'success': False, 'error': str(e)}, status=500)

    def send_json(self, data, status=200):
        """发送JSON响应"""
        from datetime import datetime, date
        # 自定义 JSON 编码器，支持 Decimal 和 datetime 类型
        class CustomEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, Decimal):
                    return float(obj)
                if isinstance(obj, (datetime, date)):
                    return obj.strftime('%Y-%m-%d %H:%M:%S') if isinstance(obj, datetime) else obj.strftime('%Y-%m-%d')
                return super().default(obj)

        self.send_response(status)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, cls=CustomEncoder).encode('utf-8'))
    
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

    def serve_file(self, filepath):
        """发送文件（通用）"""
        try:
            # 安全检查：防止目录遍历
            if '..' in filepath or filepath.startswith('/'):
                self.send_error(403, 'Forbidden')
                return

            if not os.path.exists(filepath):
                 self.send_error(404, 'File not found')
                 return

            with open(filepath, 'rb') as f:
                content = f.read()

            import mimetypes
            content_type, _ = mimetypes.guess_type(filepath)
            if not content_type:
                content_type = 'application/octet-stream'

            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f'Failed to read file: {e}')
    
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

        elif self.path == '/api/social/guestbook/reaction':
            # 移除表情回应
            user_id = self.require_auth()
            if user_id is None:
                return

            # 从请求体获取参数
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))

                message_id = data.get('message_id')
                reaction_type = data.get('reaction_type')

                if not message_id or not reaction_type:
                    self.send_json({'success': False, 'message': '请提供留言ID和表情类型'})
                    return

                result = guestbook_manager.remove_reaction(message_id, user_id, reaction_type)
                self.send_json(result)
            else:
                self.send_json({'success': False, 'message': '请求体为空'}, status=400)

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

    def send_social_html(self):
        """发送社交中心页面"""
        try:
            with open('social.html', 'r', encoding='utf-8') as f:
                html_content = f.read()
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        except Exception as e:
            print(f"❌ 读取 social.html 失败: {e}")
            self.send_error(404, 'Social page not found')

    def send_file_manager_html(self):
        """发送文件管理页面"""
        html_content = self.get_file_manager_template()
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def get_file_manager_template(self):
        """获取文件管理页面模板"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文件管理 - 个人AI助理</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }

        .back-link {
            display: inline-block;
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            margin-bottom: 20px;
            transition: all 0.3s;
        }

        .back-link:hover {
            background: rgba(255,255,255,0.2);
        }

        .container {
            max-width: 100%;
            width: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 30px 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }

        @media (min-width: 1920px) {
            .container {
                max-width: 1800px;
            }
        }

        h1 {
            font-size: 32px;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            color: #666;
            margin-bottom: 30px;
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

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 20px;
            border-radius: 12px;
            color: white;
            text-align: center;
        }

        .stat-card:nth-child(2) {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }

        .stat-card:nth-child(3) {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        }

        .stat-card h3 {
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 10px;
        }

        .stat-card .value {
            font-size: 32px;
            font-weight: 700;
        }

        .category-filters {
            display: flex;
            gap: 10px;
            margin-bottom: 25px;
            flex-wrap: wrap;
        }

        .category-tag {
            padding: 8px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s;
            background: white;
            font-size: 14px;
        }

        .category-tag:hover {
            border-color: #667eea;
            color: #667eea;
        }

        .category-tag.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }

        .file-grid {
            margin-bottom: 30px;
        }

        /* 卡片式布局（图片类别使用）*/
        .file-grid:not(:has(.file-list)) {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }

        .file-card {
            background: #f8f9fa;
            border-radius: 12px;
            overflow: hidden;
            transition: all 0.3s;
            border: 2px solid transparent;
        }

        .file-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.1);
            border-color: #667eea;
        }

        .file-icon-wrapper {
            height: 150px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
            font-size: 64px;
        }

        .file-info {
            padding: 15px;
        }

        .file-card .filename {
            font-size: 14px;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .file-card .description {
            font-size: 13px;
            color: #666;
            margin-bottom: 8px;
            line-height: 1.4;
            max-height: 40px;
            overflow: hidden;
        }

        .file-card .tags {
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

        .file-card .meta {
            font-size: 11px;
            color: #999;
            margin-bottom: 12px;
        }

        .file-card .actions {
            display: flex;
            gap: 8px;
        }

        .file-card .actions button {
            flex: 1;
            padding: 8px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }

        .btn-download {
            background: #28a745;
            color: white;
        }

        .btn-download:hover {
            background: #218838;
        }

        .btn-delete {
            background: #ff4444;
            color: white;
        }

        .btn-delete:hover {
            background: #cc0000;
        }

        .btn-share {
            background: #17a2b8;
            color: white;
        }

        .btn-share:hover {
            background: #138496;
        }

        /* 好友选择弹窗 */
        .share-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 10000;
            align-items: center;
            justify-content: center;
        }

        .share-modal.active {
            display: flex;
        }

        .share-modal-content {
            background: white;
            border-radius: 16px;
            padding: 30px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }

        .share-modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .share-modal-header h2 {
            font-size: 20px;
            color: #333;
        }

        .share-modal-close {
            background: none;
            border: none;
            font-size: 28px;
            cursor: pointer;
            color: #999;
            line-height: 1;
        }

        .share-modal-close:hover {
            color: #333;
        }

        .friend-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .friend-item {
            display: flex;
            align-items: center;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .friend-item:hover {
            border-color: #667eea;
            background: #f8f9fa;
        }

        .friend-item.selected {
            border-color: #667eea;
            background: #e3f2fd;
        }

        .friend-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            margin-right: 12px;
        }

        .friend-info {
            flex: 1;
        }

        .friend-name {
            font-size: 15px;
            font-weight: 600;
            color: #333;
        }

        .friend-status {
            font-size: 12px;
            color: #999;
        }

        .share-modal-footer {
            margin-top: 20px;
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }

        .share-modal-footer button {
            padding: 10px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
        }

        .share-modal-footer .btn-cancel {
            background: #e0e0e0;
            color: #666;
        }

        .share-modal-footer .btn-cancel:hover {
            background: #d0d0d0;
        }

        .share-modal-footer .btn-confirm {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .share-modal-footer .btn-confirm:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .share-modal-footer .btn-confirm:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        /* 列表布局样式 - 表格式 */
        .file-list {
            width: 100%;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: block !important; /* 覆盖父容器的grid */
        }

        /* 大屏幕：自动扩展填充空间 */
        @media (min-width: 900px) {
            .file-list {
                overflow-x: auto; /* 内容过宽时允许滚动 */
            }

            .file-list-header {
                display: grid;
                grid-template-columns: 3fr 2fr 1fr 1.5fr 1.5fr;
                gap: 20px;
                padding: 14px 24px;
                background: #f5f5f5;
                border-bottom: 2px solid #e0e0e0;
                font-size: 13px;
                font-weight: 600;
                color: #666;
            }

            .file-list-item {
                display: grid;
                grid-template-columns: 3fr 2fr 1fr 1.5fr 1.5fr;
                gap: 20px;
                align-items: center;
                padding: 12px 24px;
                transition: all 0.2s;
                border-bottom: 1px solid #f0f0f0;
            }
        }

        /* 中等屏幕：固定最小宽度，允许横向滚动 */
        @media (max-width: 899px) and (min-width: 769px) {
            .file-list {
                overflow-x: auto;
            }

            .file-list-header {
                display: grid;
                grid-template-columns: minmax(180px, 2.5fr) minmax(140px, 1.3fr) minmax(70px, 0.7fr) minmax(110px, 1.1fr) minmax(130px, 1fr);
                gap: 16px;
                padding: 14px 24px;
                background: #f5f5f5;
                border-bottom: 2px solid #e0e0e0;
                font-size: 13px;
                font-weight: 600;
                color: #666;
                min-width: 630px;
            }

            .file-list-item {
                display: grid;
                grid-template-columns: minmax(180px, 2.5fr) minmax(140px, 1.3fr) minmax(70px, 0.7fr) minmax(110px, 1.1fr) minmax(130px, 1fr);
                gap: 16px;
                align-items: center;
                padding: 12px 24px;
                transition: all 0.2s;
                border-bottom: 1px solid #f0f0f0;
                min-width: 630px;
            }
        }

        .file-list-item:hover {
            background: #f8f9fa;
        }

        .file-list-item:last-child {
            border-bottom: none;
        }

        .file-list-cell-name {
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 0;
        }

        .file-list-icon {
            font-size: 24px;
            flex-shrink: 0;
        }

        .file-list-name {
            font-size: 14px;
            font-weight: 500;
            color: #333;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .file-list-cell {
            font-size: 13px;
            color: #666;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .file-list-actions {
            display: flex;
            gap: 8px;
            justify-content: flex-end;
        }

        .file-list-actions button {
            padding: 6px 14px;
            font-size: 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
            white-space: nowrap;
        }

        /* 移动端 */
        @media (max-width: 768px) {
            .file-list-header {
                display: none;
            }

            .file-list-item {
                grid-template-columns: 1fr;
                gap: 8px;
                padding: 15px;
            }

            .file-list-cell-name {
                grid-column: 1;
            }

            .file-list-cell {
                font-size: 12px;
                padding-left: 40px;
            }

            .file-list-actions {
                grid-column: 1;
                justify-content: flex-start;
                padding-left: 40px;
            }
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
            grid-column: 1 / -1;
        }

        .empty-state svg {
            width: 120px;
            height: 120px;
            margin-bottom: 20px;
            opacity: 0.3;
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

        .preview-item {
            background: white;
            padding: 15px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 10px;
        }

        .preview-item .icon {
            font-size: 32px;
        }

        .preview-item .info {
            flex: 1;
        }

        .preview-item .remove {
            background: #ff4444;
            color: white;
            border: none;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
        }
    </style>
</head>
<body>
    <a href="/ai/" class="back-link">← 返回主页</a>

    <div class="container">
        <h1>📁 文件管理</h1>
        <p class="subtitle">管理您的所有文件 - 支持文档、图片、音视频等多种格式</p>

        <div class="stats">
            <div class="stat-card">
                <h3>📊 文件总数</h3>
                <div class="value" id="totalFiles">0</div>
            </div>
            <div class="stat-card">
                <h3>💾 存储空间</h3>
                <div class="value" id="totalSize">0 MB</div>
            </div>
            <div class="stat-card">
                <h3>📅 今日上传</h3>
                <div class="value" id="todayUploads">0</div>
            </div>
        </div>

        <div class="toolbar">
            <input type="file" id="fileUpload" multiple>
            <button class="btn btn-primary" onclick="document.getElementById('fileUpload').click()">
                ⬆️ 上传文件
            </button>
            <input type="text" id="searchKeyword" class="search-box" placeholder="搜索文件名或描述..." onkeypress="if(event.key==='Enter') searchFiles()">
            <button class="btn btn-success" onclick="searchFiles()">🔍 搜索</button>
        </div>

        <div class="category-filters">
            <div class="category-tag active" data-category="all" onclick="filterByCategory('all', event)">
                📋 全部
            </div>
            <div class="category-tag" data-category="document" onclick="filterByCategory('document', event)">
                📄 文档
            </div>
            <div class="category-tag" data-category="image" onclick="filterByCategory('image', event)">
                🖼️ 图片
            </div>
            <div class="category-tag" data-category="video" onclick="filterByCategory('video', event)">
                🎬 视频
            </div>
            <div class="category-tag" data-category="audio" onclick="filterByCategory('audio', event)">
                🎵 音频
            </div>
            <div class="category-tag" data-category="archive" onclick="filterByCategory('archive', event)">
                📦 压缩包
            </div>
            <div class="category-tag" data-category="other" onclick="filterByCategory('other', event)">
                📎 其他
            </div>
        </div>

        <div id="uploadPreview" class="upload-preview">
            <h3>准备上传的文件</h3>
            <div id="previewList"></div>
            <div id="uploadProgress" style="display:none; margin:15px 0;">
                <div style="margin-bottom:8px; color:#666; font-size:14px; display:flex; justify-content:space-between; align-items:center;">
                    <span id="uploadStatus">正在上传...</span>
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span id="uploadPercent" style="font-weight:600;">0%</span>
                        <button id="cancelUploadBtn" onclick="cancelUpload()" style="padding:4px 12px; background:#dc3545; color:white; border:none; border-radius:4px; cursor:pointer; font-size:12px;">取消</button>
                    </div>
                </div>
                <div style="width:100%; height:24px; background:#e9ecef; border-radius:12px; overflow:hidden;">
                    <div id="progressBar" style="width:0%; height:100%; background:linear-gradient(90deg, #4CAF50, #81C784); transition:width 0.3s ease;"></div>
                </div>
                <div style="margin-top:8px; font-size:12px; color:#999;">
                    <span id="uploadedSize">0 MB</span> / <span id="totalSize">0 MB</span>
                </div>
            </div>
            <input type="text" id="bulkDesc" placeholder="添加文件描述（可选）" style="width:100%; padding:10px; margin-bottom:10px; border:1px solid #ddd; border-radius:6px;">
            <input type="text" id="bulkTags" placeholder="添加标签，用逗号分隔（可选）" style="width:100%; padding:10px; margin-bottom:10px; border:1px solid #ddd; border-radius:6px;">
            <button class="btn btn-success" onclick="uploadFiles()" style="width:100%;">✅ 开始上传</button>
        </div>

        <div id="fileGrid" class="file-grid">
            <div class="empty-state">正在加载文件...</div>
        </div>
    </div>

    <!-- 好友选择弹窗 -->
    <div id="shareModal" class="share-modal">
        <div class="share-modal-content">
            <div class="share-modal-header">
                <h2>📤 分享文件给好友</h2>
                <button class="share-modal-close" onclick="closeShareModal()">×</button>
            </div>
            <div id="shareFileName" style="margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 8px; font-size: 14px; color: #666;">
                正在分享：<span id="shareFileNameText" style="color: #333; font-weight: 600;"></span>
            </div>
            <div id="friendList" class="friend-list">
                <div style="text-align: center; padding: 20px; color: #999;">正在加载好友列表...</div>
            </div>
            <div class="share-modal-footer">
                <button class="btn-cancel" onclick="closeShareModal()">取消</button>
                <button class="btn-confirm" id="confirmShareBtn" onclick="confirmShare()" disabled>确认分享</button>
            </div>
        </div>
    </div>

    <script>
        let selectedFiles = [];
        let allFiles = [];
        let currentCategory = 'all';

        window.onload = function() {
            loadAllFiles();
            // loadStats(); // 移除这里的调用，改为在loadAllFiles完成后调用
        };

        document.getElementById('fileUpload').addEventListener('change', function(e) {
            selectedFiles = Array.from(e.target.files);
            if (selectedFiles.length > 0) {
                showUploadPreview();
            }
        });

        function showUploadPreview() {
            const preview = document.getElementById('uploadPreview');
            const list = document.getElementById('previewList');

            list.innerHTML = selectedFiles.map((file, index) => {
                const icon = getFileIconByType(file.type);
                const size = formatFileSize(file.size);
                return `
                    <div class="preview-item">
                        <div class="icon">${icon}</div>
                        <div class="info">
                            <div style="font-weight:600;">${file.name}</div>
                            <div style="font-size:12px; color:#666;">${size}</div>
                        </div>
                        <button class="remove" onclick="removeFile(${index})">×</button>
                    </div>
                `;
            }).join('');

            preview.classList.add('active');
        }

        function removeFile(index) {
            selectedFiles.splice(index, 1);
            if (selectedFiles.length === 0) {
                document.getElementById('uploadPreview').classList.remove('active');
            } else {
                showUploadPreview();
            }
        }

        // 上传取消控制
        let uploadCancelled = false;
        let currentXhr = null;

        function cancelUpload() {
            if (confirm('确定要取消上传吗？')) {
                uploadCancelled = true;
                if (currentXhr) {
                    currentXhr.abort();
                }
                document.getElementById('uploadStatus').textContent = '❌ 上传已取消';
                document.getElementById('cancelUploadBtn').disabled = true;
                setTimeout(() => {
                    document.getElementById('uploadProgress').style.display = 'none';
                    document.getElementById('progressBar').style.width = '0%';
                    uploadCancelled = false;
                    document.getElementById('cancelUploadBtn').disabled = false;
                }, 2000);
            }
        }

        async function uploadFiles() {
            const description = document.getElementById('bulkDesc').value;
            const tagsInput = document.getElementById('bulkTags').value;
            const tags = tagsInput.split(',').map(t => t.trim()).filter(t => t);
            const token = localStorage.getItem('token');

            if (!token) {
                alert('请先登录');
                return;
            }

            // 重置取消标志
            uploadCancelled = false;

            // 显示进度条
            const progressDiv = document.getElementById('uploadProgress');
            const progressBar = document.getElementById('progressBar');
            const uploadPercent = document.getElementById('uploadPercent');
            const uploadStatus = document.getElementById('uploadStatus');
            const uploadedSize = document.getElementById('uploadedSize');
            const totalSize = document.getElementById('totalSize');

            progressDiv.style.display = 'block';

            // 计算总大小
            const totalBytes = selectedFiles.reduce((sum, file) => sum + file.size, 0);
            totalSize.textContent = (totalBytes / (1024 * 1024)).toFixed(2) + ' MB';

            let uploadedBytes = 0;
            let successCount = 0;

            for (let i = 0; i < selectedFiles.length; i++) {
                // 检查是否已取消
                if (uploadCancelled) {
                    break;
                }

                const file = selectedFiles[i];
                uploadStatus.textContent = `正在上传: ${file.name} (${i + 1}/${selectedFiles.length})`;

                try {
                    await uploadSingleFile(file, description, tags, token, (loaded, total) => {
                        // 更新进度 - 限制不超过当前文件大小
                        const actualLoaded = Math.min(loaded, total);
                        const currentTotal = uploadedBytes + actualLoaded;
                        const percent = Math.min(100, Math.round((currentTotal / totalBytes) * 100));
                        progressBar.style.width = percent + '%';
                        uploadPercent.textContent = percent + '%';
                        uploadedSize.textContent = (currentTotal / (1024 * 1024)).toFixed(2) + ' MB';
                    });

                    uploadedBytes += file.size;
                    successCount++;
                    console.log(`上传成功: ${file.name}`);
                } catch (error) {
                    if (uploadCancelled) {
                        break;
                    }
                    console.error(`上传失败: ${file.name}`, error);
                    alert(`上传失败: ${file.name}`);
                }
            }

            // 上传完成或取消
            if (!uploadCancelled) {
                uploadStatus.textContent = `✅ 上传完成！成功 ${successCount}/${selectedFiles.length} 个文件`;
                setTimeout(() => {
                    loadAllFiles();
                    loadStats();
                    document.getElementById('uploadPreview').classList.remove('active');
                    progressDiv.style.display = 'none';
                    progressBar.style.width = '0%';
                    selectedFiles = [];
                    document.getElementById('bulkDesc').value = '';
                    document.getElementById('bulkTags').value = '';
                }, 2000);
            }
        }

        function uploadSingleFile(file, description, tags, token, onProgress) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();

                reader.onload = function(e) {
                    const base64 = e.target.result.split(',')[1];
                    const xhr = new XMLHttpRequest();

                    // 保存当前xhr以便取消
                    currentXhr = xhr;

                    xhr.upload.addEventListener('progress', (event) => {
                        if (event.lengthComputable) {
                            // 传递实际加载量和文件大小，让外部限制进度
                            onProgress(event.loaded, file.size);
                        }
                    });

                    xhr.addEventListener('load', () => {
                        currentXhr = null;
                        if (xhr.status === 200) {
                            try {
                                const result = JSON.parse(xhr.responseText);
                                if (result.success) {
                                    resolve(result);
                                } else {
                                    reject(new Error(result.message || '上传失败'));
                                }
                            } catch (e) {
                                reject(e);
                            }
                        } else {
                            reject(new Error(`HTTP ${xhr.status}`));
                        }
                    });

                    xhr.addEventListener('error', () => {
                        currentXhr = null;
                        reject(new Error('网络错误'));
                    });

                    xhr.addEventListener('abort', () => {
                        currentXhr = null;
                        reject(new Error('上传取消'));
                    });

                    xhr.open('POST', '/ai/api/file/upload');
                    xhr.setRequestHeader('Content-Type', 'application/json');
                    xhr.setRequestHeader('Authorization', 'Bearer ' + token);
                    xhr.send(JSON.stringify({
                        file_data: base64,
                        original_name: file.name,
                        mime_type: file.type,
                        description: description,
                        tags: tags
                    }));
                };

                reader.onerror = () => reject(new Error('文件读取失败'));
                reader.readAsDataURL(file);
            });
        }

        async function loadAllFiles() {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/ai/api/files', {
                    headers: token ? {'Authorization': 'Bearer ' + token} : {}
                });
                allFiles = await response.json();
                console.log(`[DEBUG] 加载了 ${allFiles.length} 个文件`);
                if (allFiles.length > 0) {
                    console.log(`[DEBUG] 第一个文件:`, allFiles[0]);
                    // 统计category分布
                    const categoryCount = {};
                    allFiles.forEach(f => {
                        const cat = f.category || 'undefined';
                        categoryCount[cat] = (categoryCount[cat] || 0) + 1;
                    });
                    console.log(`[DEBUG] Category分布:`, categoryCount);
                }
                displayFiles(allFiles);
                // 在文件加载完成后再加载统计信息
                loadStats();
            } catch (error) {
                console.error('加载文件失败:', error);
                document.getElementById('fileGrid').innerHTML = '<div class="empty-state"><p>加载失败，请刷新重试</p></div>';
            }
        }

        async function loadStats() {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/ai/api/file/stats', {
                    headers: token ? {'Authorization': 'Bearer ' + token} : {}
                });
                const data = await response.json();
                if (data.success && data.stats) {
                    document.getElementById('totalFiles').textContent = data.stats.total_files || 0;
                    document.getElementById('totalSize').textContent = (data.stats.total_size_mb || 0).toFixed(1) + ' MB';

                    // 使用本地日期而不是UTC日期
                    const now = new Date();
                    const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

                    console.log(`[DEBUG] 客户端当前时间: ${now}`);
                    console.log(`[DEBUG] 今日日期: ${today}`);
                    console.log(`[DEBUG] allFiles数量: ${allFiles.length}`);

                    // 显示前3个文件的created_at
                    if (allFiles.length > 0) {
                        console.log(`[DEBUG] 前3个文件的created_at:`);
                        allFiles.slice(0, 3).forEach((f, i) => {
                            console.log(`  ${i+1}. ${f.original_name}: ${f.created_at}`);
                        });
                    }

                    const todayFiles = allFiles.filter(f =>
                        f.created_at && f.created_at.startsWith(today)
                    );
                    console.log(`[DEBUG] 今日上传的文件:`, todayFiles.map(f => f.original_name));

                    const todayCount = todayFiles.length;
                    document.getElementById('todayUploads').textContent = todayCount;
                    console.log(`[DEBUG] 今日上传数量: ${todayCount}`);
                }
            } catch (error) {
                console.error('加载统计失败:', error);
            }
        }

        async function searchFiles() {
            const keyword = document.getElementById('searchKeyword').value;

            if (!keyword) {
                loadAllFiles();
                return;
            }

            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/ai/api/file/search', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? {'Authorization': 'Bearer ' + token} : {})
                    },
                    body: JSON.stringify({ keyword })
                });
                const data = await response.json();
                displayFiles(data.results || data);
            } catch (error) {
                console.error('搜索失败:', error);
            }
        }

        function filterByCategory(category, event) {
            currentCategory = category;

            document.querySelectorAll('.category-tag').forEach(tag => {
                tag.classList.remove('active');
            });
            event.target.classList.add('active');

            if (category === 'all') {
                console.log(`[DEBUG] 显示所有文件，总数: ${allFiles.length}`);
                displayFiles(allFiles);
            } else {
                const filtered = allFiles.filter(f => f.category === category);
                console.log(`[DEBUG] 过滤 category=${category}，找到 ${filtered.length} 个文件`);
                console.log(`[DEBUG] allFiles总数: ${allFiles.length}`);
                if (filtered.length > 0) {
                    console.log(`[DEBUG] 第一个文件:`, filtered[0]);
                }
                displayFiles(filtered);
            }
        }

        function displayFiles(files) {
            const grid = document.getElementById('fileGrid');

            if (!files || files.length === 0) {
                grid.innerHTML = `
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" fill="currentColor">
                            <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                        </svg>
                        <h3>暂无文件</h3>
                        <p>点击上方按钮上传文件</p>
                    </div>
                `;
                return;
            }

            // 图片类别使用网格布局，其他使用列表布局
            const isImageCategory = currentCategory === 'image';

            if (isImageCategory) {
                // 网格布局 - 显示图片预览
                grid.innerHTML = files.map(file => {
                    const tagsHtml = (file.tags && Array.isArray(file.tags)) ?
                        file.tags.map(tag => `<span class="tag">${tag}</span>`).join('') : '';
                    const fileSize = formatFileSize(file.file_size || 0);
                    const uploadTime = file.created_at || '未知时间';
                    const imagePath = file.file_path.startsWith('/') ? '/ai' + file.file_path : '/ai/' + file.file_path;

                    return `
                        <div class="file-card">
                            <div class="file-icon-wrapper">
                                <img src="${imagePath}" alt="${file.original_name}" style="width:100%; height:100%; object-fit:cover; border-radius:8px;">
                            </div>
                            <div class="file-info">
                                <div class="filename" title="${file.original_name}">
                                    ${file.original_name}
                                </div>
                                ${file.description ? `<div class="description">${file.description}</div>` : ''}
                                ${tagsHtml ? `<div class="tags">${tagsHtml}</div>` : ''}
                                <div class="meta">
                                    📅 ${uploadTime.split(' ')[0]} | 💾 ${fileSize} | 📥 ${file.download_count || 0}次
                                </div>
                                <div class="actions">
                                    <button class="btn-download" onclick="downloadFile(${file.id}, '${file.original_name}')">📥 下载</button>
                                    <button class="btn-share" onclick="shareFile(${file.id}, '${file.original_name}', '${file.category}')">📤 分享</button>
                                    <button class="btn-delete" onclick="deleteFile(${file.id})">🗑️ 删除</button>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                // 列表布局 - 表格式显示
                grid.innerHTML = `
                    <div class="file-list">
                        <div class="file-list-header">
                            <div>文件名</div>
                            <div>修改日期</div>
                            <div>大小</div>
                            <div>类型</div>
                            <div>操作</div>
                        </div>
                        ${files.map(file => {
                            const icon = getFileIcon(file.category, file.mime_type);
                            const fileSize = formatFileSize(file.file_size || 0);
                            const fileType = getFileTypeLabel(file.mime_type, file.original_name);
                            const uploadFullTime = file.created_at || '未知时间';

                            return `
                                <div class="file-list-item">
                                    <div class="file-list-cell-name">
                                        <div class="file-list-icon">${icon}</div>
                                        <div class="file-list-name" title="${file.original_name}">${file.original_name}</div>
                                    </div>
                                    <div class="file-list-cell">${uploadFullTime}</div>
                                    <div class="file-list-cell">${fileSize}</div>
                                    <div class="file-list-cell" title="${fileType}">${fileType}</div>
                                    <div class="file-list-actions">
                                        <button class="btn-download" onclick="downloadFile(${file.id}, '${file.original_name}')">下载</button>
                                        <button class="btn-share" onclick="shareFile(${file.id}, '${file.original_name}', '${file.category}')">分享</button>
                                        <button class="btn-delete" onclick="deleteFile(${file.id})">删除</button>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                `;
            }
        }

        function downloadFile(id, filename) {
            const token = localStorage.getItem('token');
            const link = document.createElement('a');
            link.href = `/api/file/${id}/download`;
            if (token) {
                link.href += '?token=' + token;
            }
            link.download = filename;
            link.click();
        }

        async function deleteFile(id) {
            if (!confirm('确定要删除这个文件吗？')) return;

            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/ai/api/file/delete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? {'Authorization': 'Bearer ' + token} : {})
                    },
                    body: JSON.stringify({ id })
                });

                const result = await response.json();
                if (result.success) {
                    loadAllFiles();
                    loadStats();
                } else {
                    alert('删除失败：' + result.message);
                }
            } catch (error) {
                console.error('删除失败:', error);
                alert('删除失败，请重试');
            }
        }

        // 分享功能相关变量
        let currentShareFile = null;
        let selectedFriendId = null;

        // 打开分享弹窗
        async function shareFile(fileId, fileName, category) {
            currentShareFile = { id: fileId, name: fileName, category: category };
            selectedFriendId = null;

            // 更新文件名显示
            document.getElementById('shareFileNameText').textContent = fileName;

            // 显示弹窗
            document.getElementById('shareModal').classList.add('active');

            // 加载好友列表
            await loadFriendList();
        }

        // 加载好友列表
        async function loadFriendList() {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/ai/api/social/friends/list', {
                    headers: {
                        'Authorization': 'Bearer ' + token
                    }
                });

                const data = await response.json();
                const friendList = document.getElementById('friendList');

                if (!data.friends || data.friends.length === 0) {
                    friendList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">暂无好友，请先添加好友</div>';
                    return;
                }

                // 渲染好友列表
                friendList.innerHTML = data.friends.map(friend => {
                    const avatarText = friend.friend_username ? friend.friend_username.charAt(0).toUpperCase() : '?';
                    return `
                        <div class="friend-item" onclick="selectFriend(${friend.friend_id}, '${friend.friend_username}')">
                            <div class="friend-avatar">${avatarText}</div>
                            <div class="friend-info">
                                <div class="friend-name">${friend.friend_username}</div>
                                <div class="friend-status">点击选择</div>
                            </div>
                        </div>
                    `;
                }).join('');

            } catch (error) {
                console.error('加载好友列表失败:', error);
                document.getElementById('friendList').innerHTML = '<div style="text-align: center; padding: 20px; color: #f44336;">加载失败，请重试</div>';
            }
        }

        // 选择好友
        function selectFriend(friendId, friendName) {
            selectedFriendId = friendId;

            // 更新UI选中状态
            document.querySelectorAll('.friend-item').forEach(item => {
                item.classList.remove('selected');
            });
            event.target.closest('.friend-item').classList.add('selected');

            // 启用确认按钮
            document.getElementById('confirmShareBtn').disabled = false;
        }

        // 确认分享
        async function confirmShare() {
            if (!selectedFriendId || !currentShareFile) {
                alert('请选择要分享的好友');
                return;
            }

            try {
                const token = localStorage.getItem('token');

                // 构建消息内容
                const messageContent = `分享了文件：${currentShareFile.name}`;
                const messageType = currentShareFile.category === 'image' ? 'image' : 'file';

                // 发送私信
                const response = await fetch('/ai/api/social/messages/send', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify({
                        receiver_id: selectedFriendId,
                        content: messageContent,
                        message_type: messageType,
                        image_id: messageType === 'image' ? currentShareFile.id : null,
                        file_id: messageType === 'file' ? currentShareFile.id : null
                    })
                });

                const result = await response.json();

                if (result.success) {
                    alert('分享成功！');
                    closeShareModal();
                } else {
                    alert('分享失败: ' + (result.message || '未知错误'));
                }

            } catch (error) {
                console.error('分享失败:', error);
                alert('分享失败，请重试');
            }
        }

        // 关闭分享弹窗
        function closeShareModal() {
            document.getElementById('shareModal').classList.remove('active');
            currentShareFile = null;
            selectedFriendId = null;
            document.getElementById('confirmShareBtn').disabled = true;
        }

        function getFileIcon(category, mimeType) {
            const iconMap = {
                'document': '📄',
                'image': '🖼️',
                'video': '🎬',
                'audio': '🎵',
                'archive': '📦',
                'other': '📎'
            };
            return iconMap[category] || '📎';
        }

        function getFileTypeLabel(mimeType, filename) {
            // 从文件名获取扩展名
            const ext = filename ? ('.' + filename.split('.').pop().toLowerCase()) : '';

            // MIME类型到文件类型描述的映射
            const typeMap = {
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': `Microsoft Word ${ext}`,
                'application/msword': `Microsoft Word ${ext}`,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': `Microsoft Excel ${ext}`,
                'application/vnd.ms-excel': `Microsoft Excel ${ext}`,
                'application/vnd.openxmlformats-officedocument.presentationml.presentation': `Microsoft PowerPoint ${ext}`,
                'application/vnd.ms-powerpoint': `Microsoft PowerPoint ${ext}`,
                'application/pdf': `PDF文档 ${ext}`,
                'text/plain': `文本文件 ${ext}`,
                'text/csv': `CSV文件 ${ext}`,
                'image/jpeg': `JPEG图片 ${ext}`,
                'image/png': `PNG图片 ${ext}`,
                'image/gif': `GIF图片 ${ext}`,
                'image/bmp': `BMP图片 ${ext}`,
                'image/webp': `WebP图片 ${ext}`,
                'video/mp4': `MP4视频 ${ext}`,
                'video/mpeg': `MPEG视频 ${ext}`,
                'video/quicktime': `MOV视频 ${ext}`,
                'video/x-msvideo': `AVI视频 ${ext}`,
                'audio/mpeg': `MP3音频 ${ext}`,
                'audio/wav': `WAV音频 ${ext}`,
                'audio/ogg': `OGG音频 ${ext}`,
                'application/zip': `ZIP压缩包 ${ext}`,
                'application/x-rar-compressed': `RAR压缩包 ${ext}`,
                'application/x-7z-compressed': `7Z压缩包 ${ext}`,
                'application/gzip': `GZIP压缩包 ${ext}`,
                'application/json': `JSON文件 ${ext}`,
                'application/xml': `XML文件 ${ext}`,
                'text/html': `HTML文件 ${ext}`,
                'text/css': `CSS文件 ${ext}`,
                'text/javascript': `JavaScript ${ext}`,
                'application/javascript': `JavaScript ${ext}`
            };

            // 如果有精确的MIME类型映射，使用它
            if (mimeType && typeMap[mimeType]) {
                return typeMap[mimeType];
            }

            // 否则根据MIME类型分类
            if (mimeType) {
                if (mimeType.startsWith('image/')) return `图片文件 ${ext}`;
                if (mimeType.startsWith('video/')) return `视频文件 ${ext}`;
                if (mimeType.startsWith('audio/')) return `音频文件 ${ext}`;
                if (mimeType.startsWith('text/')) return `文本文件 ${ext}`;
            }

            // 最后使用扩展名
            return ext ? `${ext.toUpperCase().substring(1)}文件` : '未知类型';
        }

        function getFileIconByType(mimeType) {
            if (mimeType.startsWith('image/')) return '🖼️';
            if (mimeType.startsWith('video/')) return '🎬';
            if (mimeType.startsWith('audio/')) return '🎵';
            if (mimeType.includes('pdf')) return '📄';
            if (mimeType.includes('word') || mimeType.includes('document')) return '📝';
            if (mimeType.includes('excel') || mimeType.includes('sheet')) return '📊';
            if (mimeType.includes('powerpoint') || mimeType.includes('presentation')) return '📽️';
            if (mimeType.includes('zip') || mimeType.includes('rar') || mimeType.includes('7z')) return '📦';
            return '📎';
        }

        function formatFileSize(bytes) {
            if (!bytes) return '0 B';
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
            return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
        }
    </script>
</body>
</html>'''

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

        /* 加载动画样式 */
        .loading-dots {
            display: inline-block;
        }

        .loading-dots span {
            animation: blink 1.4s infinite;
            animation-fill-mode: both;
        }

        .loading-dots span:nth-child(2) {
            animation-delay: 0.2s;
        }

        .loading-dots span:nth-child(3) {
            animation-delay: 0.4s;
        }

        .loading-dots span:nth-child(4) {
            animation-delay: 0.6s;
        }

        @keyframes blink {
            0%, 80%, 100% {
                opacity: 0;
            }
            40% {
                opacity: 1;
            }
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
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>个人助手</title>
    <link rel="stylesheet" href="/mobile_ui_patch.css">
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
        
        /* 左侧导航栏 */
        .sidebar {
            width: 250px;
            background: #2c3e50;
            display: flex;
            flex-direction: column;
            position: fixed;
            left: 0;
            top: 0;
            bottom: 0;
            z-index: 100;
            color: white;
            transition: all 0.3s;
        }

        /* 侧边栏头部 */
        .sidebar-header {
            padding: 20px;
            background: #34495e;
            border-bottom: 1px solid #465669;
        }

        .sidebar-header h2 {
            font-size: 18px;
            margin-bottom: 5px;
            color: white;
        }

        .sidebar-header p {
            font-size: 12px;
            opacity: 0.7;
            color: white;
        }

        /* 侧边栏导航区域 */
        .sidebar-nav {
            flex: 1;
            overflow-y: auto;
            padding: 10px 0;
        }

        /* 导航项 */
        .nav-item {
            padding: 15px 20px;
            cursor: pointer;
            border-left: 3px solid transparent;
            transition: all 0.3s;
            color: white;
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 15px;
        }

        .nav-item:hover {
            background: #34495e;
        }

        .nav-item.active {
            background: #34495e;
            border-left-color: #3498db;
        }

        .nav-item-icon {
            font-size: 20px;
            width: 24px;
            text-align: center;
        }

        /* 侧边栏底部 */
        .sidebar-footer {
            padding: 15px;
            background: #1a252f;
            border-top: 1px solid #465669;
        }

        .sidebar-footer button {
            width: 100%;
            background: #e74c3c;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
        }

        .sidebar-footer button:hover {
            background: #c0392b;
        }

        /* 旧的图标样式保留用于兼容 */
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
            margin-left: 250px;
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
            align-items: flex-start;
            padding: 60px 40px 40px 40px;
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
                padding: 0 !important; /* 去除内边距 */
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: transparent;
                z-index: 1000;
            }
            
            .input-wrapper {
                border-radius: 0 !important;
                background: rgba(255, 255, 255, 0.95) !important;
                backdrop-filter: blur(10px);
                border: none !important;
                border-top: 1px solid rgba(0,0,0,0.1) !important;
                padding: 8px 12px !important;
                padding-bottom: max(8px, env(safe-area-inset-bottom)) !important;
            }
            
            textarea#aiInput {
                background: #f0f2f5 !important;
                border: 1px solid #ddd !important;
                border-radius: 20px !important;
                color: #333 !important;
                padding: 8px 12px !important;
            }
            
            .send-button {
                width: 36px;
                height: 36px;
                background: #007bff !important;
                box-shadow: none !important;
            }

            /* 移动端文件按钮样式 */
            .file-button {
                width: 32px !important;
                height: 32px !important;
                margin-right: 4px !important;
                background: linear-gradient(135deg, #9B9B9B 0%, #7A7A7A 50%, #5A5A5A 100%) !important;
                flex-shrink: 0 !important;
            }

            .file-button span {
                font-size: 18px !important;
            }
        }

        @media (max-width: 480px) {
            #aiChatBox {
                padding: 80px 16px 20px;
                gap: 20px;
            }
        }

        .input-wrapper {
            background: rgba(40, 40, 40, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 4px 4px 4px 20px;
            display: flex;
            align-items: flex-end; /* 底部对齐，适应多行 */
            gap: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .input-icon {
            color: #888;
            font-size: 20px;
            cursor: pointer;
            transition: color 0.3s;
            margin-bottom: 12px; /* 图标底部对齐 */
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
            max-height: 120px; /* 约5行高度 */
            font-family: inherit;
            line-height: 1.5em;
            padding: 10px 0;
            overflow-y: hidden; /* 默认隐藏滚动条 */
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
            background: linear-gradient(135deg, #6BB6FF 0%, #4A9FE5 50%, #3B8ED0 100%);
            border: none;
            box-shadow: 0 4px 8px rgba(59, 142, 208, 0.4),
                        inset 0 1px 2px rgba(255, 255, 255, 0.5),
                        inset 0 -2px 4px rgba(0, 0, 0, 0.2);
            flex-shrink: 0;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .send-button:hover {
            background: linear-gradient(135deg, #7DC5FF 0%, #5AAEF0 50%, #4A9FE5 100%);
            box-shadow: 0 6px 12px rgba(59, 142, 208, 0.5),
                        inset 0 1px 2px rgba(255, 255, 255, 0.6),
                        inset 0 -2px 4px rgba(0, 0, 0, 0.15);
            transform: translateY(-1px);
        }

        .send-button:active {
            transform: translateY(1px);
            box-shadow: 0 2px 4px rgba(59, 142, 208, 0.3),
                        inset 0 1px 2px rgba(255, 255, 255, 0.4),
                        inset 0 -1px 2px rgba(0, 0, 0, 0.3);
        }

        .send-button span {
            color: #ffffff;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
            font-weight: bold;
        }

        /* 文件上传按钮样式 */
        .file-button {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #9B9B9B 0%, #7A7A7A 50%, #5A5A5A 100%);
            border: none;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2),
                        inset 0 1px 2px rgba(255, 255, 255, 0.3);
            flex-shrink: 0;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-right: 6px;
        }

        .file-button:hover {
            background: linear-gradient(135deg, #ABABAB 0%, #8A8A8A 50%, #6A6A6A 100%);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3),
                        inset 0 1px 2px rgba(255, 255, 255, 0.4);
            transform: translateY(-1px);
        }

        .file-button:active {
            transform: translateY(1px);
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2),
                        inset 0 1px 2px rgba(255, 255, 255, 0.2);
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

        .plan-title.urgent {
            color: #ff4444;
            font-weight: 700;
        }

        .plan-title.important {
            color: #ff9900;
            font-weight: 700;
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

        .plan-btn-pin {
            background: rgba(255, 193, 7, 0.2);
            color: #ffc107;
        }

        .plan-btn-pin:hover {
            background: #ffc107;
            color: #000;
        }

        .plan-btn-edit {
            background: rgba(23, 162, 184, 0.2);
            color: #17a2b8;
        }

        .plan-btn-edit:hover {
            background: #17a2b8;
            color: white;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.02); }
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
                display: flex;
                justify-content: center;
                align-items: flex-start;
                padding: 60px 20px 20px 20px;
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

        /* 强制注入：手机端极致体验版 v6 (顶部锚定 - 解决推顶问题) */
        @media (max-width: 768px) {
            /* 1. 锁死 Body，禁止页面级滚动 */
            html, body { 
                height: 100% !important; 
                width: 100% !important; 
                margin: 0 !important; 
                padding: 0 !important; 
                overflow: hidden !important; 
                /* background: #f7f7f8 !important;  已移除：允许显示用户自定义背景 */
                color: #1a1a1a !important; 
                position: fixed !important; /* iOS 防抖动核心 */
            }
            
            /* 2. 顶部导航 - 永远钉在最上面 */
            .header { 
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                right: 0 !important;
                height: 50px !important; 
                background: #fff !important; 
                border-bottom: 1px solid #e5e5e5 !important; 
                display: flex !important; 
                align-items: center !important; 
                justify-content: center !important; 
                z-index: 1000 !important; 
                color: #000 !important;
            }
            
            /* 3. 聊天滚动区 - 钉在顶部，延伸到底部 */
            #chat-view, .chat-container, #aiChatBox { 
                display: block !important;
                position: fixed !important; /* 固定定位，不随页面滚动 */
                top: 50px !important;       /* 从标题栏下方开始 */
                bottom: 0 !important;       /* 一直延伸到屏幕底 */
                left: 0 !important;
                right: 0 !important;
                width: 100% !important;
                height: auto !important;
                
                /* 关键：内部滚动 */
                overflow-y: scroll !important; 
                -webkit-overflow-scrolling: touch !important; 
                
                /* 关键：顶部留出约20行空间(520px)，底部留出空间 */
                padding: 520px 12px 100px 12px !important; 
                
                background: #f7f7f8 !important; 
                z-index: 10 !important;
            }
            
            /* 4. 底部输入区 - 消除间距，紧贴键盘 */
            .input-area, .input-container { 
                position: fixed !important; 
                bottom: 0 !important; 
                left: 0 !important; 
                right: 0 !important;
                width: 100% !important;
                background: transparent !important; 
                
                /* 关键修改：移除底部 padding，消除与键盘辅助栏的间隙 */
                padding: 0 !important; 
                
                display: flex !important; 
                align-items: flex-end !important; 
                gap: 0 !important;
                z-index: 2000 !important; 
                min-height: auto !important; 
            }
            
            .input-wrapper {
                border-radius: 0 !important;
                background: rgba(255, 255, 255, 0.1) !important; /* 半透明背景 */
                backdrop-filter: blur(10px);
                border: none !important;
                border-top: 1px solid rgba(255,255,255,0.1) !important;
                padding: 8px 12px !important;
                padding-bottom: max(8px, env(safe-area-inset-bottom)) !important;
                width: 100% !important;
                margin: 0 !important;
                display: flex !important;
                align-items: flex-end !important;
                gap: 10px !important;
            }
            
            .input-area input, .input-container textarea, textarea#aiInput { 
                flex: 1 !important; 
                min-height: 36px !important; 
                max-height: 120px !important;
                border: 1px solid #ddd !important; 
                background: #ffffff !important; 
                border-radius: 20px !important; 
                padding: 8px 12px !important; 
                font-size: 16px !important; 
                color: #333 !important; 
                margin: 0 !important;
                appearance: none !important;
                resize: none !important;
                line-height: 20px !important;
            }

            .input-area button, .send-button {
                background: #007bff !important;
                color: white !important;
                border: none !important;
                border-radius: 50% !important;
                padding: 0 !important;
                width: 36px !important;
                height: 36px !important;
                margin: 0 0 1px 0 !important;
                min-width: 36px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                box-shadow: none !important;
            }
            
            .send-button span {
                font-size: 16px !important;
                margin-left: 2px !important;
            }

            /* 移动端文件按钮样式 */
            .file-button {
                width: 30px !important;
                height: 30px !important;
                margin: 0 2px 1px 0 !important;
                min-width: 30px !important;
                background: linear-gradient(135deg, #9B9B9B 0%, #7A7A7A 50%, #5A5A5A 100%) !important;
                flex-shrink: 0 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }

            .file-button span {
                font-size: 16px !important;
            }

            /* 5. 样式修复 */
            .sidebar { display: none !important; }
            .container { margin-left: 0 !important; }
            .message { display: flex !important; width: 100% !important; margin-bottom: 16px !important; color: #1a1a1a !important; }
            .message.user { flex-direction: row-reverse !important; }
            .message.user .message-content, .message.user .message-bubble { background: #10a37f !important; color: white !important; margin-right: 0 !important; margin-left: auto !important; border-bottom-right-radius: 4px !important; }
            .message.assistant { flex-direction: row !important; }
            .message.assistant .message-content, .message.assistant .message-bubble { background: #fff !important; color: #333 !important; margin-left: 0 !important; margin-right: auto !important; border: 1px solid #e5e5e5 !important; border-bottom-left-radius: 4px !important; }
            
            /* 6. 隐藏多余元素 */
            .main-content > header { display: none !important; }
            .welcome-message h3, .welcome-message p { color: #333 !important; }
        }
    </style>
    <link rel="stylesheet" href="/mobile_ui_patch.css?v=2.0">
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
            <div class="drawer-item" onclick="window.open('/ai/file-manager', '_blank'); closeMobileMenu();">
                <span style="margin-right: 12px; font-size: 18px;">📁</span>文件管理
            </div>
            <div class="drawer-item" onclick="window.location.href='/ai/social'; closeMobileMenu();">
                <span style="margin-right: 12px; font-size: 18px;">👥</span>朋友
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

    <!-- 左侧导航栏 -->
    <div class="sidebar">
        <!-- 侧边栏头部 -->
        <div class="sidebar-header">
            <h2>AI Personal Assistant</h2>
            <p id="sidebar-username">加载中...</p>
        </div>
        
        <!-- 侧边栏导航 -->
        <div class="sidebar-nav">
            <div class="nav-item active" data-view="chat" onclick="switchView('chat')">
                <span class="nav-item-icon">💬</span>
                <span>聊天</span>
            </div>
            <div class="nav-item" data-view="plans" onclick="switchView('plans')">
                <span class="nav-item-icon">📋</span>
                <span>工作计划</span>
            </div>
            <div class="nav-item" data-view="reminders" onclick="switchView('reminders')">
                <span class="nav-item-icon">⏰</span>
                <span>提醒事项</span>
            </div>
            <div class="nav-item" data-view="friends" onclick="switchView('friends')">
                <span class="nav-item-icon">👥</span>
                <span>朋友</span>
            </div>
            <div class="nav-item" data-view="files" onclick="switchView('files')">
                <span class="nav-item-icon">📁</span>
                <span>文件管理</span>
            </div>
            <div class="nav-item" data-view="settings" onclick="switchView('settings')">
                <span class="nav-item-icon">⚙️</span>
                <span>设置</span>
            </div>
        </div>
        
        <!-- 侧边栏底部 -->
        <div class="sidebar-footer">
            <button onclick="logout()">退出登录</button>
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
                                <input type="file" id="imageUpload" accept="image/*" multiple style="display:none" onchange="handleImageSelect(event)">
                                <input type="file" id="cameraInput" accept="image/*" capture="environment" style="display:none" onchange="handleCameraCapture(event)">
                                <input type="file" id="fileUpload" multiple style="display:none" onchange="handleFileSelect(event)">

                                <!-- 文件上传按钮组 -->
                                <button class="file-button" onclick="document.getElementById('cameraInput').click()" title="拍照">
                                    <span style="font-size: 20px;">📷</span>
                                </button>
                                <button class="file-button" onclick="document.getElementById('imageUpload').click()" title="选择图片">
                                    <span style="font-size: 20px;">🖼️</span>
                                </button>
                                <button class="file-button" onclick="document.getElementById('fileUpload').click()" title="选择文件">
                                    <span style="font-size: 20px;">📎</span>
                                </button>

                                <textarea id="aiInput" rows="1" placeholder="How can I help you?" oninput="autoResizeTextarea(this)" onkeydown="handleAIKeyPress(event)" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" inputmode="search" name="chat_input" data-form-type="other"></textarea>
                                <button class="send-button" onclick="sendAI()">
                                    <span style="font-size: 24px;">▶</span>
                                </button>
                            </div>
                <!-- 图片预览区域 -->
                <div id="imagePreviewContainer" style="display:none; margin-top:15px;">
                    <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:10px;" id="imagePreviewList">
                        <!-- 动态添加图片预览 -->
            </div>
                    <div style="margin-top:10px;">
                        <input type="text" id="imageDescription" placeholder="添加图片描述（可选）" lang="zh-CN" style="width:100%; padding:8px; margin-bottom:8px; background:rgba(40,40,40,0.9); border:1px solid rgba(255,255,255,0.2); border-radius:8px; color:#fff;">
                        <input type="text" id="imageTags" placeholder="添加标签，用逗号分隔（可选）" lang="zh-CN" style="width:100%; padding:8px; margin-bottom:8px; background:rgba(40,40,40,0.9); border:1px solid rgba(255,255,255,0.2); border-radius:8px; color:#fff;">
                        <button onclick="uploadSelectedImages()" style="width:100%; padding:12px; background:#28a745; color:white; border:none; border-radius:8px; cursor:pointer; font-size:16px; font-weight:600;">
                            ✅ 上传图片到图片库
                        </button>
            </div>
            </div>
                <!-- 文件预览区域 -->
                <div id="filePreviewContainer" style="display:none; margin-top:10px; background:rgba(64,64,64,0.6); padding:10px; border-radius:8px;">
                    <div style="display:flex; align-items:center; justify-content:space-between;">
                        <div style="display:flex; align-items:center;">
                            <span style="font-size:24px; margin-right:10px;">📄</span>
                            <div>
                                <div id="fileName" style="font-weight:bold; color:#fff;">filename.pdf</div>
                                <div id="fileSize" style="font-size:12px; color:#aaa;">1.2 MB</div>
                            </div>
                        </div>
                        <span onclick="clearFileSelection()" style="cursor:pointer; color:#ff4444; font-weight:bold;">✕</span>
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
                
                <!-- 过滤器和批量编辑 -->
                <div style="display:flex; gap:10px; margin-bottom:20px; flex-wrap: wrap; align-items: center;">
                    <button onclick="filterWorkPlans('all')" class="filter-btn active" data-filter="all">📋 全部</button>
                    <button onclick="filterWorkPlans('pending')" class="filter-btn" data-filter="pending">⭕ 未开始</button>
                    <button onclick="filterWorkPlans('in_progress')" class="filter-btn" data-filter="in_progress">🔄 进行中</button>
                    <button onclick="filterWorkPlans('completed')" class="filter-btn" data-filter="completed">✅ 已完成</button>
                    <button onclick="filterWorkPlans('cancelled')" class="filter-btn" data-filter="cancelled">❌ 已取消</button>
                    <div style="flex:1;"></div>
                    <button id="batchEditBtn" onclick="toggleBatchEditMode()" style="padding:8px 16px; background:#6c757d; color:white; border:none; border-radius:4px; cursor:pointer; font-size:14px; font-weight:600;">
                        ✏️ 批量编辑
                    </button>
                    <button id="saveBatchEditBtn" onclick="saveBatchEdit()" style="display:none; padding:8px 16px; background:#28a745; color:white; border:none; border-radius:4px; cursor:pointer; font-size:14px; font-weight:600;">
                        💾 保存
                    </button>
                    <button id="cancelBatchEditBtn" onclick="cancelBatchEdit()" style="display:none; padding:8px 16px; background:#dc3545; color:white; border:none; border-radius:4px; cursor:pointer; font-size:14px; font-weight:600;">
                        ❌ 取消
                    </button>
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

    <!-- 提醒事项弹窗 -->
    <div id="remindersModal" class="modal">
        <div class="modal-content" style="max-width: 700px; max-height: 90vh; overflow-y: auto;">
            <span class="close" onclick="closeReminders()">&times;</span>
            <h3>⏰ 提醒事项</h3>

            <!-- 创建提醒按钮 -->
            <button onclick="showCreateReminderForm()" style="width: 100%; padding: 12px; background: #10a37f; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 600; margin-bottom: 20px;">
                ➕ 创建新提醒
            </button>

            <!-- 创建提醒表单（默认隐藏） -->
            <div id="createReminderForm" style="display: none; background: #ffffff; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #ddd;">
                <h4 style="margin-top: 0; margin-bottom: 15px; color: #000;">创建新提醒</h4>

                <!-- 提醒内容 -->
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #000;">提醒内容</label>
                    <textarea id="reminderContent" placeholder="请输入提醒内容（最多5000字）" maxlength="5000" rows="3" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; resize: vertical; color: #000; background: #fff;"></textarea>
                </div>

                <!-- 日期选择 -->
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #000;">📅 日期</label>
                    <input type="date" id="reminderDate" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; color: #000; background: #fff;">
                </div>

                <!-- 时间选择 -->
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #000;">⏰ 时间</label>
                    <input type="time" id="reminderTime" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; color: #000; background: #fff;">
                </div>

                <!-- 循环类型 -->
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #000;">🔄 循环类型</label>
                    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                        <button class="repeat-type-btn" data-type="once" onclick="selectRepeatType('once')" style="padding: 8px 16px; border: 2px solid #10a37f; background: #10a37f; color: white; border-radius: 20px; cursor: pointer; font-size: 14px;">单次</button>
                        <button class="repeat-type-btn" data-type="minutely" onclick="selectRepeatType('minutely')" style="padding: 8px 16px; border: 2px solid #ddd; background: white; color: #333; border-radius: 20px; cursor: pointer; font-size: 14px;">每分钟</button>
                        <button class="repeat-type-btn" data-type="hourly" onclick="selectRepeatType('hourly')" style="padding: 8px 16px; border: 2px solid #ddd; background: white; color: #333; border-radius: 20px; cursor: pointer; font-size: 14px;">每小时</button>
                        <button class="repeat-type-btn" data-type="daily" onclick="selectRepeatType('daily')" style="padding: 8px 16px; border: 2px solid #ddd; background: white; color: #333; border-radius: 20px; cursor: pointer; font-size: 14px;">每天</button>
                        <button class="repeat-type-btn" data-type="weekly" onclick="selectRepeatType('weekly')" style="padding: 8px 16px; border: 2px solid #ddd; background: white; color: #333; border-radius: 20px; cursor: pointer; font-size: 14px;">每周</button>
                        <button class="repeat-type-btn" data-type="monthly" onclick="selectRepeatType('monthly')" style="padding: 8px 16px; border: 2px solid #ddd; background: white; color: #333; border-radius: 20px; cursor: pointer; font-size: 14px;">每月</button>
                        <button class="repeat-type-btn" data-type="yearly" onclick="selectRepeatType('yearly')" style="padding: 8px 16px; border: 2px solid #ddd; background: white; color: #333; border-radius: 20px; cursor: pointer; font-size: 14px;">每年</button>
                    </div>
                </div>

                <!-- 同时提醒好友 -->
                <div style="margin-bottom: 15px;">
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; user-select: none;">
                        <input type="checkbox" id="alsoNotifyFriends" onchange="toggleFriendSelection()" style="width: 18px; height: 18px; cursor: pointer;">
                        <span style="font-weight: 600; color: #000;">👥 同时提醒好友</span>
                    </label>
                </div>

                <!-- 好友选择区域（默认隐藏） -->
                <div id="friendSelectionArea" style="display: none; margin-bottom: 15px; background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <label style="font-weight: 600; color: #000;">选择要提醒的好友</label>
                        <button onclick="selectAllFriends()" style="padding: 4px 12px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">全选</button>
                    </div>
                    <div id="friendCheckboxList" style="max-height: 200px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;">
                        <p style="text-align: center; color: #666; padding: 20px;">加载好友列表中...</p>
                    </div>
                </div>

                <!-- 按钮组 -->
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button onclick="hideCreateReminderForm()" style="padding: 10px 20px; background: #f0f0f0; color: #333; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600;">取消</button>
                    <button onclick="saveNewReminder()" style="padding: 10px 20px; background: #10a37f; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600;">保存</button>
                </div>
            </div>

            <!-- 提醒列表 -->
            <div id="remindersView" style="margin-top: 20px;">
                <div style="text-align: center; padding: 40px;">
                    <div style="font-size: 48px; margin-bottom: 10px;">⏰</div>
                    <p style="color: #666;">加载中...</p>
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

            <div class="form-group" style="background:#f8f9fa; padding:15px; border-radius:8px; margin-bottom:20px;">
                <label style="font-size:1.1em; margin-bottom:15px; display:block;">🤖 AI助理名字</label>
                <p style="color:#666; font-size:0.9em; margin-bottom:10px;">给你的AI助理取个名字吧</p>
                <input type="text" id="aiAssistantName" placeholder="例如：小智、小助手、阿福等"
                       style="width:100%; padding:10px; border:1px solid #ddd; border-radius:6px; background:white; font-size:14px;"
                       maxlength="20">
                <p style="color:#999; font-size:0.75em; margin-top:8px;">💡 设置后，AI会记住这个名字并在对话中使用</p>
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
            // 只保留最近10条
            if (inputHistory.length > 10) {
                inputHistory = inputHistory.slice(inputHistory.length - 10);
            }

            localStorage.setItem('chatInputHistory', JSON.stringify(inputHistory));
            historyIndex = -1; // 重置索引
        }

        // 自动调整textarea高度（最多4行）
        function autoResizeTextarea(textarea) {
            if (!textarea) return;

            // 重置高度以获取正确的scrollHeight
            textarea.style.height = 'auto';

            // 计算新高度，限制最大高度为120px（约4行）
            const maxHeight = 120;
            const minHeight = 36;
            let newHeight = textarea.scrollHeight;

            if (newHeight < minHeight) {
                newHeight = minHeight;
            } else if (newHeight > maxHeight) {
                newHeight = maxHeight;
                textarea.style.overflowY = 'auto';
            } else {
                textarea.style.overflowY = 'hidden';
            }

            textarea.style.height = newHeight + 'px';
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
                            autoResizeTextarea(input); // 调整高度
                        }
                    } else if (historyIndex > 0) {
                        historyIndex--;
                        event.preventDefault();
                        input.value = inputHistory[historyIndex];
                        autoResizeTextarea(input); // 调整高度
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
                            autoResizeTextarea(input); // 调整高度
                        } else {
                            // 回到最新草稿
                            historyIndex = -1;
                            input.value = currentDraft;
                            autoResizeTextarea(input); // 调整高度
                        }
                    }
                }
            }
        }
        
        // AI助手
            
        function appendAI(role, text, timestamp = null, fileInfo = null) {
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

            // 通用列表检测：匹配 "未完成XXX（共N个）" 或 "XXX列表（共N个）" 等模式
            const listPattern = /(未完成|当前)(.+?)（共\s*(\d+)\s*[个项条]）/;
            const listMatch = text.match(listPattern);

            if (listMatch) {
                const listType = listMatch[2].trim(); // 提取类别名称，如"工作"、"财务记录"等
                console.log('🔍 检测到列表：' + listType + '，准备添加编辑按钮');
                console.log('🔍 完整匹配:', listMatch[0]);
                console.log('🔍 提取的listType:', listType);

                // 检查是否有对应的列表数据
                const listData = window.lastListData || [];
                console.log('📊 列表数据:', listData.length, '个项目');

                // 创建容器
                const container = document.createElement('div');
                container.className = 'list-container';
                container.setAttribute('data-list-type', listType); // 保存类别信息
                container.style.cssText = 'position: relative;';

                // 添加按钮栏（+号和编辑按钮）
                const editButtonBar = document.createElement('div');
                editButtonBar.className = 'list-edit-bar';
                editButtonBar.style.cssText = 'display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 8px;';
                editButtonBar.innerHTML = `
                    <button onclick="addNewListItem(this)" class="list-add-btn" style="padding: 6px 12px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">
                        ➕ 添加
                    </button>
                    <button onclick="toggleListEditMode(this)" class="list-edit-btn" style="padding: 6px 12px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">
                        ✏️ 编辑
                    </button>
                    <button onclick="saveListEdit(this)" class="list-save-btn" style="display: none; padding: 6px 12px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">
                        💾 保存
                    </button>
                    <button onclick="cancelListEdit(this)" class="list-cancel-btn" style="display: none; padding: 6px 12px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">
                        ❌ 取消
                    </button>
                `;
                container.appendChild(editButtonBar);
                console.log('✅ 编辑按钮已添加');

                // 创建列表内容
                const listContent = document.createElement('div');
                listContent.className = 'list-content';

                const lines = text.split('\\n');
                let result = '';
                let taskIndex = 0;

                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    const match = line.match(/^(\d+)\. (.+)$/);
                    if (match) {
                        const num = match[1];
                        let content = match[2];

                        // 收集后续的子项内容（不以数字开头的行）
                        let j = i + 1;
                        while (j < lines.length && !lines[j].match(/^\d+\. /)) {
                            if (lines[j].trim()) {  // 跳过空行
                                content += '\\n' + lines[j];
                            }
                            j++;
                        }
                        i = j - 1;  // 跳过已处理的子项

                        const taskData = listData[taskIndex] || {};
                        const taskId = taskData.id || 0;
                        const hasUrgent = content.startsWith('急');
                        const hasImportant = content.startsWith('重要');

                        result += `<div class="list-item" data-task-id="${taskId}" data-index="${taskIndex}" draggable="false" style="display: flex; align-items: flex-start; margin-bottom: 8px;">`;

                        // 添加可点击的圆圈标记
                        result += `<span class="complete-circle" onclick="completeListItem(${taskId}, this)" style="cursor: pointer; font-size: 16px; margin-right: 8px; user-select: none; line-height: 1.5;">○</span>`;

                        // 编辑模式的复选框（默认隐藏）
                        result += `<div class="list-checkboxes" style="display: none; margin-bottom: 4px;">`;
                        result += `<label style="margin-right: 12px; cursor: pointer; user-select: none;">`;
                        result += `<input type="checkbox" class="urgent-check" ${hasUrgent ? 'checked' : ''} style="margin-right: 4px;">`;
                        result += `<span style="color: red; font-weight: bold;">急</span>`;
                        result += `</label>`;
                        result += `<label style="cursor: pointer; user-select: none;">`;
                        result += `<input type="checkbox" class="important-check" ${hasImportant ? 'checked' : ''} style="margin-right: 4px;">`;
                        result += `<span style="color: orange; font-weight: bold;">重要</span>`;
                        result += `</label>`;
                        result += `<span style="margin-left: 12px; color: #999; font-size: 11px;">☰ 拖动排序</span>`;
                        result += `</div>`;

                        // 任务内容（包含子项，整体截断）
                        result += `<div style="flex: 1; display: flex; align-items: center; gap: 8px;">`;
                        result += `<span style="flex: 1; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.5; white-space: pre-wrap;">`;
                        if (content.startsWith('急')) {
                            result += `<span style="color:red;font-weight:bold;">${content}</span>`;
                        } else if (content.startsWith('重要')) {
                            result += `<span style="color:orange;font-weight:bold;">${content}</span>`;
                        } else {
                            result += content;
                        }
                        result += `</span>`;
                        // 添加编辑按钮
                        result += `<button onclick="editListItem(${taskId}, '${content.replace(/'/g, "\\'")}', this)" style="padding: 4px 8px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 11px; opacity: 0.7; transition: opacity 0.2s;" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.7'">✏️</button>`;
                        result += `</div>`;

                        result += `</div>`;
                        taskIndex++;
                    } else {
                        // 非列表项的行（通常不会执行到这里，因为已经被合并到上面的列表项中了）
                        if (line.trim()) {
                            result += line + '<br>';
                        }
                    }
                }


                listContent.innerHTML = result;
                container.appendChild(listContent);

                textDiv.appendChild(container);
                console.log('✅ 工作列表容器已添加到消息中');
            } else {
                textDiv.textContent = text;
            }
            
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = timeStr;
            
            content.appendChild(textDiv);

            // 新增：如果有文件，显示文件卡片
            if (fileInfo) {
                const fileCard = document.createElement('div');
                fileCard.style.cssText = 'margin-top: 8px; background: rgba(0,0,0,0.05); padding: 8px; border-radius: 6px; display: flex; align-items: center; cursor: pointer; border: 1px solid rgba(0,0,0,0.1);';
                // 使用 /ai/ 前缀以适配 Nginx 路由
                const fileName = fileInfo.filename || fileInfo.name;
                const filePath = `/ai/uploads/files/${fileName}`;
                
                fileCard.onclick = () => window.open(filePath, '_blank');
                
                fileCard.innerHTML = `
                    <span style="font-size: 20px; margin-right: 8px;">📄</span>
                    <div style="flex: 1; overflow: hidden;">
                        <div style="font-weight: 500; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${fileInfo.name || fileInfo.original_name}</div>
                        <div style="font-size: 11px; color: #666;">${formatFileSize(fileInfo.size || fileInfo.file_size)}</div>
                    </div>
                    <span style="font-size: 14px; color: #4A90E2;">⬇️</span>
                `;
                content.appendChild(fileCard);
            }

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
                    },
                    body: JSON.stringify({})
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

                // 清空聊天历史列表，不再加载
                const chatList = document.getElementById('chatList');
                if (chatList) {
                    chatList.innerHTML = '<p style="text-align:center; color:#999; padding:20px;">新对话模式 - 历史记录已隐藏</p>';
                }
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

            // 发送给 Flutter App 添加日历
            if (window.FlutterApp) {
                try {
                    window.FlutterApp.postMessage(JSON.stringify({
                        type: 'add_calendar_event',
                        title: 'AI助理: ' + title,
                        description: content,
                        startTime: time
                    }));
                } catch (e) {
                    console.error('发送日历事件失败:', e);
                }
            }
            
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
        
        let selectedFiles = []; // 支持多文件上传
        let currentFileId = null;
        let uploadedFileIds = []; // 存储已上传的文件ID

        function triggerFileUpload() {
            document.getElementById('fileUpload').click();
        }

        async function handleFileSelect(event) {
            const files = event.target.files;
            if (!files || files.length === 0) return;

            // 清空之前的选择
            selectedFiles = [];
            uploadedFileIds = [];

            // 显示文件预览容器
            document.getElementById('filePreviewContainer').style.display = 'block';

            if (files.length === 1) {
                // 单文件：显示文件名和大小，立即上传
                const file = files[0];
                document.getElementById('fileName').textContent = '正在上传: ' + file.name;
                document.getElementById('fileSize').textContent = formatFileSize(file.size);
                await uploadSingleFile(file);
            } else {
                // 多文件：显示文件数量和总大小，逐个上传
                let totalSize = 0;
                Array.from(files).forEach(file => {
                    selectedFiles.push(file);
                    totalSize += file.size;
                });
                document.getElementById('fileName').textContent = `正在上传 ${files.length} 个文件...`;
                document.getElementById('fileSize').textContent = `总大小: ${formatFileSize(totalSize)}`;

                // 逐个上传文件
                for (let i = 0; i < selectedFiles.length; i++) {
                    const file = selectedFiles[i];
                    document.getElementById('fileName').textContent = `正在上传: ${file.name} (${i + 1}/${selectedFiles.length})`;
                    await uploadSingleFile(file);
                }

                // 所有文件上传完成
                document.getElementById('fileName').textContent = `已上传 ${uploadedFileIds.length} 个文件`;
                document.getElementById('fileSize').textContent = `总大小: ${formatFileSize(totalSize)}`;
            }

            // 清空 input，允许重复选择同一文件
            document.getElementById('fileUpload').value = '';
        }

        async function uploadSingleFile(file) {
            const reader = new FileReader();
            return new Promise((resolve, reject) => {
                reader.onload = async function(e) {
                    const base64Data = e.target.result;

                    try {
                        const response = await fetch('/api/file/upload', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Authorization': 'Bearer ' + localStorage.getItem('token')
                            },
                            body: JSON.stringify({
                                file_data: base64Data,
                                original_name: file.name,
                                mime_type: file.type,
                                file_size: file.size
                            })
                        });

                        const result = await response.json();
                        if (result.success) {
                            uploadedFileIds.push(result.file.id);
                            currentFileId = result.file.id; // 保存最后一个上传的文件ID
                            resolve(result);
                        } else {
                            alert('上传失败: ' + result.message);
                            reject(new Error(result.message));
                        }
                    } catch (error) {
                        alert('上传出错: ' + error);
                        reject(error);
                    }
                };
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
        }

        function clearFileSelection() {
            selectedFiles = [];
            uploadedFileIds = [];
            currentFileId = null;
            document.getElementById('filePreviewContainer').style.display = 'none';
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function triggerImageUpload() {
            document.getElementById('imageUpload').click();
        }
        
        function handleImageSelect(event) {
            const files = event.target.files;
            if (!files || files.length === 0) return;

            // 按钮选择时，清空之前及其预览（标准文件输入行为）
            selectedImages = [];
            document.getElementById('imagePreviewList').innerHTML = '';

            addFilesToPreview(files);
        }

        // 处理拍照
        function handleCameraCapture(event) {
            const files = event.target.files;
            if (!files || files.length === 0) return;

            // 拍照后直接上传并发送
            const file = files[0];
            uploadAndSendFile(file);

            // 清空input以便下次拍照
            event.target.value = '';
        }

        function addFilesToPreview(files) {
            const previewList = document.getElementById('imagePreviewList');
            document.getElementById('imagePreviewContainer').style.display = 'block';
            
            // 处理每个选中的文件
            Array.from(files).forEach((file) => {
                // 如果是文件对象，处理之
                if (!file.type.startsWith('image/')) {
                    console.log(`文件 ${file.name} 不是图片，已跳过`);
                    return;
                }
                
                // 给截图文件命名（如果需要）
                if (!file.name || file.name === 'image.png') {
                    // 创建一个新的 File 对象以修改名称
                    const newName = 'screenshot_' + new Date().toISOString().replace(/[:.]/g, '-') + '.png';
                    file = new File([file], newName, {type: file.type});
                }
                
                // 读取文件
                const reader = new FileReader();
                reader.onload = function(e) {
                    const imageData = e.target.result;
                    // 添加到全局数组
                    selectedImages.push({
                        file: file,
                        data: imageData,
                        name: file.name
                    });
                    
                    // 重新渲染所有预览以保证索引正确
                    renderPreviewList();
                };
                reader.readAsDataURL(file);
            });
        }

        function renderPreviewList() {
            const previewList = document.getElementById('imagePreviewList');
            previewList.innerHTML = '';
            
            if (selectedImages.length === 0) {
                document.getElementById('imagePreviewContainer').style.display = 'none';
                return;
            }
            
            document.getElementById('imagePreviewContainer').style.display = 'block';
            
            selectedImages.forEach((img, index) => {
                const previewCard = document.createElement('div');
                previewCard.style.cssText = 'position:relative; display:inline-block;';
                previewCard.innerHTML = `
                    <img src="${img.data}" style="width:120px; height:120px; object-fit:cover; border-radius:8px; border:2px solid rgba(255,255,255,0.2);">
                    <button onclick="removeImage(${index})" style="position:absolute; top:-8px; right:-8px; width:24px; height:24px; border-radius:50%; background:#dc3545; color:white; border:none; cursor:pointer; font-size:16px; line-height:1;">×</button>
                    <div style="font-size:11px; color:#999; margin-top:4px; text-align:center; max-width:120px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${img.name}</div>
                `;
                previewList.appendChild(previewCard);
            });
        }

        function setupPasteListener() {
            const aiInput = document.getElementById('aiInput');
            if (!aiInput) return;

            aiInput.addEventListener('paste', function(e) {
                const items = (e.clipboardData || e.originalEvent.clipboardData).items;
                const files = [];
                
                for (let i = 0; i < items.length; i++) {
                    if (items[i].type.indexOf('image') !== -1) {
                        const file = items[i].getAsFile();
                        if (file) files.push(file);
                    }
                }
                
                if (files.length > 0) {
                    addFilesToPreview(files);
                }
            });
        }
        
        function removeImage(index) {
            selectedImages.splice(index, 1);
            renderPreviewList();
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

        // 显示加载动画
        function showLoading() {
            const box = document.getElementById('aiChatBox');
            const loadingId = 'loading-' + Date.now();
            const loadingDiv = document.createElement('div');
            loadingDiv.id = loadingId;
            loadingDiv.className = 'message assistant';
            loadingDiv.innerHTML = `
                <div class="ai-message">
                    <span class="loading-dots">正在思考<span>.</span><span>.</span><span>.</span></span>
                </div>
            `;
            box.appendChild(loadingDiv);
            box.scrollTop = box.scrollHeight;
            return loadingId;
        }

        // 移除加载动画
        function removeLoading(loadingId) {
            const loadingEl = document.getElementById(loadingId);
            if (loadingEl) {
                loadingEl.remove();
            }
        }

        // 上传文件并发送消息
        async function uploadAndSendFile(file, message = '') {
            try {
                // 显示上传中提示
                const loadingId = showLoading();

                // 读取文件为base64
                const reader = new FileReader();
                reader.onload = async function(e) {
                    try {
                        const fileData = e.target.result;

                        // 上传文件到服务器
                        const response = await fetch('/api/file/upload', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Authorization': 'Bearer ' + localStorage.getItem('token')
                            },
                            body: JSON.stringify({
                                file_data: fileData,
                                original_name: file.name,
                                mime_type: file.type,
                                description: message || '聊天中发送的文件',
                                tags: []
                            })
                        });

                        const result = await response.json();

                        if (result.success && result.file) {
                            // 移除加载动画
                            removeLoading(loadingId);

                            // 设置文件ID并发送消息
                            currentFileId = result.file.id;

                            // 显示用户消息（包含文件信息）
                            const fileInfo = {
                                name: result.file.original_name,
                                size: result.file.file_size
                            };
                            appendAI('user', message || '发送了文件', null, fileInfo);

                            // 发送到AI
                            const aiResponse = await fetch('/api/ai/chat', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'Authorization': 'Bearer ' + localStorage.getItem('token'),
                                    'X-Session-ID': getOrCreateSessionId()
                                },
                                body: JSON.stringify({
                                    message: message || '我发送了一个文件',
                                    file_id: currentFileId
                                })
                            });

                            const aiResult = await aiResponse.json();

                            // 显示AI回复
                            if (aiResult.response) {
                                appendAI('assistant', aiResult.response);
                            }

                            // 清空文件ID
                            currentFileId = null;
                        } else {
                            removeLoading(loadingId);
                            alert('文件上传失败：' + (result.message || result.error || '未知错误'));
                        }
                    } catch (error) {
                        removeLoading(loadingId);
                        console.error('上传文件出错:', error);
                        alert('上传文件出错：' + error.message);
                    }
                };

                reader.readAsDataURL(file);
            } catch (error) {
                console.error('处理文件出错:', error);
                alert('处理文件出错：' + error.message);
            }
        }

        async function sendAI() {
            const input = document.getElementById('aiInput');
            const message = input.value.trim();
            const originalText = message; // 保存原始文本用于乐观更新

            if (!message && !currentFileId) return; // 如果没有消息也没有文件，则不发送

            // 保存输入历史记录
            if (message) {
                saveInputHistory(message);
            }

            // 清空输入
            input.value = '';
            autoResizeTextarea(input); // 重置高度

            // 乐观更新：立即显示用户消息
            let fileInfo = null;
            if (currentFileId) {
                const fileName = document.getElementById('fileName').textContent;
                const fileSize = document.getElementById('fileSize').textContent;
                // 模拟 fileInfo 对象用于预览
                fileInfo = {
                    name: fileName.replace('正在上传: ', ''),
                    size: 0 // 实际上formatFileSize返回的是字符串，这里appendAI里再次格式化可能会有问题，但appendAI处理了
                };
                // appendAI 里 formatFileSize 需要数字，或者我们直接在 innerHTML 里处理
                // 简单起见，我们传给 appendAI 的 fileInfo.size 如果是字符串，formatFileSize 可能返回 NaN
                // 让我们直接修改 appendAI 让他支持字符串 size (如果已经是格式化好的)
                // 或者在这里不做太复杂，直接显示文件名
            }
            
            appendAI('user', originalText, null, fileInfo); 
            
            // 显示加载状态
            const loadingId = showLoading();

            try {
                const resp = await fetch('/api/ai/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + localStorage.getItem('token'),
                        'X-Session-ID': getOrCreateSessionId() // ✨ 添加会话ID
                    },
                    body: JSON.stringify({
                        message: message,
                        file_id: currentFileId // 传递文件ID
                    })
                });

                // 发送后清空文件选择
                if (currentFileId) {
                    clearFileSelection();
                }

                const data = await resp.json();
                removeLoading(loadingId);

                // 保存列表数据（如果有）
                if (data.list_data && data.list_data.length > 0) {
                    window.lastListData = data.list_data;
                    console.log('保存列表数据:', data.list_data.length, '个项目');
                } else if (data.work_list_data && data.work_list_data.length > 0) {
                    // 兼容旧版本的 work_list_data
                    window.lastListData = data.work_list_data;
                    console.log('保存列表数据:', data.work_list_data.length, '个任务');
                }

                if (data.response) {
                    appendAI('assistant', data.response);
                }

                // 处理识别到的计划（如果有）
                if (data.detected_plans && data.detected_plans.length > 0) {
                    // TODO: 实现showPlanConfirmation函数
                    // data.detected_plans.forEach(plan => {
                    //     showPlanConfirmation(plan);
                    // });
                    console.log('检测到计划:', data.detected_plans);
                }

                // 处理识别到的提醒
                if (data.detected_reminders && data.detected_reminders.length > 0) {
                    // 刷新提醒列表
                    loadReminders();

                    // 调试：弹窗确认是否进入此逻辑
                    // alert('Web端捕获到 ' + data.detected_reminders.length + ' 个提醒，准备写入日历');

                    // 发送给 Flutter App 添加日历
                    if (window.FlutterApp) {
                        try {
                            data.detected_reminders.forEach(reminder => {
                                const message = {
                                    type: 'add_calendar_event',
                                    title: 'AI助理: ' + (reminder.content || '提醒事项'),
                                    description: reminder.content || '',
                                    startTime: reminder.remind_time
                                };
                                // 如果有循环类型，添加到消息中
                                if (reminder.recurrence) {
                                    message.recurrence = reminder.recurrence;
                                }
                                window.FlutterApp.postMessage(JSON.stringify(message));
                            });
                            // alert('✅ 已发送指令给App'); // 成功发送
                        } catch (e) {
                            alert('❌ 发送失败: ' + e);
                        }
                    } else {
                        // alert('⚠️ 未检测到 FlutterApp 环境'); // 关键调试点
                    }
                }

            } catch (error) {
                removeLoading(loadingId);
                appendAI('assistant', '⚠️ 抱歉，发生了错误，请稍后重试。');
                console.error('Chat error:', error);
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

            // 3. 保存AI助理名字到服务器
            const aiNameInput = document.getElementById('aiAssistantName');
            const aiAssistantName = aiNameInput ? aiNameInput.value.trim() : '';

            if (aiAssistantName) {
                try {
                    const response = await fetchWithAuth('/api/user/update-ai-assistant-name', {
                        method: 'POST',
                        body: JSON.stringify({
                            ai_assistant_name: aiAssistantName
                        })
                    });
                    const data = await response.json();
                    if (!data.success) {
                        console.error('保存AI助理名字失败:', data.message);
                    }
                } catch (e) {
                    console.error('保存AI助理名字出错:', e);
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
        // ✨ 获取或生成浏览器会话ID（存储在sessionStorage，关闭浏览器后清空）
        function getOrCreateSessionId() {
            let sessionId = sessionStorage.getItem('browser_session_id');
            if (!sessionId) {
                // 生成新的会话ID（UUID格式）
                sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                sessionStorage.setItem('browser_session_id', sessionId);
                console.log('🔑 生成新的浏览器会话ID:', sessionId);
            }
            return sessionId;
        }

        function fetchWithAuth(url, options = {}) {
            const token = localStorage.getItem('token');
            const sessionId = getOrCreateSessionId(); // ✨ 获取会话ID
            const headers = options.headers || {};

            if (token) {
                headers['Authorization'] = 'Bearer ' + token;
            }

            // ✨ 添加会话ID到请求头
            headers['X-Session-ID'] = sessionId;

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
                        // loadChatHistory(); // 已禁用自动加载历史记录
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


        // ============ 视图切换函数 ============

        function switchView(viewName) {
            console.log('切换到视图:', viewName);

            // 更新导航项的active状态
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            document.querySelector(`.nav-item[data-view="${viewName}"]`)?.classList.add('active');

            // 根据不同视图执行不同操作
            switch(viewName) {
                case 'chat':
                    // 显示聊天界面（默认视图）
                    window.location.href = '/ai/';
                    break;
                case 'plans':
                    // 打开工作计划
                    openWorkPlans();
                    break;
                case 'reminders':
                    // 打开提醒事项
                    openReminders();
                    break;
                case 'friends':
                    // 打开朋友/社交中心
                    window.open('/ai/social', '_blank');
                    break;
                case 'files':
                    // 打开文件管理
                    window.open('/ai/file-manager', '_blank');
                    break;
                case 'settings':
                    // 打开设置
                    openSettings();
                    break;
            }
        }

        function openReminders() {
            // 显示提醒事项弹窗
            document.getElementById('remindersModal').style.display = 'block';
            // 加载提醒列表
            loadReminders();
        }

        function closeReminders() {
            document.getElementById('remindersModal').style.display = 'none';
        }

        async function loadReminders() {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/reminders', {
                    headers: {
                        'Authorization': 'Bearer ' + token
                    }
                });

                if (!response.ok) throw new Error('加载失败');

                const data = await response.json();
                const reminders = data.reminders || [];

                const container = document.getElementById('remindersView');
                if (!container) return;

                if (reminders.length === 0) {
                    container.innerHTML = `
                        <div style="text-align: center; padding: 40px;">
                            <div style="font-size: 48px; margin-bottom: 10px;">⏰</div>
                            <p style="color: #666;">暂无提醒事项</p>
                        </div>
                    `;
                    return;
                }

                let html = '<div style="padding: 10px;">';
                reminders.forEach(reminder => {
                    const time = new Date(reminder.remind_time).toLocaleString('zh-CN');
                    const status = reminder.triggered ? '已触发' : '待触发';
                    const statusColor = reminder.triggered ? '#999' : '#10a37f';

                    html += `
                        <div style="background: #ffffff; padding: 15px; margin-bottom: 10px; border-radius: 8px; border: 1px solid #e0e0e0;">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div style="flex: 1;">
                                    <div style="font-weight: 600; margin-bottom: 5px; color: #000;">${reminder.content}</div>
                                    <div style="font-size: 12px; color: #666;">
                                        ⏰ ${time}
                                        <span style="margin-left: 10px; color: ${statusColor}; font-weight: 600;">${status}</span>
                                    </div>
                                </div>
                                <button onclick="deleteReminder(${reminder.id})" style="background: #ff6b6b; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 12px; font-weight: 600;">删除</button>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';

                container.innerHTML = html;
            } catch (error) {
                console.error('加载提醒失败:', error);
                const container = document.getElementById('remindersView');
                if (container) {
                    container.innerHTML = `
                        <div style="text-align: center; padding: 40px;">
                            <p style="color: #ff6b6b;">加载失败，请重试</p>
                        </div>
                    `;
                }
            }
        }

        async function deleteReminder(id) {
            if (!confirm('确定要删除这个提醒吗？')) return;

            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/reminder/delete', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + token,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ reminder_id: id })
                });

                if (!response.ok) throw new Error('删除失败');

                // 重新加载列表
                loadReminders();
            } catch (error) {
                console.error('删除提醒失败:', error);
                alert('删除失败，请重试');
            }
        }

        // 全局变量存储当前选择的循环类型
        let currentRepeatType = 'once';

        function showCreateReminderForm() {
            const form = document.getElementById('createReminderForm');
            form.style.display = 'block';

            // 设置默认日期和时间
            const now = new Date();
            const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);

            // 设置日期为明天
            const dateStr = tomorrow.toISOString().split('T')[0];
            document.getElementById('reminderDate').value = dateStr;

            // 设置时间为当前时间
            const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
            document.getElementById('reminderTime').value = timeStr;

            // 清空内容
            document.getElementById('reminderContent').value = '';

            // 重置循环类型为单次
            currentRepeatType = 'once';
            selectRepeatType('once');
        }

        function hideCreateReminderForm() {
            document.getElementById('createReminderForm').style.display = 'none';
        }

        function selectRepeatType(type) {
            currentRepeatType = type;

            // 更新所有按钮的样式
            document.querySelectorAll('.repeat-type-btn').forEach(btn => {
                if (btn.dataset.type === type) {
                    btn.style.background = '#10a37f';
                    btn.style.color = 'white';
                    btn.style.borderColor = '#10a37f';
                } else {
                    btn.style.background = 'white';
                    btn.style.color = '#333';
                    btn.style.borderColor = '#ddd';
                }
            });
        }

        // 切换好友选择区域
        function toggleFriendSelection() {
            const checkbox = document.getElementById('alsoNotifyFriends');
            const friendArea = document.getElementById('friendSelectionArea');

            if (checkbox.checked) {
                friendArea.style.display = 'block';
                loadFriendsForReminder();
            } else {
                friendArea.style.display = 'none';
            }
        }

        // 加载好友列表用于提醒
        async function loadFriendsForReminder() {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/social/friends', {
                    headers: {'Authorization': 'Bearer ' + token}
                });

                if (!response.ok) {
                    throw new Error('加载好友列表失败');
                }

                const data = await response.json();
                const friends = data.friends || [];

                const container = document.getElementById('friendCheckboxList');

                if (friends.length === 0) {
                    container.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">暂无好友</p>';
                    return;
                }

                container.innerHTML = friends.map(friend => `
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: white; border-radius: 6px; cursor: pointer; user-select: none; border: 1px solid #e0e0e0;">
                        <input type="checkbox" class="friend-checkbox" value="${friend.id}" style="width: 18px; height: 18px; cursor: pointer;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 14px;">
                            ${friend.username.substring(0, 1).toUpperCase()}
                        </div>
                        <span style="color: #000; font-weight: 500;">${friend.username}</span>
                    </label>
                `).join('');
            } catch (error) {
                console.error('加载好友列表失败:', error);
                document.getElementById('friendCheckboxList').innerHTML = '<p style="text-align: center; color: #ff6b6b; padding: 20px;">加载失败</p>';
            }
        }

        // 全选好友
        function selectAllFriends() {
            const checkboxes = document.querySelectorAll('.friend-checkbox');
            const allChecked = Array.from(checkboxes).every(cb => cb.checked);

            checkboxes.forEach(cb => {
                cb.checked = !allChecked;
            });
        }

        // 从工作计划创建提醒
        function createReminderFromPlan(planId, title, deadline) {
            showCreateReminderForm();

            // 填充内容
            document.getElementById('reminderContent').value = title;

            // 如果有截止日期，使用截止日期
            if (deadline) {
                const deadlineDate = new Date(deadline);
                const dateStr = deadlineDate.toISOString().split('T')[0];
                document.getElementById('reminderDate').value = dateStr;

                // 设置时间为9:00
                document.getElementById('reminderTime').value = '09:00';
            }
        }

        // 从工作记录创建提醒
        function createReminderFromRecord(content, deadline) {
            showCreateReminderForm();

            // 填充内容
            document.getElementById('reminderContent').value = content;

            // 如果有截止日期，使用截止日期
            if (deadline) {
                const deadlineDate = new Date(deadline);
                const dateStr = deadlineDate.toISOString().split('T')[0];
                document.getElementById('reminderDate').value = dateStr;

                // 设置时间为9:00
                document.getElementById('reminderTime').value = '09:00';
            }
        }

        async function saveNewReminder() {
            const content = document.getElementById('reminderContent').value.trim();
            const date = document.getElementById('reminderDate').value;
            const time = document.getElementById('reminderTime').value;

            // 验证输入
            if (!content) {
                alert('请输入提醒内容');
                return;
            }

            if (!date || !time) {
                alert('请选择日期和时间');
                return;
            }

            // 组合日期和时间
            const remindTimeStr = `${date} ${time}:00`;

            // 调试日志
            console.log('🔍 [前端] 准备创建提醒:');
            console.log('  - content:', content);
            console.log('  - remind_time:', remindTimeStr);
            console.log('  - currentRepeatType:', currentRepeatType);

            try {
                const token = localStorage.getItem('token');

                const requestBody = {
                    content: content,
                    remind_time: remindTimeStr,
                    repeat_type: currentRepeatType
                };
                console.log('  - 请求体:', JSON.stringify(requestBody));

                // 为自己创建提醒
                const response = await fetch('/api/reminder/add', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + token,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestBody)
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || '创建失败');
                }

                // 检查是否需要同时提醒好友
                const alsoNotifyFriends = document.getElementById('alsoNotifyFriends').checked;
                if (alsoNotifyFriends) {
                    // 获取选中的好友ID
                    const selectedFriends = Array.from(document.querySelectorAll('.friend-checkbox:checked'))
                        .map(cb => cb.value);

                    if (selectedFriends.length > 0) {
                        // 为每个好友创建提醒
                        const friendPromises = selectedFriends.map(friendId =>
                            fetch('/api/social/reminders/create', {
                                method: 'POST',
                                headers: {
                                    'Authorization': 'Bearer ' + token,
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    friend_id: friendId,
                                    content: content,
                                    remind_time: remindTimeStr,
                                    repeat_type: currentRepeatType
                                })
                            })
                        );

                        // 等待所有好友提醒创建完成
                        await Promise.all(friendPromises);
                    }
                }

                // 隐藏表单
                hideCreateReminderForm();

                // 重置好友选择
                document.getElementById('alsoNotifyFriends').checked = false;
                document.getElementById('friendSelectionArea').style.display = 'none';

                // 重新加载列表
                loadReminders();

                // 显示成功提示
                if (alsoNotifyFriends) {
                    const selectedCount = document.querySelectorAll('.friend-checkbox:checked').length;
                    alert(`✅ 提醒创建成功！已同时提醒 ${selectedCount} 位好友`);
                } else {
                    alert('✅ 提醒创建成功！');
                }
            } catch (error) {
                console.error('创建提醒失败:', error);
                alert('创建失败：' + error.message);
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

                    // 加载AI助理名字
                    const aiNameInput = document.getElementById('aiAssistantName');
                    if (aiNameInput && user.ai_assistant_name) {
                        aiNameInput.value = user.ai_assistant_name;
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
                        
                        appendAI(msg.role, msg.content, timeStr, msg.file_info);
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

        // ==================== 提醒通知系统 ====================

        /**
         * 检查到期的提醒并显示通知
         */
        async function checkDueReminders() {
            try {
                const token = localStorage.getItem('token');
                if (!token) {
                    console.log('[提醒检查] Token不存在，跳过');
                    return;
                }

                const response = await fetch('/api/reminders/check', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (!response.ok) {
                    console.log('[提醒检查] API响应失败:', response.status);
                    return;
                }

                const data = await response.json();
                console.log('[提醒检查] API返回:', data);

                if (data.success && data.reminders && data.reminders.length > 0) {
                    console.log(`[提醒检查] 找到${data.reminders.length}条到期提醒`);
                    // 显示所有到期的提醒
                    data.reminders.forEach((reminder, index) => {
                        console.log(`[提醒检查] 显示第${index + 1}条:`, reminder);
                        showReminderNotification(reminder);
                    });
                }
            } catch (e) {
                console.error('[提醒检查] 异常:', e);
            }
        }

        /**
         * 显示提醒通知（优先使用Electron原生通知）
         */
        function showReminderNotification(reminder) {
            const title = '📢 任务提醒';
            const body = reminder.content;

            // 1. 优先使用Electron原生通知（如果在Electron环境中）
            if (window.electronAPI && window.electronAPI.showNotification) {
                console.log('使用Electron原生通知:', title, body);
                window.electronAPI.showNotification(title, body, false);
                return;
            }

            // 2. 降级到Web Notification API
            if ('Notification' in window) {
                if (Notification.permission === 'granted') {
                    try {
                        const notification = new Notification(title, {
                            body: body,
                            icon: '/favicon.ico',
                            tag: `reminder-${reminder.id}`,
                            requireInteraction: true // 需要用户主动关闭
                        });

                        // 点击通知时聚焦窗口
                        notification.onclick = () => {
                            window.focus();
                            notification.close();
                        };

                        console.log('✅ Web通知已显示:', body);
                    } catch (e) {
                        console.error('Web通知显示失败:', e);
                        // 降级到页面内通知
                        showInPageAlert(title, body);
                    }
                } else if (Notification.permission === 'default') {
                    // 请求通知权限
                    Notification.requestPermission().then(permission => {
                        if (permission === 'granted') {
                            showReminderNotification(reminder);
                        } else {
                            showInPageAlert(title, body);
                        }
                    });
                } else {
                    // 权限被拒绝，使用页面内通知
                    showInPageAlert(title, body);
                }
            } else {
                // 浏览器不支持通知，使用页面内通知
                showInPageAlert(title, body);
            }
        }

        /**
         * 页面内通知（最后降级方案）
         */
        function showInPageAlert(title, message) {
            // 创建通知元素
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px 30px;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(102, 126, 234, 0.5);
                z-index: 10000;
                max-width: 400px;
                animation: slideInRight 0.3s ease-out;
                cursor: pointer;
            `;
            notification.innerHTML = `
                <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">${title}</div>
                <div style="font-size: 14px; line-height: 1.5;">${message}</div>
            `;

            // 添加到页面
            document.body.appendChild(notification);

            // 点击关闭
            notification.onclick = () => notification.remove();

            // 5秒后自动关闭
            setTimeout(() => {
                notification.style.animation = 'slideOutRight 0.3s ease-out';
                setTimeout(() => notification.remove(), 300);
            }, 5000);

            console.log('✅ 页面内通知已显示:', message);
        }

        /**
         * 启动提醒检查器（每10秒检查一次）
         */
        function startReminderChecker() {
            // 首次立即检查
            checkDueReminders();

            // 每10秒检查一次
            setInterval(checkDueReminders, 10000);

            console.log('✅ 提醒检查器已启动（10秒间隔）');
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

            // 2.5. 初始化侧边栏用户名显示
            try {
                const username = localStorage.getItem('username') || '用户';
                const sidebarUsername = document.getElementById('sidebar-username');
                if (sidebarUsername) {
                    sidebarUsername.textContent = username;
                }
            } catch (e) {
                console.error('Init sidebar username failed:', e);
            }

            // 3. 计算文本框最大高度 (新功能)
            try {
                calculateMaxHeight();
            } catch (e) {
                console.error('Calculate max height failed:', e);
            }

            // 3.5. 初始化textarea自动高度调整（仅手机端）
            try {
                const aiInput = document.getElementById('aiInput');
                if (aiInput && window.innerWidth <= 768) {
                    // 监听输入事件
                    aiInput.addEventListener('input', function() {
                        autoResizeTextarea(this);
                    });

                    // 初始化高度
                    autoResizeTextarea(aiInput);

                    console.log('✅ Textarea自动高度已启用');
                }
            } catch (e) {
                console.error('Init textarea auto-resize failed:', e);
            }

            // 4. 打字机效果
            try {
                const welcomeTextElem = document.getElementById('welcomeText');
                if (welcomeTextElem) {
                    const username = localStorage.getItem('username') || '访客';
                    typeWriter(welcomeTextElem, `怕忘事儿？交给我，随时帮你记、帮你找～`, 80);
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
                    
                    // 初始化粘贴图片功能
                    if (typeof setupPasteListener === 'function') {
                        setupPasteListener();
                    }
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

            // 9. 启动提醒检查（Electron原生通知 或 Web Notification）
            try {
                startReminderChecker();
            } catch (e) {
                console.error('Start reminder checker failed:', e);
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

            // 保存当前计划列表供批量编辑使用
            window.currentPlans = filteredPlans;

            container.innerHTML = filteredPlans.map((plan, index) => {
                const priorityIcon = priorityIconMap[plan.priority] || '🟡';
                const statusText = statusMap[plan.status] || plan.status;
                const description = plan.description || plan.content || '';

                // 判断任务标题样式和标记状态
                let titleClass = 'plan-title';
                const hasUrgent = plan.title.startsWith('急');
                const hasImportant = plan.title.startsWith('重要');

                if (hasUrgent) {
                    titleClass += ' urgent';
                } else if (hasImportant) {
                    titleClass += ' important';
                }

                // 编辑模式下的复选框
                const editModeCheckboxes = window.batchEditMode ? `
                    <div class="batch-edit-controls" style="display:flex; gap:8px; margin-bottom:10px; padding:8px; background:rgba(102, 126, 234, 0.1); border-radius:4px;">
                        <label style="display:flex; align-items:center; gap:4px; cursor:pointer; user-select:none;">
                            <input type="checkbox" class="urgent-checkbox" data-plan-id="${plan.id}" ${hasUrgent ? 'checked' : ''}
                                   style="width:18px; height:18px; cursor:pointer;">
                            <span style="color:#dc3545; font-weight:bold;">急</span>
                        </label>
                        <label style="display:flex; align-items:center; gap:4px; cursor:pointer; user-select:none;">
                            <input type="checkbox" class="important-checkbox" data-plan-id="${plan.id}" ${hasImportant ? 'checked' : ''}
                                   style="width:18px; height:18px; cursor:pointer;">
                            <span style="color:#ff8c00; font-weight:bold;">重要</span>
                        </label>
                        <div style="flex:1;"></div>
                        <span style="color:#999; font-size:12px;">☰ 拖动排序</span>
                    </div>
                ` : '';

                return `
                    <div class="plan-card ${window.batchEditMode ? 'draggable' : ''}"
                         data-plan-id="${plan.id}"
                         data-index="${index}"
                         draggable="${window.batchEditMode ? 'true' : 'false'}"
                         ondragstart="${window.batchEditMode ? 'handleDragStart(event)' : ''}"
                         ondragover="${window.batchEditMode ? 'handleDragOver(event)' : ''}"
                         ondrop="${window.batchEditMode ? 'handleDrop(event)' : ''}"
                         ondragend="${window.batchEditMode ? 'handleDragEnd(event)' : ''}"
                         style="${window.batchEditMode ? 'cursor:move;' : ''}">
                        ${editModeCheckboxes}
                        <div class="plan-header">
                            <h4 class="${titleClass}">${priorityIcon} ${plan.title}</h4>
                            <span class="plan-status status-${statusText.replace(/\\s+/g, '')}">${statusText}</span>
                        </div>
                        ${description ? `<p style="color:#aaa; font-size:14px; margin:8px 0;">${description}</p>` : ''}
                        <div class="plan-meta">
                            ${plan.deadline || plan.due_date ? `<span>⏰ ${plan.deadline || plan.due_date}</span>` : ''}
                            <span>📅 创建: ${plan.created_at ? plan.created_at.substring(0, 10) : ''}</span>
                        </div>
                        <div class="plan-actions" style="${window.batchEditMode ? 'display:none;' : ''}">
                            <button class="plan-btn plan-btn-pin" onclick="pinWorkPlan(${plan.id})" title="置顶">
                                📌 置顶
                            </button>
                            <button class="plan-btn plan-btn-edit" onclick="editWorkPlan(${plan.id}, '${plan.title.replace(/'/g, "\\'")}', '${description.replace(/'/g, "\\'")}', '${plan.deadline || plan.due_date || ''}', '${plan.priority}')">
                                ✏️ 编辑
                            </button>
                            <button class="plan-btn plan-btn-reminder" onclick="createReminderFromPlan(${plan.id}, '${plan.title.replace(/'/g, "\\'")}', '${plan.deadline || plan.due_date || ''}')">
                                ⏰ 提醒
                            </button>
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

        // 置顶工作计划
        async function pinWorkPlan(planId) {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/plan/pin', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? {'Authorization': 'Bearer ' + token} : {})
                    },
                    body: JSON.stringify({id: planId})
                });

                if (response.ok) {
                    loadWorkPlans();
                    // 可选：显示提示
                    const result = await response.json();
                    if (result.success) {
                        // 简单的视觉反馈
                        const card = document.querySelector(`[data-plan-id="${planId}"]`);
                        if (card) {
                            card.style.animation = 'pulse 0.3s ease-in-out';
                            setTimeout(() => {
                                card.style.animation = '';
                            }, 300);
                        }
                    }
                } else {
                    const error = await response.text();
                    console.error('置顶失败:', error);
                    alert('❌ 置顶失败');
                }
            } catch (e) {
                console.error('置顶工作计划失败:', e);
                alert('❌ 置顶失败: ' + e.message);
            }
        }

        // ========== 批量编辑功能 ==========

        // 切换批量编辑模式
        function toggleBatchEditMode() {
            window.batchEditMode = !window.batchEditMode;

            const batchEditBtn = document.getElementById('batchEditBtn');
            const saveBatchEditBtn = document.getElementById('saveBatchEditBtn');
            const cancelBatchEditBtn = document.getElementById('cancelBatchEditBtn');

            if (window.batchEditMode) {
                // 进入编辑模式
                batchEditBtn.style.display = 'none';
                saveBatchEditBtn.style.display = 'block';
                cancelBatchEditBtn.style.display = 'block';

                // 保存原始数据用于取消
                window.originalPlans = JSON.parse(JSON.stringify(window.currentPlans));
            } else {
                // 退出编辑模式
                batchEditBtn.style.display = 'block';
                saveBatchEditBtn.style.display = 'none';
                cancelBatchEditBtn.style.display = 'none';
            }

            // 重新渲染列表
            loadWorkPlans();
        }

        // 取消批量编辑
        function cancelBatchEdit() {
            window.batchEditMode = false;

            const batchEditBtn = document.getElementById('batchEditBtn');
            const saveBatchEditBtn = document.getElementById('saveBatchEditBtn');
            const cancelBatchEditBtn = document.getElementById('cancelBatchEditBtn');

            batchEditBtn.style.display = 'block';
            saveBatchEditBtn.style.display = 'none';
            cancelBatchEditBtn.style.display = 'none';

            // 重新加载原始数据
            loadWorkPlans();
        }

        // 保存批量编辑
        async function saveBatchEdit() {
            try {
                const token = localStorage.getItem('token');
                const updates = [];

                // 获取所有计划卡片
                const planCards = document.querySelectorAll('.plan-card');

                planCards.forEach((card, index) => {
                    const planId = parseInt(card.getAttribute('data-plan-id'));
                    const urgentCheckbox = card.querySelector('.urgent-checkbox');
                    const importantCheckbox = card.querySelector('.important-checkbox');

                    // 找到原始计划数据
                    const originalPlan = window.currentPlans.find(p => p.id === planId);
                    if (!originalPlan) return;

                    // 构建新标题
                    let newTitle = originalPlan.title;

                    // 移除现有的"急"和"重要"前缀
                    newTitle = newTitle.replace(/^急\s*/, '').replace(/^重要\s*/, '');

                    // 根据复选框状态添加前缀
                    if (urgentCheckbox && urgentCheckbox.checked) {
                        newTitle = '急 ' + newTitle;
                    } else if (importantCheckbox && importantCheckbox.checked) {
                        newTitle = '重要 ' + newTitle;
                    }

                    updates.push({
                        id: planId,
                        title: newTitle,
                        sort_order: planCards.length - index  // 倒序，越靠前sort_order越大
                    });
                });

                // 发送批量更新请求
                const response = await fetch('/api/plan/batch-update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? {'Authorization': 'Bearer ' + token} : {})
                    },
                    body: JSON.stringify({updates})
                });

                if (response.ok) {
                    // 退出编辑模式
                    window.batchEditMode = false;

                    const batchEditBtn = document.getElementById('batchEditBtn');
                    const saveBatchEditBtn = document.getElementById('saveBatchEditBtn');
                    const cancelBatchEditBtn = document.getElementById('cancelBatchEditBtn');

                    batchEditBtn.style.display = 'block';
                    saveBatchEditBtn.style.display = 'none';
                    cancelBatchEditBtn.style.display = 'none';

                    // 重新加载列表
                    loadWorkPlans();
                    alert('✅ 保存成功');
                } else {
                    const error = await response.text();
                    console.error('批量更新失败:', error);
                    alert('❌ 保存失败');
                }
            } catch (e) {
                console.error('批量更新失败:', e);
                alert('❌ 保存失败: ' + e.message);
            }
        }

        // ========== 拖拽排序功能 ==========

        let draggedElement = null;

        function handleDragStart(e) {
            draggedElement = e.target.closest('.plan-card');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/html', draggedElement.innerHTML);
            draggedElement.style.opacity = '0.4';
        }

        function handleDragOver(e) {
            if (e.preventDefault) {
                e.preventDefault();
            }
            e.dataTransfer.dropEffect = 'move';

            const targetCard = e.target.closest('.plan-card');
            if (targetCard && targetCard !== draggedElement) {
                const container = document.getElementById('workPlansList');
                const allCards = Array.from(container.querySelectorAll('.plan-card'));
                const draggedIndex = allCards.indexOf(draggedElement);
                const targetIndex = allCards.indexOf(targetCard);

                if (draggedIndex < targetIndex) {
                    targetCard.parentNode.insertBefore(draggedElement, targetCard.nextSibling);
                } else {
                    targetCard.parentNode.insertBefore(draggedElement, targetCard);
                }
            }

            return false;
        }

        function handleDrop(e) {
            if (e.stopPropagation) {
                e.stopPropagation();
            }
            return false;
        }

        function handleDragEnd(e) {
            if (draggedElement) {
                draggedElement.style.opacity = '1';
            }

            // 更新所有卡片的data-index
            const container = document.getElementById('workPlansList');
            const allCards = container.querySelectorAll('.plan-card');
            allCards.forEach((card, index) => {
                card.setAttribute('data-index', index);
            });
        }

        // ========== 聊天列表编辑功能 ==========

        function toggleListEditMode(button) {
            const container = button.closest('.list-container');
            const editBar = container.querySelector('.list-edit-bar');
            const editBtn = editBar.querySelector('.list-edit-btn');
            const saveBtn = editBar.querySelector('.list-save-btn');
            const cancelBtn = editBar.querySelector('.list-cancel-btn');
            const items = container.querySelectorAll('.list-item');
            const checkboxes = container.querySelectorAll('.list-checkboxes');

            // 切换按钮显示
            editBtn.style.display = 'none';
            saveBtn.style.display = 'block';
            cancelBtn.style.display = 'block';

            // 显示复选框
            checkboxes.forEach(cb => cb.style.display = 'block');

            // 启用拖拽
            items.forEach(item => {
                item.setAttribute('draggable', 'true');
                item.style.cursor = 'move';
                item.style.padding = '8px';
                item.style.marginBottom = '4px';
                item.style.background = 'rgba(102, 126, 234, 0.05)';
                item.style.borderRadius = '4px';

                // 添加拖拽事件
                item.addEventListener('dragstart', handleListDragStart);
                item.addEventListener('dragover', handleListDragOver);
                item.addEventListener('drop', handleListDrop);
                item.addEventListener('dragend', handleListDragEnd);
            });

            // 保存原始数据
            container.dataset.editMode = 'true';
        }

        function cancelListEdit(button) {
            const container = button.closest('.list-container');
            const editBar = container.querySelector('.list-edit-bar');
            const editBtn = editBar.querySelector('.list-edit-btn');
            const saveBtn = editBar.querySelector('.list-save-btn');
            const cancelBtn = editBar.querySelector('.list-cancel-btn');
            const checkboxes = container.querySelectorAll('.list-checkboxes');
            const items = container.querySelectorAll('.list-item');

            // 切换按钮显示
            editBtn.style.display = 'block';
            saveBtn.style.display = 'none';
            cancelBtn.style.display = 'none';

            // 隐藏复选框
            checkboxes.forEach(cb => cb.style.display = 'none');

            // 禁用拖拽
            items.forEach(item => {
                item.setAttribute('draggable', 'false');
                item.style.cursor = 'default';
                item.style.padding = '0';
                item.style.marginBottom = '0';
                item.style.background = 'none';
                item.style.borderRadius = '0';

                // 移除拖拽事件
                item.removeEventListener('dragstart', handleListDragStart);
                item.removeEventListener('dragover', handleListDragOver);
                item.removeEventListener('drop', handleListDrop);
                item.removeEventListener('dragend', handleListDragEnd);
            });

            container.dataset.editMode = 'false';

            // 重新加载列表（恢复原始状态）
            location.reload();
        }

        async function saveListEdit(button) {
            const container = button.closest('.list-container');
            const listType = container.getAttribute('data-list-type');
            const items = container.querySelectorAll('.list-item');
            const updates = [];

            items.forEach((item, index) => {
                const taskId = parseInt(item.dataset.taskId);
                if (!taskId) return;

                const urgentCheck = item.querySelector('.urgent-check');
                const importantCheck = item.querySelector('.important-check');

                // 获取原始任务数据
                const taskData = window.lastListData.find(t => t.id === taskId);
                if (!taskData) return;

                // 构建新标题
                let newTitle = taskData.title;

                // 移除现有的"急"和"重要"前缀
                newTitle = newTitle.replace(/^急\\s*/, '').replace(/^重要\\s*/, '');

                // 根据复选框状态添加前缀
                if (urgentCheck && urgentCheck.checked) {
                    newTitle = '急 ' + newTitle;
                } else if (importantCheck && importantCheck.checked) {
                    newTitle = '重要 ' + newTitle;
                }

                updates.push({
                    id: taskId,
                    title: newTitle,
                    sort_order: items.length - index  // 倒序，越靠前sort_order越大
                });
            });

            try {
                const token = localStorage.getItem('token');
                let apiUrl;

                // 根据类别类型选择不同的API
                if (listType === '工作') {
                    // 工作任务使用 plan API
                    apiUrl = '/api/plan/batch-update';
                } else {
                    // 其他子类别使用 record API
                    apiUrl = '/api/record/batch-update';
                }

                const response = await fetch(apiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? {'Authorization': 'Bearer ' + token} : {})
                    },
                    body: JSON.stringify({updates})
                });

                if (response.ok) {
                    alert('✅ 保存成功');
                    // 重新加载页面以显示更新后的数据
                    location.reload();
                } else {
                    const error = await response.text();
                    console.error('批量更新失败:', error);
                    alert('❌ 保存失败');
                }
            } catch (e) {
                console.error('批量更新失败:', e);
                alert('❌ 保存失败: ' + e.message);
            }
        }

        // 拖拽相关变量和函数
        let listDraggedElement = null;

        function handleListDragStart(e) {
            listDraggedElement = e.target.closest('.list-item');
            e.dataTransfer.effectAllowed = 'move';
            listDraggedElement.style.opacity = '0.4';
        }

        function handleListDragOver(e) {
            if (e.preventDefault) {
                e.preventDefault();
            }
            e.dataTransfer.dropEffect = 'move';

            const targetItem = e.target.closest('.list-item');
            if (targetItem && targetItem !== listDraggedElement) {
                const container = targetItem.closest('.list-content');
                const allItems = Array.from(container.querySelectorAll('.list-item'));
                const draggedIndex = allItems.indexOf(listDraggedElement);
                const targetIndex = allItems.indexOf(targetItem);

                if (draggedIndex < targetIndex) {
                    targetItem.parentNode.insertBefore(listDraggedElement, targetItem.nextSibling);
                } else {
                    targetItem.parentNode.insertBefore(listDraggedElement, targetItem);
                }
            }

            return false;
        }

        function handleListDrop(e) {
            if (e.stopPropagation) {
                e.stopPropagation();
            }
            return false;
        }

        function handleListDragEnd(e) {
            if (listDraggedElement) {
                listDraggedElement.style.opacity = '1';
            }

            // 更新所有项的data-index
            const container = listDraggedElement.closest('.list-content');
            const allItems = container.querySelectorAll('.list-item');
            allItems.forEach((item, index) => {
                item.setAttribute('data-index', index);
            });
        }

        // 添加新工作任务
        async function addNewListItem(button) {
            const listType = button.closest('.list-container').getAttribute('data-list-type');
            console.log('🔍 addNewListItem - listType:', listType);
            const taskTitle = prompt('请输入新的' + listType + '：');
            if (!taskTitle || taskTitle.trim() === '') {
                return;
            }

            try {
                const token = localStorage.getItem('token');
                let apiUrl, requestBody;

                // 根据类别类型选择不同的API
                if (listType === '工作') {
                    // 工作任务使用 plan API
                    apiUrl = '/api/plan/add';
                    requestBody = {
                        title: taskTitle.trim(),
                        description: '',
                        priority: 'medium',
                        status: 'pending'
                    };
                    console.log('✅ 使用工作API:', apiUrl);
                } else {
                    // 其他子类别使用 record API
                    apiUrl = '/api/record/add';
                    requestBody = {
                        title: taskTitle.trim(),
                        subcategory_name: listType
                    };
                    console.log('✅ 使用记录API:', apiUrl, '子类别:', listType);
                }

                const response = await fetch(apiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? {'Authorization': 'Bearer ' + token} : {})
                    },
                    body: JSON.stringify(requestBody)
                });

                if (response.ok) {
                    alert('✅ 添加成功');
                    // 重新加载页面以显示新任务
                    location.reload();
                } else {
                    const error = await response.text();
                    console.error('添加任务失败:', error);
                    alert('❌ 添加失败');
                }
            } catch (e) {
                console.error('添加任务失败:', e);
                alert('❌ 添加失败: ' + e.message);
            }
        }

        // 完成工作任务
        async function completeListItem(taskId, circleElement) {
            if (!taskId) {
                alert('❌ 无效的任务ID');
                return;
            }

            if (!confirm('确认完成这项工作吗？')) {
                return;
            }

            try {
                const token = localStorage.getItem('token');
                // 获取列表类型
                const listContainer = circleElement.closest('.list-container');
                const listType = listContainer ? listContainer.getAttribute('data-list-type') : '工作';

                let apiUrl, requestBody;

                // 根据类别类型选择不同的API
                if (listType === '工作') {
                    // 工作任务使用 plan API
                    apiUrl = '/api/plan/update';
                    requestBody = {
                        id: taskId,
                        status: 'completed'
                    };
                } else {
                    // 其他子类别使用 record API
                    apiUrl = '/api/record/update';
                    requestBody = {
                        record_id: taskId,
                        status: 'completed'
                    };
                }

                const response = await fetch(apiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? {'Authorization': 'Bearer ' + token} : {})
                    },
                    body: JSON.stringify(requestBody)
                });

                if (response.ok) {
                    // 隐藏该任务项（添加淡出动画）
                    const taskItem = circleElement.closest('.list-item');
                    taskItem.style.transition = 'opacity 0.3s';
                    taskItem.style.opacity = '0';
                    setTimeout(() => {
                        taskItem.style.display = 'none';
                    }, 300);
                } else {
                    const error = await response.text();
                    console.error('完成任务失败:', error);
                    alert('❌ 操作失败');
                }
            } catch (e) {
                console.error('完成任务失败:', e);
                alert('❌ 操作失败: ' + e.message);
            }
        }

        // 编辑列表项
        function editListItem(taskId, currentTitle, buttonElement) {
            if (!taskId) {
                alert('❌ 无效的任务ID');
                return;
            }

            // 获取列表类型
            const listContainer = buttonElement.closest('.list-container');
            const listType = listContainer ? listContainer.getAttribute('data-list-type') : '';

            // 创建编辑对话框
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            `;

            modal.innerHTML = `
                <div style="background: #1e1e1e; padding: 24px; border-radius: 12px; width: 90%; max-width: 500px;">
                    <h3 style="margin: 0 0 20px 0; color: #fff;">编辑内容</h3>
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; margin-bottom: 8px; color: #aaa;">内容</label>
                        <textarea id="editListItemContent" rows="4" style="width: 100%; padding: 10px; border: 1px solid #444; border-radius: 6px; background: #2a2a2a; color: #fff; font-size: 14px; resize: vertical;">${currentTitle}</textarea>
                    </div>
                    <div style="display: flex; gap: 12px; justify-content: flex-end;">
                        <button onclick="this.closest('[style*=fixed]').remove()" style="padding: 10px 20px; border: 1px solid #444; border-radius: 6px; background: #2a2a2a; color: #fff; cursor: pointer;">取消</button>
                        <button onclick="saveEditedListItem(${taskId}, '${listType}')" style="padding: 10px 20px; border: none; border-radius: 6px; background: #10a37f; color: #fff; cursor: pointer;">保存</button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            // 点击背景关闭
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                }
            });

            // 聚焦到输入框
            setTimeout(() => {
                const textarea = document.getElementById('editListItemContent');
                textarea.focus();
                textarea.setSelectionRange(textarea.value.length, textarea.value.length);
            }, 100);
        }

        // 保存编辑后的列表项
        async function saveEditedListItem(taskId, listType) {
            const newContent = document.getElementById('editListItemContent').value.trim();

            if (!newContent) {
                alert('❌ 内容不能为空');
                return;
            }

            try {
                const token = localStorage.getItem('token');
                let apiUrl, requestBody;

                // 根据类别类型选择不同的API
                if (listType === '工作') {
                    // 工作任务使用 plan API
                    apiUrl = '/api/plan/update';
                    requestBody = {
                        id: taskId,
                        title: newContent
                    };
                } else {
                    // 其他子类别使用 record API
                    apiUrl = '/api/record/update';
                    requestBody = {
                        record_id: taskId,
                        title: newContent
                    };
                }

                const response = await fetch(apiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? {'Authorization': 'Bearer ' + token} : {})
                    },
                    body: JSON.stringify(requestBody)
                });

                if (response.ok) {
                    // 关闭对话框
                    document.querySelector('[style*="position: fixed"]').remove();
                    // 重新加载页面以显示更新后的数据
                    alert('✅ 保存成功');
                    location.reload();
                } else {
                    const error = await response.text();
                    console.error('保存失败:', error);
                    alert('❌ 保存失败');
                }
            } catch (e) {
                console.error('保存失败:', e);
                alert('❌ 保存失败: ' + e.message);
            }
        }

        // 编辑工作计划
        function editWorkPlan(planId, title, description, deadline, priority) {
            // 创建编辑对话框
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            `;

            modal.innerHTML = `
                <div style="background: #1e1e1e; padding: 24px; border-radius: 12px; width: 90%; max-width: 500px; max-height: 80vh; overflow-y: auto;">
                    <h3 style="margin: 0 0 20px 0; color: #fff;">编辑工作计划</h3>
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; margin-bottom: 8px; color: #aaa;">标题</label>
                        <input type="text" id="editPlanTitle" value="${title}" style="width: 100%; padding: 10px; border: 1px solid #444; border-radius: 6px; background: #2a2a2a; color: #fff; font-size: 14px;">
                    </div>
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; margin-bottom: 8px; color: #aaa;">描述</label>
                        <textarea id="editPlanDesc" rows="4" style="width: 100%; padding: 10px; border: 1px solid #444; border-radius: 6px; background: #2a2a2a; color: #fff; font-size: 14px; resize: vertical;">${description}</textarea>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; margin-bottom: 8px; color: #aaa;">截止日期</label>
                        <input type="date" id="editPlanDeadline" value="${deadline ? deadline.substring(0, 10) : ''}" style="width: 100%; padding: 10px; border: 1px solid #444; border-radius: 6px; background: #2a2a2a; color: #fff; font-size: 14px;">
                    </div>
                    <div style="margin-bottom: 24px;">
                        <label style="display: block; margin-bottom: 8px; color: #aaa;">优先级</label>
                        <select id="editPlanPriority" style="width: 100%; padding: 10px; border: 1px solid #444; border-radius: 6px; background: #2a2a2a; color: #fff; font-size: 14px;">
                            <option value="low" ${priority === 'low' ? 'selected' : ''}>低</option>
                            <option value="medium" ${priority === 'medium' ? 'selected' : ''}>中</option>
                            <option value="high" ${priority === 'high' ? 'selected' : ''}>高</option>
                            <option value="urgent" ${priority === 'urgent' ? 'selected' : ''}>紧急</option>
                        </select>
                    </div>
                    <div style="display: flex; gap: 12px; justify-content: flex-end;">
                        <button onclick="this.closest('[style*=fixed]').remove()" style="padding: 10px 20px; border: 1px solid #444; border-radius: 6px; background: #2a2a2a; color: #fff; cursor: pointer;">取消</button>
                        <button onclick="saveEditedPlan(${planId})" style="padding: 10px 20px; border: none; border-radius: 6px; background: #10a37f; color: #fff; cursor: pointer;">保存</button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            // 点击背景关闭
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                }
            });
        }

        // 保存编辑后的工作计划
        async function saveEditedPlan(planId) {
            const title = document.getElementById('editPlanTitle').value.trim();
            const description = document.getElementById('editPlanDesc').value.trim();
            const deadline = document.getElementById('editPlanDeadline').value;
            const priority = document.getElementById('editPlanPriority').value;

            if (!title) {
                alert('请输入标题');
                return;
            }

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
                        title,
                        description,
                        deadline: deadline || null,
                        priority
                    })
                });

                if (response.ok) {
                    // 关闭对话框
                    document.querySelector('[style*="position: fixed"]').remove();
                    // 重新加载列表
                    loadWorkPlans();
                    alert('✅ 保存成功');
                } else {
                    const error = await response.text();
                    console.error('保存失败:', error);
                    alert('❌ 保存失败');
                }
            } catch (e) {
                console.error('保存工作计划失败:', e);
                alert('❌ 保存失败: ' + e.message);
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
                            <div style="color:#333; font-size:15px; line-height:1.6; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">
                                ${record.content}
                            </div>
                        </div>
                        <div style="display:flex; flex-direction:column; gap:8px; align-items:flex-end; margin-left:10px;">
                            <span style="background:#e7f3ff; color:#0056b3; padding:4px 12px; border-radius:12px; font-size:12px; font-weight:600; white-space:nowrap;">
                                ✓ ${record.status}
                            </span>
                            <button class="plan-btn plan-btn-reminder" onclick="createReminderFromRecord('${record.content.replace(/'/g, "\\'")}', '${record.deadline || ''}')">
                                ⏰ 提醒
                            </button>
                        </div>
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
            max-width: 100%;
            width: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 30px 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }

        @media (min-width: 1920px) {
            .container {
                max-width: 1800px;
            }
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

        .btn-share {
            background: #17a2b8;
            color: white;
        }

        .btn-share:hover {
            background: #138496;
        }

        /* 好友选择弹窗样式 */
        .share-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 10000;
            align-items: center;
            justify-content: center;
        }

        .share-modal.active {
            display: flex;
        }

        .share-modal-content {
            background: white;
            border-radius: 16px;
            padding: 30px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }

        .share-modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .share-modal-header h2 {
            font-size: 20px;
            color: #333;
        }

        .share-modal-close {
            background: none;
            border: none;
            font-size: 28px;
            cursor: pointer;
            color: #999;
            line-height: 1;
        }

        .share-modal-close:hover {
            color: #333;
        }

        .friend-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .friend-item {
            display: flex;
            align-items: center;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .friend-item:hover {
            border-color: #667eea;
            background: #f8f9fa;
        }

        .friend-item.selected {
            border-color: #667eea;
            background: #e3f2fd;
        }

        .friend-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            margin-right: 12px;
        }

        .friend-info {
            flex: 1;
        }

        .friend-name {
            font-size: 15px;
            font-weight: 600;
            color: #333;
        }

        .friend-status {
            font-size: 12px;
            color: #999;
        }

        .share-modal-footer {
            margin-top: 20px;
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }

        .share-modal-footer button {
            padding: 10px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
        }

        .share-modal-footer .btn-cancel {
            background: #e0e0e0;
            color: #666;
        }

        .share-modal-footer .btn-cancel:hover {
            background: #d0d0d0;
        }

        .share-modal-footer .btn-confirm {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .share-modal-footer .btn-confirm:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .share-modal-footer .btn-confirm:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
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
        <a href="/ai/" class="back-link">← 返回主页</a>
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

    <!-- 好友选择弹窗 -->
    <div id="shareModal" class="share-modal">
        <div class="share-modal-content">
            <div class="share-modal-header">
                <h2>📤 分享图片给好友</h2>
                <button class="share-modal-close" onclick="closeShareModal()">×</button>
            </div>
            <div id="shareFileName" style="margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 8px; font-size: 14px; color: #666;">
                正在分享：<span id="shareFileNameText" style="color: #333; font-weight: 600;"></span>
            </div>
            <div id="friendList" class="friend-list">
                <div style="text-align: center; padding: 20px; color: #999;">正在加载好友列表...</div>
            </div>
            <div class="share-modal-footer">
                <button class="btn-cancel" onclick="closeShareModal()">取消</button>
                <button class="btn-confirm" id="confirmShareBtn" onclick="confirmShare()" disabled>确认分享</button>
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
                                <button class="btn-share" onclick="shareImage(${img.id}, '${img.original_name || img.filename}')">📤 分享</button>
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

        // 分享功能相关变量
        let currentShareImage = null;
        let selectedFriendId = null;

        // 打开分享弹窗
        async function shareImage(imageId, imageName) {
            currentShareImage = { id: imageId, name: imageName };
            selectedFriendId = null;
            document.getElementById('shareFileNameText').textContent = imageName;
            document.getElementById('shareModal').classList.add('active');
            await loadFriendList();
        }

        // 加载好友列表
        async function loadFriendList() {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/ai/api/social/friends/list', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                const data = await response.json();
                const friendList = document.getElementById('friendList');
                if (!data.friends || data.friends.length === 0) {
                    friendList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">暂无好友，请先添加好友</div>';
                    return;
                }
                friendList.innerHTML = data.friends.map(friend => {
                    const avatarText = friend.friend_username ? friend.friend_username.charAt(0).toUpperCase() : '?';
                    return `<div class="friend-item" onclick="selectFriend(${friend.friend_id}, '${friend.friend_username}')">
                        <div class="friend-avatar">${avatarText}</div>
                        <div class="friend-info">
                            <div class="friend-name">${friend.friend_username}</div>
                            <div class="friend-status">点击选择</div>
                        </div></div>`;
                }).join('');
            } catch (error) {
                console.error('加载好友列表失败:', error);
                document.getElementById('friendList').innerHTML = '<div style="text-align: center; padding: 20px; color: #f44336;">加载失败，请重试</div>';
            }
        }

        // 选择好友
        function selectFriend(friendId, friendName) {
            selectedFriendId = friendId;
            document.querySelectorAll('.friend-item').forEach(item => item.classList.remove('selected'));
            event.target.closest('.friend-item').classList.add('selected');
            document.getElementById('confirmShareBtn').disabled = false;
        }

        // 确认分享
        async function confirmShare() {
            if (!selectedFriendId || !currentShareImage) {
                alert('请选择要分享的好友');
                return;
            }
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/ai/api/social/messages/send', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify({
                        receiver_id: selectedFriendId,
                        content: `分享了图片：${currentShareImage.name}`,
                        message_type: 'image',
                        image_id: currentShareImage.id,
                        file_id: null
                    })
                });
                const result = await response.json();
                if (result.success) {
                    alert('分享成功！');
                    closeShareModal();
                } else {
                    alert('分享失败: ' + (result.message || '未知错误'));
                }
            } catch (error) {
                console.error('分享失败:', error);
                alert('分享失败，请重试');
            }
        }

        // 关闭分享弹窗
        function closeShareModal() {
            document.getElementById('shareModal').classList.remove('active');
            currentShareImage = null;
            selectedFriendId = null;
            document.getElementById('confirmShareBtn').disabled = true;
        }

        // 按Esc关闭模态框
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeModal();
            }
        });

        // 开机自检逻辑 (调试用)
        window.addEventListener('load', function() {
            setTimeout(function() {
                // alert('Web端代码已更新v3'); 

                if (window.FlutterApp) {
                    // alert('✅ FlutterApp通信桥接成功');
                } else {
                    // alert('⚠️ 未检测到FlutterApp (如果是手机端则有问题)');
                }
            }, 1000);
        });
    </script>
</body>
</html>'''
    
    def log_message(self, format, *args):
        """日志"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format%args}")

def run_server(port=8000):
    """运行服务器"""
    # ✅ 启用提醒调度器和 WebSocket 推送
    print("🚀 正在启动提醒调度器和 WebSocket 服务器...")
    scheduler = get_global_scheduler(db_manager=db_manager)
    scheduler.start()
    print("✅ 提醒调度器已启动（30秒检查间隔）")

    # 启动 WebSocket 服务器
    if scheduler.ws_server:
        scheduler.ws_server.start()
        print("✅ WebSocket 服务器已启动在端口 8001")
    else:
        print("⚠️ WebSocket 服务器未初始化")

    server = HTTPServer(('', port), AssistantHandler)

    print(f"\n{'='*60}")
    print(f"🤖 个人助手系统 - Web版")
    print(f"{'='*60}")
    print(f"\n✅ HTTP 服务器: http://localhost:{port}")
    print(f"✅ WebSocket 服务器: ws://localhost:8001")
    print(f"✅ 提醒推送: 已启用")
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
