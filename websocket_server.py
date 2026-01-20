#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WebSocket 服务器 - 用于推送提醒通知到移动端"""

import asyncio
import websockets
import json
from datetime import datetime
import threading

class WebSocketServer:
    """WebSocket 服务器，用于实时推送提醒"""

    def __init__(self, host='0.0.0.0', port=8001):
        self.host = host
        self.port = port
        self.clients = {}  # {user_id: set(websocket_connections)}
        self.server = None
        self.loop = None
        self.thread = None

    def start(self):
        """在新线程中启动 WebSocket 服务器"""
        if self.thread and self.thread.is_alive():
            print(f"⚠️ WebSocket 服务器已在运行，跳过重复启动")
            return

        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        print(f"✅ WebSocket 服务器已启动在 {self.host}:{self.port}")

    def _run_server(self):
        """运行 WebSocket 服务器"""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            start_server = websockets.serve(
                self._handle_client,
                self.host,
                self.port
            )

            self.loop.run_until_complete(start_server)
            print(f"✅ WebSocket 服务器正在监听 {self.host}:{self.port}")
            self.loop.run_forever()
        except Exception as e:
            print(f"❌ WebSocket 服务器异常: {e}")
            import traceback
            traceback.print_exc()

    async def _handle_client(self, websocket, path):
        """处理客户端连接"""
        user_id = None
        try:
            # 等待客户端发送认证信息
            auth_message = await websocket.recv()
            auth_data = json.loads(auth_message)

            if auth_data.get('type') == 'auth':
                user_id = auth_data.get('user_id')
                token = auth_data.get('token')

                # TODO: 验证 token 的有效性
                # 这里简化处理，实际应该验证 token

                if user_id:
                    # 注册客户端
                    if user_id not in self.clients:
                        self.clients[user_id] = set()
                    self.clients[user_id].add(websocket)

                    print(f"✅ 用户 {user_id} 已连接 WebSocket")

                    # 发送连接成功消息
                    await websocket.send(json.dumps({
                        'type': 'connected',
                        'message': '连接成功'
                    }))

                    # 保持连接，等待消息或断开
                    async for message in websocket:
                        # 处理客户端发来的消息（如心跳）
                        data = json.loads(message)
                        if data.get('type') == 'ping':
                            await websocket.send(json.dumps({'type': 'pong'}))

        except websockets.exceptions.ConnectionClosed:
            print(f"⚠️ 用户 {user_id} 断开连接")
        except Exception as e:
            print(f"❌ WebSocket 错误: {e}")
        finally:
            # 清理连接
            if user_id and user_id in self.clients:
                self.clients[user_id].discard(websocket)
                if not self.clients[user_id]:
                    del self.clients[user_id]

    def send_reminder(self, user_id, reminder_data):
        """发送提醒到指定用户的所有连接"""
        # 转换为字符串以匹配 self.clients 的键类型
        user_id = str(user_id)
        print(f"🔍 DEBUG send_reminder: user_id={user_id}, type={type(user_id)}")
        print(f"🔍 DEBUG self.clients.keys()={list(self.clients.keys())}")

        if not self.loop:
            print("⚠️ WebSocket 服务器未启动")
            return False

        if user_id not in self.clients or not self.clients[user_id]:
            print(f"⚠️ 用户 {user_id} 没有活动的 WebSocket 连接")
            print(f"🔍 DEBUG: user_id in self.clients = {user_id in self.clients}")
            if user_id in self.clients:
                print(f"🔍 DEBUG: len(self.clients[user_id]) = {len(self.clients[user_id])}")
            return False

        # 在 WebSocket 的事件循环中发送消息
        asyncio.run_coroutine_threadsafe(
            self._send_to_user(user_id, reminder_data),
            self.loop
        )
        return True

    async def _send_to_user(self, user_id, reminder_data):
        """异步发送消息到用户的所有连接"""
        if user_id not in self.clients:
            return

        message = json.dumps({
            'type': 'reminder',
            'data': reminder_data,
            'timestamp': datetime.now().isoformat()
        })

        # 发送到该用户的所有连接
        disconnected = set()
        for websocket in self.clients[user_id]:
            try:
                await websocket.send(message)
                print(f"✅ 已推送提醒到用户 {user_id}")
            except Exception as e:
                print(f"❌ 发送失败: {e}")
                disconnected.add(websocket)

        # 清理断开的连接
        for websocket in disconnected:
            self.clients[user_id].discard(websocket)

    def stop(self):
        """停止 WebSocket 服务器"""
        if self.loop:
            self.loop.stop()
        print("⏹️ WebSocket 服务器已停止")


# 全局实例
_global_ws_server = None

def get_websocket_server():
    """获取全局 WebSocket 服务器实例"""
    global _global_ws_server
    if _global_ws_server is None:
        _global_ws_server = WebSocketServer()
    return _global_ws_server
