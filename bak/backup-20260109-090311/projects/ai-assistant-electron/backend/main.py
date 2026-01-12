#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Personal Assistant - Python后端启动入口
Electron子进程版本，使用SQLite数据库
"""

import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import socket

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

from sqlite_manager import SQLiteManager
from user_manager import UserManager
from ai_chat_assistant import AIAssistant


def get_free_port():
    """获取可用端口"""
    # 优先使用环境变量中的端口
    if 'BACKEND_PORT' in os.environ:
        return int(os.environ['BACKEND_PORT'])

    # 否则自动分配
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class AIAssistantHandler(BaseHTTPRequestHandler):
    """简化版HTTP请求处理器"""

    # 类级别的共享实例
    db_manager = None
    user_manager = None
    ai_assistant = None

    def log_message(self, format, *args):
        """重写日志输出"""
        sys.stderr.write(f"[{self.log_date_time_string()}] {format%args}\n")

    def do_OPTIONS(self):
        """处理CORS预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def send_json_response(self, data, status=200):
        """发送JSON响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def get_current_user(self):
        """从Authorization header获取当前用户"""
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header[7:]  # 去掉 "Bearer "
        result = self.user_manager.verify_token(token)

        if result['success']:
            return result['user_id']
        return None

    def require_auth(self):
        """要求认证，返回user_id或None"""
        user_id = self.get_current_user()
        if not user_id:
            self.send_json_response({'success': False, 'message': '未授权'}, 401)
        return user_id

    def do_GET(self):
        """处理GET请求"""
        parsed = urlparse(self.path)
        path = parsed.path

        # API路由
        if path == '/api/plans':
            self.handle_get_plans()
        elif path == '/api/reminders':
            self.handle_get_reminders()
        elif path == '/api/user/profile':
            self.handle_get_profile()
        elif path == '/api/chats':
            self.handle_get_chats()
        elif path == '/api/chat/history':
            self.handle_get_chat_history()
        else:
            self.send_json_response({'success': False, 'message': 'Not Found'}, 404)

    def do_POST(self):
        """处理POST请求"""
        path = self.path

        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body.decode('utf-8')) if body else {}
        except:
            data = {}

        # API路由
        if path == '/api/auth/register':
            self.handle_register(data)
        elif path == '/api/auth/login':
            self.handle_login(data)
        elif path == '/api/auth/logout':
            self.handle_logout(data)
        elif path == '/api/auth/verify':
            self.handle_verify_token(data)
        elif path == '/api/ai/chat':
            self.handle_chat(data)
        elif path == '/api/ai/clear':
            self.handle_clear_conversation(data)
        elif path == '/api/plan/add':
            self.handle_add_plan(data)
        elif path == '/api/plan/update':
            self.handle_update_plan(data)
        elif path == '/api/plan/delete':
            self.handle_delete_plan(data)
        elif path == '/api/reminder/add':
            self.handle_add_reminder(data)
        elif path == '/api/reminder/delete':
            self.handle_delete_reminder(data)
        elif path == '/api/user/change-password':
            self.handle_change_password(data)
        else:
            self.send_json_response({'success': False, 'message': 'Not Found'}, 404)

    # === 认证相关 ===
    def handle_register(self, data):
        """用户注册"""
        username = data.get('username', '')
        password = data.get('password', '')
        phone = data.get('phone', '')

        result = self.user_manager.register(username, password, phone)
        self.send_json_response(result)

    def handle_login(self, data):
        """用户登录"""
        username = data.get('username', '')
        password = data.get('password', '')

        result = self.user_manager.login(username, password)
        self.send_json_response(result)

    def handle_logout(self, data):
        """退出登录"""
        user_id = self.get_current_user()
        if not user_id:
            self.send_json_response({'success': False, 'message': '未登录'}, 401)
            return

        auth_header = self.headers.get('Authorization', '')
        token = auth_header[7:] if auth_header.startswith('Bearer ') else ''

        result = self.user_manager.logout(token)
        self.send_json_response(result)

    def handle_verify_token(self, data):
        """验证token"""
        user_id = self.get_current_user()
        if user_id:
            self.send_json_response({'success': True, 'user_id': user_id})
        else:
            self.send_json_response({'success': False, 'message': 'Token无效'}, 401)

    # === AI聊天相关 ===
    def handle_chat(self, data):
        """AI聊天"""
        user_id = self.require_auth()
        if not user_id:
            return

        message = data.get('message', '')
        if not message:
            self.send_json_response({'success': False, 'message': '消息不能为空'})
            return

        try:
            response = self.ai_assistant.chat(message, user_id=user_id)
            self.send_json_response({'success': True, **response})
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'聊天失败: {str(e)}'})

    def handle_clear_conversation(self, data):
        """清空对话历史"""
        user_id = self.require_auth()
        if not user_id:
            return

        try:
            self.ai_assistant.clear_conversation(user_id)
            self.send_json_response({'success': True, 'message': '对话历史已清空'})
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'清空失败: {str(e)}'})

    def handle_get_chats(self):
        """获取最近聊天记录"""
        user_id = self.require_auth()
        if not user_id:
            return

        try:
            messages = self.ai_assistant.memory.get_recent_messages(limit=100, user_id=user_id)
            self.send_json_response({'success': True, 'messages': messages})
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'获取失败: {str(e)}'})

    def handle_get_chat_history(self):
        """获取24小时聊天历史"""
        user_id = self.require_auth()
        if not user_id:
            return

        try:
            messages = self.ai_assistant.memory.get_messages_last_24h(user_id)
            self.send_json_response({'success': True, 'messages': messages})
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'获取失败: {str(e)}'})

    # === 工作计划相关 ===
    def handle_get_plans(self):
        """获取工作计划列表"""
        user_id = self.require_auth()
        if not user_id:
            return

        try:
            plans = self.ai_assistant.planner.list_plans(user_id=user_id, status='all')
            self.send_json_response({'success': True, 'plans': plans})
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'获取失败: {str(e)}'})

    def handle_add_plan(self, data):
        """添加工作计划"""
        user_id = self.require_auth()
        if not user_id:
            return

        title = data.get('title', '')
        content = data.get('content', '')
        priority = data.get('priority', 'medium')
        due_date = data.get('due_date')

        try:
            plan_id = self.ai_assistant.planner.create_plan(
                title=title,
                content=content,
                priority=priority,
                due_date=due_date,
                user_id=user_id
            )
            self.send_json_response({'success': True, 'plan_id': plan_id})
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'添加失败: {str(e)}'})

    def handle_update_plan(self, data):
        """更新计划状态"""
        user_id = self.require_auth()
        if not user_id:
            return

        plan_id = data.get('plan_id')
        status = data.get('status')

        try:
            self.ai_assistant.planner.update_plan_status(plan_id, status, user_id=user_id)
            self.send_json_response({'success': True})
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'更新失败: {str(e)}'})

    def handle_delete_plan(self, data):
        """删除计划"""
        user_id = self.require_auth()
        if not user_id:
            return

        plan_id = data.get('plan_id')

        try:
            self.ai_assistant.planner.delete_plan(plan_id, user_id=user_id)
            self.send_json_response({'success': True})
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'删除失败: {str(e)}'})

    # === 提醒相关 ===
    def handle_get_reminders(self):
        """获取提醒列表"""
        user_id = self.require_auth()
        if not user_id:
            return

        try:
            reminders = self.ai_assistant.reminder.get_user_reminders(user_id, status='all')
            self.send_json_response({'success': True, 'reminders': reminders})
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'获取失败: {str(e)}'})

    def handle_add_reminder(self, data):
        """添加提醒"""
        user_id = self.require_auth()
        if not user_id:
            return

        content = data.get('content', '')
        remind_time = data.get('remind_time', '')

        try:
            reminder_id = self.ai_assistant.reminder.create_reminder(
                content=content,
                remind_time=remind_time,
                user_id=user_id
            )
            self.send_json_response({'success': True, 'reminder_id': reminder_id})
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'添加失败: {str(e)}'})

    def handle_delete_reminder(self, data):
        """删除提醒"""
        user_id = self.require_auth()
        if not user_id:
            return

        reminder_id = data.get('reminder_id')

        try:
            self.ai_assistant.reminder.delete_reminder(reminder_id, user_id=user_id)
            self.send_json_response({'success': True})
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'删除失败: {str(e)}'})

    # === 用户相关 ===
    def handle_get_profile(self):
        """获取用户信息"""
        user_id = self.require_auth()
        if not user_id:
            return

        try:
            user = self.user_manager.get_user_by_id(user_id)
            if user:
                # 移除敏感信息
                user.pop('password', None)
                user.pop('password_hash', None)
                self.send_json_response({'success': True, 'user': user})
            else:
                self.send_json_response({'success': False, 'message': '用户不存在'}, 404)
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'获取失败: {str(e)}'})

    def handle_change_password(self, data):
        """修改密码"""
        user_id = self.require_auth()
        if not user_id:
            return

        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')

        result = self.user_manager.change_password(user_id, old_password, new_password)
        self.send_json_response(result)


def main():
    """主函数"""
    print("=" * 50)
    print("AI Personal Assistant - Python Backend")
    print("=" * 50)

    # 获取端口
    port = get_free_port()

    # 初始化数据库管理器（SQLite）
    data_dir = os.path.expanduser('~/Library/Application Support/AIAssistant')
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, 'data.db')

    print(f"数据库路径: {db_path}")

    db_manager = SQLiteManager(db_path)

    # 初始化管理器（类级别共享）
    AIAssistantHandler.db_manager = db_manager
    AIAssistantHandler.user_manager = UserManager(db_manager)
    AIAssistantHandler.ai_assistant = AIAssistant()

    # 输出端口号给Electron（必须使用flush=True）
    print(f"SERVER_PORT:{port}", flush=True)

    # 启动HTTP服务器
    server = HTTPServer(('127.0.0.1', port), AIAssistantHandler)
    print(f"✅ 服务器启动成功: http://127.0.0.1:{port}")
    print(f"按Ctrl+C停止服务器")
    print("=" * 50)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        server.shutdown()
        db_manager.close()
        print("✅ 服务器已关闭")


if __name__ == '__main__':
    main()
